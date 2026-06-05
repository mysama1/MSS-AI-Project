#!/usr/bin/env python3
"""
MSS-VDP PHP Scanner
Rules: P1_SUPPRESS (@ operator), P2_LEAK (fopen without fclose),
       P3_INJECT (unsanitized SQL), P4_NULL (no isset/??),
       P5_SESSION (session_start without security config)
"""
import sys, os, json, argparse, re
from tree_sitter import Language, Parser
import tree_sitter_php as tsp

PHP = Language(tsp.language_php())

class RuleEngine:
    def __init__(self):
        self.parser = Parser(PHP)
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
            'target': path, 'target_type': '.php',
            'total_lines': len(content.split('\n')),
            'violations': violations,
            'verdict': 'reject' if any(v['severity']=='reject' for v in violations)
                       else 'warn' if violations else 'pass',
        }

# ── Rules ──

class P1_SuppressionOperator:
    def __init__(self): self.rule_id, self.severity = 'P1_ERR', 'warn'
    def check(self, node, content):
        # Regex scan for @ operator suppressing errors
        if node.type == 'expression_statement':
            text = content[node.start_byte:node.end_byte]
            if text.strip().startswith('@'):
                return [{'rule_id': self.rule_id, 'severity': self.severity,
                         'loc': f'L{node.start_point[0]+1}', 'kind': 'error_suppression',
                         'detail': '@ operator suppresses all errors — hides bugs'}]
        return []

class P2_FileLeak:
    def __init__(self): self.rule_id, self.severity = 'P2_LEAK', 'warn'
    def check(self, node, content):
        if node.type in ('function_call_expression', 'expression_statement'):
            text = content[node.start_byte:node.end_byte]
            open_fns = ['fopen(', 'opendir(', 'socket_create(', 'curl_init(', 'popen(', 'proc_open(']
            for fn in open_fns:
                if fn in text:
                    line = node.start_point[0]
                    nearby = '\n'.join(content.split('\n')[line:line+20])
                    close_fn = fn.replace('_create', '_close').replace('_init', '_close').replace('(', '_close(')
                    if 'fclose' not in nearby and 'pclose' not in nearby and 'closedir' not in nearby and 'curl_close' not in nearby:
                        return [{'rule_id': self.rule_id, 'severity': self.severity,
                                 'loc': f'L{line+1}', 'kind': 'resource_leak',
                                 'detail': f'{fn.strip()} without close — resource leak'}]
        return []

class P3_SQLInjection:
    def __init__(self): self.rule_id, self.severity = 'P3_INJECT', 'reject'
    def check(self, node, content):
        if node.type in ('function_call_expression', 'expression_statement'):
            text = content[node.start_byte:node.end_byte]
            dangerous = ['mysql_query', 'mysqli_query', 'pg_query', 'sqlite_query']
            for d in dangerous:
                if d + '(' in text or d + ' (' in text:
                    # Check for variable interpolation without escaping
                    has_var = '$' in text and ('addslashes' not in text.lower() and 'mysqli_real_escape' not in text.lower() and 'bindParam' not in text.lower() and 'prepared' not in text.lower())
                    if has_var:
                        return [{'rule_id': self.rule_id, 'severity': self.severity,
                                 'loc': f'L{node.start_point[0]+1}', 'kind': 'sql_injection',
                                 'detail': 'SQL query with variable interpolation without escaping — SQL injection risk'}]
        return []

class P4_MissingNullCheck:
    def __init__(self): self.rule_id, self.severity = 'P4_NULL', 'warn'
    def check(self, node, content):
        if node.type == 'expression_statement':
            text = content[node.start_byte:node.end_byte]
            # Pattern: $var->method() or $var['key'] without isset/?? guard
            m = re.search(r'(\$\w+)\s*->|(\$\w+)\s*\[', text)
            if m:
                var = m.group(1) or m.group(2)
                line = node.start_point[0]
                before = '\n'.join(content.split('\n')[max(0,line-3):line])
                if 'isset(' + var not in before and var + ' ??' not in before:
                    return [{'rule_id': self.rule_id, 'severity': self.severity,
                             'loc': f'L{line+1}', 'kind': 'no_null_check',
                             'detail': f'Access on {var} without isset() or ?? — potential undefined/null error'}]
        return []

class P5_SessionSecurity:
    def __init__(self): self.rule_id, self.severity = 'P5_SESSION', 'warn'
    def check(self, node, content):
        if node.type in ('function_call_expression', 'expression_statement'):
            text = content[node.start_byte:node.end_byte]
            if 'session_start()' in text or 'session_start (' in text:
                # Check if security config was set before
                func_start = node.start_point[0]
                nearby = '\n'.join(content.split('\n')[max(0,func_start-10):func_start])
                if 'session.cookie_secure' not in nearby and 'session.cookie_httponly' not in nearby:
                    return [{'rule_id': self.rule_id, 'severity': self.severity,
                             'loc': f'L{func_start+1}', 'kind': 'insecure_session',
                             'detail': 'session_start() without secure/httponly cookie config'}]
        return []

def main():
    ap = argparse.ArgumentParser(description='MSS-VDP PHP Scanner')
    ap.add_argument('target'); ap.add_argument('--json', action='store_true')
    args = ap.parse_args()
    e = RuleEngine()
    e.register(P1_SuppressionOperator()); e.register(P2_FileLeak())
    e.register(P3_SQLInjection()); e.register(P4_MissingNullCheck())
    e.register(P5_SessionSecurity())
    
    if not os.path.exists(args.target): print('Target not found'); sys.exit(1)
    results = []
    if os.path.isfile(args.target):
        results = [e.scan(args.target)]
    else:
        for root, dirs, files in os.walk(args.target):
            dirs[:] = [d for d in dirs if not d.startswith('.') and d not in ('node_modules', '.git', 'vendor')]
            for f in files:
                if f.endswith('.php'): results.append(e.scan(os.path.join(root, f)))
    
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
