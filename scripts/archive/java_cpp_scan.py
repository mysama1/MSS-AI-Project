#!/usr/bin/env python3
"""
MSS-VDP Java/C/C++ Scanner — DEV-201
Static analysis with tree-sitter
"""
import sys, os, json, argparse
from pathlib import Path
from tree_sitter import Language, Parser, Node
import tree_sitter_java as tsj
import tree_sitter_cpp as tscpp
import tree_sitter_c as tsc

JAVA_LANG = Language(tsj.language())
CPP_LANG = Language(tscpp.language())
C_LANG = Language(tsc.language())

LANG_MAP = {
    '.java': JAVA_LANG, '.cpp': CPP_LANG, '.cc': CPP_LANG, '.cxx': CPP_LANG,
    '.hpp': CPP_LANG, '.h': C_LANG, '.c': C_LANG,
}


class Rule:
    def __init__(self, rule_id, severity, desc):
        self.rule_id = rule_id; self.severity = severity; self.description = desc
    def check(self, node: Node, content: str) -> list: return []


class RuleEngine:
    def __init__(self, lang: Language):
        self.parser = Parser(lang)
        self.rules: list[Rule] = []
    def register(self, r: Rule): self.rules.append(r)
    
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
        ext = os.path.splitext(path)[1]
        return {
            'target': path, 'target_type': ext,
            'total_lines': len(content.split('\n')),
            'violations': sorted(violations, key=lambda v: v['loc']),
            'verdict': 'reject' if any(v['severity']=='reject' for v in violations)
                       else 'warn' if violations else 'pass',
        }


# ── Java Rules ──

class J1_UnclosedResource(Rule):
    """Detect InputStream/Connection not in try-with-resources."""
    def __init__(self):
        super().__init__('J1_LEAK', 'warn', 'Resource opened without try-with-resources')
    def check(self, node, content):
        if node.type == 'local_variable_declaration':
            text = node.text.decode('utf-8')
            res_types = ['InputStream', 'OutputStream', 'Reader', 'Writer',
                        'Connection', 'Statement', 'ResultSet', 'Socket', 'Channel']
            opens = ['new FileInputStream', 'new FileOutputStream', 'new BufferedReader',
                    '.openConnection()', '.createStatement()', '.executeQuery(',
                    'new Socket(', 'Files.newInputStream']
            has_type = any(t in text for t in res_types)
            has_open = any(o in text for o in opens)
            if has_type and has_open:
                # Check if try block exists nearby in same method context
                line_num = node.start_point[0]
                nearby = '\n'.join(content.split('\n')[max(0,line_num-2):line_num+10])
                if 'try (' not in nearby and 'try(' not in nearby:
                    return [{
                        'rule_id': self.rule_id, 'severity': self.severity,
                        'loc': f'L{line_num+1}', 'kind': 'unclosed_resource',
                        'detail': 'Resource opened without try-with-resources — may leak',
                        'quote': content.split('\n')[line_num].strip()[:80]
                    }]
        return []


class J2_HttpNoTimeout(Rule):
    """Detect HttpURLConnection without setConnectTimeout."""
    def __init__(self):
        super().__init__('J2_TIMEOUT', 'warn', 'HTTP connection without timeout')
    def check(self, node, content):
        if node.type == 'local_variable_declaration' or node.type == 'expression_statement':
            text = node.text.decode('utf-8')
            if '.openConnection()' in text:
                line_num = node.start_point[0]
                nearby = '\n'.join(content.split('\n')[max(0,line_num-2):line_num+10])
                if 'setConnectTimeout' not in nearby and 'setReadTimeout' not in nearby:
                    return [{
                        'rule_id': self.rule_id, 'severity': self.severity,
                        'loc': f'L{line_num+1}', 'kind': 'http_no_timeout',
                        'detail': 'HttpURLConnection without setConnectTimeout/setReadTimeout',
                        'quote': content.split('\n')[line_num].strip()[:80]
                    }]
        return []


class J3_NullableReturn(Rule):
    """Detect public methods returning null without @Nullable."""
    def __init__(self):
        super().__init__('J3_NULL', 'warn', 'Nullable return without annotation')
    def check(self, node, content):
        if node.type == 'method_declaration':
            text = node.text.decode('utf-8')
            if 'public' in text[:50] and 'return null' in text:
                if '@Nullable' not in text and '@CheckForNull' not in text:
                    line = node.start_point[0] + 1
                    return [{
                        'rule_id': self.rule_id, 'severity': self.severity,
                        'loc': f'L{line}', 'kind': 'nullable_no_annotation',
                        'detail': 'Public method returns null without @Nullable annotation',
                        'quote': content.split('\n')[node.start_point[0]].strip()[:80]
                    }]
        return []


# ── C/C++ Rules ──

