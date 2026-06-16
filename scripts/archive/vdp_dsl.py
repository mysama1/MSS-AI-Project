#!/usr/bin/env python3
"""
DEV-204: VDP Rules DSL
Define custom VDP rules in YAML — no Python required.
"""
import re
import json
import sys
from typing import Dict, List, Any

# ── DSL Definition (YAML-like dict) ──

SAMPLE_DSL = {
    "version": "1.0",
    "rules": [
        {
            "id": "CUSTOM-001",
            "name": "no-debug-print",
            "severity": "warn",
            "description": "Detect debug print statements in production code",
            "pattern": {
                "type": "regex",
                "match": r"(?m)^.*console\.(log|debug|warn)\(.*\).*$",
                "context": 2,
            },
            "suggestion": "Replace with proper logger.info/warn/error"
        },
        {
            "id": "CUSTOM-002",
            "name": "no-hardcoded-secrets",
            "severity": "reject",
            "description": "Detect hardcoded credentials, API keys, tokens",
            "pattern": {
                "type": "regex",
                "match": r"(?im)(password|secret|token|api_key|apikey)\s*[:=]\s*[\"\\'][^\"\\']{8,}[\"\\']",
            },
            "suggestion": "Use environment variables or secure vault"
        },
        {
            "id": "CUSTOM-003",
            "name": "todo-without-ticket",
            "severity": "info",
            "description": "TODO comments without JIRA/GitHub issue reference",
            "pattern": {
                "type": "regex",
                "match": r"(?im)^.*TODO:?(?!.*(?:#\d+|TICKET|ISSUE)).*$",
            },
            "suggestion": "Add ticket reference: TODO(#123): description"
        },
        {
            "id": "CUSTOM-004",
            "name": "mutating-foreign-state",
            "severity": "warn",
            "description": "Mutating props/state from parent (React anti-pattern)",
            "pattern": {
                "type": "regex",
                "match": r"(?m)^.*props\.\w+\s*=.*$",
            },
            "suggestion": "Use setState or callback pattern instead"
        },
        {
            "id": "CUSTOM-005",
            "name": "unbounded-any-type",
            "severity": "warn",
            "description": "TypeScript 'any' type without justification comment",
            "pattern": {
                "type": "regex",
                "match": r":\s*any\b",
                "context_before": 1,
                "exclude": ["// justified", "// intentional", "// TODO: type"],
            },
            "suggestion": "Add // justified comment or use proper type"
        },
    ]
}


class DSLRule:
    """A compiled rule from DSL."""
    def __init__(self, rule_def: Dict):
        self.rule_id = rule_def['id']
        self.name = rule_def.get('name', '')
        self.severity = rule_def.get('severity', 'warn')
        self.description = rule_def.get('description', '')
        self.suggestion = rule_def.get('suggestion', '')
        
        pattern = rule_def.get('pattern', {})
        self.pattern_type = pattern.get('type', 'regex')
        self.match = re.compile(pattern['match'])
        self.context = pattern.get('context', 0)
        self.exclude = [re.compile(e) for e in pattern.get('exclude', [])]
    
    def check(self, content: str, filename: str = '') -> List[Dict]:
        violations = []
        lines = content.split('\n')
        
        for i, line in enumerate(lines):
            if self.match.search(line):
                # Check exclusions
                if any(e.search(line) for e in self.exclude):
                    continue
                
                violations.append({
                    'rule_id': self.rule_id,
                    'severity': self.severity,
                    'loc': f'L{i+1}',
                    'kind': self.name,
                    'detail': f'{self.description}: "{line.strip()[:60]}"',
                    'suggestion': self.suggestion,
                    'context': lines[max(0,i-self.context):i+self.context+1],
                })
        
        return violations


class DSLRuleEngine:
    """Load and execute VDP rules from DSL definitions."""
    
    def __init__(self):
        self.rules: List[DSLRule] = []
    
    def load(self, dsl: Dict[str, Any]):
        """Load rules from DSL dict or JSON file."""
        for rule_def in dsl.get('rules', []):
            self.rules.append(DSLRule(rule_def))
    
    def load_file(self, path: str):
        """Load from JSON or YAML file."""
        ext = path.rsplit('.', 1)[-1].lower()
        with open(path, 'r', encoding='utf-8') as f:
            if ext in ('yaml', 'yml'):
                import yaml
                dsl = yaml.safe_load(f)
            else:
                dsl = json.load(f)
        self.load(dsl)
    
    def scan_content(self, content: str, filename: str = '') -> List[Dict]:
        violations = []
        for rule in self.rules:
            violations.extend(rule.check(content, filename))
        return sorted(violations, key=lambda v: v['loc'])
    
    def scan_file(self, path: str) -> dict:
        try:
            with open(path, 'r', encoding='utf-8', errors='replace') as f:
                content = f.read()
        except Exception as e:
            return {'target': path, 'error': str(e), 'violations': []}
        
        violations = self.scan_content(content, path)
        return {
            'target': path,
            'total_lines': len(content.split('\n')),
            'violations': violations,
            'verdict': 'reject' if any(v['severity']=='reject' for v in violations)
                       else 'warn' if violations else 'pass',
        }


def main():
    import argparse, os
    ap = argparse.ArgumentParser(description='MSS-VDP Rules DSL Checker')
    ap.add_argument('target', help='File or directory to scan')
    ap.add_argument('--rules', default='', help='Path to DSL rules file (JSON)')
    ap.add_argument('--demo', action='store_true', help='Run with built-in demo rules')
    ap.add_argument('--json', action='store_true', help='JSON output')
    args = ap.parse_args()
    
    engine = DSLRuleEngine()
    
    if args.rules:
        engine.load_file(args.rules)
    elif args.demo:
        engine.load(SAMPLE_DSL)
    else:
        engine.load(SAMPLE_DSL)
    
    if os.path.isfile(args.target):
        results = [engine.scan_file(args.target)]
    else:
        results = []
        for root, dirs, files in os.walk(args.target):
            dirs[:] = [d for d in dirs if not d.startswith('.') and d not in ('node_modules', '.git', 'target')]
            for f in files:
                if f.endswith(('.js', '.ts', '.tsx', '.py', '.java', '.rs', '.cpp', '.c')):
                    results.append(engine.scan_file(os.path.join(root, f)))
    
    if args.json:
        print(json.dumps(results if len(results) > 1 else results[0], indent=2, ensure_ascii=False))
    else:
        total = sum(len(r.get('violations', [])) for r in results)
        rejects = sum(1 for r in results if r.get('verdict') == 'reject')
        print(f"DSL Scan: {len(results)} files, {rejects} rejects, {total} violations")
        for r in results:
            vs = r.get('violations', [])
            if vs:
                print(f"\n  {r['target']}:")
                for v in vs:
                    print(f"    [{v['severity']:6s}] {v['rule_id']:14s} {v['loc']:6s} {v['detail'][:80]}")


if __name__ == '__main__':
    main()
