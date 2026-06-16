#!/usr/bin/env python3
"""
MSS-VDP Go Scanner
Rules: G1_ERR (error unchecked), G2_DEFER (missing defer close),
       G3_LEAK (goroutine leak), G4_NIL (nil deref), G5_TIMEOUT (no context timeout)
"""
import sys, os, json, argparse
from pathlib import Path
from tree_sitter import Language, Parser
import tree_sitter_go as tsgo

GO_LANG = Language(tsgo.language())


class Rule:
    def __init__(self, rule_id, severity, desc):
        self.rule_id = rule_id; self.severity = severity; self.description = desc
    def check(self, node, content: str) -> list: return []


class RuleEngine:
    def __init__(self):
        self.parser = Parser(GO_LANG)
        self.rules: list[Rule] = []
    def register(self, r): self.rules.append(r)
    
    def scan(self, path: str) -> dict:
        try:
            with open(path, 'r', encoding='utf-8', errors='replace') as f:
                content = f.read()
        except Exception as e:
            return {'target': path, 'error': str(e), 'violations': []}
        
        tree = self.parser.parse(content.encode('utf-8'))
        violations = []
        
        def visit(node):
            for rule in self.rules:
                violations.extend(rule.check(node, content))
            for child in node.children:
                visit(child)
        
        visit(tree.root_node)
        
        return {
            'target': path, 'target_type': '.go',
            'total_lines': len(content.split('\n')),
            'violations': sorted(violations, key=lambda v: v['loc']),
            'verdict': 'reject' if any(v['severity']=='reject' for v in violations)
                       else 'warn' if violations else 'pass',
        }


# ── Go Rules ──

class G1_UncheckedError(Rule):
    """Detect function calls where error return is not checked (val, _ = ... or single assign)."""
    def __init__(self):
        super().__init__('G1_ERR', 'reject', 'Function with error return not checked')
    
    def check(self, node, content):
        if node.type in ('assignment_statement', 'short_var_declaration'):
            text = node.text.decode('utf-8')
            func_names = ['os.Open', 'os.Create', 'os.Remove', 'os.Rename',
                         'ioutil.ReadFile', 'ioutil.WriteFile', 'ioutil.ReadAll',
                         'json.Unmarshal', 'json.Marshal', 'http.Get', 'http.Post',
                         'fmt.Scanf', 'strconv.Atoi', 'strconv.Parse',
                         'file.Read', 'file.Write', 'io.ReadAll', 'io.Copy',
                         'sql.Open', 'sql.Query', 'sql.Exec',
                         'http.NewRequest', 'http.ListenAndServe',
                         'tls.Listen', 'crypto.GenerateKey']
            has_func = any(fn in text for fn in func_names)
            has_underscore = ', _' in text or '= _' in text
            assigns_one = text.count('=') == 1 and ('=' in text) and ',' not in text
            
            if has_func and (has_underscore or assigns_one):
                line = node.start_point[0] + 1
                return [{
                    'rule_id': self.rule_id, 'severity': self.severity,
                    'loc': f'L{line}', 'kind': 'unchecked_error',
                    'detail': 'Error return from call not checked — may silently fail',
                    'quote': content.split('\n')[node.start_point[0]].strip()[:80]
                }]
        return []


class G2_MissingDeferClose(Rule):
    """Detect resources opened without defer close."""
    def __init__(self):
        super().__init__('G2_DEFER', 'warn', 'Resource opened without defer Close()')
    
    def check(self, node, content):
        if node.type == 'short_var_declaration' or node.type == 'assignment_statement':
            text = node.text.decode('utf-8')
            closeable = ['os.Open', 'os.Create', 'net.Dial', 'net.Listen',
                        'http.Get', 'http.Post', 'sql.Open',
                        'tls.Dial', 'grpc.Dial', 'exec.Command',
                        'os.OpenFile', 'net.DialTimeout']
            has_open = any(fn + '(' in text for fn in closeable)
            
            if has_open:
                fn_start = node.start_point[0]
                nearby = '\n'.join(content.split('\n')[fn_start:fn_start+20])
                if 'defer ' not in nearby:
                    line = fn_start + 1
                    return [{
                        'rule_id': self.rule_id, 'severity': self.severity,
                        'loc': f'L{line}', 'kind': 'missing_defer_close',
                        'detail': 'Resource opened without defer Close() — potential leak',
                        'quote': content.split('\n')[fn_start].strip()[:80]
                    }]
        return []


