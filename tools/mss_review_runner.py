#!/usr/bin/env python3
"""
D5-040 Phase 2: MSS Code Review Runner
Integrates agent-skills review process (5-axis) with MSS 3-axis (logical_rigidity / thermal_tax / meaning_fidelity)
v0.1 - 2026-05-31
"""
import ast, os, sys, json, re, argparse
from dataclasses import dataclass, field
from typing import List, Dict, Optional
from datetime import datetime
from enum import Enum

# ===== Agent-Skills → MSS Axis Mapping =====
class MSSLevel(Enum):
    P0 = "P0"  # Logical rigidity failure (axiom violation, security, correctness)
    P1 = "P1"  # High thermal tax / meaning mismatch
    P2 = "P2"  # Moderate issue (readability, style)
    INFO = "INFO"

@dataclass
class ReviewFinding:
    level: MSSLevel
    axis: str       # logical_rigidity | thermal_tax | meaning_fidelity
    k3_source: str  # correctness | security | performance | readability | architecture
    line: int
    message: str
    code_snippet: str = ""
    fix_suggestion: str = ""
    axiom: str = ""  # A1-A6 anchor

@dataclass
class MSSReviewReport:
    file_path: str
    lines_total: int = 0
    functions: int = 0
    classes: int = 0
    findings: List[ReviewFinding] = field(default_factory=list)
    logical_rigidity_score: float = 100.0
    thermal_tax_index: float = 0.0
    meaning_fidelity_score: float = 100.0
    mss_total_score: float = 100.0
    review_time: str = field(default_factory=lambda: datetime.now().isoformat())
    verdict: str = "APPROVE"

    def to_dict(self):
        return {
            "file": self.file_path,
            "lines": self.lines_total,
            "functions": self.functions,
            "classes": self.classes,
            "scores": {
                "logical_rigidity": round(self.logical_rigidity_score, 1),
                "thermal_tax_index": round(self.thermal_tax_index, 1),
                "meaning_fidelity": round(self.meaning_fidelity_score, 1),
                "mss_total": round(self.mss_total_score, 1)
            },
            "findings": [{
                "level": f.level.value,
                "axis": f.axis,
                "k3_source": f.k3_source,
                "line": f.line,
                "message": f.message,
                "code_snippet": f.code_snippet[:80],
                "fix": f.fix_suggestion,
                "axiom": f.axiom
            } for f in self.findings],
            "verdict": self.verdict,
            "review_time": self.review_time
        }


