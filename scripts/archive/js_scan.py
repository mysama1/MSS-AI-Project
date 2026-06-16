#!/usr/bin/env python3
"""
MSS-VDP JS/TS Scanner — 真吞错检测
DEV-001 Block 1: Parser Shell + Rule Dispatch Framework
"""
import sys, os, json, re, argparse
from pathlib import Path
from tree_sitter import Language, Parser, Node
import tree_sitter_javascript as tsjs
import tree_sitter_typescript as tsts

# Language setup
JS_LANG = Language(tsjs.language())
TS_LANG = Language(tsts.language_typescript())
TSX_LANG = Language(tsts.language_tsx())

FILE_MAP = {
    '.js': JS_LANG, '.jsx': JS_LANG,
    '.ts': TS_LANG, '.tsx': TSX_LANG,
    '.mjs': JS_LANG, '.cjs': JS_LANG,
    '.mts': TS_LANG, '.cts': TS_LANG,
}

def detect_lang(path: str):
    ext = Path(path).suffix
    return FILE_MAP.get(ext)

# ── Rule Framework ──

class Rule:
    """Base class for JS/TS detection rules."""
    def __init__(self, rule_id: str, severity: str, description: str):
        self.rule_id = rule_id
        self.severity = severity  # reject | warn | info
        self.description = description
    
    def check(self, node: Node, content: str) -> list:
        """Return list of violation dicts for this node."""
        return []

class RuleEngine:
    def __init__(self, language: Language):
        self.parser = Parser(language)
        self.rules: list[Rule] = []
    
    def register(self, rule: Rule):
        self.rules.append(rule)
    
    def scan(self, path: str) -> dict:
        """Scan a file and return violations."""
        # Set current file on path-dependent rules
        for rule in self.rules:
            if hasattr(rule, '_current_file'):
                rule._current_file = path
        
        try:
            with open(path, 'r', encoding='utf-8', errors='replace') as f:
                content = f.read()
        except Exception as e:
            return {'target': path, 'error': str(e), 'violations': []}

        tree = self.parser.parse(content.encode('utf-8'))
        violations = []
        
        # Walk all nodes
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
            'target': path,
            'target_type': os.path.splitext(path)[1],
            'total_lines': len(content.split('\n')),
            'violations': sorted(violations, key=lambda v: v['loc']),
            'verdict': 'reject' if any(v['severity']=='reject' for v in violations)
                       else 'warn' if violations else 'pass',
        }


# ── Rule Implementations ──

class V2_EmptyCatch(Rule):
    """Detect empty catch blocks that silently swallow errors."""
    def __init__(self):
        super().__init__('V2_ERROR', 'reject', 'Empty catch block silently swallows error')
    
    def check(self, node: Node, content: str):
        if node.type == 'catch_clause':
            body = node.child_by_field_name('body')
            if body and body.type == 'statement_block':
                # Empty catch: no children besides { }
                children = [c for c in body.children if c.type not in ('{', '}')]
                if not children:
                    line = node.start_point[0] + 1
                    return [{
                        'rule_id': self.rule_id,
                        'severity': self.severity,
                        'loc': f'L{line}',
                        'kind': 'empty_catch',
                        'detail': 'Empty catch block swallows all errors silently',
                        'quote': content.split('\n')[node.start_point[0]].strip()[:80]
                    }]
        return []


class V1_MissingImport(Rule):
    """Detect import/require of non-existent files."""
    _current_file = None
    
    def __init__(self):
        super().__init__('V1_PATH', 'reject', 'Import references non-existent file')
    
    def check(self, node: Node, content: str):
        violations = []
        file_dir = os.path.dirname(os.path.abspath(self._current_file))
        
        # ESM: import ... from './path'
        if node.type == 'import_statement':
            source = node.child_by_field_name('source')
            if source:
                import_path = source.text.decode('utf-8').strip('"\'')
                if import_path.startswith('.') or import_path.startswith('/'):
                    # Relative or absolute path
                    resolved = os.path.normpath(os.path.join(file_dir, import_path))
                    # Try with extensions
                    for ext in ('', '.js', '.ts', '.jsx', '.tsx', '.mjs', '.cjs', '.mts', '.cts', '/index.js', '/index.ts'):
                        if os.path.exists(resolved + ext):
                            break
                    else:
                        line = node.start_point[0] + 1
                        violations.append({
                            'rule_id': self.rule_id, 'severity': self.severity,
                            'loc': f'L{line}', 'kind': 'missing_import',
                            'detail': f"Import path '{import_path}' not found: {resolved}",
                            'quote': content.split('\n')[node.start_point[0]].strip()[:80]
                        })
        
        # CJS: require('./path')
        if node.type == 'call_expression':
            func = node.child_by_field_name('function')
            if func and func.type == 'identifier' and func.text == b'require':
                args = node.child_by_field_name('arguments')
                if args:
                    first_arg = args.children[1] if len(args.children) > 1 else None  # skip (
                    if first_arg and first_arg.type == 'string':
                        req_path = first_arg.text.decode('utf-8').strip('"\'')
                        if req_path.startswith('.') or req_path.startswith('/'):
                            resolved = os.path.normpath(os.path.join(file_dir, req_path))
                            for ext in ('', '.js', '.ts', '.jsx', '.tsx', '.mjs', '.cjs', '.mts', '.cts', '/index.js', '/index.ts'):
                                if os.path.exists(resolved + ext):
                                    break
                            else:
                                line = node.start_point[0] + 1
                                violations.append({
                                    'rule_id': self.rule_id, 'severity': self.severity,
                                    'loc': f'L{line}', 'kind': 'missing_require',
                                    'detail': f"Require path '{req_path}' not found: {resolved}",
                                    'quote': content.split('\n')[node.start_point[0]].strip()[:80]
                                })
        return violations


