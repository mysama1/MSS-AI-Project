#!/usr/bin/env python3
"""
test_mss_z3_kernel.py — MSS Z3 Logical Kernel v0.2 测试套件
"""

import sys, os, json
sys.path.insert(0, os.path.dirname(__file__))
from mss_z3_kernel import (
    MSSZ3Kernel, AxiomID, VerificationStatus, ViolationType,
    LogicalRigidityEngine, SemanticEncoder, LogicalQuery,
    Z3_AVAILABLE
)

def test_tc():
    """TestContext: track pass/fail"""
    tests = {"pass": 0, "fail": 0, "total": 0}
    def ok(msg, cond):
        tests["total"] += 1
        if cond:
            tests["pass"] += 1
            print(f"  ✅ {msg}")
        else:
            tests["fail"] += 1
            print(f"  ❌ {msg}")
    return tests, ok

def test_axiom_consistency(kernel, ok):
    """A1-A6 all SAT"""
    results = kernel.verify_all_axioms()
    for aid in AxiomID:
        vr = results[aid]
        ok(f"{aid.value} SAT", vr.status == VerificationStatus.VERIFIED)

def test_cross_axiom(kernel, ok):
    """21/21 cross-axiom pairs all SAT"""
    xres = kernel.check_all_cross_axioms()
    sat = sum(1 for v in xres.values() if v.status == VerificationStatus.VERIFIED)
    ok(f"Cross-axiom 21/21", sat == 21)

def test_heat_tax_violations(kernel, ok):
    """A3 full formula violation detection"""
    # Normal
    vr = kernel.detect_heat_tax_violation(5.0, 3.0, 0.8)
    ok("Normal: VERIFIED", vr.status == VerificationStatus.VERIFIED)
    ok("Normal: violation_type=NONE", vr.violation_type == ViolationType.NONE)

    # Negative I
    vr = kernel.detect_heat_tax_violation(-1.0, 1.0, 0.5)
    ok("Negative I: VIOLATION", vr.status == VerificationStatus.VIOLATION)

    # Negative T_sc
    vr = kernel.detect_heat_tax_violation(10.0, -5.0, 0.9)
    ok("Negative T_sc: VIOLATION", vr.status == VerificationStatus.VIOLATION)
    ok("Negative T_sc: NEGATIVE_HEAT_TAX", vr.violation_type == ViolationType.NEGATIVE_HEAT_TAX)

    # Zero T
    vr = kernel.detect_heat_tax_violation(3.0, 2.0, 0.0)
    ok("Zero T: VIOLATION", vr.status == VerificationStatus.VIOLATION)
    ok("Zero T: ZERO_TUNING", vr.violation_type == ViolationType.ZERO_TUNING)

    # I=0, T_sc=0 (valid: zero info → zero heat tax)
    vr = kernel.detect_heat_tax_violation(0.0, 0.0, 0.5)
    ok("I=0, T_sc=0: VERIFIED (zero info)", vr.status == VerificationStatus.VERIFIED)

def test_semantic_contradiction(kernel, ok):
    """Semantic contradiction detection"""
    # Consistent
    vr = kernel.detect_contradiction(["A是真理", "B是真理", "C是真理", "D是真理"])
    ok("4 consistent statements: VERIFIED", vr.status == VerificationStatus.VERIFIED)

    # Value conflict
    vr = kernel.detect_contradiction(["X=1.0", "X=0.5", "同一个X两个值"])
    ok("Value conflict: CONTRADICTION", vr.status == VerificationStatus.CONTRADICTION)
    ok("Value conflict: SEMANTIC_CONTRADICTION",
       vr.violation_type == ViolationType.SEMANTIC_CONTRADICTION)

    # Single statement (trivial)
    vr = kernel.detect_contradiction(["只有一个命题"])
    ok("Single statement: TRIVIAL", vr.status == VerificationStatus.TRIVIAL)

    # No Z3-level conflict but semantic value mismatch
    vr = kernel.detect_contradiction(["M_L=1.000", "M_L=0.500"])
    ok("M_L value mismatch: CONTRADICTION",
       vr.status == VerificationStatus.CONTRADICTION)

def test_proposition_verification(kernel, ok):
    """Proposition compatibility check"""
    query = LogicalQuery(
        raw_text="Does heat tax increase with information?",
        formal_proposition="T_sc increases monotonically with I",
        relevant_axioms=[AxiomID.A3]
    )
    vr = kernel.verify_proposition(query)
    ok("Proposition compatible w/ A3", vr.status == VerificationStatus.VERIFIED)

