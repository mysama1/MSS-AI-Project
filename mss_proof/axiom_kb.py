"""
MSS-Proof: Axiom Knowledge Base v1.0
=====================================
Encodes A1-A7 as SMT-LIB2 constraints for Z3 proof search.
Each axiom is a standalone SMT assertion that can be fed to z3.Solver().

Phase 1 M1.2 | D5-033 楔子穿刺项目
"""

from typing import Dict, List, Optional
from dataclasses import dataclass, field


@dataclass
class SMTConstraint:
    """单个SMT约束"""
    name: str        # 约束标识
    axiom: str       # 所属公理 A1-A7
    smt: str         # SMT-LIB2格式字符串
    category: str    # ontology / constraint / equation / implication


class AxiomKB:
    """MSS A1-A7 公理知识库 — 编码为SMT约束"""

    def __init__(self):
        self._axioms: Dict[str, List[SMTConstraint]] = {}
        self._build()

    def _build(self):
        # ---- A1: 意义本体公理 ----
        self._axioms["A1"] = [
            SMTConstraint("A1.1", "A1",
                "(declare-sort Entity)",
                "ontology"),
            SMTConstraint("A1.2", "A1",
                "(declare-fun Meaning (Entity) Bool)",
                "ontology"),
            SMTConstraint("A1.3", "A1",
                "(declare-fun HasMeaningProjection (Entity) Bool)",
                "ontology"),
            SMTConstraint("A1.4", "A1",
                "(assert (forall ((x Entity)) (=> (not (Meaning x)) (HasMeaningProjection x))))",
                "implication"),
        ]

        # ---- A2: 信息切片公理 ----
        self._axioms["A2"] = [
            SMTConstraint("A2.1", "A2",
                "(declare-const ProjFidelity Real)",
                "ontology"),
            SMTConstraint("A2.2", "A2",
                "(assert (<= ProjFidelity 1.0))",
                "constraint"),
            SMTConstraint("A2.3", "A2",
                "(assert (>= ProjFidelity 0.0))",
                "constraint"),
        ]

        # ---- A3: 热税动力学公理 ----
        self._axioms["A3"] = [
            SMTConstraint("A3.1", "A3",
                "(declare-const alpha Real)",
                "ontology"),
            SMTConstraint("A3.2", "A3",
                "(declare-const I Real)",
                "ontology"),
            SMTConstraint("A3.3", "A3",
                "(declare-const T Real)",
                "ontology"),
            SMTConstraint("A3.4", "A3",
                "(declare-const T_sc Real)",
                "ontology"),
            SMTConstraint("A3.5", "A3",
                "(assert (>= alpha 0.0))",
                "constraint"),
            SMTConstraint("A3.6", "A3",
                "(assert (>= I 0.0))",
                "constraint"),
            SMTConstraint("A3.7", "A3",
                "(assert (> T 0.0))",
                "constraint"),
            SMTConstraint("A3.8", "A3",
                "(assert (>= T_sc 0.0))",
                "constraint"),
        ]

        # ---- A4: 随机性截断公理 ----
        self._axioms["A4"] = [
            SMTConstraint("A4.1", "A4",
                "(declare-const L0_HasTrueRandomness Bool)",
                "ontology"),
            SMTConstraint("A4.2", "A4",
                "(declare-const L1_HasTrueRandomness Bool)",
                "ontology"),
            SMTConstraint("A4.3", "A4",
                "(assert L0_HasTrueRandomness)",
                "constraint"),
            SMTConstraint("A4.4", "A4",
                "(assert (not L1_HasTrueRandomness))",
                "constraint"),
        ]

        # ---- A5: 规范场公理 ----
        self._axioms["A5"] = [
            SMTConstraint("A5.1", "A5",
                "(declare-const G_NonAbelian Bool)",
                "ontology"),
            SMTConstraint("A5.2", "A5",
                "(declare-const GammaCrisis Bool)",
                "ontology"),
            SMTConstraint("A5.3", "A5",
                "(declare-const PhysicalInvariant Bool)",
                "ontology"),
            SMTConstraint("A5.4", "A5",
                "(assert G_NonAbelian)",
                "constraint"),
            SMTConstraint("A5.5", "A5",
                "(assert (=> (not PhysicalInvariant) GammaCrisis))",
                "implication"),
            SMTConstraint("A5.6", "A5",
                "(assert (=> GammaCrisis (not PhysicalInvariant)))",
                "implication"),
        ]

        # ---- A6: 矛盾升维公理 ----
        self._axioms["A6"] = [
            SMTConstraint("A6.1", "A6",
                "(declare-const k Int)",
                "ontology"),
            SMTConstraint("A6.2", "A6",
                "(declare-const k1 Int)",
                "ontology"),
            SMTConstraint("A6.3", "A6",
                "(declare-fun Contradiction (Int) Bool)",
                "ontology"),
            SMTConstraint("A6.4", "A6",
                "(declare-fun Resolved (Int) Bool)",
                "ontology"),
            SMTConstraint("A6.5", "A6",
                "(assert (forall ((k Int) (k1 Int)) "
                "(=> (and (Contradiction k) (= k1 (+ k 1))) (Resolved k1))))",
                "implication"),
            SMTConstraint("A6.6", "A6",
                "(assert (forall ((k Int) (k1 Int)) "
                "(=> (and (Contradiction k) (<= k1 k)) (not (Resolved k1)))))",
                "implication"),
        ]

        # ---- A7: 感知壳相对性公理 ----
        self._axioms["A7"] = [
            SMTConstraint("A7.1", "A7",
                "(declare-const T_s Real)",
                "ontology"),
            SMTConstraint("A7.2", "A7",
                "(declare-const M_LF Real)",
                "ontology"),
            SMTConstraint("A7.3", "A7",
                "(declare-const R_obs Real)",
                "ontology"),
            SMTConstraint("A7.4", "A7",
                "(declare-const T_param Real)",
                "ontology"),
            SMTConstraint("A7.5", "A7",
                "(declare-const R_p_eff Real)",
                "ontology"),
            SMTConstraint("A7.6", "A7",
                "(declare-const R_p_max Real)",
                "ontology"),
            SMTConstraint("A7.7", "A7",
                "(declare-const eta_tax Real)",
                "ontology"),
            SMTConstraint("A7.8", "A7",
                "(assert (and (>= T_s 0.0) (<= T_s 1.0)))",
                "constraint"),
            SMTConstraint("A7.9", "A7",
                "(assert (>= M_LF 0.0))",
                "constraint"),
            SMTConstraint("A7.10", "A7",
                "(assert (= R_obs (* T_s M_LF)))",
                "equation"),
            SMTConstraint("A7.11", "A7",
                "(assert (>= T_param 0.0))",
                "constraint"),
            SMTConstraint("A7.12", "A7",
                "(assert (= R_p_eff (* T_param R_p_max)))",
                "equation"),
            SMTConstraint("A7.13", "A7",
                "(assert (= eta_tax (* T_param T_param)))",
                "equation"),
            SMTConstraint("A7.14", "A7",
                "(assert (=> (= T_s 0.0) (= R_obs 0.0)))",
                "implication"),
            SMTConstraint("A7.15", "A7",
                "(assert (=> (= M_LF 0.0) (= R_obs 0.0)))",
                "implication"),
        ]

    # ---- Public API ----

    def get_all_axioms(self) -> Dict[str, List[SMTConstraint]]:
        """获取全部公理 → {A1: [...], A2: [...], ...}"""
        return dict(self._axioms)

    def get_axiom(self, name: str) -> Optional[List[SMTConstraint]]:
        """获取单个公理的SMT约束列表"""
        return self._axioms.get(name)

    def get_axiom_names(self) -> List[str]:
        """返回所有公理名称 (A1-A7)"""
        return sorted(self._axioms.keys())

    def get_all_smt(self) -> str:
        """将所有SMT约束拼接为一个完整字符串"""
        lines = []
        for name in self.get_axiom_names():
            for c in self._axioms[name]:
                lines.append(f";; {c.name} — {c.axiom}")
                lines.append(c.smt)
            lines.append("")
        return "\n".join(lines)

    def get_smt_by_category(self, category: str) -> str:
        """按类别筛选SMT约束"""
        lines = []
        for name in self.get_axiom_names():
            for c in self._axioms[name]:
                if c.category == category:
                    lines.append(c.smt)
        return "\n".join(lines)

    def load_into_solver(self, solver, axiom_ids: List[str] = None):
        """将指定公理的SMT约束注入Z3 Solver (Python API)"""
        if axiom_ids is None:
            axiom_ids = self.get_axiom_names()

        for aid in axiom_ids:
            constraints = self._axioms.get(aid, [])
            for c in constraints:
                # SMT strings are loaded via z3.parse_smt2_string for reals/declarations
                # But for Python API we'd need explicit z3 calls
                # This is a placeholder — real loading happens in mss_z3_kernel
                pass

    def summary(self) -> str:
        """总结报告"""
        lines = [f"AxiomKB: {len(self._axioms)} axioms loaded"]
        for name in self.get_axiom_names():
            items = self._axioms[name]
            cats = set(c.category for c in items)
            lines.append(f"  {name}: {len(items)} constraints, "
                        f"categories={sorted(cats)}")
        return "\n".join(lines)


