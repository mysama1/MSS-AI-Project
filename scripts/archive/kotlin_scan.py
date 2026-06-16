#!/usr/bin/env python3
"""
MSS-VDP Kotlin Scanner (regex-based — no tree-sitter)
Rules: K1_NULL (nullable deref), K2_LEAK (stream not closed),
       K3_COROUTINE (launch without scope), K4_ERR (throw without catch),
       K5_TIMEOUT (URL.openConnection without timeout)
"""
import sys, os, json, argparse, re
from pathlib import Path

class Rule:
    def __init__(self, rule_id, severity, desc):
        self.rule_id = rule_id; self.severity = severity; self.description = desc
    def check(self, code: str) -> list:
        return []

class K1_NullableDereference(Rule):
    def __init__(self): super().__init__('K1_NULL', 'warn', 'Nullable type dereference without safe-call')
    def check(self, code: str) -> list:
        violations = []
        # Pattern:  var.property  or  var.method()  where var is nullable (Type?)
        for m in re.finditer(r'val\s+(\w+)\s*:\s*(\w+\?)\s*=', code):
            varname = m.group(1)
            # Find usages of this variable that aren't safe-call
            safe_pattern = re.escape(varname) + r'\?\.'
            unsafe_uses = re.findall(re.escape(varname) + r'\.\w+', code)
            safe_uses = re.findall(safe_pattern, code)
            if len(unsafe_uses) > len(safe_uses):
                line = code[:m.start()].count('\n') + 1
                violations.append({
                    'rule_id': self.rule_id, 'severity': self.severity,
                    'loc': f'L{line}', 'kind': 'nullable_deref',
                    'detail': f'{varname}: {m.group(2)} used without ?. safe-call operator',
                    'quote': code.split('\n')[line-1].strip()[:80],
                })
        return violations

class K2_StreamLeak(Rule):
    def __init__(self): super().__init__('K2_LEAK', 'warn', 'Stream/Reader/Writer not closed')
    def check(self, code: str) -> list:
        violations = []
        openers = ['FileInputStream', 'FileOutputStream', 'BufferedReader',
                   'BufferedWriter', 'FileReader', 'FileWriter',
                   'InputStream', 'OutputStream']
        for cls in openers:
            for m in re.finditer(re.escape(cls) + r'\s*\(', code):
                line = code[:m.start()].count('\n')
                # Check next 20 lines for .close()
                nearby_lines = code.split('\n')[line:line+20]
                nearby = '\n'.join(nearby_lines)
                if '.close()' not in nearby and '.use {' not in nearby and '.use{' not in nearby:
                    violations.append({
                        'rule_id': self.rule_id, 'severity': self.severity,
                        'loc': f'L{line+1}', 'kind': 'stream_leak',
                        'detail': f'{cls} opened without .close() or .use{{}} — resource leak',
                        'quote': nearby_lines[0].strip()[:80] if nearby_lines else '',
                    })
        return violations

class K3_CoroutineLeak(Rule):
    def __init__(self): super().__init__('K3_COROUTINE', 'warn', 'Coroutine launched without scope')
    def check(self, code: str) -> list:
        violations = []
        for m in re.finditer(r'(?:launch|async)\s*\{', code):
            line = code[:m.start()].count('\n')
            before = '\n'.join(code.split('\n')[max(0,line-3):line+1])
            if 'CoroutineScope' not in before and 'coroutineScope' not in before and 'runBlocking' not in before:
                violations.append({
                    'rule_id': self.rule_id, 'severity': self.severity,
                    'loc': f'L{line+1}', 'kind': 'coroutine_leak',
                    'detail': 'launch/async without CoroutineScope — potential coroutine leak',
                    'quote': code.split('\n')[line].strip()[:80],
                })
        return violations

class K4_UnhandledThrow(Rule):
    def __init__(self): super().__init__('K4_ERR', 'warn', 'throw without try-catch')
    def check(self, code: str) -> list:
        violations = []
        for m in re.finditer(r'(?<!\\)throw\s+', code):
            line = code[:m.start()].count('\n')
            before = '\n'.join(code.split('\n')[max(0,line-10):line])
            if 'try {' not in before and 'try{' not in before:
                violations.append({
                    'rule_id': self.rule_id, 'severity': self.severity,
                    'loc': f'L{line+1}', 'kind': 'unhandled_throw',
                    'detail': 'throw without surrounding try-catch — may crash',
                    'quote': code.split('\n')[line].strip()[:80],
                })
        return violations

class K5_HttpNoTimeout(Rule):
    def __init__(self): super().__init__('K5_TIMEOUT', 'warn', 'URL.openConnection without timeout')
    def check(self, code: str) -> list:
        violations = []
        for m in re.finditer(r'URL\s*\(.*?\)\s*\.\s*openConnection', code):
            line = code[:m.start()].count('\n')
            nearby = '\n'.join(code.split('\n')[line:line+5])
            if '.connectTimeout' not in nearby and '.readTimeout' not in nearby:
                violations.append({
                    'rule_id': self.rule_id, 'severity': self.severity,
                    'loc': f'L{line+1}', 'kind': 'http_no_timeout',
                    'detail': 'URL.openConnection without connectTimeout/readTimeout — may hang',
                    'quote': code.split('\n')[line].strip()[:80],
                })
        return violations

class KtScanner:
    def __init__(self):
        self.rules = [K1_NullableDereference(), K2_StreamLeak(),
                      K3_CoroutineLeak(), K4_UnhandledThrow(), K5_HttpNoTimeout()]
    
    def scan(self, path: str) -> dict:
        try:
            with open(path, 'r', encoding='utf-8', errors='replace') as f:
                code = f.read()
        except Exception as e:
            return {'target': path, 'error': str(e), 'violations': []}
        
        violations = []
        for rule in self.rules:
            violations.extend(rule.check(code))
        
        violations.sort(key=lambda v: v['loc'])
        return {
            'target': path, 'target_type': '.kt',
            'total_lines': len(code.split('\n')),
            'violations': violations,
            'verdict': 'reject' if any(v['severity']=='reject' for v in violations)
                       else 'warn' if violations else 'pass',
        }

def main():
    ap = argparse.ArgumentParser(description='MSS-VDP Kotlin Scanner')
    ap.add_argument('target'); ap.add_argument('--json', action='store_true')
    args = ap.parse_args()
    s = KtScanner()
    
    if os.path.isfile(args.target):
        results = [s.scan(args.target)]
    else:
        results = []
        for root, dirs, files in os.walk(args.target):
            dirs[:] = [d for d in dirs if not d.startswith('.') and d not in ('node_modules','.git')]
            for f in files:
                if f.endswith(('.kt', '.kts')): results.append(s.scan(os.path.join(root,f)))
    
    if args.json:
        print(json.dumps(results[0] if len(results)==1 else results, indent=2, ensure_ascii=False))
    else:
        total_v = sum(len(r.get('violations',[])) for r in results)
        rejects = sum(1 for r in results if r.get('verdict')=='reject')
        print(f"Scanned {len(results)} file(s): {rejects} reject(s), {total_v} violation(s)")
        for r in results:
            for v in r.get('violations', []):
                print(f"  [{v['severity']:6s}] {v['rule_id']} {v['loc']}: {v['detail'][:90]}")
    sys.exit(1 if rejects else 0)

if __name__ == '__main__': main()
