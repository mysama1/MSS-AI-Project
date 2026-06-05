"""
MSS-Proof: Formal Theorem Proving Engine
=========================================
楔子穿刺项目 — MSS公理体系的自动化数学证明

Phase 1 M1.2 Deliverables:
  - tptp_parser.py    : TPTP FOF/CNF/TFF format parser
  - axiom_kb.py       : A1-A7 axiom SMT knowledge base
  - proof_search.py   : BFS/DFS/Best-First proof search engine
  - proof_explain.py  : Human-readable proof output (MD/LaTeX/HTML)
  - benchmark.py      : Benchmark runner and reporting
"""

from .tptp_parser import (
    TPTPProblem, TPTPStatement, TPTPRole, TPTPLogic, TPTPParser,
    TPTPStatus, TPTPUSAGE, TPTPInclude,
)

from .axiom_kb import (
    AxiomKB, SMTConstraint,
)

from .proof_search import (
    ProofState, ProofResult, SearchStrategy, InferenceRule,
    Prover, Z3Prover, RuleEngine,
    goal_proximity, depth_penalty, heat_tax_penalty, combined_heuristic,
    prove_string, prove_file,
)

from .proof_explain import (
    ProofExplainer,
)

from .benchmark import (
    BenchmarkRunner, BenchmarkReport,
    SYNTHETIC_PROBLEMS,
)

__all__ = [
    # TPTP Parser
    "TPTPProblem", "TPTPStatement", "TPTPRole", "TPTPLogic", "TPTPParser",
    "TPTPStatus", "TPTPUSAGE", "TPTPInclude",
    # Axiom KB
    "AxiomKB", "SMTConstraint",
    # Proof Search
    "ProofState", "ProofResult", "SearchStrategy", "InferenceRule",
    "Prover", "Z3Prover", "RuleEngine",
    "goal_proximity", "depth_penalty", "heat_tax_penalty", "combined_heuristic",
    "prove_string", "prove_file",
    # Proof Explainer
    "ProofExplainer",
    # Benchmark
    "BenchmarkRunner", "BenchmarkReport", "SYNTHETIC_PROBLEMS",
]