class C1_MallocNoFree(Rule):
    """Detect malloc/calloc/realloc without corresponding free."""
    def __init__(self):
        super().__init__('C1_MEMORY', 'reject', 'malloc without free')
    def check(self, node, content):
        if node.type == 'call_expression':
            text = node.text.decode('utf-8')
            if text.startswith('malloc(') or text.startswith('calloc(') or text.startswith('realloc('):
                fn_start = node.start_point[0]
                # Search nearby scope for free()
                nearby = '\n'.join(content.split('\n')[fn_start:fn_start+30])
                if 'free(' not in nearby:
                    return [{
                        'rule_id': self.rule_id, 'severity': self.severity,
                        'loc': f'L{fn_start+1}', 'kind': 'malloc_no_free',
                        'detail': 'malloc/calloc without corresponding free() in scope',
                        'quote': content.split('\n')[fn_start].strip()[:80]
                    }]
        return []


class C2_UnsafeString(Rule):
    """Detect strcpy/sprintf/gets without bounds check."""
    def __init__(self):
        super().__init__('C2_BUFFER', 'reject', 'Unsafe string operation')
    def check(self, node, content):
        if node.type == 'call_expression':
            text = node.text.decode('utf-8')
            unsafe = ['strcpy(', 'strcat(', 'sprintf(', 'gets(', 'scanf(']
            if any(text.startswith(u) for u in unsafe):
                line = node.start_point[0] + 1
                return [{
                    'rule_id': self.rule_id, 'severity': self.severity,
                    'loc': f'L{line}', 'kind': 'unsafe_string_op',
                    'detail': f'Unsafe {text.split("(")[0]} — use bounded alternative (snprintf, strncpy)',
                    'quote': content.split('\n')[node.start_point[0]].strip()[:80]
                }]
        return []


class C3_UnsafeNullDeref(Rule):
    """Detect potential null pointer dereference patterns."""
    def __init__(self):
        super().__init__('C3_NULLPTR', 'warn', 'Potential null pointer dereference')
    def check(self, node, content):
        if node.type == 'expression_statement':
            text = node.text.decode('utf-8')
            if '->' in text:
                varname = text.split('->')[0].strip()
                before = content[:node.start_byte]
                # Check if variable was checked for null before this point
                last_check = max(before.rfind(f'if ({varname})'), before.rfind(f'if({varname})'),
                               before.rfind(f'{varname} != NULL'), before.rfind(f'{varname} != nullptr'))
                if last_check < 0:
                    line = node.start_point[0] + 1
                    return [{
                        'rule_id': self.rule_id, 'severity': self.severity,
                        'loc': f'L{line}', 'kind': 'null_deref_risk',
                        'detail': f'Pointer dereference ({varname}->) without visible null check',
                        'quote': content.split('\n')[node.start_point[0]].strip()[:80]
                    }]
        return []


def create_java_engine() -> RuleEngine:
    e = RuleEngine(JAVA_LANG)
    e.register(J1_UnclosedResource())
    e.register(J2_HttpNoTimeout())
    e.register(J3_NullableReturn())
    return e

def create_cpp_engine() -> RuleEngine:
    e = RuleEngine(CPP_LANG)
    e.register(C1_MallocNoFree())
    e.register(C2_UnsafeString())
    e.register(C3_UnsafeNullDeref())
    return e

def create_c_engine() -> RuleEngine:
    e = RuleEngine(C_LANG)
    e.register(C1_MallocNoFree())
    e.register(C2_UnsafeString())
    e.register(C3_UnsafeNullDeref())
    return e

ENGINE_MAP = {
    '.java': create_java_engine, '.cpp': create_cpp_engine, '.cc': create_cpp_engine,
    '.cxx': create_cpp_engine, '.hpp': create_cpp_engine, '.h': create_c_engine, '.c': create_c_engine,
}


def scan_file(path: str) -> dict:
    ext = Path(path).suffix
    factory = ENGINE_MAP.get(ext)
    if not factory:
        return {'target': path, 'error': f'Unsupported: {ext}', 'violations': []}
    return factory().scan(path)


def main():
    ap = argparse.ArgumentParser(description='MSS-VDP Java/C/C++ Scanner')
    ap.add_argument('target', help='File or directory')
    ap.add_argument('--json', action='store_true')
    args = ap.parse_args()
    
    if not os.path.exists(args.target):
        print(f"Error: {args.target} not found", file=sys.stderr)
        sys.exit(1)
    
    if os.path.isfile(args.target):
        results = [scan_file(args.target)]
    else:
        results = []
        for root, dirs, files in os.walk(args.target):
            dirs[:] = [d for d in dirs if not d.startswith('.') and d not in ('node_modules', 'target', '.git', 'build', 'out')]
            for f in files:
                ext = Path(f).suffix
                if ext in LANG_MAP:
                    results.append(scan_file(os.path.join(root, f)))
    
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
                print(f"\n  {r['target']} ({r['target_type']}):")
                for v in vs:
                    print(f"    [{v['severity']:6s}] {v['rule_id']:12s} {v['loc']:6s} {v['kind']:25s} {v['detail'][:80]}")


if __name__ == '__main__':
    main()
