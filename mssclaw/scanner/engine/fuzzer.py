#!/usr/bin/env python3
"""
MSS-VDP Fuzzer v1.0
随机变异生成测试代码 → 跑所有扫描器 → 检测崩溃/假阴性/假阳性
用法: py -3.11 vdp_fuzzer.py --rounds 100
"""
import sys, os, json, subprocess, random, string, tempfile, time
from datetime import datetime
from pathlib import Path
from collections import defaultdict

SKILL_DIR = os.path.dirname(os.path.abspath(__file__))

# ── 各语言的基础代码模板 ──

TEMPLATES = {
    "python": [
        'def foo(): pass',
        'import os\nos.path.join("a","b")',
        'try:\n    x=1/0\nexcept:\n    pass',
        'with open("f.txt") as f:\n    f.read()',
        'print("hello")',
    ],
    "javascript": [
        'function foo() { return 1; }',
        'const x = await fetch("/api");',
        'try { risky(); } catch(e) {}',
        'setInterval(() => {}, 1000);',
        'new Promise((resolve) => resolve(1));',
    ],
    "go": [
        'package main\nfunc main() {}',
        'package main\nimport "os"\nfunc main() { os.Open("f.txt") }',
        'package main\nimport "net/http"\nfunc main() { http.Get("http://x.com") }',
    ],
    "ruby": [
        'def foo; end',
        'File.open("f.txt")',
        'begin; rescue => e; end',
    ],
    "php": [
        '<?php echo "hello";',
        '<?php $f = fopen("f.txt","r");',
        '<?php session_start();',
    ],
    "rust": [
        'fn main() {}',
        'fn main() { let x = 1; println!("{}", x); }',
    ],
}

# ── 变异算子 ──

MUTATIONS = [
    ("insert_bare_except", lambda c: c.replace("try:", "try:\n    risky()\nexcept:")),
    ("insert_posix_cmd", lambda c: c + "\n# os.system('ls -l')"),
    ("insert_unchecked_error", lambda c: c.replace("return", "_, _ = risky_call()\n    return")),
    ("insert_no_close", lambda c: c.replace("open(", "open('leaked.txt')\n# no close\nx = open(")),
    ("insert_eval", lambda c: c + "\neval('1+1')"),
    ("insert_sql_inject", lambda c: c + "\n# mysql_query('SELECT * FROM users WHERE name=\\'$user\\'')"),
    ("insert_at_suppress", lambda c: c + "\n# @file_get_contents('x.txt')"),
    ("insert_no_timeout", lambda c: c.replace("http.Get", "# no timeout\nresp, _ = http.Get")),
    ("insert_goroutine_leak", lambda c: c + "\n// go func() { for {} }()"),
    ("insert_ls_cmd", lambda c: c + "\n# ls /tmp"),
    ("duplicate_lines", lambda c: c + "\n" + c),
    ("add_unicode_noise", lambda c: c + "\n# 这是一段中文注释 😀 🚀"),
    ("add_long_line", lambda c: c + "x" * 300),
    ("add_null_deref", lambda c: c.replace("if", "x = nil\n# no nil check\nif")),
]

SCANNER_MAP = {
    "python": "python_script",
    "javascript": "javascript",
    "go": "go",
    "ruby": "ruby",
    "php": "php",
    "rust": "rust",
}

SCANNERS = {
    "python_script": ("vdp_scan.py", "--format", "json", ".py"),
    "javascript": ("js_scan.py", "--json", ".js"),
    "go": ("go_scan.py", "--json", ".go"),
    "ruby": ("ruby_scan.py", "--json", ".rb"),
    "php": ("php_scan.py", "--json", ".php"),
    "rust": ("rust_scan.py", "--json", ".rs"),
}