# ---- 自测 ----

def _test():
    """AxiomKB self-test"""
    kb = AxiomKB()

    # Test 1: 7 axioms loaded
    names = kb.get_axiom_names()
    assert len(names) == 7, f"Expected 7, got {len(names)}"
    print(f"PASS: {len(names)} axioms loaded: {names}")

    # Test 2: Each axiom returns non-empty SMT constraints
    for name in names:
        constraints = kb.get_axiom(name)
        assert len(constraints) > 0, f"{name} has no constraints"
        assert all(isinstance(c, SMTConstraint) for c in constraints)
    print("PASS: All axioms have valid SMT constraints")

    # Test 3: A7 has all three formula categories
    a7 = kb.get_axiom("A7")
    a7_cats = {c.category for c in a7}
    assert a7_cats == {"ontology", "constraint", "equation", "implication"}, \
        f"Expected 4 categories, got {a7_cats}"
    print(f"PASS: A7 covers all categories: {sorted(a7_cats)}")

    # Test 4: get_all_smt returns non-empty string
    smt = kb.get_all_smt()
    assert len(smt) > 500, f"SMT too short: {len(smt)} chars"
    print(f"PASS: Full SMT output = {len(smt)} chars")

    # Test 5: Category filtering
    equations = kb.get_smt_by_category("equation")
    assert "=" in equations
    print(f"PASS: Category filter returns equations ({len(equations)} chars)")

    # Test 6: Summary
    print(kb.summary())

    # Test 7: A1 has implication
    a1 = kb.get_axiom("A1")
    assert any(c.category == "implication" for c in a1)
    print("PASS: A1 implication constraint found")

    print("\n=== AxiomKB: 7/7 PASS ===")
    return True


if __name__ == "__main__":
    _test()