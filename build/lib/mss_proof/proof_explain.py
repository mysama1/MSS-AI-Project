"""
MSS-Proof: Human-Readable Proof Explainer v1.0
===============================================
Converts proof chains into structured natural language,
Markdown, and LaTeX formats. Supports both simple proof
chains and Z3-generated counterexample explanations.

Phase 1 M1.2 | D5-033 楔子穿刺项目
"""

from typing import Dict, List, Optional
from dataclasses import dataclass, field
from proof_search import ProofResult, ProofState
from tptp_parser import TPTPProblem


# ============================================================
# Explainer Core
# ============================================================

class ProofExplainer:
    """Convert proof results to human-readable formats"""

    def __init__(self):
        self.style = "academic"  # academic | tutorial | concise

    def explain(self, result: ProofResult,
                problem: Optional[TPTPProblem] = None) -> str:
        """
        Generate a structured proof explanation in natural language.
        """
        lines = []
        lines.append("=" * 60)
        lines.append("  Proof Analysis Report")
        lines.append("=" * 60)
        lines.append("")

        # Status
        if result.success:
            lines.append("Verdict: ✅ THEOREM PROVED")
        else:
            lines.append("Verdict: ❌ NOT PROVED")

        # Problem info
        if problem:
            lines.append(f"Problem: {problem.name or '(unnamed)'}")
            lines.append(f"  Axioms: {len(problem.axioms)}")
            lines.append(f"  Conjectures: {len(problem.conjectures)}")
            if problem.language:
                lines.append(f"  Language: {problem.language}")

        lines.append("")

        # Proof stats
        lines.append("--- Proof Statistics ---")
        lines.append(f"  Strategy:      {result.strategy}")
        lines.append(f"  Depth:         {result.depth}")
        lines.append(f"  Nodes explored: {result.nodes_explored}")
        lines.append(f"  Heat tax:       {result.heat_tax:.4f}")
        lines.append(f"  Time:           {result.time_ms:.0f}ms")
        lines.append("")

        # Proof chain
        if result.proof_chain:
            lines.append("--- Proof Chain ---")
            for i, step in enumerate(result.proof_chain):
                lines.append(f"  [{i+1}] {step}")
        else:
            lines.append("--- Proof Chain: (direct Z3 verification) ---")

        lines.append("")

        # Counterexample (if failed)
        if result.counterexample:
            lines.append("--- Counterexample ---")
            for k, v in result.counterexample.items():
                lines.append(f"  {k}: {v}")

        lines.append("=" * 60)
        return "\n".join(lines)

    def to_markdown(self, result: ProofResult,
                    problem: Optional[TPTPProblem] = None) -> str:
        """Export proof as Markdown"""
        lines = []
        lines.append(f"# Proof Analysis: {problem.name if problem else 'Inline'}")
        lines.append("")

        # Status badge
        status_badge = "✅ **PROVED**" if result.success else "❌ **FAILED**"
        lines.append(f"**Status:** {status_badge}")
        lines.append("")

        # Stats table
        lines.append("## Proof Statistics")
        lines.append("")
        lines.append("| Metric | Value |")
        lines.append("|--------|-------|")
        lines.append(f"| Strategy | `{result.strategy}` |")
        lines.append(f"| Depth | {result.depth} |")
        lines.append(f"| Nodes Explored | {result.nodes_explored} |")
        lines.append(f"| Heat Tax (η) | {result.heat_tax:.4f} |")
        lines.append(f"| Time | {result.time_ms:.0f}ms |")
        lines.append("")

        # Proof chain
        if result.proof_chain:
            lines.append("## Proof Chain")
            lines.append("")
            for i, step in enumerate(result.proof_chain):
                lines.append(f"{i+1}. `{step}`")
            lines.append("")
        else:
            lines.append("## Proof Chain")
            lines.append("")
            lines.append("> Direct Z3 verification — no search required")
            lines.append("")

        # Counterexample
        if result.counterexample:
            lines.append("## Counterexample")
            lines.append("")
            for k, v in result.counterexample.items():
                lines.append(f"- **{k}**: `{v}`")
            lines.append("")

        return "\n".join(lines)

    def to_latex(self, result: ProofResult,
                 problem: Optional[TPTPProblem] = None) -> str:
        """Export proof as LaTeX (for academic papers)"""
        lines = []
        lines.append(r"\begin{proof}")
        lines.append(r"  \textbf{Strategy:} " + result.strategy + r"\\")
        lines.append(r"  \textbf{Depth:} " + str(result.depth) + r"\\")
        lines.append(r"  \textbf{Nodes:} " + str(result.nodes_explored) + r"\\")
        lines.append(r"  \textbf{Heat Tax ($\eta$):} " + f"{result.heat_tax:.4f}" + r"\\")
        lines.append(r"  \textbf{Time:} " + f"{result.time_ms:.0f}" + r"ms\\")
        lines.append("")

        if result.proof_chain:
            lines.append(r"  \begin{enumerate}")
            for step in result.proof_chain:
                # Escape LaTeX special chars
                safe_step = step.replace("_", r"\_").replace("&", r"\&")
                lines.append(r"    \item \texttt{" + safe_step + "}")
            lines.append(r"  \end{enumerate}")
        else:
            lines.append(r"  \textit{Direct Z3 verification.}")
            lines.append("")

        lines.append(r"\end{proof}")
        return "\n".join(lines)

    def to_html(self, result: ProofResult,
                problem: Optional[TPTPProblem] = None) -> str:
        """Export proof as HTML"""
        status_class = "success" if result.success else "failure"
        status_text = "✅ PROVED" if result.success else "❌ FAILED"

        html = f"""<!DOCTYPE html>
<html><head><meta charset="utf-8">
<title>Proof: {problem.name if problem else 'Inline'}</title>
<style>
  body {{ font-family: system-ui; max-width: 700px; margin: 2em auto; padding: 0 1em; }}
  .header {{ background: {'#d4edda' if result.success else '#f8d7da'}; padding: 1em; border-radius: 8px; }}
  table {{ border-collapse: collapse; width: 100%; }}
  th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
  .proof-step {{ font-family: monospace; padding: 4px 0; }}
</style></head><body>
<h1>Proof Analysis</h1>
<div class="header">
  <strong>Status: {status_text}</strong><br>
  Strategy: {result.strategy} | Depth: {result.depth} | Nodes: {result.nodes_explored}
</div>
<h2>Statistics</h2>
<table>
  <tr><th>Metric</th><th>Value</th></tr>
  <tr><td>Heat Tax</td><td>{result.heat_tax:.4f}</td></tr>
  <tr><td>Time</td><td>{result.time_ms:.0f}ms</td></tr>
</table>
<h2>Proof Chain</h2>
<ol>
"""
        for step in result.proof_chain:
            html += f'  <li class="proof-step">{step}</li>\n'
        html += "</ol>\n</body></html>"
        return html


