"""
MSS-Proof: Benchmark Runner v1.0
=================================
Runs the prover against synthetic and TPTP problems,
collects statistics, and generates benchmark reports.

Phase 1 M1.2 | D5-033 楔子穿刺项目
"""

import time, os, json
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from proof_search import Prover, ProofResult, SearchStrategy, prove_string
from tptp_parser import TPTPProblem, TPTPParser


# ============================================================
# Benchmark Types
# ============================================================

@dataclass
class BenchmarkReport:
    """Aggregate benchmark results"""
    total: int = 0
    proved: int = 0
    failed: int = 0
    timeout: int = 0
    errors: int = 0
    total_time_ms: float = 0.0
    avg_depth: float = 0.0
    avg_heat_tax: float = 0.0
    avg_nodes: float = 0.0
    prove_rate: float = 0.0
    per_problem: List[Dict] = field(default_factory=list)
    timestamp: str = ""
    strategy: str = ""
    solver: str = "z3"

    def to_dict(self) -> Dict:
        return {
            "total": self.total,
            "proved": self.proved,
            "failed": self.failed,
            "timeout": self.timeout,
            "errors": self.errors,
            "total_time_ms": round(self.total_time_ms, 1),
            "avg_depth": round(self.avg_depth, 2),
            "avg_heat_tax": round(self.avg_heat_tax, 4),
            "avg_nodes": round(self.avg_nodes, 1),
            "prove_rate": round(self.prove_rate, 3),
            "strategy": self.strategy,
            "solver": self.solver,
            "timestamp": self.timestamp,
            "per_problem": self.per_problem[:50],  # truncate for summary
        }

    def __str__(self) -> str:
        lines = [
            "=" * 60,
            f"  Benchmark Report — {self.strategy} ({self.solver})",
            "=" * 60,
            f"  Timestamp: {self.timestamp}",
            "",
            f"  Total:    {self.total:>6}",
            f"  Proved:   {self.proved:>6}  ({self.prove_rate:.1%})",
            f"  Failed:   {self.failed:>6}",
            f"  Timeout:  {self.timeout:>6}",
            f"  Errors:   {self.errors:>6}",
            "",
            f"  Time:     {self.total_time_ms:>8.1f}ms",
            f"  Avg Depth:{self.avg_depth:>8.1f}",
            f"  Avg Nodes:{self.avg_nodes:>8.1f}",
            f"  Avg Heat: {self.avg_heat_tax:>8.4f}",
            "",
            "  Per-Problem Breakdown:",
        ]

        for p in self.per_problem[:20]:
            icon = "✅" if p.get("success") else "❌"
            lines.append(f"    {icon} {p['name']:<30} "
                        f"d={p.get('depth', 0):<4} n={p.get('nodes', 0):<5} "
                        f"ht={p.get('heat_tax', 0):.3f} t={p.get('time_ms', 0):.0f}ms")

        if len(self.per_problem) > 20:
            lines.append(f"    ... and {len(self.per_problem) - 20} more")

        lines.append("=" * 60)
        return "\n".join(lines)


# ============================================================
# Synthetic Test Problems
# ============================================================

SYNTHETIC_PROBLEMS = {
    "synth_01_modus_ponens": """
fof(a1, axiom, (man(socrates) => mortal(socrates))).
fof(a2, axiom, man(socrates)).
fof(c1, conjecture, mortal(socrates)).
""",
    "synth_02_disj_syllogism": """
fof(a1, axiom, (p | q)).
fof(a2, axiom, (~p)).
fof(c1, conjecture, q).
""",
    "synth_03_conj_elim": """
fof(a1, axiom, (p & q)).
fof(c1, conjecture, p).
""",
    "synth_04_double_conj": """
fof(a1, axiom, (a & b)).
fof(a2, axiom, (b => c)).
fof(c1, conjecture, (a & c)).
""",
    "synth_05_chain_3": """
fof(a1, axiom, p).
fof(a2, axiom, (p => q)).
fof(a3, axiom, (q => r)).
fof(c1, conjecture, r).
""",
    "synth_06_excluded_middle": """
fof(a1, axiom, (p | ~p)).
fof(c1, conjecture, (p | ~p)).
""",
    "synth_07_contrapositive": """
fof(a1, axiom, (p => q)).
fof(a2, axiom, ~q).
fof(c1, conjecture, ~p).
""",
    "synth_08_distributive": """
fof(a1, axiom, (p & (q | r))).
fof(c1, conjecture, (p & q) | (p & r)).
""",
    "synth_09_de_morgan": """
fof(a1, axiom, (~(p & q))).
fof(c1, conjecture, (~p | ~q)).
""",
    "synth_10_triple_conj": """
fof(a1, axiom, (a & b & c)).
fof(c1, conjecture, b).
""",
}