class VdpFuzzer:
    def __init__(self, rounds: int = 100):
        self.rounds = rounds
        self.results = []
        self.crashes = 0
        self.total_violations = 0
        self.seed = random.randint(1, 999999)
        random.seed(self.seed)
    
    def generate_test_case(self) -> tuple:
        """Generate a mutated test case for a random language."""
        lang = random.choice(list(TEMPLATES.keys()))
        base = random.choice(TEMPLATES[lang])
        
        # Apply 1-5 random mutations
        n_mutations = random.randint(1, 5)
        mutated = base
        applied = []
        for _ in range(n_mutations):
            mut_name, mut_fn = random.choice(MUTATIONS)
            try:
                new = mut_fn(mutated)
                if new != mutated:
                    mutated = new
                    applied.append(mut_name)
            except:
                pass
        
        return lang, mutated, applied, base
    
    def scan(self, lang: str, code: str) -> dict:
        """Run the appropriate scanner on generated code."""
        mapped = SCANNER_MAP.get(lang, lang)
        scanner_info = SCANNERS.get(mapped)
        if not scanner_info:
            return {"violations": 0, "crash": True, "error": f"No scanner for {lang}/{mapped}"}
        
        scanner, flag, ext = scanner_info[0], scanner_info[1], scanner_info[2]
        scanner_path = os.path.join(SKILL_DIR, scanner)
        
        if not os.path.exists(scanner_path):
            return {"error": f"Scanner not found: {scanner}"}
        
        # Write temp file
        tmp = tempfile.NamedTemporaryFile(suffix=ext, mode='w', encoding='utf-8', delete=False)
        try:
            tmp.write(code)
            tmp.close()
            
            r = subprocess.run(
                [sys.executable, scanner_path, tmp.name, flag],
                capture_output=True, text=True, timeout=15,
                encoding='utf-8', errors='replace',
            )
            
            violations = []
            crash = False
            error_msg = None
            
            try:
                data = json.loads(r.stdout) if r.stdout.strip() else {}
                items = data if isinstance(data, list) else [data]
                for item in items:
                    violations.extend(item.get('violations', []))
            except json.JSONDecodeError:
                # Scanner crashed or output not JSON
                crash = True
                error_msg = f"JSON parse error: {r.stdout[:100]}... stderr: {r.stderr[:100]}"
            
            if r.returncode not in (0, 1, 2) and not crash:
                crash = True
                error_msg = f"RC={r.returncode}, stderr: {r.stderr[:200]}"
            
            return {
                "violations": len(violations),
                "crash": crash,
                "error": error_msg,
                "returncode": r.returncode,
                "timeout": False,
            }
        except subprocess.TimeoutExpired:
            return {"violations": 0, "crash": True, "error": "Timeout (15s)", "timeout": True}
        except Exception as e:
            return {"violations": 0, "crash": True, "error": str(e)[:200]}
        finally:
            try:
                os.unlink(tmp.name)
            except:
                pass
    
    def run(self) -> dict:
        """Run all fuzzing rounds."""
        print(f"🎲 VDP Fuzzer — {self.rounds} rounds (seed={self.seed})")
        print("=" * 60)
        
        start_time = time.monotonic()
        lang_stats = defaultdict(lambda: {"scans": 0, "crashes": 0, "violations": 0})
        
        for i in range(self.rounds):
            lang, code, mutations, base = self.generate_test_case()
            result = self.scan(lang, code)
            
            lang_stats[lang]["scans"] += 1
            if result["crash"]:
                lang_stats[lang]["crashes"] += 1
                self.crashes += 1
            lang_stats[lang]["violations"] += result["violations"]
            self.total_violations += result["violations"]
            
            status = "💥" if result["crash"] else "✅" if result["violations"] > 0 else "·"
            self.results.append({
                "round": i + 1,
                "lang": lang,
                "mutations": mutations,
                "status": status,
                **result,
            })
            
            if (i + 1) % 20 == 0 or result["crash"]:
                print(f"  [{i+1:4d}/{self.rounds}] {status} {lang:10s} "
                      f"{result['violations']:2d}v  muts:{','.join(mutations[:2])}")
            
            if result["crash"] and result.get("error"):
                print(f"       💥 CRASH: {result['error'][:100]}")
        
        elapsed = time.monotonic() - start_time
        
        report = {
            "timestamp": datetime.now().isoformat(),
            "seed": self.seed,
            "rounds": self.rounds,
            "elapsed_sec": round(elapsed, 1),
            "total_violations": self.total_violations,
            "crashes": self.crashes,
            "crash_rate": round(self.crashes / self.rounds * 100, 1),
            "by_language": {
                lang: {
                    "scans": s["scans"],
                    "crashes": s["crashes"],
                    "violations": s["violations"],
                    "avg_violations": round(s["violations"] / max(1, s["scans"]), 1),
                    "crash_rate": round(s["crashes"] / max(1, s["scans"]) * 100, 1),
                }
                for lang, s in sorted(lang_stats.items())
            },
            "verdict": "PASS" if self.crashes == 0 else "WARN" if self.crashes <= 2 else "FAIL",
        }
        
        return report


def main():
    import argparse
    ap = argparse.ArgumentParser(description='MSS-VDP Fuzzer')
    ap.add_argument('--rounds', '-n', type=int, default=50, help='Fuzzing rounds (default: 50)')
    ap.add_argument('--seed', type=int, default=0, help='Random seed (0=random)')
    ap.add_argument('--json', action='store_true', help='JSON output')
    args = ap.parse_args()
    
    fuzzer = VdpFuzzer(rounds=args.rounds)
    if args.seed:
        fuzzer.seed = args.seed
        random.seed(args.seed)
    
    report = fuzzer.run()
    
    print("\n" + "=" * 60)
    print(f"Verdict: {report['verdict']}  |  {report['crashes']}/{report['rounds']} crashes "
          f"({report['crash_rate']}%)  |  {report['elapsed_sec']}s")
    print("\nBy language:")
    for lang, s in report["by_language"].items():
        print(f"  {lang:12s} {s['scans']:3d} scans  {s['violations']:4d}v  "
              f"avg={s['avg_violations']:.1f}  crashes={s['crashes']} ({s['crash_rate']:.0f}%)")
    
    if args.json:
        report_path = os.path.join(SKILL_DIR, '.mss', 'fuzzer_report.json')
        os.makedirs(os.path.dirname(report_path), exist_ok=True)
        with open(report_path, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        print(f"\nReport: {report_path}")
    
    sys.exit(1 if report["verdict"] == "FAIL" else 0)


if __name__ == '__main__':
    main()
