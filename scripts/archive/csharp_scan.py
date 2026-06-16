#!/usr/bin/env python3
"""
MSS-VDP C# Scanner (regex-based — no tree-sitter)
Rules: C1_NULL (deref without null check), C2_DISPOSE (no using/Dispose),
       C3_ASYNC (async without await), C4_ERR (empty catch),
       C5_TIMEOUT (HttpClient without timeout)
"""
import sys, os, json, argparse, re
from pathlib import Path

class Rule:
    def __init__(self, rule_id, severity, desc):
        self.rule_id = rule_id; self.severity = severity; self.description = desc
    def check(self, code: str) -> list:
        return []

class C1_NullDereference(Rule):
    def __init__(self): super().__init__('C1_NULL', 'warn', 'Object dereference without null check')
    def check(self, code: str) -> list:
        violations = []
        for m in re.finditer(r'(\w+)\s+(\w+)\s*=\s*(\w+)\(', code):
            varname = m.group(2)
            if varname in ('var', 'int', 'string', 'bool', 'float', 'double'): continue
            decl_line = code[:m.start()].count('\n') + 1
            # Check next 15 lines for null check
            nearby = '\n'.join(code.split('\n')[decl_line:decl_line+15])
            uses = re.findall(re.escape(varname) + r'\.\w+', nearby)
            if uses and f'{varname} != null' not in nearby and f'{varname} is null' not in nearby:
                violations.append({
                    'rule_id': self.rule_id, 'severity': self.severity,
                    'loc': f'L{decl_line}', 'kind': 'null_deref',
                    'detail': f'{varname} used without null check — potential NullReferenceException',
                    'quote': code.split('\n')[decl_line-1].strip()[:80],
                })
        return violations

class C2_MissingDispose(Rule):
    def __init__(self): super().__init__('C2_DISPOSE', 'warn', 'IDisposable without using/Dispose')
    def check(self, code: str) -> list:
        violations = []
        disposables = ['StreamReader', 'StreamWriter', 'FileStream',
                       'SqlConnection', 'SqlCommand', 'HttpClient',
                       'TcpClient', 'UdpClient', 'WebClient',
                       'MemoryStream', 'BinaryReader', 'BinaryWriter',
                       'Stream', 'TextReader', 'TextWriter']
        for cls in disposables:
            for m in re.finditer(r'\bnew\s+' + re.escape(cls) + r'\s*\(', code):
                line = code[:m.start()].count('\n')
                before = '\n'.join(code.split('\n')[max(0,line-3):line+1])
                after = '\n'.join(code.split('\n')[line:line+5])
                if 'using (' not in before and 'using(' not in before and '.Dispose()' not in after:
                    violations.append({
                        'rule_id': self.rule_id, 'severity': self.severity,
                        'loc': f'L{line+1}', 'kind': 'missing_dispose',
                        'detail': f'new {cls} without using() or .Dispose() — resource leak',
                        'quote': code.split('\n')[line].strip()[:80],
                    })
        return violations

class C3_AsyncVoid(Rule):
    def __init__(self): super().__init__('C3_ASYNC', 'warn', 'async method without await')
    def check(self, code: str) -> list:
        violations = []
        for m in re.finditer(r'async\s+(?:void|Task|Task<\w+>)\s+(\w+)\s*\(', code):
            func_name = m.group(1)
            line = code[:m.start()].count('\n')
            # Find the method body
            brace_start = code.find('{', m.end())
            if brace_start < 0: continue
            depth = 0; body_end = brace_start
            for i in range(brace_start, len(code)):
                if code[i] == '{': depth += 1
                elif code[i] == '}':
                    depth -= 1
                    if depth == 0: body_end = i; break
            body = code[brace_start:body_end]
            if 'await ' not in body:
                violations.append({
                    'rule_id': self.rule_id, 'severity': self.severity,
                    'loc': f'L{line+1}', 'kind': 'async_no_await',
                    'detail': f'async method {func_name} lacks await — runs synchronously',
                    'quote': code.split('\n')[line].strip()[:80],
                })
        return violations

class C4_EmptyCatch(Rule):
    def __init__(self): super().__init__('C4_ERR', 'reject', 'Empty catch block')
    def check(self, code: str) -> list:
        violations = []
        for m in re.finditer(r'catch\s*(?:\(.*?\))?\s*\{\s*\}', code, re.DOTALL):
            line = code[:m.start()].count('\n') + 1
            violations.append({
                'rule_id': self.rule_id, 'severity': self.severity,
                'loc': f'L{line}', 'kind': 'empty_catch',
                'detail': 'Empty catch block — exceptions silently swallowed',
                'quote': code.split('\n')[line-1].strip()[:80],
            })
        return violations

class C5_HttpNoTimeout(Rule):
    def __init__(self): super().__init__('C5_TIMEOUT', 'warn', 'HttpClient without timeout')
    def check(self, code: str) -> list:
        violations = []
        for m in re.finditer(r'new\s+HttpClient\s*\(', code):
            line = code[:m.start()].count('\n')
            nearby = '\n'.join(code.split('\n')[line:line+5])
            if 'Timeout' not in nearby:
                violations.append({
                    'rule_id': self.rule_id, 'severity': self.severity,
                    'loc': f'L{line+1}', 'kind': 'http_no_timeout',
                    'detail': 'HttpClient without Timeout — may hang indefinitely',
                    'quote': code.split('\n')[line].strip()[:80],
                })
        return violations

class CsharpScanner:
    def __init__(self):
        self.rules = [C1_NullDereference(), C2_MissingDispose(),
                      C3_AsyncVoid(), C4_EmptyCatch(), C5_HttpNoTimeout()]
    
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
            'target': path, 'target_type': '.cs',
            'total_lines': len(code.split('\n')),
            'violations': violations,
            'verdict': 'reject' if any(v['severity']=='reject' for v in violations)
                       else 'warn' if violations else 'pass',
        }

def main():
    ap = argparse.ArgumentParser(description='MSS-VDP C# Scanner')
    ap.add_argument('target'); ap.add_argument('--json', action='store_true')
    args = ap.parse_args()
    s = CsharpScanner()
    
    if os.path.isfile(args.target):
        results = [s.scan(args.target)]
    else:
        results = []
        for root, dirs, files in os.walk(args.target):
            dirs[:] = [d for d in dirs if not d.startswith('.') and d not in ('node_modules','.git','obj','bin')]
            for f in files:
                if f.endswith('.cs'): results.append(s.scan(os.path.join(root,f)))
    
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