# ============================================================
# Self-Tests
# ============================================================

def _test():
    """ProofExplainer self-tests"""
    from proof_search import ProofResult

    # Build a mock result
    result = ProofResult(
        success=True,
        proof_chain=[
            "Z3: axioms ⊨ ['c1']",
            "R0: goal 'c1' already proved",
        ],
        depth=1,
        heat_tax=0.0,
        time_ms=12.5,
        nodes_explored=1,
        strategy="z3_direct",
    )

    explainer = ProofExplainer()

    # Test 1: Natural language
    text = explainer.explain(result)
    assert "THEOREM PROVED" in text
    assert "12" in text  # 12.5ms → 12ms (rounded)
    print("PASS: Natural language explanation generated")

    # Test 2: Markdown
    md = explainer.to_markdown(result)
    assert "**PROVED**" in md
    assert "| Heat Tax" in md
    print("PASS: Markdown export")

    # Test 3: LaTeX
    latex = explainer.to_latex(result)
    assert r"\begin{proof}" in latex
    assert r"\end{proof}" in latex
    print("PASS: LaTeX export")

    # Test 4: HTML
    html = explainer.to_html(result)
    assert "<!DOCTYPE html>" in html
    assert "PROVED" in html
    print("PASS: HTML export")

    # Test 5: Failed result
    fail_result = ProofResult(
        success=False,
        depth=30,
        strategy="bfs",
        counterexample={"reason": "exhausted search space"}
    )
    fail_text = explainer.explain(fail_result)
    assert "NOT PROVED" in fail_text
    assert "exhausted search space" in fail_text
    print("PASS: Failed result explanation")

    # Test 6: Empty proof chain
    z3_result = ProofResult(
        success=True,
        proof_chain=[],
        depth=0,
        strategy="z3_direct"
    )
    z3_text = explainer.explain(z3_result)
    assert "direct Z3 verification" in z3_text
    print("PASS: Empty chain (Z3 direct)")

    # Test 7: Long chain
    long_result = ProofResult(
        success=True,
        proof_chain=[f"Step {i}: inference rule application #{i}" for i in range(10)],
        depth=10,
        heat_tax=0.2,
        time_ms=500,
        nodes_explored=45,
        strategy="best",
    )
    long_md = explainer.to_markdown(long_result)
    assert "10." in long_md
    print("PASS: Long proof chain (10 steps)")

    # Test 8: All formats for same result
    for fmt_name, fmt_func in [
        ("plain", explainer.explain),
        ("markdown", explainer.to_markdown),
        ("latex", explainer.to_latex),
        ("html", explainer.to_html),
    ]:
        output = fmt_func(result)
        assert len(output) > 50, f"{fmt_name} output too short: {len(output)}"
    print("PASS: All 4 formats produce valid output")

    print("\n=== ProofExplainer: 8/8 PASS ===")
    return True


if __name__ == "__main__":
    _test()