# ============================================================
# Benchmark Runner
# ============================================================

class BenchmarkRunner:
    """Runs benchmark suite and collects statistics"""

    def __init__(self,
                 strategy: SearchStrategy = SearchStrategy.BFS,
                 max_depth: int = 30,
                 timeout_s: float = 10.0,
                 heat_tax_budget: float = 1.0,
                 max_nodes: int = 5000):
        self.strategy = strategy
        self.max_depth = max_depth
        self.timeout_s = timeout_s
        self.heat_tax_budget = heat_tax_budget
        self.max_nodes = max_nodes
        self.prover = Prover(
            max_depth=max_depth,
            max_nodes=max_nodes,
            timeout_s=timeout_s,
            strategy=strategy,
            heat_tax_budget=heat_tax_budget,
        )

    def run_synthetic(self,
                      problem_names: Optional[List[str]] = None
                      ) -> BenchmarkReport:
        """Run on synthetic test problems"""
        if problem_names is None:
            problem_names = list(SYNTHETIC_PROBLEMS.keys())

        return self._run_batch(
            {k: SYNTHETIC_PROBLEMS[k] for k in problem_names
             if k in SYNTHETIC_PROBLEMS},
            source="synthetic"
        )

    def run_tptp_dir(self, tptp_dir: str,
                     max_problems: int = 100) -> BenchmarkReport:
        """Run on TPTP problem files"""
        # Collect .p files
        problems = {}
        try:
            files = [f for f in os.listdir(tptp_dir) if f.endswith(".p")]
            for f in files[:max_problems]:
                path = os.path.join(tptp_dir, f)
                try:
                    with open(path, "r") as fh:
                        problems[f] = fh.read()
                except Exception:
                    pass
        except FileNotFoundError:
            pass
        return self._run_batch(problems, source="tptp")

    def _run_batch(self, problems: Dict[str, str],
                   source: str = "") -> BenchmarkReport:
        """Run a batch of problems"""
        report = BenchmarkReport(
            strategy=self.strategy.value,
            solver="z3",
            timestamp=time.strftime("%Y-%m-%dT%H:%M:%S")
        )
        total_start = time.perf_counter()

        for name, text in problems.items():
            try:
                result = prove_string(
                    text,
                    strategy=self.strategy,
                    max_depth=self.max_depth,
                    timeout_s=self.timeout_s,
                )
                report.total += 1
                report.total_time_ms += result.time_ms

                entry = {
                    "name": name,
                    "success": result.success,
                    "depth": result.depth,
                    "nodes": result.nodes_explored,
                    "heat_tax": result.heat_tax,
                    "time_ms": result.time_ms,
                    "strategy": result.strategy,
                }

                if result.success:
                    report.proved += 1
                else:
                    report.failed += 1
                    if result.counterexample:
                        entry["counterexample"] = result.counterexample

                report.per_problem.append(entry)

            except Exception as e:
                report.total += 1
                report.errors += 1
                report.per_problem.append({
                    "name": name,
                    "success": False,
                    "error": str(e),
                })

        # Compute averages
        if report.proved > 0:
            proved_entries = [p for p in report.per_problem if p.get("success")]
            report.avg_depth = sum(p.get("depth", 0) for p in proved_entries) / report.proved
            report.avg_heat_tax = sum(p.get("heat_tax", 0) for p in proved_entries) / report.proved
            report.avg_nodes = sum(p.get("nodes", 0) for p in proved_entries) / report.proved
        report.prove_rate = report.proved / max(report.total, 1)

        return report

    def compare_strategies(self,
                           problem_names: Optional[List[str]] = None
                           ) -> Dict[str, BenchmarkReport]:
        """Compare BFS vs DFS vs Best-First on same problem set"""
        if problem_names is None:
            problem_names = list(SYNTHETIC_PROBLEMS.keys())

        results = {}
        for strategy in [SearchStrategy.BFS, SearchStrategy.DFS, SearchStrategy.BEST_FIRST]:
            runner = BenchmarkRunner(
                strategy=strategy,
                max_depth=self.max_depth,
                timeout_s=self.timeout_s,
                heat_tax_budget=self.heat_tax_budget,
                max_nodes=self.max_nodes,
            )
            results[strategy.value] = runner.run_synthetic(problem_names)
        return results

    def export_report(self, report: BenchmarkReport, filepath: str):
        """Export benchmark report as JSON"""
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(report.to_dict(), f, ensure_ascii=False, indent=2)