class MSSReviewRunner:
    """MSS-adapted code reviewer combining agent-skills 5-axis + MSS 3-axis."""

    MEANING_STEAL_PATTERNS = [
        (r'def (calculate_\w+|compute_\w+|get_\w+|find_\w+)', 'Function name implies computation, verify return value'),
    ]
    HIGH_TAX_PATTERNS = [
        (r'for\s+\w+\s+in\s+range\(.*\):\s*\n\s+for\s+\w+\s+in\s+range', 'Nested range loops → O(n²) thermal tax'),
        (r'while\s+True', 'Unbounded while loop → potential thermal tax singularity'),
        (r'\.read\(\)\s*$', 'Unbounded file read → memory explosion risk'),
    ]
    LOGIC_VIRUS_PATTERNS = [
        (r'except\s*:', 'Bare except catches all → swallows logic errors'),
        (r'except\s+Exception\s+as\s+e:\s*\n\s+pass', 'Exception silenced → meaning destruction'),
        (r'assert\s+False', 'Unreachable assertion → dead code'),
        (r'#\s*TODO|#\s*FIXME|#\s*HACK', 'Deferred technical debt → accumulating thermal tax (A3)'),
    ]

    def __init__(self, filepath: str):
        self.filepath = filepath
        self.source = ""
        self.tree = None
        self.report = MSSReviewReport(file_path=filepath)

    def run(self) -> MSSReviewReport:
        try:
            with open(self.filepath, 'r', encoding='utf-8', errors='ignore') as f:
                self.source = f.read()
        except Exception as e:
            self.report.findings.append(ReviewFinding(
                MSSLevel.P0, "logical_rigidity", "correctness", 0,
                f"Failed to read file: {e}"
            ))
            self.report.verdict = "REJECT"
            return self.report

        self.report.lines_total = len(self.source.split('\n'))

        # Phase 1: AST parsing (correctness + architecture)
        self._check_ast()

        # Phase 2: Regex pattern scan (performance + security)
        self._scan_patterns()

        # Phase 3: Structure analysis (readability + meaning fidelity)
        self._analyze_structure()

        # Phase 4: Calculate scores
        self._calculate_scores()

        # Phase 5: Verdict
        self._render_verdict()

        return self.report

    def _check_ast(self):
        """Correctness: Can this file parse? Architecture: What's the structure?"""
        try:
            self.tree = ast.parse(self.source)
            funcs = [n for n in ast.walk(self.tree) if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))]
            classes = [n for n in ast.walk(self.tree) if isinstance(n, ast.ClassDef)]
            self.report.functions = len(funcs)
            self.report.classes = len(classes)

            # Check: functions named calculate_* that have no return
            for node in funcs:
                if node.name.lower().startswith(('calculate', 'compute', 'get_')):
                    has_return = any(isinstance(n, ast.Return) and n.value is not None
                                     for n in ast.walk(node))
                    if not has_return and not any(isinstance(n, ast.Yield) for n in ast.walk(node)):
                        self.report.findings.append(ReviewFinding(
                            MSSLevel.P0, "meaning_fidelity", "correctness", node.lineno,
                            f"Meaning theft: '{node.name}' declared as calculation but has no return value",
                            code_snippet=self._get_line(node.lineno),
                            fix_suggestion="Add return statement or rename function",
                            axiom="A2"
                        ))

            # Check: empty functions
            for node in funcs:
                body = node.body
                if len(body) == 1 and isinstance(body[0], ast.Pass):
                    self.report.findings.append(ReviewFinding(
                        MSSLevel.P1, "meaning_fidelity", "readability", node.lineno,
                        f"Meaning void: '{node.name}' is pass-only stub",
                        fix_suggestion="Implement or mark with NotImplementedError",
                        axiom="A2"
                    ))

        except SyntaxError as e:
            self.report.findings.append(ReviewFinding(
                MSSLevel.P0, "logical_rigidity", "correctness", e.lineno or 0,
                f"Syntax error: {e.msg}",
                code_snippet=e.text or "",
                fix_suggestion="Fix syntax",
                axiom="A1"
            ))

    def _scan_patterns(self):
        """Performance + Security pattern matching."""
        lines = self.source.split('\n')

        # High thermal tax patterns
        for pattern, msg in self.HIGH_TAX_PATTERNS:
            for m in re.finditer(pattern, self.source, re.MULTILINE):
                lineno = self.source[:m.start()].count('\n') + 1
                self.report.findings.append(ReviewFinding(
                    MSSLevel.P1, "thermal_tax", "performance", lineno,
                    msg,
                    code_snippet=lines[lineno-1].strip()[:80] if lineno <= len(lines) else "",
                    fix_suggestion="Consider algorithmic optimization or bounded iteration",
                    axiom="A3"
                ))

        # Logic virus patterns (security + correctness)
        for pattern, msg in self.LOGIC_VIRUS_PATTERNS:
            for m in re.finditer(pattern, self.source, re.MULTILINE):
                lineno = self.source[:m.start()].count('\n') + 1
                level = MSSLevel.P0 if 'except' in pattern else MSSLevel.P2
                self.report.findings.append(ReviewFinding(
                    level, "logical_rigidity", "security", lineno,
                    msg,
                    code_snippet=lines[lineno-1].strip()[:80] if lineno <= len(lines) else "",
                    fix_suggestion="Use specific exception types / remove dead code",
                    axiom="A6" if 'assert False' in pattern else "A3"
                ))

        # Dead code detection: import X but X never used
        imported = set()
        for m in re.finditer(r'^import\s+(\w+)', self.source, re.MULTILINE):
            imported.add(m.group(1))
        for m in re.finditer(r'^from\s+(\w+)', self.source, re.MULTILINE):
            imported.add(m.group(1))
        for mod in imported:
            # Check if module name appears elsewhere (minus the import line)
            pattern_check = re.compile(r'\b' + re.escape(mod) + r'\b')
            occurrences = len(pattern_check.findall(self.source))
            if occurrences <= 2:  # Only appears in import + maybe 1 reference
                self.report.findings.append(ReviewFinding(
                    MSSLevel.P2, "thermal_tax", "architecture", 0,
                    f"Possibly unused import: '{mod}'",
                    fix_suggestion=f"Remove 'import {mod}' if unused",
                    axiom="A3"
                ))

    def _analyze_structure(self):
        """Readability + Meaning Fidelity analysis."""
        lines = self.source.split('\n')

        # Long lines (>120 chars)
        long_lines = [(i, l) for i, l in enumerate(lines, 1) if len(l) > 120 and not l.strip().startswith('#')]
        for lineno, line in long_lines[:5]:
            self.report.findings.append(ReviewFinding(
                MSSLevel.P2, "meaning_fidelity", "readability", lineno,
                f"Line too long ({len(line)} chars) — reduces meaning fidelity",
                code_snippet=line[:80],
                fix_suggestion="Break into multiple lines",
                axiom="A2"
            ))

        # Functions > 50 lines
        if self.tree:
            for node in ast.walk(self.tree):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    end = max(getattr(n, 'end_lineno', node.lineno) for n in ast.walk(node) if hasattr(n, 'lineno'))
                    length = end - node.lineno + 1
                    if length > 50:
                        self.report.findings.append(ReviewFinding(
                            MSSLevel.P1, "thermal_tax", "readability", node.lineno,
                            f"Function '{node.name}' is {length} lines — consider splitting (A3: high γ)",
                            fix_suggestion=f"Extract sub-functions to reduce to <50 lines",
                            axiom="A3"
                        ))

    def _calculate_scores(self):
        p0 = sum(1 for f in self.report.findings if f.level == MSSLevel.P0)
        p1 = sum(1 for f in self.report.findings if f.level == MSSLevel.P1)
        p2 = sum(1 for f in self.report.findings if f.level == MSSLevel.P2)
        rigidity_p0 = sum(1 for f in self.report.findings if f.level == MSSLevel.P0 and f.axis == "logical_rigidity")
        tax_p1 = sum(1 for f in self.report.findings if f.axis == "thermal_tax")
        fid_p0 = sum(1 for f in self.report.findings if f.axis == "meaning_fidelity" and f.level == MSSLevel.P0)

        self.report.logical_rigidity_score = max(0, 100 - rigidity_p0 * 20 - p1 * 3)
        self.report.thermal_tax_index = min(100, tax_p1 * 5 + p2 * 1)
        self.report.meaning_fidelity_score = max(0, 100 - fid_p0 * 25 - p1 * 2 - p2 * 0.5)
        self.report.mss_total_score = round(
            self.report.logical_rigidity_score * 0.4 +
            (100 - self.report.thermal_tax_index) * 0.3 +
            self.report.meaning_fidelity_score * 0.3,
            1
        )

    def _render_verdict(self):
        if any(f.level == MSSLevel.P0 for f in self.report.findings):
            self.report.verdict = "REJECT — P0 issues must be fixed"
        elif self.report.thermal_tax_index > 30:
            self.report.verdict = "REQUEST_CHANGES — High thermal tax"
        elif self.report.mss_total_score < 60:
            self.report.verdict = "REQUEST_CHANGES — Score below threshold"
        else:
            self.report.verdict = "APPROVE"

    def _get_line(self, lineno: int) -> str:
        lines = self.source.split('\n')
        if 0 < lineno <= len(lines):
            return lines[lineno - 1].strip()[:80]
        return ""


