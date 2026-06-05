#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MSS-VDP Pre-Commit Static Analyzer v1.0

Zero-dependency static checks for Python projects. Covers the three most common
"normative field thermal tax escape" patterns identified in MSS engineering:

  NAMING-002  Hidden directory filtering  (regex, <1ms)
  CLI-001     Subcommand handler gaps     (regex+AST, ~5ms)
  CFLOW-003   Branch variable gaps        (AST only, ~10ms) [EXPERIMENTAL]

Usage:
  python vdp_precommit.py check <file>              → scan single file
  python vdp_precommit.py check --dir <project>     → scan all .py files
  python vdp_precommit.py check --stdin             → scan piped input
"""
import sys, os, re, ast, json, argparse
from pathlib import Path

VERSION = "1.0"

# ───────────────────────────────────────────
#  NAMING-002: Hidden directory filter check
# ───────────────────────────────────────────

_HIDDEN_ITER_PATTERNS = [
    r'os\.listdir\s*\(',
    r'\.iterdir\s*\(\s*\)',
    r'glob\.glob\s*\(',
    r'os\.walk\s*\(',
    r'os\.scandir\s*\(',
]

_FILTER_PATTERN = r'startswith\s*\(\s*[\'"]_[\'"]'


def _strip_comments(code: str) -> str:
    """Remove Python comments from code for regex scanning."""
    clean = []
    for line in code.split('\n'):
        stripped = line.strip()
        if stripped.startswith('#'):
            clean.append('')
        else:
            in_string = False
            for i, ch in enumerate(line):
                if ch in ('"', "'"):
                    in_string = not in_string
                if ch == '#' and not in_string:
                    line = line[:i]
                    break
            clean.append(line)
    return '\n'.join(clean)


def check_naming_002(code: str, filepath: str = "") -> list:
    """Check that directory iteration calls filter out underscore-prefixed entries."""
    violations = []
    lines = code.split('\n')
    for pat in _HIDDEN_ITER_PATTERNS:
        for m in re.finditer(pat, code):
            pos = m.start()
            # Look ahead 600 chars for a filter
            ahead = code[pos:pos+600]
            if re.search(_FILTER_PATTERN, ahead):
                continue
            # Check if there's an explicit ignore list
            if re.search(r'if\s+(?:not\s+)?.*startswith', ahead) or \
               re.search(r'\[.*for\s+.*\s+in\s+.*\s+if\s+not', ahead):
                continue
            line_no = code[:pos].count('\n') + 1
            violations.append({
                "rule": "NAMING-002",
                "severity": "warn",
                "loc": f"L{line_no}",
                "kind": "HIDDEN_DIR_NOT_FILTERED",
                "quote": lines[line_no-1].strip()[:120],
                "fix": "Add: if entry.startswith('_'): continue  after iteration call",
                "file": filepath
            })
    return violations


# ───────────────────────────────────────────
#  CLI-001: Subcommand definition vs handler
# ───────────────────────────────────────────

def check_cli_001(code: str, filepath: str = "") -> list:
    """Check that every argparse subcommand has a handler branch."""
    violations = []
    # Strip comments to avoid matching example code
    clean_code = _strip_comments(code)
    sub_defs = set(re.findall(r"""(?:sub|parser)\.add_parser\s*\(\s*['"](\w+)['"]""", clean_code))
    # Regex: args.xxx == 'yyy' or getattr(args,'xxx') == 'yyy'
    handlers = set()
    for m in re.finditer(r"""args\.(\w+)\s*==\s*['"](\w+)['"]""", clean_code):
        handlers.add(m.group(2))  # the value being compared
    # Also check args.cmd in {pattern} style
    for m in re.finditer(r"""(?:cmd|command|subcommand)\s*in\s*[\[({]\s*['"](\w+)['"]""", clean_code):
        handlers.add(m.group(1))
    unhandled = sub_defs - handlers
    for cmd in sorted(unhandled):
        # Find the definition line
        for m in re.finditer(rf"""(?:sub|parser)\.add_parser\s*\(\s*['"]{cmd}['"]""", code):
            line_no = code[:m.start()].count('\n') + 1
            violations.append({
                "rule": "CLI-001",
                "severity": "error",
                "loc": f"L{line_no}",
                "kind": "SUBCMD_NO_HANDLER",
                "quote": f"Subcommand '{cmd}' defined but has no handler branch",
                "fix": f"Add: elif args.cmd == '{cmd}': handler_{cmd}()",
                "file": filepath
            })
    return violations


# ───────────────────────────────────────────
#  CFLOW-003: Branch variable completeness
# ───────────────────────────────────────────

