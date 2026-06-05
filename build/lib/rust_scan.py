#!/usr/bin/env python3
"""
MSS-VDP Rust Scanner — 真吞错检测
DEV-101: Static analysis for Rust source files
"""
import sys, os, json, argparse
from pathlib import Path
from tree_sitter import Language, Parser, Node
import tree_sitter_rust as tsr

RUST_LANG = Language(tsr.language())
RUST_EXTS = {'.rs'}


class Rule:
    def __init__(self, rule_id: str, severity: str, description: str):
        self.rule_id = rule_id
        self.severity = severity
        self.description = description
    
    def check(self, node: Node, content: str) -> list:
        return []


class RuleEngine:
    def __init__(self):
        self.parser = Parser(RUST_LANG)
        self.rules: list[Rule] = []
    
    def register(self, rule: Rule):
        self.rules.append(rule)
    
    def scan(self, path: str) -> dict:
        try:
            with open(path, 'r', encoding='utf-8', errors='replace') as f:
                content = f.read()
        except Exception as e:
            return {'target': path, 'error': str(e), 'violations': []}
        
        tree = self.parser.parse(content.encode('utf-8'))
        violations = []
        cursor = tree.root_node.walk()
        visited = set()
        
        def visit():
            node = cursor.node
            if node.id not in visited:
                visited.add(node.id)
                for rule in self.rules:
                    violations.extend(rule.check(node, content))
            if cursor.goto_first_child():
                visit()
                while cursor.goto_next_sibling():
                    visit()
                cursor.goto_parent()
        
        visit()
        
        return {
            'target': path, 'target_type': '.rs',
            'total_lines': len(content.split('\n')),
            'violations': sorted(violations, key=lambda v: v['loc']),
            'verdict': 'reject' if any(v['severity']=='reject' for v in violations)
                       else 'warn' if violations else 'pass',
        }


# ── Rust-Specific Rules ──

class R1_BareUnwrap(Rule):
    """Detect .unwrap() and .expect() that can panic at runtime."""
    def __init__(self):
        super().__init__('R1_PANIC', 'warn', 'Potential panic: .unwrap() without prior check')

    def check(self, node: Node, content: str):
        if node.type in ('call_expression', 'field_expression'):
            text = node.text.decode('utf-8')
            if '.unwrap()' in text or text.endswith('.unwrap()') or '.expect(' in text:
                line = node.start_point[0] + 1
                return [{
                    'rule_id': self.rule_id, 'severity': self.severity,
                    'loc': f'L{line}', 'kind': 'bare_unwrap',
                    'detail': '.unwrap() may panic — consider .ok_or()? or match',
                    'quote': content.split('\n')[node.start_point[0]].strip()[:80]
                }]
        return []


class R2_SilentError(Rule):
    """Detect `let _ =` silencing Result values."""
    def __init__(self):
        super().__init__('R2_ERROR', 'warn', 'Silently ignored Result or error')

    def check(self, node: Node, content: str):
        # let _ = expr → silently discards Result errors
        if node.type == 'let_declaration':
            text = node.text.decode('utf-8')
            if 'let _ =' in text or 'let _unused =' in text:
                line = node.start_point[0] + 1
                return [{
                    'rule_id': self.rule_id, 'severity': self.severity,
                    'loc': f'L{line}', 'kind': 'silent_discard',
                    'detail': 'Result silently discarded with let _ = — use .unwrap_or_log() or explicit match',
                    'quote': content.split('\n')[node.start_point[0]].strip()[:80]
                }]
        return []


class R3_MemoryLeak(Rule):
    """Detect Box::leak, std::mem::forget, unsafe without safety comment."""
    def __init__(self):
        super().__init__('R3_LEAK', 'warn', 'Potential memory leak or unsafe usage')

    def check(self, node: Node, content: str):
        violations = []
        text = node.text.decode('utf-8')
        
        if node.type == 'call_expression':
            if 'Box::leak(' in text or 'mem::forget(' in text:
                line = node.start_point[0] + 1
                violations.append({
                    'rule_id': self.rule_id, 'severity': self.severity,
                    'loc': f'L{line}', 'kind': 'intentional_leak',
                    'detail': f'Intentional memory leak detected — ensure justified',
                    'quote': content.split('\n')[node.start_point[0]].strip()[:80]
                })
        
        if node.type == 'unsafe_block' or (node.type == 'function_item' and 'unsafe' in node.text.decode('utf-8')[:10]):
            line_start = node.start_point[0]
            line_block = content.split('\n')[max(0, line_start - 1):line_start + 1]
            has_safety = any('SAFETY' in l or 'Safety' in l for l in line_block)
            if not has_safety:
                violations.append({
                    'rule_id': self.rule_id, 'severity': self.severity,
                    'loc': f'L{line_start+1}', 'kind': 'unsafe_no_safety_doc',
                    'detail': 'unsafe block/fn without // SAFETY: comment',
                    'quote': line_block[-1].strip()[:80] if line_block else '?'
                })
        
        return violations