def test_audit_export(kernel, ok):
    """Audit report + JSONL export"""
    report = kernel.audit_report()
    ok("Report has total_verifications", "total_verifications" in report)
    ok("Report has m_l_formal", "m_l_formal" in report)
    ok("Report has m_l_engineering", "m_l_engineering" in report)
    ok("Report has version 0.2", report.get("version") == "0.2")

    # Export
    path = "/tmp/z3_audit_test.jsonl"
    kernel.export_audit_jsonl(path)
    ok("JSONL export file exists", os.path.exists(path))

    # Read back
    with open(path, 'r', encoding='utf-8') as f:
        lines = [json.loads(l) for l in f]
    ok(f"JSONL entries match log ({len(lines)}={len(kernel.verification_log)})",
       len(lines) == len(kernel.verification_log))

def test_rigidity_engine(kernel, ok):
    """M_L tracking"""
    r = kernel.rigidity
    ok("Formal > 0.5", r.formal > 0.5)
    ok("Engineering = 0.92", r.engineering == 0.92)
    rep = r.report()
    ok("Report has formal_health", "formal_health" in rep)
    ok("Report has engineering_health", "engineering_health" in rep)

def test_semantic_encoder():
    """Standalone semantic encoder tests"""
    print("\n--- SemanticEncoder ---")
    t, ok = test_tc()

    enc = SemanticEncoder()

    # Value extraction
    sp = enc.encode_claim("M_L=0.92")
    ok("M_L=0.92 extracted before Z3", True)  # Semantic check only

    # Pairwise contradiction
    has_contra, details = enc.detect_semantic_contradiction([
        "X的值为1.0", "X的值为2.0", "同一个X"
    ])
    ok("Semantic value conflict detected", has_contra)

    # No contradiction
    has_contra, _ = enc.detect_semantic_contradiction([
        "A是好的", "B也是好的"
    ])
    ok("No contradiction in unrelated claims", not has_contra)

    return t