def check_cflow_003(code: str, filepath: str = "") -> list:
    """[EXPERIMENTAL] Check try/except blocks for vars assigned in try but not except."""
    violations = []
    try:
        tree = ast.parse(code)
    except SyntaxError:
        return violations

    for node in ast.walk(tree):
        if not isinstance(node, ast.Try):
            continue
        if not node.handlers:
            continue

        try_vars = set()
        for stmt in node.body:
            for child in ast.walk(stmt):
                if isinstance(child, ast.Assign):
                    for t in child.targets:
                        if isinstance(t, ast.Name):
                            try_vars.add(t.id)

        handler_vars = set()
        for handler in node.handlers:
            for child in ast.walk(handler):
                if isinstance(child, ast.Assign):
                    for t in child.targets:
                        if isinstance(t, ast.Name):
                            handler_vars.add(t.id)

        both = try_vars & handler_vars
        if both:
            violations.append({
                "rule": "CFLOW-003",
                "severity": "warn",
                "loc": f"L{node.lineno}",
                "kind": "TRY_EXCEPT_VAR_SHADOW",
                "quote": f"vars {sorted(both)} assigned in both try and except — verify completeness",
                "fix": "Ensure these vars have correct fallback values in except block",
                "file": filepath
            })

    return violations


# ───────────────────────────────────────────
#  Check runner
# ───────────────────────────────────────────

# ── CLOSURE rules (from CLOSURE-001, CLOSURE-002) ──

ARBITRARY_RATIO_PATS = [
    r'\d{2,3}%',           # e.g. 75%, 20% in text
    r'\d+\.\d%',          # e.g. 12.5%
]

def check_arbitrary_ratio(code, filepath):
    """NO_ARBITRARY_RATIO: flag percentage claims without derivation."""
    violations = []
    lines = code.split('\n')
    for i, line in enumerate(lines):
        for pat in ARBITRARY_RATIO_PATS:
            if re.search(pat, line):
                # Skip if line contains derivation keywords
                if not re.search(r'(measured|observed|computed|derived|fitted|calculated)', line, re.I):
                    violations.append({
                        'rule': 'NO_ARBITRARY_RATIO', 'rule_id': 'CLOSURE-001-R1',
                        'severity': 'warn', 'loc': f'L{i+1}',
                        'kind': 'PCT_WITHOUT_DERIVATION',
                        'quote': line.strip()[:100],
                        'fix': 'Add derivation or mark as qualitative estimate'
                    })
    return violations


def check_continuity_on_discrete(code, filepath):
    """NO_CONTINUITY_ON_DISCRETE: flag \"continuity\" arguments on discrete functions."""
    violations = []
    lines = code.split('\n')
    discrete_keywords = ['collatz', 'integer', 'discrete', 'integer-valued']
    has_discrete_context = any(kw in code.lower() for kw in discrete_keywords)
    if not has_discrete_context:
        return violations
    for i, line in enumerate(lines):
        low = line.lower()
        if 'continuity' in low or 'continuous' in low:
            # Skip negations and self-referential statements
            if re.search(r'(no|not|without)\s+(continuity|continuous)', low):
                continue
            if re.search(r'(continuity|continuous)\s+.+(no|not)', low):
                continue  # "continuity ... not available"
            if 'meaning-field' in low or 'meaning field' in low:
                continue
            violations.append({
                'rule': 'NO_CONTINUITY_ON_DISCRETE', 'rule_id': 'CLOSURE-002-R1',
                'severity': 'reject', 'loc': f'L{i+1}',
                'kind': 'CONTINUITY_ON_DISCRETE_DOMAIN',
                'quote': line.strip()[:100],
                'fix': 'Discrete maps require combinatorial arguments, not continuity'
            })
    return violations


def check_inequality_3point(code, filepath):
    """INEQUALITY_3POINT: warn if inequality claimed without test values."""
    violations = []
    lines = code.split('\n')
    has_inequality = any(re.search(r'[<>]|\\le|\\ge|\\lt|\\gt|\\leq|\\geq', l) for l in lines)
    if not has_inequality:
        return violations
    # Check if at least 3 numeric test values are present
    numeric_counts = []
    for line in lines:
        nums = re.findall(r'\b\d+\b', line)
        if nums:
            numeric_counts.extend(nums)
    # Simple heuristic: if there are inequality claims but fewer than 3 distinct
    # numeric constants that look like test values, flag it
    test_values = [int(n) for n in numeric_counts if 1 <= int(n) <= 1000]
    if len(set(test_values)) < 3:
        violations.append({
            'rule': 'INEQUALITY_3POINT_CHECK', 'rule_id': 'CLOSURE-002-R2',
            'severity': 'warn', 'loc': 'global',
            'kind': 'INSUFFICIENT_TEST_VALUES',
            'quote': f'Inequality claims present but only {len(set(test_values))} distinct test values found',
            'fix': 'Verify inequality direction with >=3 values: small, large, boundary'
        })
    return violations