class V5_NoTimeout(Rule):
    """Detect network calls without timeout."""
    def __init__(self):
        super().__init__('V5_TIMEOUT', 'warn', 'Network request without timeout')
    
    def check(self, node: Node, content: str):
        if node.type == 'call_expression':
            func = node.child_by_field_name('function')
            if func is None:
                return []
            
            # fetch() without signal/AbortController
            if func.type == 'identifier' and func.text == b'fetch':
                args = node.child_by_field_name('arguments')
                args_text = args.text.decode('utf-8') if args else ''
                if 'signal' not in args_text and 'AbortSignal' not in args_text:
                    line = node.start_point[0] + 1
                    return [{
                        'rule_id': self.rule_id, 'severity': self.severity,
                        'loc': f'L{line}', 'kind': 'fetch_no_timeout',
                        'detail': 'fetch() called without AbortSignal/timeout — request may hang indefinitely',
                        'quote': content.split('\n')[node.start_point[0]].strip()[:80]
                    }]
            
            # axios.get/post/etc without { timeout }
            if func.type == 'member_expression':
                obj = func.child_by_field_name('object')
                prop = func.child_by_field_name('property')
                if obj and obj.text == b'axios' and prop:
                    args = node.child_by_field_name('arguments')
                    args_text = args.text.decode('utf-8') if args else ''
                    if 'timeout' not in args_text:
                        line = node.start_point[0] + 1
                        return [{
                            'rule_id': self.rule_id, 'severity': self.severity,
                            'loc': f'L{line}', 'kind': 'axios_no_timeout',
                            'detail': 'axios request without timeout parameter',
                            'quote': content.split('\n')[node.start_point[0]].strip()[:80]
                        }]
        return []


class V8_MemoryLeak(Rule):
    """Detect potential memory leaks: missing cleanup."""
    def __init__(self):
        super().__init__('V8_LEAK', 'warn', 'Potential memory leak: missing cleanup')
    
    def check(self, node: Node, content: str):
        violations = []
        
        # useEffect without cleanup return
        if node.type == 'call_expression':
            func = node.child_by_field_name('function')
            if func and func.type == 'identifier' and func.text == b'useEffect':
                args = node.child_by_field_name('arguments')
                if args:
                    body_text = content[node.start_byte:node.end_byte]
                    if ('subscribe(' in body_text or 'addEventListener(' in body_text or 'setInterval(' in body_text) and 'return' not in body_text:
                        line = node.start_point[0] + 1
                        violations.append({
                            'rule_id': self.rule_id, 'severity': self.severity,
                            'loc': f'L{line}', 'kind': 'useEffect_no_cleanup',
                            'detail': 'useEffect with subscription/listener but no cleanup return function',
                            'quote': content.split('\n')[node.start_point[0]].strip()[:80]
                        })
        
        # addEventListener without matching removeEventListener
        if node.type == 'call_expression':
            func = node.child_by_field_name('function')
            if func and func.type == 'member_expression':
                prop = func.child_by_field_name('property')
                if prop and prop.text == b'addEventListener':
                    # Use AST to find actual removeEventListener calls (not string search)
                    found_remove = False
                    cursor2 = node.walk()
                    root = node
                    while root.parent:
                        root = root.parent
                    root_cursor = root.walk()
                    def search_remove(cursor):
                        nonlocal found_remove
                        n = cursor.node
                        if n.type == 'call_expression':
                            nf = n.child_by_field_name('function')
                            if nf and nf.type == 'member_expression':
                                np = nf.child_by_field_name('property')
                                if np and np.text == b'removeEventListener':
                                    found_remove = True
                                    return
                        if cursor.goto_first_child():
                            search_remove(cursor)
                            while cursor.goto_next_sibling():
                                search_remove(cursor)
                            cursor.goto_parent()
                    search_remove(root_cursor)
                    if not found_remove:
                        line = node.start_point[0] + 1
                        violations.append({
                            'rule_id': self.rule_id, 'severity': self.severity,
                            'loc': f'L{line}', 'kind': 'addEventListener_no_remove',
                            'detail': 'addEventListener used but no removeEventListener call found',
                            'quote': content.split('\n')[node.start_point[0]].strip()[:80]
                        })
        
        # setInterval without clearInterval
        if node.type == 'call_expression':
            func = node.child_by_field_name('function')
            if func and func.type == 'identifier' and func.text == b'setInterval':
                found_clear = False
                root = node
                while root.parent:
                    root = root.parent
                root_cursor = root.walk()
                def search_clear(cursor):
                    nonlocal found_clear
                    n = cursor.node
                    if n.type == 'call_expression':
                        nf = n.child_by_field_name('function')
                        if nf and nf.type == 'identifier' and nf.text == b'clearInterval':
                            found_clear = True
                            return
                    if cursor.goto_first_child():
                        search_clear(cursor)
                        while cursor.goto_next_sibling():
                            search_clear(cursor)
                        cursor.goto_parent()
                search_clear(root_cursor)
                if not found_clear:
                    line = node.start_point[0] + 1
                    violations.append({
                        'rule_id': self.rule_id, 'severity': self.severity,
                        'loc': f'L{line}', 'kind': 'setInterval_no_clear',
                        'detail': 'setInterval used but no clearInterval call found',
                        'quote': content.split('\n')[node.start_point[0]].strip()[:80]
                    })
        
        return violations


