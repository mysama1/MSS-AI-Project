#!/usr/bin/env python3
"""
DEV-004: 自动化测试流水线 — cron触发→21轮回测→报告→告警
"""
import sys, os, json, time, subprocess
from pathlib import Path
from datetime import datetime

HERE = Path(__file__).resolve().parent
PY = sys.executable
WORKSPACE = Path(os.environ.get('MSS_WORKSPACE', r'E:\QClaw-Data\workspace'))
BENCHMARK_RUNNER = HERE / "benchmark_runner.py"
JUDGE_PY = WORKSPACE / "engineering-problems" / "tests" / "judge.py"
GOLDEN = WORKSPACE / "engineering-problems" / "tests" / "golden_answers.json"
OUTDIR = WORKSPACE / "benchmark_results"
ALERT_THRESHOLD = 95.0

def green(s): return f"\033[32m{s}\033[0m"
def red(s): return f"\033[31m{s}\033[0m"
def yellow(s): return f"\033[33m{s}\033[0m"
def cyan(s): return f"\033[36m{s}\033[0m"

def run(cmd, timeout=300):
    """Run a command, return (returncode, stdout, stderr)."""
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout,
                          encoding='utf-8', errors='replace')
        return r.returncode, r.stdout, r.stderr
    except subprocess.TimeoutExpired:
        return -1, "", "TIMEOUT"
    except Exception as e:
        return -1, "", str(e)