def check_completeness_gate(code, filepath):
    """COMPLETENESS_GATE: flag 'complete proof' claims without case enumeration."""
    violations = []
    lines = code.split('\n')
    completeness_claims = [
        r'complete\s+proof', r'fully\s+solved', r'totally\s+resolved',
        r'complete\s+solution', r'definitively\s+proven',
    ]
    has_open = any(kw in code.lower() for kw in ['open', 'remains', 'boundary', 'limitation'])
    for i, line in enumerate(lines):
        for pat in completeness_claims:
            if re.search(pat, line, re.I):
                if not has_open:
                    violations.append({
                        'rule': 'COMPLETENESS_GATE', 'rule_id': 'CLOSURE-002-R3',
                        'severity': 'reject', 'loc': f'L{i+1}',
                        'kind': 'UNGUARDED_COMPLETENESS_CLAIM',
                        'quote': line.strip()[:100],
                        'fix': 'Add explicit boundary/limitation statement, or enumerate all cases'
                    })
    return violations


CHECKS = {
    "NAMING-002": check_naming_002,
    "CLI-001": check_cli_001,
    "CFLOW-003": check_cflow_003,
    "NO_ARBITRARY_RATIO": check_arbitrary_ratio,
    "NO_CONTINUITY_ON_DISCRETE": check_continuity_on_discrete,
    "INEQUALITY_3POINT_CHECK": check_inequality_3point,
    "COMPLETENESS_GATE": check_completeness_gate,
}


def check_file(filepath: str, rules: list = None) -> dict:
    """Run all enabled checks on a single Python file."""
    rules = rules or list(CHECKS.keys())
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            code = f.read()
    except Exception as e:
        return {"file": filepath, "error": str(e)}
    
    violations = []
    for rule_id in rules:
        if rule_id in CHECKS:
            violations.extend(CHECKS[rule_id](code, filepath))
    
    return {
        "file": filepath,
        "violations": violations,
        "count": len(violations),
        "verdict": "error" if any(v["severity"] == "error" for v in violations)
                   else ("warn" if violations else "pass")
    }


def check_directory(dirpath: str, rules: list = None) -> list:
    """Recursively scan all .py files in a directory."""
    results = []
    for root, dirs, files in os.walk(dirpath):
        # Filter hidden dirs
        dirs[:] = [d for d in dirs if not d.startswith('.') and d != '__pycache__']
        for fn in files:
            if fn.endswith('.py'):
                results.append(check_file(os.path.join(root, fn), rules))
    return results


# ───────────────────────────────────────────
#  CLI
# ───────────────────────────────────────────

def main():
    ap = argparse.ArgumentParser(description="MSS-VDP Pre-Commit Static Analyzer v%s" % VERSION)
    sub = ap.add_subparsers(dest="cmd")

    ck = sub.add_parser("check", help="Run static checks")
    ck.add_argument("target", nargs="?", help="File or directory to check")
    ck.add_argument("--dir", help="Scan directory recursively")
    ck.add_argument("--stdin", action="store_true", help="Read code from stdin")
    ck.add_argument("--rules", nargs="*", default=list(CHECKS.keys()),
                    help=f"Rules to run: {list(CHECKS.keys())}")
    ck.add_argument("--json", action="store_true", help="Output as JSON")

    args = ap.parse_args()

    if args.cmd == "check":
        if args.stdin:
            code = sys.stdin.read()
            results = {"stdin": {}}
            for r in args.rules:
                if r in CHECKS:
                    results[r] = CHECKS[r](code, "(stdin)")
            if args.json:
                print(json.dumps(results, ensure_ascii=False, indent=2))
            else:
                total = sum(len(v) for v in results.values() if isinstance(v, list))
                print(f"stdin: {total} violation(s)")
                for k, v in results.items():
                    if isinstance(v, list):
                        for item in v:
                            print(f"  [{item['rule']}] {item['loc']}: {item['quote'][:80]}")
            return

        if args.dir:
            results = check_directory(args.dir, args.rules)
        elif args.target:
            if os.path.isdir(args.target):
                results = check_directory(args.target, args.rules)
            else:
                results = [check_file(args.target, args.rules)]
        else:
            ap.print_help()
            return

        if args.json:
            print(json.dumps(results, ensure_ascii=False, indent=2))
        else:
            total_v = sum(r["count"] for r in results)
            errors = sum(1 for r in results if r.get("verdict") == "error")
            print(f"Scanned {len(results)} file(s): {errors} error(s), {total_v} violation(s)")
            for r in results:
                if r["violations"]:
                    print(f"\n  {r['file']}:")
                    for v in r["violations"]:
                        print(f"    [{v['rule']}] {v['loc']} {v['kind']}: {v['quote'][:100]}")
    else:
        ap.print_help()


if __name__ == "__main__":
    main()