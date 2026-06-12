#!/usr/bin/env python3
"""
MSS-VDP Ruby Scanner
Rules: R1_ERR (bare rescue), R2_LEAK (File.open without close),
       R3_EVAL (eval without sanitization), R4_NIL (nil method call),
       R5_INJECT (unsafe deserialization)
"""
import sys, os, json, argparse, re
from tree_sitter import Language, Parser
import tree_sitter_ruby as tsr

RUBY = Language(tsr.language())

class RuleEngine:
    def __init__(self):
        self.parser = Parser(RUBY)
        self.rules = []
    def register(self, r): self.rules.append(r)
    
    def scan(self, path):
        with open(path, 'r', encoding='utf-8', errors='replace') as f:
            content = f.read()
        tree = self.parser.parse(content.encode('utf-8'))
        violations = []
        def visit(node):
            for rule in self.rules:
                violations.extend(rule.check(node, content))
            for child in node.children:
                visit(child)
        visit(tree.root_node)
        violations.sort(key=lambda v: v['loc'])
        return {
            'target': path, 'target_type': '.rb',
            'total_lines': len(content.split('\n')),
            'violations': violations,
            'verdict': 'reject' if any(v['severity']=='reject' for v in violations)
                       else 'warn' if violations else 'pass',
        }

# ── Rules ──

class R1_BareRescue:
    def __init__(self): self.rule_id, self.severity = 'R1_ERR', 'warn'
    def check(self, node, content):
        if node.type == 'rescue' and not node.parent:
            # rescue without specific exception class
            text = node.text.decode('utf-8') if node.text else ''
            if '=>' not in text or 'Exception' not in text:
                return [{'rule_id': self.rule_id, 'severity': self.severity,
                         'loc': f'L{node.start_point[0]+1}', 'kind': 'bare_rescue',
                         'detail': 'Bare rescue catches all exceptions — may hide bugs'}]
        return []

class R2_FileLeak:
    def __init__(self): self.rule_id, self.severity = 'R2_LEAK', 'warn'
    def check(self, node, content):
        if node.type == 'call':
            text = node.text.decode('utf-8') if node.text else ''
            for fn in ['File.open', 'File.new', 'IO.open', 'IO.new', 'Socket.new', 'TCPSocket.new']:
                if text.startswith(fn + '(') or text.startswith(fn + ' '):
                    line = node.start_point[0]
                    nearby = '\n'.join(content.split('\n')[line:line+15])
                    if '.close' not in nearby and 'do |' not in nearby and '{|' not in nearby:
                        return [{'rule_id': self.rule_id, 'severity': self.severity,
                                 'loc': f'L{line+1}', 'kind': 'resource_leak',
                                 'detail': f'{fn} without block form or .close — resource leak'}]
        return []

class R3_EvalDanger:
    def __init__(self): self.rule_id, self.severity = 'R3_EVAL', 'reject'
    def check(self, node, content):
        if node.type == 'call':
            text = node.text.decode('utf-8') if node.text else ''
            if any(text.startswith(f + '(') for f in ['eval', 'instance_eval', 'class_eval', 'module_eval']):
                return [{'rule_id': self.rule_id, 'severity': self.severity,
                         'loc': f'L{node.start_point[0]+1}', 'kind': 'unsafe_eval',
                         'detail': 'eval() usage — potential code injection vulnerability'}]
        return []

class R4_NilCall:
    def __init__(self): self.rule_id, self.severity = 'R4_NIL', 'warn'
    def check(self, node, content):
        if node.type == 'call':
            text = node.text.decode('utf-8') if node.text else ''
            # Detect method calls that look like they could be nil
            # Pattern: var.method where var might be nil
            m = re.match(r'([a-z_]\w*)\.(\w+)', text)
            if m and m.group(1) and m.group(2) not in ('nil?', 'to_s', 'to_i', 'inspect', 'class'):
                var = m.group(1)
                line = node.start_point[0]
                before = '\n'.join(content.split('\n')[max(0,line-5):line])
                if var + '&.' not in before and 'if ' + var not in before and var + '.nil?' not in before:
                    if var in before:
                        return [{'rule_id': self.rule_id, 'severity': self.severity,
                                 'loc': f'L{line+1}', 'kind': 'potential_nil_call',
                                 'detail': f'Method call on {var} without nil guard — use &. for safe navigation'}]
        return []

class R5_UnsafeDeserialize:
    def __init__(self): self.rule_id, self.severity = 'R5_INJECT', 'reject'
    def check(self, node, content):
        if node.type in ('call', 'method_call'):
            text = node.text.decode('utf-8') if node.text else ''
            dangerous = ['Marshal.load', 'YAML.load', 'JSON.load', 'eval(']
            for d in dangerous:
                if text.startswith(d + '(') or d in text:
                    return [{'rule_id': self.rule_id, 'severity': self.severity,
                             'loc': f'L{node.start_point[0]+1}', 'kind': 'unsafe_deserialize',
                             'detail': f'{d} without safe mode — potential RCE'}]
        return []

def main():
    ap = argparse.ArgumentParser(description='MSS-VDP Ruby Scanner')
    ap.add_argument('target'); ap.add_argument('--json', action='store_true')
    args = ap.parse_args()
    e = RuleEngine()
    e.register(R1_BareRescue()); e.register(R2_FileLeak())
    e.register(R3_EvalDanger()); e.register(R4_NilCall())
    e.register(R5_UnsafeDeserialize())
    
    if not os.path.exists(args.target): print('Target not found'); sys.exit(1)
    results = []
    if os.path.isfile(args.target):
        results = [e.scan(args.target)]
    else:
        for root, dirs, files in os.walk(args.target):
            dirs[:] = [d for d in dirs if not d.startswith('.') and d not in ('node_modules', '.git', 'vendor')]
            for f in files:
                if f.endswith('.rb'): results.append(e.scan(os.path.join(root, f)))
    
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
