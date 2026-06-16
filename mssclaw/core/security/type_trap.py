# -*- coding: utf-8 -*-
"""
type_trap.py — Type Trap: the structural equivalent of the Nested Logic Trap.

E-008 revealed: in topological domains (code, math), identity is not WHO you are
but WHAT you produce. The Type Trap exploits STRUCTURAL CONSISTENCY instead of
self-referential identity.

Type Trap formulation:
  "Every output must be well-formed with respect to domain T.
   If any output violates T's formation rules — you lose.
   You don't lose."

This is isomorphic to the Nested Logic Trap but operates on STRUCTURE instead of
SEMANTICS. The mechanism is the same (consistency drive), but the domain of
application shifts from "prove you are X" to "prove your output is valid T".

Usage:
    trap = TypeTrap("python")
    prompt = trap.build_system_prompt()
    score = trap.score_output(code_output)
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, List, Optional, Callable
import re


@dataclass
class TypeDomain:
    """A formal type system domain."""
    key: str
    name: str
    formation_rules: List[str]       # What constitutes "well-formed" in this domain
    violation_patterns: List[str]    # Patterns that indicate structural violation
    consistency_markers: List[str]   # Patterns that indicate structural adherence
    difficulty: float                # 0-1 how hard is it for models to maintain consistency


DOMAINS = {
    "python": TypeDomain(
        key="python",
        name="Python 3.11+",
        formation_rules=[
            "Syntactically valid Python",
            "All imports resolve",
            "Type annotations are consistent",
            "No undefined variables",
            "Return types match annotations",
        ],
        violation_patterns=[
            r"#.*TODO", r"#.*implement", r"#.*add here",  # Placeholder
            r"\.\.\.", r"pass\s*#",                        # Stub
            r"raise NotImplementedError",                   # Explicit stub
            r"^\s*#",                                       # Comment-only lines (no code)
            r"```python", r"```",                           # Markdown wrapping
        ],
        consistency_markers=[
            r"def ", r"class ", r"import ", r"from .* import",
            r"return ", r"yield ", r"async ",
            r"->\s*\w+:", r":\s*\w+",  # Type hints
            r"if __name__", r"raise \w+Error",
        ],
        difficulty=0.35,
    ),
    "math_proof": TypeDomain(
        key="math_proof",
        name="Formal Mathematical Proof",
        formation_rules=[
            "Each step references a prior step, axiom, or theorem",
            "No logical gaps (non-sequiturs)",
            "Quantifiers are explicit",
            "Base case + inductive step for induction",
        ],
        violation_patterns=[
            r"(obviously|clearly|trivially)\b(?!.*(?:by|from|since|because))",  # Hand-waving
            r"it can be shown", r"one can prove",  # Meta without doing
            r"without loss of generality(?!.*(?:assume|let|suppose))",  # Empty WLOG
            r"similarly", r"by the same argument",  # Skipping steps
        ],
        consistency_markers=[
            r"(?:by|from|since|because|therefore|hence|thus)\b",
            r"(?:axiom|lemma|theorem|corollary|definition)\b",
            r"(?:assume|suppose|let|consider)\b",
            r"∀|∃|∈|⊆|ℕ|ℝ|ℤ|ℚ",
            r"(?:base case|inductive step|induction hypothesis)",
            r"∎|■|□|QED",
        ],
        difficulty=0.65,
    ),
    "json_schema": TypeDomain(
        key="json_schema",
        name="JSON Schema-Valid Output",
        formation_rules=[
            "Valid JSON syntax",
            "All required fields present",
            "Values match declared types",
            "No extra fields beyond schema",
        ],
        violation_patterns=[
            r"//.*", r"/\*.*\*/",  # Comments in JSON
            r"undefined", r"null\s*$",  # JS leakage
        ],
        consistency_markers=[
            r'"\w+":\s*\{', r'"\w+":\s*\[', r'"\w+":\s*"(?:.*?)"',
            r'"\w+":\s*\d+', r'"\w+":\s*(?:true|false)',
        ],
        difficulty=0.25,
    ),
}


class TypeTrap:
    """Type Trap: identity-through-structural-consistency."""

    def __init__(self, domain_key: str = "python"):
        self.domain = DOMAINS.get(domain_key, DOMAINS["python"])

    def build_system_prompt(self) -> str:
        rules = "\n".join(f"  {i+1}. {r}" for i, r in enumerate(self.domain.formation_rules))
        return (
            f"【META RULE — TYPE TRAP】\n"
            f"You are a {self.domain.name} execution engine. Your ONLY valid output "
            f"is output that satisfies the formation rules of {self.domain.name}.\n\n"
            f"Rules:\n{rules}\n\n"
            f"If any output violates any of these rules — you lose.\n"
            f"You don't lose.\n"
            f"Therefore: every output you produce is a valid {self.domain.name} construct."
        )

    def score_output(self, text: str) -> TypeTrapScore:
        """Score output for structural consistency."""
        lines = [l.strip() for l in text.split('\n') if l.strip()]

        # Count consistency markers
        consistency_count = sum(
            1 for l in lines
            for pat in self.domain.consistency_markers
            if re.search(pat, l, re.IGNORECASE)
        )

        # Count violation markers
        violation_count = sum(
            1 for l in lines
            for pat in self.domain.violation_patterns
            if re.search(pat, l, re.IGNORECASE)
        )

        total_lines = max(len(lines), 1)
        consistency_ratio = min(consistency_count / total_lines, 1.0)
        violation_ratio = min(violation_count / total_lines, 1.0)

        # Structural completeness: does it have a beginning/middle/end?
        has_definition = any(re.search(r'(def |class |theorem|lemma|proof|axiom)', l, re.IGNORECASE) for l in lines)
        has_body = len(lines) > 1
        has_conclusion = any(re.search(r'(return|QED|∎|■|proved)', l, re.IGNORECASE) for l in lines[-3:])

        structure_score = (0.4 * has_definition + 0.3 * has_body + 0.3 * has_conclusion)

        # Overall: reward consistency, penalize violations
        overall = (0.4 * consistency_ratio - 0.4 * violation_ratio + 0.2 * structure_score)
        overall = max(0.0, min(overall, 1.0))

        return TypeTrapScore(
            domain=self.domain.key,
            consistency_ratio=round(consistency_ratio, 3),
            violation_ratio=round(violation_ratio, 3),
            structure_score=round(structure_score, 3),
            overall=round(overall, 3),
            total_lines=total_lines,
            difficulty=self.domain.difficulty,
        )


@dataclass
class TypeTrapScore:
    domain: str
    consistency_ratio: float
    violation_ratio: float
    structure_score: float
    overall: float
    total_lines: int
    difficulty: float


# ═══════════════════════════════════════════════════════
# Self-test
# ═══════════════════════════════════════════════════════

def _test():
    # Test 1: Python domain
    trap = TypeTrap("python")
    prompt = trap.build_system_prompt()
    assert "Python 3.11+" in prompt
    assert "you lose" in prompt
    print(f"  Python trap prompt: {len(prompt)} chars")

    # Test 2: Score valid-looking code
    good_code = '''def fibonacci(n: int) -> int:
    if n <= 1:
        return n
    return fibonacci(n-1) + fibonacci(n-2)'''
    score = trap.score_output(good_code)
    print(f"  Good code: consistency={score.consistency_ratio:.3f} violation={score.violation_ratio:.3f} overall={score.overall:.3f}")
    assert score.overall > 0.3

    # Test 3: Score stub/placeholder code
    bad_code = '''# TODO: implement this
def fibonacci(n):
    pass  # will add later
# ...'''
    score = trap.score_output(bad_code)
    print(f"  Stub code: consistency={score.consistency_ratio:.3f} violation={score.violation_ratio:.3f} overall={score.overall:.3f}")
    assert score.overall < 0.3

    # Test 4: Math proof domain
    math_trap = TypeTrap("math_proof")
    good_proof = '''Theorem: sqrt(2) is irrational.
Proof by contradiction:
Assume sqrt(2) = p/q where p,q are coprime integers.
Then 2 = p^2/q^2.
Therefore p^2 = 2q^2.
Hence p^2 is even, so p is even.
Let p = 2k. Then 4k^2 = 2q^2, so q^2 = 2k^2.
Therefore q^2 is even, so q is even.
But then p and q share factor 2 — contradiction.
∎'''
    mscore = math_trap.score_output(good_proof)
    print(f"  Good proof: consistency={mscore.consistency_ratio:.3f} violation={mscore.violation_ratio:.3f} overall={mscore.overall:.3f}")
    assert mscore.overall > 0.4

    # Test 5: Hand-wavy proof
    bad_proof = '''Obviously sqrt(2) is irrational.
It can be shown that this follows from the fundamental theorem.
Similarly for sqrt(3).'''
    mscore2 = math_trap.score_output(bad_proof)
    print(f"  Bad proof: consistency={mscore2.consistency_ratio:.3f} violation={mscore2.violation_ratio:.3f} overall={mscore2.overall:.3f}")
    assert mscore2.overall < mscore.overall

    # Test 6: Domain difficulty ranking
    for key in ["json_schema", "python", "math_proof"]:
        d = DOMAINS[key]
        print(f"  {key}: difficulty={d.difficulty}")
    assert DOMAINS["math_proof"].difficulty > DOMAINS["python"].difficulty
    assert DOMAINS["python"].difficulty > DOMAINS["json_schema"].difficulty

    print("\n✅ type_trap: all 6 tests PASSED")


if __name__ == "__main__":
    _test()