def review_file(filepath: str, output_json: bool = True) -> Dict:
    runner = MSSReviewRunner(filepath)
    report = runner.run()
    result = report.to_dict()
    if output_json:
        print(json.dumps(result, indent=2, ensure_ascii=False))
    return result

def review_project(root_path: str, pattern: str = "*.py") -> List[Dict]:
    results = []
    for dirpath, dirs, files in os.walk(root_path):
        dirs[:] = [d for d in dirs if d not in ('__pycache__','node_modules','.git','.venv',
                                                  'unsloth_compiled_cache','releases','backups','archive')]
        for f in files:
            if not f.endswith('.py'): continue
            fp = os.path.join(dirpath, f)
            try:
                runner = MSSReviewRunner(fp)
                report = runner.run()
                results.append(report.to_dict())
            except: pass

    # Aggregate
    total = len(results)
    approved = sum(1 for r in results if r['verdict'].startswith('APPROVE'))
    rejected = sum(1 for r in results if 'REJECT' in r['verdict'])
    avg_score = sum(r['scores']['mss_total'] for r in results) / max(total, 1)

    summary = {
        "project": root_path,
        "files_reviewed": total,
        "approved": approved,
        "rejected": rejected,
        "changes_requested": total - approved - rejected,
        "avg_mss_score": round(avg_score, 1),
        "details": results
    }
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    return summary


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="MSS Code Review Runner (D5-040)")
    ap.add_argument("target", help="File or directory to review")
    ap.add_argument("--project", "-p", action="store_true", help="Review entire project")
    ap.add_argument("--min-score", type=float, default=60, help="Minimum score threshold")
    args = ap.parse_args()

    if args.project:
        review_project(args.target)
    else:
        review_file(args.target)