class V9_AsyncTrap(Rule):
    """Detect async patterns that silently swallow errors."""
    def __init__(self):
        super().__init__('V9_ASYNC', 'warn', 'Async pattern that may silently fail')
    
    def check(self, node: Node, content: str):
        if node.type == 'call_expression':
            func = node.child_by_field_name('function')
            if func and func.type == 'member_expression':
                prop = func.child_by_field_name('property')
                if prop and prop.text == b'forEach':
                    args = node.child_by_field_name('arguments')
                    if args:
                        args_text = content[args.start_byte:args.end_byte]
                        if 'async' in args_text:
                            line = node.start_point[0] + 1
                            return [{
                                'rule_id': self.rule_id, 'severity': self.severity,
                                'loc': f'L{line}', 'kind': 'forEach_async',
                                'detail': 'Array.forEach() with async callback — iterations are not awaited',
                                'quote': content.split('\n')[node.start_point[0]].strip()[:80]
                            }]
        return []


class V2_UnhandledPromise(Rule):
    """Detect .then() chains without .catch()."""
    def __init__(self):
        super().__init__('V2_ERROR', 'warn', 'Promise chain without error handler')
    
    def check(self, node: Node, content: str):
        if node.type == 'call_expression':
            # Check if this is a .then() call
            func = node.child_by_field_name('function')
            if func and func.type == 'member_expression':
                prop = func.child_by_field_name('property')
                if prop and prop.text == b'then':
                    # Walk up to find if there's a .catch() anywhere in the chain
                    current = node
                    has_catch = False
                    # Check parent chain
                    for _ in range(5):
                        parent = current.parent
                        if parent is None:
                            break
                        if parent.type == 'call_expression':
                            pf = parent.child_by_field_name('function')
                            if pf and pf.type == 'member_expression':
                                pp = pf.child_by_field_name('property')
                                if pp and pp.text in (b'catch', b'finally'):
                                    has_catch = True
                                    break
                        elif parent.type == 'expression_statement':
                            break
                        current = parent
                    
                    if not has_catch:
                        line = node.start_point[0] + 1
                        return [{
                            'rule_id': self.rule_id,
                            'severity': self.severity,
                            'loc': f'L{line}',
                            'kind': 'unhandled_promise',
                            'detail': 'Promise .then() chain without .catch() error handler',
                            'quote': content.split('\n')[node.start_point[0]].strip()[:80]
                        }]
        return []


# ── CLI ──

def create_engine(ext: str) -> RuleEngine:
    """Create a RuleEngine with all registered rules for the given file type."""
    lang = FILE_MAP.get(ext)
    if lang is None:
        raise ValueError(f"Unsupported file type: {ext}")
    engine = RuleEngine(lang)
    engine.register(V2_EmptyCatch())
    engine.register(V2_UnhandledPromise())
    engine.register(V1_MissingImport())
    engine.register(V5_NoTimeout())
    engine.register(V8_MemoryLeak())
    engine.register(V9_AsyncTrap())
    return engine


def scan_file(path: str) -> dict:
    ext = Path(path).suffix
    engine = create_engine(ext)
    return engine.scan(path)


def scan_directory(directory: str) -> list:
    results = []
    for root, dirs, files in os.walk(directory):
        dirs[:] = [d for d in dirs if not d.startswith('.') and d not in ('node_modules', '__pycache__', '.git', 'dist', 'build')]
        for f in files:
            ext = Path(f).suffix
            if ext in FILE_MAP:
                results.append(scan_file(os.path.join(root, f)))
    return results


def main():
    ap = argparse.ArgumentParser(description='MSS-VDP JS/TS Scanner')
    ap.add_argument('target', help='File or directory to scan')
    ap.add_argument('--json', action='store_true', help='JSON output')
    ap.add_argument('--rules', nargs='*', help='Specific rules to run')
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
                print(f"\n  {r['target']} ({r['target_type']}):")
                for v in vs:
                    print(f"    [{v['severity']:6s}] {v['rule_id']:12s} {v['loc']:6s} {v['kind']:25s} {v['detail'][:60]}")


if __name__ == '__main__':
    main()