def main():
    timestamp = datetime.now().strftime('%Y-%m-%dT%H:%M:%S')
    datestr = datetime.now().strftime('%Y%m%d')
    
    print(cyan(f"\n{'='*60}"))
    print(cyan(f"  MSS Benchmark Pipeline  |  {timestamp}"))
    print(cyan(f"{'='*60}\n"))

    os.makedirs(OUTDIR, exist_ok=True)
    
    results = {
        "timestamp": timestamp,
        "date": datestr,
        "stages": {}
    }

    # ── Stage 0: Self-test ──
    print(yellow("[0] Self-test — validate check engine"))
    rc, out, err = run([PY, str(BENCHMARK_RUNNER), "--self-test", "--output",
                        str(OUTDIR / f"selftest_{datestr}.json")], timeout=60)
    selftest_ok = rc == 0 and "PASS" in out
    results["stages"]["selftest"] = {"passed": selftest_ok, "exit_code": rc}
    if selftest_ok:
        print(green("  Self-test PASSED"))
    else:
        print(red(f"  Self-test FAILED (exit {rc})"))
        if err:
            print(f"  {err[:200]}")

    # ── Stage 1: Run benchmark ──
    print(yellow("\n[1] Run benchmark — 21 rounds with LLM"))
    bench_start = time.time()
    rc, out, err = run([PY, str(BENCHMARK_RUNNER), "--suite", "all",
                        "--run", "--report", "--output",
                        str(OUTDIR / f"benchmark_{datestr}.json")], timeout=600)
    bench_elapsed = time.time() - bench_start
    results["stages"]["benchmark"] = {"exit_code": rc, "elapsed_s": round(bench_elapsed, 1)}
    
    if rc == 0:
        print(green(f"  Benchmark completed ({bench_elapsed:.1f}s)"))
        # Try to parse scores from output
        try:
            bench_data = json.loads(out) if out.strip().startswith('{') else {}
        except:
            bench_data = {}
        results["stages"]["benchmark"]["data"] = bench_data
    else:
        print(red(f"  Benchmark FAILED (exit {rc})"))
    
    # ── Stage 2: Judge scoring ──
    print(yellow("\n[2] LLM Judge — score against golden answers"))
    score = None
    
    if os.path.exists(JUDGE_PY) and os.path.exists(GOLDEN):
        rc, out, err = run([PY, str(JUDGE_PY), "--input",
                           str(OUTDIR / f"benchmark_{datestr}.json"),
                           "--golden", str(GOLDEN)], timeout=300)
        results["stages"]["judge"] = {"exit_code": rc}
        
        # Extract score from output
        for line in out.split('\n'):
            if 'score' in line.lower() or 'average' in line.lower():
                import re
                match = re.search(r'(\d+\.?\d*)', line)
                if match:
                    score = float(match.group(1))
                    break
        
        if score is not None:
            results["stages"]["judge"]["score"] = score
            color = green if score >= ALERT_THRESHOLD else red
            print(f"  Score: {color(score)}% (threshold: {ALERT_THRESHOLD}%)")
            if score < ALERT_THRESHOLD:
                print(red(f"  ⚠️ ALERT: Score below {ALERT_THRESHOLD}% threshold!"))
        else:
            print(yellow(f"  Judge completed but score not parsed"))
    else:
        results["stages"]["judge"] = {"error": f"Missing {JUDGE_PY} or {GOLDEN}"}
        print(yellow(f"  Judge skipped — missing files"))
    
    # ── Stage 3: Generate report ──
    print(yellow("\n[3] Generate HTML report"))
    try:
        from report_generator import generate_html
        html = generate_html(results, f"MSS Benchmark — {datestr}")
        html_path = OUTDIR / f"benchmark_report_{datestr}.html"
        with open(html_path, 'w', encoding='utf-8') as f:
            f.write(html)
        results["stages"]["report"] = {"html": str(html_path), "generated": True}
        print(green(f"  HTML report: {html_path}"))
    except ImportError:
        sys.path.insert(0, str(HERE))
        try:
            from report_generator import generate_html
            html = generate_html(results, f"MSS Benchmark — {datestr}")
            html_path = OUTDIR / f"benchmark_report_{datestr}.html"
            with open(html_path, 'w', encoding='utf-8') as f:
                f.write(html)
            results["stages"]["report"] = {"html": str(html_path), "generated": True}
            print(green(f"  HTML report: {html_path}"))
        except Exception as e:
            results["stages"]["report"] = {"error": str(e)}
            print(yellow(f"  Report generation skipped: {e}"))
    
    # ── Stage 4: Alert ──
    alert = False
    if score is not None and score < ALERT_THRESHOLD:
        alert = True
        alert_msg = f"MSS Benchmark Alert: score {score}% below threshold {ALERT_THRESHOLD}%"
        alert_file = OUTDIR / f"ALERT_{datestr}.txt"
        with open(alert_file, 'w', encoding='utf-8') as f:
            f.write(f"{alert_msg}\n")
            f.write(f"Timestamp: {timestamp}\n")
            f.write(f"Score: {score}%\n")
            f.write(f"Report: {html_path}\n")
        print(red(f"\n  ⚠️ ALERT written to: {alert_file}"))
    results["stages"]["alert"] = {"triggered": alert, "threshold": ALERT_THRESHOLD}
    
    # ── Save full results ──
    result_path = OUTDIR / f"pipeline_{datestr}.json"
    results["elapsed_total_s"] = round(time.time() - (
        time.time() - bench_elapsed - 5  # approximate
    ), 1)
    with open(result_path, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    
    # ── Final summary ──
    print(cyan(f"\n{'='*60}"))
    print(cyan(f"  PIPELINE COMPLETE"))
    print(cyan(f"{'='*60}"))
    print(f"  Self-test:  {'PASS' if selftest_ok else 'FAIL'}")
    print(f"  Benchmark:  exit={rc}")
    print(f"  Score:      {score if score else 'N/A'}%")
    if alert:
        print(red(f"  ⚠️ ALERT TRIGGERED — score < {ALERT_THRESHOLD}%"))
    else:
        print(green(f"  No alert — score OK"))
    print(f"  Results:    {result_path}")
    print()
    
    return 0 if (selftest_ok and score and score >= ALERT_THRESHOLD) else 1

if __name__ == "__main__":
    sys.exit(main())