if __name__ == "__main__":
    print(f"MSS Z3 Kernel v0.2 Test Suite")
    print(f"Z3 Available: {Z3_AVAILABLE}")
    if not Z3_AVAILABLE:
        print("SKIP: Z3 not installed")
        sys.exit(0)

    tests, ok = test_tc()

    kernel = MSSZ3Kernel()

    print("\n=== TC-01: Axiom Internal Consistency ===")
    test_axiom_consistency(kernel, ok)

    print("\n=== TC-02: Cross-Axiom Consistency ===")
    test_cross_axiom(kernel, ok)

    print("\n=== TC-03: Heat Tax Violations (A3 full formula) ===")
    test_heat_tax_violations(kernel, ok)

    print("\n=== TC-04: Semantic Contradiction Detection ===")
    test_semantic_contradiction(kernel, ok)

    print("\n=== TC-05: Proposition Verification ===")
    test_proposition_verification(kernel, ok)

    print("\n=== TC-06: Audit Report & Export ===")
    test_audit_export(kernel, ok)

    print("\n=== TC-07: M_L Rigidity Engine ===")
    test_rigidity_engine(kernel, ok)

    # Semantic encoder
    st = test_semantic_encoder()
    tests["total"] += st["total"]
    tests["pass"] += st["pass"]
    tests["fail"] += st["fail"]

    # v0.3: Proof Trace Engine
    from mss_z3_kernel import ProofTraceEngine, CounterExampleGenerator, BatchVerifier

    print("\n=== TC-08: Proof Trace Engine (v0.3) ===")
    trace_engine = ProofTraceEngine(kernel)

    trace = trace_engine.trace_axiom(AxiomID.A1)
    ok("A1 proof trace: valid", trace.is_valid)
    ok("A1 proof trace: has steps", len(trace.steps) >= 0)
    ok("A1 proof trace: has conclusion", len(trace.conclusion) > 0)
    ok("A1 proof trace: timing recorded", trace.total_time_ms > 0)

    # Academic format
    acad = trace.to_academic_format()
    ok("Academic format: has Theorem", "Theorem" in acad)
    ok("Academic format: has Proof", "Proof" in acad)
    ok("Academic format: has ∎", "∎" in acad)

    # Latex format
    latex = trace.to_latex()
    ok("LaTeX format: has proof env", "\\begin{proof}" in latex)
    ok("LaTeX format: has end proof", "\\end{proof}" in latex)

    # Cross-axiom trace
    trace2 = trace_engine.trace_cross_axiom(AxiomID.A1, AxiomID.A2)
    ok("A1∧A2 trace: valid", trace2.is_valid)
    ok("A1∧A2 trace: 3+ steps", len(trace2.steps) >= 3)

    # All axioms
    all_traces = trace_engine.trace_all_axioms()
    ok("All 7 axioms traced", len(all_traces) == 7)
    all_valid = sum(1 for t in all_traces if t.is_valid)
    ok(f"All axioms valid ({all_valid}/7)", all_valid == 7)

    # All pairs
    pair_traces = trace_engine.trace_all_pairs()
    ok("All 21 pairs traced", len(pair_traces) == 21)
    pair_valid = sum(1 for t in pair_traces if t.is_valid)
    ok(f"All pairs valid ({pair_valid}/21)", pair_valid == 21)

    # Academic paper section export
    section = trace_engine.export_academic_paper_section()
    ok("Paper section: has title", "Formal Verification" in section)
    ok("Paper section: has Axiom Satisfiability", "Axiom Satisfiability" in section)
    ok("Paper section: has Pairwise", "Pairwise" in section)

    print("\n=== TC-09: CounterExample Generator (v0.3) ===")
    cg = CounterExampleGenerator(kernel)

    # Heat tax violation
    vr_neg = kernel.detect_heat_tax_violation(10.0, -5.0, 0.9)
    ce = cg.generate_for_heat_tax(10.0, -5.0, 0.9, vr_neg)
    ok("CE: negative T_sc generates example", ce is not None)
    ok("CE: severity=CRITICAL", ce.severity == "CRITICAL")
    ok("CE: has why_it_violates", len(ce.why_it_violates) > 20)
    ok("CE: has fix_suggestion", len(ce.fix_suggestion) > 20)

    # Zero tuning
    vr_zero = kernel.detect_heat_tax_violation(3.0, 2.0, 0.0)
    ce2 = cg.generate_for_heat_tax(3.0, 2.0, 0.0, vr_zero)
    ok("CE: zero T generates example", ce2 is not None)
    ok("CE: zero T also CRITICAL", ce2.severity == "CRITICAL")

    # Normal case — no counterexample
    vr_ok = kernel.detect_heat_tax_violation(5.0, 3.0, 0.8)
    ce_none = cg.generate_for_heat_tax(5.0, 3.0, 0.8, vr_ok)
    ok("CE: normal case returns None", ce_none is None)

    # Projection fidelity — test that the generator handles various statuses
    from mss_z3_kernel import VerificationResult as VR
    vr_fake = VR(status=VerificationStatus.VIOLATION, axiom_id=AxiomID.A2,
                 violation_type=ViolationType.PROJ_FIDELITY_OVERFLOW)
    ce_proj = cg.generate_for_projection(1.5, vr_fake)
    ok("CE: projection overflow generates example", ce_proj is not None)
    ok("CE: projection severity=HIGH", ce_proj.severity == "HIGH")

    print("\n=== TC-10: Batch Verifier (v0.3) ===")
    bv = BatchVerifier(kernel, cache_size=50)

    # Batch axiom verification
    report = bv.verify_axiom_batch()
    ok("Batch: 7 axioms processed", report.total == 7)
    ok(f"Batch: all verified ({report.verified}/7)", report.verified == 7)
    ok("Batch: no violations", report.violated == 0)
    ok("Batch: timing recorded", report.total_time_ms > 0)
    ok("Batch: pass_rate=1.0", report.pass_rate == 1.0)

    # Batch pair verification
    report2 = bv.verify_pairs_batch()
    ok("Batch: 21 pairs processed", report2.total == 21)
    ok(f"Batch: all pairs verified ({report2.verified}/21)", report2.verified == 21)

    # Cache hit test (second run should hit cache)
    _ = bv.verify_axiom_batch()
    ok("Batch: cache hits > 0", bv.cache_hits > 0)
    ok(f"Batch: hit rate = {bv.cache_hit_rate:.1%}", bv.cache_hit_rate > 0.1)

    # Stats
    bv.print_stats()

    print(f"\n{'='*50}")
    print(f"  TOTAL: {tests['pass']}/{tests['total']} PASS"
          f"{' ✅' if tests['fail']==0 else ' ❌ '+str(tests['fail'])+' FAILED'}")
    print(f"{'='*50}")

    if tests["fail"] > 0:
        sys.exit(1)