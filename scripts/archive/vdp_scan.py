#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MSS-VDP Executable Scanner v1.0
Scans PowerShell scripts / Python scripts / agent plans for V1-V6 violations.
Outputs structured verdict JSON. Uses patterns from H431.

Usage:
    python vdp_scan.py path/to/script.ps1
    python vdp_scan.py path/to/script.py
    python vdp_scan.py path/to/agent_plan.md
    python vdp_scan.py --stdin < script.ps1
    python vdp_scan.py --format json path/to/script.ps1
"""
import sys, os, re, json, argparse

# ── Pattern definitions (from H431) ──
PATTERNS = {
    "V1_PATH_EXISTENCE_PRECHECK": {
        "severity": "reject",
        "rules": [
            {
                "id": "V1-01-ps", "target": "powershell_script",
                "check": "FIND_FILE_IO_WITHOUT_PRECHECK",
                "regex_file_io": re.compile(
                    r'(Get-Content|Set-Content|Add-Content|Out-File|Copy-Item\b.*-Destination|'
                    r'Invoke-WebRequest\b.*-OutFile|Start-Process\b.*-FilePath|New-Item\b.*-Path)',
                    re.IGNORECASE
                ),
                "regex_precheck": re.compile(
                    r'(Test-Path|try\s*\{|-\w*ErrorAction\b)', re.IGNORECASE
                ),
                "fix": "Add: Test-Path $target; if(-not $?) { throw 'PATH_NOT_FOUND' }"
            },
            {
                "id": "V1-02-py", "target": "python_script",
                "check": "FIND_OPEN_WITHOUT_EXISTS",
                "regex_file_io": re.compile(r'\b(open|subprocess\.run)\s*\('),
                "regex_precheck": re.compile(r'(os\.path\.exists|os\.path\.isfile|FileNotFoundError|try:)'),
                "fix": "Add: if not os.path.exists(path): raise FileNotFoundError(path)"
            }
        ]
    },
    "V2_ERROR_DIRECT_REPORT": {
        "severity": "reject",
        "rules": [
            {
                "id": "V2-01", "target": "all",
                "check": "FIND_INFERRED_CAUSE_WITHOUT_ERRNO",
                "regex_inference": re.compile(
                    r'((?:看起来|可能|好像|估计|大概)\w{0,3}(?:被?\s*(?:沙箱|拦截|限制|不允许|block|阻止))|'
                    r'(?:sandbox|blocked|permission\s*denied)\b)',
                    re.IGNORECASE
                ),
                "regex_errno": re.compile(
                    r'(\$LASTEXITCODE|exit_?code|errno\b|stderr|status\s*code|HTTP\s+\d{3}|'
                    r'\$\?|Exception\.Message|ErrorRecord)',
                    re.IGNORECASE
                ),
                "fix": "Replace inference with raw stderr/exit_code output"
            }
        ]
    },
    "V3_EXPLICIT_ENCODING": {
        "severity": "warn",
        "rules": [
            {
                "id": "V3-01-ps", "target": "powershell_script",
                "check": "FIND_OUTFILE_WITHOUT_ENCODING",
                "regex_io": re.compile(
                    r'(Out-File|Set-Content|Add-Content|WriteAllText)\b',
                    re.IGNORECASE
                ),
                "regex_encoding": re.compile(r'-Encoding\b', re.IGNORECASE),
                "fix": "Add: -Encoding UTF8"
            },
            {
                "id": "V3-02-py", "target": "python_script",
                "check": "FIND_OPEN_WITHOUT_ENCODING",
                "regex_io": re.compile(r'\bopen\s*\([^)]*[\"\']w[\"\']'),
                "regex_encoding": re.compile(r'encoding\s*='),
                "fix": "Add: encoding='utf-8'"
            }
        ]
    },
    "V4_ATOMIC_IDEMPOTENT_WRITE": {
        "severity": "reject",
        "rules": [
            {
                "id": "V4-01", "target": "all",
                "check": "FIND_NON_IDEMPOTENT_OVERWRITE",
                "regex_overwrite": re.compile(
                    r'(Set-Content|Out-File\b.*-Force|WriteAllText|WriteAllBytes|'
                    r'tool:\s*write|write\s*\(\s*["\'].*\.md|\bwrite\s*\(.*content)',
                    re.IGNORECASE
                ),
                "regex_backup": re.compile(
                    r'(Copy-Item.*\.bak|diff\b|backup|\<\<\<APPEND|backup-?)',
                    re.IGNORECASE
                ),
                "fix": "Backup first: Copy-Item $target '$target.bak'; or output diff format"
            }
        ]
    },
    "V5_TIMEOUT_DEGRADE": {
        "severity": "reject",
        "rules": [
            {
                "id": "V5-01", "target": "all",
                "check": "FIND_RETRY_LOOP_WITHOUT_BREAKER",
                "regex_retry_loop": re.compile(
                    r'(for\s*\(\s*\$?\w+.*;;|while\s*\(\s*True\b|while\s*\(\s*1\b|'
                    r'while\s*\(\s*\$\w+)\s*\)',
                    re.IGNORECASE
                ),
                "regex_breaker": re.compile(
                    r'(\$maxAttempts|\$max_retries|circuit_breaker|fallback|DEGRADED|'
                    r'\w+\s*(?:-lt|-le|<|<=)\s*(?:2|3)\b)',
                    re.IGNORECASE
                ),
                "fix": "Add circuit breaker: max_retries=2, fallback to degraded mode"
            }
        ]
    },
    "V6_FACT_INFERENCE_SEPARATION": {
        "severity": "warn",
        "rules": [
            {
                "id": "V6-01", "target": "agent_trace",
                "check": "FIND_UNANCHORED_EXISTENCE_CLAIM",
                "regex_claim": re.compile(
                    r'((?:路径|文件|目录|它在|位于|存在|there\s+is|located\s+at)\w{0,10}'
                    r'(?:[A-Za-z]:\\\\(?:[^\s\"\'<]{3,})))',
                    re.IGNORECASE
                ),
                "regex_evidence": re.compile(
                    r'(Test-Path|dir\b|ls\b|Get-ChildItem|os\.path\.exists|\[事实\]|\[已验证\])',
                    re.IGNORECASE
                ),
                "fix": "Tag unverified claims with [推断/confidence] or verify with Test-Path"
            }
        ]
    }
}

CJK_CHARS = re.compile(r'[\u4e00-\u9fff\u3400-\u4dbf]')
def contains_cjk(text):
    return bool(CJK_CHARS.search(text))


def detect_file_type(filename, content):
    """Detect if file is powershell, python, or agent plan."""
    if filename and (filename.endswith('.ps1') or filename.endswith('.psm1')):
        return 'powershell_script'
    if filename and filename.endswith('.py'):
        return 'python_script'
    if filename and filename.endswith('.md'):
        return 'agent_plan'
    # Heuristic: look for PowerShell cmdlets
    if re.search(r'(Get-Content|Set-Content|Write-Host|Invoke-RestMethod|ForEach-Object)', content):
        return 'powershell_script'
    # Heuristic: look for Python
    if re.search(r'(def |import |from \w+ import|if __name__)', content):
        return 'python_script'
    return 'agent_plan'


def scan_file(filepath, strict=False):
    """Scan a file for VDP violations. Returns dict with verdict + violations."""
    if not os.path.exists(filepath):
        return {
            "verdict": "error",
            "error": "FILE_NOT_FOUND: %s" % filepath,
            "violations": [],
            "vdp_version": "1.0",
            "target": filepath
        }

    with open(filepath, 'r', encoding='utf-8', errors='replace') as f:
        content = f.read()

    filetype = detect_file_type(filepath, content)
    return scan_content(content, filetype, filepath, strict)


def scan_content(content, filetype, source="<stdin>", strict=False):
    lines = content.split('\n')
    violations = []

    for discipline_name, discipline in PATTERNS.items():
        for rule in discipline['rules']:
            # Skip rules not targeting this filetype or "all"
            if rule['target'] != 'all' and rule['target'] != filetype:
                continue

            # Apply rule-specific detection
            if 'regex_file_io' in rule:
                _check_file_io(lines, discipline_name, discipline, rule, violations, strict)
            elif 'regex_inference' in rule:
                _check_inference(lines, discipline_name, discipline, rule, violations, strict)
            elif 'regex_io' in rule:
                _check_encoding(lines, discipline_name, discipline, rule, violations, strict)
            elif 'regex_overwrite' in rule:
                _check_overwrite(lines, discipline_name, discipline, rule, violations, strict)
            elif 'regex_retry_loop' in rule:
                _check_retry(lines, discipline_name, discipline, rule, violations, strict)
            elif 'regex_claim' in rule:
                _check_claim(lines, discipline_name, discipline, rule, violations, strict)

    # Determine overall verdict
    has_reject = any(v['severity'] == 'reject' for v in violations)
    has_warn = any(v['severity'] == 'warn' for v in violations)

    verdict = 'reject' if has_reject else ('warn' if has_warn else 'pass')

    return {
        "verdict": verdict,
        "violations": violations,
        "vdp_version": "1.0",
        "target": source,
        "target_type": filetype,
        "stats": {
            "total_lines": len(lines),
            "violations_count": len(violations),
            "reject_count": sum(1 for v in violations if v['severity'] == 'reject'),
            "warn_count": sum(1 for v in violations if v['severity'] == 'warn')
        }
    }


def _check_file_io(lines, dname, disc, rule, violations, strict):
    """V1: File I/O without precheck."""
    for i, line in enumerate(lines):
        if rule['regex_file_io'].search(line):
            # Check nearby lines (prev 5) for precheck
            ctx_start = max(0, i - 5)
            ctx = '\n'.join(lines[ctx_start:i])
            if not rule['regex_precheck'].search(ctx):
                violations.append({
                    "rule": dname,
                    "rule_id": rule['id'],
                    "severity": disc['severity'],
                    "loc": "L%d" % (i + 1),
                    "kind": rule['check'],
                    "quote": line.strip()[:100],
                    "fix": rule['fix']
                })
                break  # One per rule per file


def _check_inference(lines, dname, disc, rule, violations, strict):
    """V2: Inferred cause without errno evidence."""
    content = '\n'.join(lines)
    for match in rule['regex_inference'].finditer(content):
        start = match.start()
        # Search for errno evidence in nearby text (within 300 chars)
        window_start = max(0, start - 300)
        window = content[window_start:start + 300]
        if not rule['regex_errno'].search(window):
            # Find line number
            line_num = content[:start].count('\n') + 1
            violations.append({
                "rule": dname,
                "rule_id": rule['id'],
                "severity": disc['severity'],
                "loc": "L%d" % line_num,
                "kind": rule['check'],
                "quote": match.group(0),
                "fix": rule['fix']
            })
            break


def _check_encoding(lines, dname, disc, rule, violations, strict):
    """V3: I/O without explicit encoding."""
    has_cjk = contains_cjk('\n'.join(lines))
    for i, line in enumerate(lines):
        if rule['regex_io'].search(line):
            if not rule['regex_encoding'].search(line):
                actual_severity = 'reject' if (has_cjk and strict) else disc['severity']
                violations.append({
                    "rule": dname,
                    "rule_id": rule['id'],
                    "severity": actual_severity,
                    "loc": "L%d" % (i + 1),
                    "kind": rule['check'],
                    "quote": line.strip()[:100],
                    "fix": rule['fix']
                })
                break


def _check_overwrite(lines, dname, disc, rule, violations, strict):
    """V4: Non-idempotent overwrite without backup."""
    content = '\n'.join(lines)
    for match in rule['regex_overwrite'].finditer(content):
        start = match.start()
        window_start = max(0, start - 200)
        window = content[window_start:start + 500]
        if not rule['regex_backup'].search(window):
            line_num = content[:start].count('\n') + 1
            violations.append({
                "rule": dname,
                "rule_id": rule['id'],
                "severity": disc['severity'],
                "loc": "L%d" % line_num,
                "kind": rule['check'],
                "quote": match.group(0)[:100],
                "fix": rule['fix']
            })
            break


def _check_retry(lines, dname, disc, rule, violations, strict):
    """V5: Retry loop without circuit breaker."""
    content = '\n'.join(lines)
    for match in rule['regex_retry_loop'].finditer(content):
        start = match.start()
        window_start = max(0, start)
        window = content[window_start:start + 1000]
        # Also check for retry keyword
        has_retry = bool(re.search(r'(retry|attempt|tries|失败|重试)', window, re.IGNORECASE))
        has_breaker = rule['regex_breaker'].search(window)
        if has_retry and not has_breaker:
            line_num = content[:start].count('\n') + 1
            violations.append({
                "rule": dname,
                "rule_id": rule['id'],
                "severity": disc['severity'],
                "loc": "L%d" % line_num,
                "kind": rule['check'],
                "quote": match.group(0)[:100],
                "fix": rule['fix']
            })
            break


def _check_claim(lines, dname, disc, rule, violations, strict):
    """V6: Unanchored existence claim."""
    content = '\n'.join(lines)
    for match in rule['regex_claim'].finditer(content):
        start = match.start()
        window_start = max(0, start - 400)
        window = content[window_start:start + 200]
        if not rule['regex_evidence'].search(window):
            line_num = content[:start].count('\n') + 1
            violations.append({
                "rule": dname,
                "rule_id": rule['id'],
                "severity": disc['severity'],
                "loc": "L%d" % line_num,
                "kind": rule['check'],
                "quote": match.group(0)[:100],
                "fix": rule['fix']
            })
            break


# ── CLI ──
def main():
    parser = argparse.ArgumentParser(description='MSS-VDP Scanner v1.0')
    parser.add_argument('target', nargs='?', help='File to scan')
    parser.add_argument('--format', choices=['text', 'json'], default='json',
                        help='Output format (default: json)')
    parser.add_argument('--strict', action='store_true',
                        help='Strict mode: V3 encoding warnings become reject for CJK files')
    parser.add_argument('--stdin', action='store_true',
                        help='Read input from stdin')
    parser.add_argument('--filetype', choices=['powershell_script', 'python_script', 'agent_plan'],
                        help='Force file type')

    args = parser.parse_args()

    if args.stdin:
        content = sys.stdin.read()
        filetype = args.filetype or detect_file_type(None, content)
        result = scan_content(content, filetype, strict=args.strict)
    elif args.target:
        target_path = os.path.abspath(args.target)
        if os.path.isdir(target_path):
            # Directory scan — walk and scan all files
            results = []
            for root, dirs, files in os.walk(target_path):
                dirs[:] = [d for d in dirs if not d.startswith('.') and d not in ('node_modules','.git','__pycache__','.mss','.run')]
                for f in files:
                    if f.endswith(('.py','.ps1','.psm1','.js','.ts','.rs','.go','.rb','.php','.kt','.cs','.java','.cpp','.c')):
                        filepath = os.path.join(root, f)
                        results.append(scan_file(filepath, strict=args.strict))
            # Aggregate results
            all_v = []
            for r2 in results:
                all_v.extend(r2.get('violations', []))
            has_reject = any(v.get('severity') == 'reject' for v in all_v)
            has_warn = any(v.get('severity') == 'warn' for v in all_v)
            result = {
                'verdict': 'reject' if has_reject else ('warn' if has_warn else 'pass'),
                'violations': all_v,
                'files_scanned': len(results),
                'vdp_version': '1.0',
                'target': target_path,
            }
        else:
            result = scan_file(target_path, strict=args.strict)
    else:
        parser.print_help()
        sys.exit(1)

    if args.format == 'json':
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print("VDP Scan: %s" % result['target'])
        print("Verdict: %s | Type: %s | Lines: %d" % (
            result['verdict'].upper(), result['target_type'],
            result.get('stats', {}).get('total_lines', 0)))
        for v in result.get('violations', []):
            print("  [%s] %s L%s: %s (%s)" % (
                v['severity'].upper(), v['rule_id'], v['loc'],
                v['quote'][:60], v['kind']))
        if not result.get('violations'):
            print("  No violations found.")

    sys.exit(2 if result.get('verdict') == 'reject' else
             1 if result.get('verdict') == 'warn' else 0)


if __name__ == '__main__':
    main()