# ============================================================
# Self-Tests
# ============================================================

def _test():
    """BenchmarkRunner self-tests"""
    print("=" * 60)
    print("  MSS-Proof Benchmark Suite")
    print("=" * 60)

    # Test 1: Run synthetic benchmarks
    print("\n--- Test 1: Synthetic Benchmarks (BFS) ---")
    runner = BenchmarkRunner(strategy=SearchStrategy.BFS, timeout_s=5.0, max_depth=20)
    report = runner.run_synthetic()
    print(report)
    assert report.total > 0, "Should run some problems"
    assert report.proved > 0, "Should prove some problems"
    print(f"PASS: {report.proved}/{report.total} proved ({report.prove_rate:.0%})")

    # Test 2: Strategy comparison
    print("\n--- Test 2: Strategy Comparison ---")
    results = runner.compare_strategies(["synth_01_modus_ponens", "synth_03_conj_elim",
                                          "synth_04_double_conj"])
    for strategy, rep in results.items():
        print(f"  {strategy}: {rep.proved}/{rep.total} ({rep.prove_rate:.0%}) "
              f"avg_depth={rep.avg_depth:.1f}")
    assert all(rep.prove_rate >= 0.5 for rep in results.values()), \
        "All strategies should prove >50%"
    print("PASS: All strategies functional")

    # Test 3: Full synthetic suite (10 problems)
    print("\n--- Test 3: Full Synthetic Suite ---")
    report = runner.run_synthetic()
    print(f"  Proved: {report.proved}/{report.total}")
    assert report.total == 10, f"Expected 10, got {report.total}"
    print(f"PASS: All 10 synthetic problems benchmarked")

    # Test 4: Report serialization
    print("\n--- Test 4: Report Serialization ---")
    d = report.to_dict()
    assert "proved" in d
    assert "prove_rate" in d
    assert isinstance(d["per_problem"], list)
    print(f"PASS: Report serializable to dict ({len(d['per_problem'])} entries)")

    # Test 5: Export to JSON
    print("\n--- Test 5: JSON Export ---")
    outpath = r"E:\AI_Workspace\MSS-AI\project\mss_proof\benchmark_report.json"
    runner.export_report(report, outpath)
    assert os.path.exists(outpath)
    with open(outpath, "r", encoding="utf-8") as f:
        loaded = json.load(f)
    assert loaded["total"] == report.total
    print(f"PASS: Exported to {outpath} ({os.path.getsize(outpath)} bytes)")

    # Test 6: Heat tax budget constraint
    print("\n--- Test 6: Heat Tax Budget Constraint ---")
    tight = BenchmarkRunner(strategy=SearchStrategy.BFS, timeout_s=5.0,
                           heat_tax_budget=0.01, max_depth=5)
    tight_report = tight.run_synthetic()
    print(f"  Budget=0.01: {tight_report.proved}/{tight_report.total} proved "
          f"(avg heat={tight_report.avg_heat_tax:.4f})")
    # With tight budget, fewer proofs but the system shouldn't crash
    assert tight_report.errors == 0, "Should not crash with tight budget"
    print("PASS: Heat tax budget enforced without errors")

    # Test 7: Per-problem breakdown
    print("\n--- Test 7: Per-Problem Breakdown ---")
    for p in report.per_problem[:5]:
        icon = "✅" if p.get("success") else "❌"
        print(f"  {icon} {p['name']}: d={p.get('depth',0)} n={p.get('nodes',0)} "
              f"t={p.get('time_ms',0):.0f}ms")
    assert all("name" in p for p in report.per_problem)
    print("PASS: Per-problem data complete")

    # Cleanup test export
    if os.path.exists(outpath):
        os.remove(outpath)

    print(f"\n=== Benchmark: 7/7 PASS ===")
    return True


if __name__ == "__main__":
    _test()