class G3_LeakedGoroutine(Rule):
    """Detect goroutines without context cancellation."""
    def __init__(self):
        super().__init__('G3_LEAK', 'warn', 'Goroutine without context cancellation')
    
    def check(self, node, content):
        if node.type == 'go_statement':
            text = node.text.decode('utf-8')
            fn_start = node.start_point[0]
            # Check if context.Context exists in parent function
            parent_text = '\n'.join(content.split('\n')[max(0,fn_start-50):fn_start+5])
            has_ctx = 'context.Context' in parent_text or 'ctx ' in parent_text
            has_select = 'select {' in text or 'select{' in text
            
            if not has_ctx and not has_select:
                line = fn_start + 1
                return [{
                    'rule_id': self.rule_id, 'severity': self.severity,
                    'loc': f'L{line}', 'kind': 'leaked_goroutine',
                    'detail': 'Goroutine launched without context cancellation — may leak',
                    'quote': content.split('\n')[fn_start].strip()[:80]
                }]
        return []


class G4_NilDereference(Rule):
    """Detect pointer usage without nil check."""
    def __init__(self):
        super().__init__('G4_NIL', 'warn', 'Pointer dereference without nil check')
    
    def check(self, node, content):
        if node.type in ('call_expression', 'short_var_declaration'):
            text = node.text.decode('utf-8')
            # Check for type assertion: x.(Type)
            m = __import__('re').search(r'(\w+)\.\(', text)
            if m:
                varname = m.group(1)
                line = node.start_point[0]
                before = '\n'.join(content.split('\n')[max(0,line-20):line])
                has_nil_check = f'{varname} != nil' in before or f'{varname} == nil' in before
                if not has_nil_check:
                    return [{
                        'rule_id': self.rule_id, 'severity': self.severity,
                        'loc': f'L{line+1}', 'kind': 'type_assertion_no_check',
                        'detail': f'Type assertion ({varname}.) without nil check — may panic',
                        'quote': content.split('\n')[line].strip()[:80]
                    }]
        return []


class G5_HttpNoTimeout(Rule):
    """Detect http.Get/http.Post without context timeout."""
    def __init__(self):
        super().__init__('G5_TIMEOUT', 'warn', 'HTTP request without context timeout')
    
    def check(self, node, content):
        if node.type == 'call_expression':
            text = node.text.decode('utf-8')
            http_calls = ['http.Get(', 'http.Post(', 'http.Head(']
            if any(c in text for c in http_calls):
                line = node.start_point[0]
                nearby = '\n'.join(content.split('\n')[max(0,line-20):line+5])
                if 'context.WithTimeout' not in nearby and 'context.WithDeadline' not in nearby:
                    return [{
                        'rule_id': self.rule_id, 'severity': self.severity,
                        'loc': f'L{line+1}', 'kind': 'http_no_timeout',
                        'detail': 'HTTP request without context timeout — may hang forever',
                        'quote': content.split('\n')[line].strip()[:80]
                    }]
        return []


def create_engine() -> RuleEngine:
    e = RuleEngine()
    e.register(G1_UncheckedError())
    e.register(G2_MissingDeferClose())
    e.register(G3_LeakedGoroutine())
    e.register(G4_NilDereference())
    e.register(G5_HttpNoTimeout())
    return e


def main():
    ap = argparse.ArgumentParser(description='MSS-VDP Go Scanner')
    ap.add_argument('target', help='File or directory')
    ap.add_argument('--json', action='store_true')
    args = ap.parse_args()
    
    engine = create_engine()
    
    if not os.path.exists(args.target):
        print(f"Error: {args.target} not found", file=sys.stderr)
        sys.exit(1)
    
    if os.path.isfile(args.target):
        results = [engine.scan(args.target)]
    else:
        results = []
        for root, dirs, files in os.walk(args.target):
            dirs[:] = [d for d in dirs if not d.startswith('.') and d not in ('node_modules', '.git', 'vendor')]
            for f in files:
                if f.endswith('.go'):
                    results.append(engine.scan(os.path.join(root, f)))
    
    if args.json:
        print(json.dumps(results if len(results) > 1 else results[0], indent=2, ensure_ascii=False))
    else:
        total = len(results)
        total_v = sum(len(r.get('violations', [])) for r in results)
        rejects = sum(1 for r in results if r.get('verdict') == 'reject')
        print(f"Scanned {total} file(s): {rejects} reject(s), {total_v} violation(s)")
        for r in results:
            vs = r.get('violations', [])
            if vs:
                print(f"\n  {r['target']}:")
                for v in vs:
                    print(f"    [{v['severity']:6s}] {v['rule_id']:12s} {v['loc']:6s} {v['kind']:25s} {v['detail'][:80]}")


if __name__ == '__main__':
    main()