class R4_TokenLeak(Rule):
    """Detect network token/timeout issues: request without timeout."""
    def __init__(self):
        super().__init__('R4_TIMEOUT', 'warn', 'Network call may hang without timeout')

    def check(self, node: Node, content: str):
        if node.type == 'call_expression':
            text = node.text.decode('utf-8')
            # reqwest::Client::new or reqwest::get without timeout
            if ('Client::new()' in text or 'reqwest::get(' in text or '::get(' in text) and 'timeout' not in text.lower():
                line = node.start_point[0] + 1
                return [{
                    'rule_id': self.rule_id, 'severity': self.severity,
                    'loc': f'L{line}', 'kind': 'no_timeout',
                    'detail': 'HTTP request without timeout — may hang indefinitely',
                    'quote': content.split('\n')[node.start_point[0]].strip()[:80]
                }]
        return []


class R5_FileOverwrite(Rule):
    """Detect std::fs::write without backup."""
    def __init__(self):
        super().__init__('R5_ATOMIC', 'warn', 'File write without backup')

    def check(self, node: Node, content: str):
        if node.type == 'call_expression':
            text = node.text.decode('utf-8')
            if 'fs::write(' in text or '::write(' in text:
                line = node.start_point[0] + 1
                return [{
                    'rule_id': self.rule_id, 'severity': self.severity,
                    'loc': f'L{line}', 'kind': 'direct_overwrite',
                    'detail': 'Direct file write without backup — use atomic write pattern',
                    'quote': content.split('\n')[node.start_point[0]].strip()[:80]
                }]
        return []


def create_engine() -> RuleEngine:
    engine = RuleEngine()
    engine.register(R1_BareUnwrap())
    engine.register(R2_SilentError())
    engine.register(R3_MemoryLeak())
    engine.register(R4_TokenLeak())
    engine.register(R5_FileOverwrite())
    return engine


def scan_file(path: str) -> dict:
    engine = create_engine()
    return engine.scan(path)


def scan_directory(directory: str) -> list:
    results = []
    for root, dirs, files in os.walk(directory):
        dirs[:] = [d for d in dirs if not d.startswith('.') and d not in ('target', 'node_modules', '.git')]
        for f in files:
            if Path(f).suffix in RUST_EXTS:
                results.append(scan_file(os.path.join(root, f)))
    return results


def main():
    ap = argparse.ArgumentParser(description='MSS-VDP Rust Scanner')
    ap.add_argument('target', help='File or directory to scan')
    ap.add_argument('--json', action='store_true', help='JSON output')
    args = ap.parse_args()
    
    target = args.target
    if not os.path.exists(target):
        print(f"Error: {target} not found", file=sys.stderr)
        sys.exit(1)
    
    if os.path.isfile(target):
        result = scan_file(target)
        results = [result]
    else:
        results = scan_directory(target)
    
    if args.json:
        print(json.dumps(results if len(results) > 1 else results[0], indent=2, ensure_ascii=False))
    else:
        total_files = len(results)
        total_violations = sum(len(r.get('violations', [])) for r in results)
        rejects = sum(1 for r in results if r.get('verdict') == 'reject')
        print(f"Scanned {total_files} file(s): {rejects} reject(s), {total_violations} violation(s)")
        for r in results:
            vs = r.get('violations', [])
            if vs:
                print(f"\n  {r['target']}:")
                for v in vs:
                    print(f"    [{v['severity']:6s}] {v['rule_id']:12s} {v['loc']:6s} {v['kind']:25s} {v['detail'][:80]}")


if __name__ == '__main__':
    main()
