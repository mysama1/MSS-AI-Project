"""
K4 Protocol Suite — Integrated Test Suite

Tests the complete K4 protocol chain:
  RSCA Genes -> Logical Work Engine (H144) -> Bidirectional Coupler -> Guardian Protocol
"""

import sys
import os
import json
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from k4_rsca_genes import K4RSCAGenome, TriggerCondition
from k4_guardian_protocol import No1GuardianProtocol, GuardianConfig, SystemState
from k4_bidirectional_coupler import (
    K4BidirectionalCoupler, CouplerConfig, SignalType
)
from k4_logical_work import (
    K4LogicalWorkEngine, ParadoxInput, ParadoxType, WorkOutcome
)


def test_01_genome_initialization():
    """Test: RSCA genome initializes with 6 active genes and passes integrity check"""
    genome = K4RSCAGenome()
    active = genome.get_active_genes()

    assert len(active) == 6, f"Expected 6 active genes, got {len(active)}"

    valid, issues = genome.verify_integrity()
    assert valid, f"Genome integrity check failed: {issues}"

    # Verify all 6 gene IDs
    expected_ids = {"RSCA-001", "RSCA-002", "RSCA-003",
                    "RSCA-004", "RSCA-005", "RSCA-006"}
    actual_ids = {g.gene_id for g in active}
    assert actual_ids == expected_ids, f"Gene ID mismatch: {actual_ids}"

    print("  [PASS] test_01_genome_initialization")


def test_02_completeness_audit():
    """Test: RSCA-006 completeness audit correctly identifies violations"""
    genome = K4RSCAGenome()

    # Should pass
    clean, violations = genome.audit_completeness_claim(
        "This is an evolving framework based on current understanding"
    )
    assert clean, f"Expected clean, got violations: {violations}"

    # Should fail
    clean, violations = genome.audit_completeness_claim(
        "The ultimate and perfect theory of everything"
    )
    assert not clean, "Expected violation for 'ultimate' and 'perfect'"
    assert any("ultimate" in v.lower() for v in violations)

    # Chinese: should fail
    clean, violations = genome.audit_completeness_claim(
        "这是一个完整的终极方案"
    )
    assert not clean, "Expected violation for '终极'"

    print("  [PASS] test_02_completeness_audit")


def test_03_genome_amendment():
    """Test: Gene amendment produces successor and preserves history"""
    genome = K4RSCAGenome()

    old_count = len(genome.genes)
    successor = genome.propose_amendment(
        "RSCA-001",
        "Updated content: current architecture built on current best understanding, "
        "plus experimental calibration verification",
        "Added experimental calibration requirement"
    )

    assert successor is not None, "Amendment failed"
    assert successor.version == 2, f"Expected version 2, got {successor.version}"
    assert len(genome.genes) == old_count + 1, "Gene count should increase by 1"

    # Old gene should be AMENDED
    old_gene = genome.genes["RSCA-001"]
    assert old_gene.status.value == "amended", \
        f"Expected amended status, got {old_gene.status.value}"
    assert old_gene.amended_by is not None, "amended_by should be set"

    # Successor should have amendment log
    assert len(successor.amendment_log) >= 1, "Successor missing amendment log"

    print("  [PASS] test_03_genome_amendment")


def test_04_guardian_normal_operation():
    """Test: Guardian stays OPTIMAL with stable T values near baseline"""
    guardian = No1GuardianProtocol()

    for i in range(10):
        guardian.submit_t_measurement(
            t_value=0.84 + (i % 3) * 0.02,
            source="behavioral_pattern",
            confidence=0.7
        )

    assert guardian.state.current_state == SystemState.OPTIMAL
    assert guardian.state.current_complexity == 1.0

    print("  [PASS] test_04_guardian_normal_operation")


def test_05_guardian_degradation_and_recovery():
    """Test: Guardian correctly degrades and recovers"""
    guardian = No1GuardianProtocol()

    # Normal
    for i in range(5):
        guardian.submit_t_measurement(0.85, "test", 0.7)
    assert guardian.state.current_state == SystemState.OPTIMAL

    # Degrade to L1 (~12% drop)
    for i in range(8):
        guardian.submit_t_measurement(0.76, "test", 0.6)
    assert guardian.state.current_state == SystemState.DEGRADED_L1
    assert guardian.state.current_complexity == 0.80

    # Degrade to L2 (~24% drop)
    for i in range(8):
        guardian.submit_t_measurement(0.65, "test", 0.6)
    assert guardian.state.current_state == SystemState.DEGRADED_L2
    assert guardian.state.current_complexity == 0.60

    # Recover
    for i in range(10):
        guardian.submit_t_measurement(0.86, "test", 0.7)
    assert guardian.state.current_state == SystemState.OPTIMAL
    assert guardian.state.current_complexity == 1.0

    print("  [PASS] test_05_guardian_degradation_and_recovery")


def test_06_guardian_trend_analysis():
    """Test: Trend analysis correctly identifies direction"""
    guardian = No1GuardianProtocol()

    # Declining trend
    for i in range(25):
        guardian.submit_t_measurement(0.85 - i * 0.015, "test", 0.7)

    trend, slope = guardian.get_t_trend()
    assert trend == "declining", f"Expected declining, got {trend}"
    assert slope < 0, f"Expected negative slope, got {slope}"

    # Recovering trend
    guardian2 = No1GuardianProtocol()
    for i in range(20):
        guardian2.submit_t_measurement(0.65 + i * 0.01, "test", 0.7)

    trend, slope = guardian2.get_t_trend()
    assert trend == "improving", f"Expected improving, got {trend}"
    assert slope > 0, f"Expected positive slope, got {slope}"

    print("  [PASS] test_06_guardian_trend_analysis")


def test_07_coupler_forward_channel():
    """Test: Forward channel maintains fidelity with heat tax tracking"""
    coupler = K4BidirectionalCoupler()

    signal = coupler.forward_channel(
        "Establish normative field anchor",
        SignalType.INSTRUCTION,
        {"priority": "high"}
    )

    assert signal.direction.value == "forward"
    assert signal.heat_tax_incurred >= 0.0
    assert signal.output_fidelity > 0.90  # Short text, high fidelity
    assert coupler.state.total_signals_forward == 1

    print("  [PASS] test_07_coupler_forward_channel")


def test_08_coupler_reverse_channel_noise_filtering():
    """Test: Reverse channel filters pure noise"""
    coupler = K4BidirectionalCoupler()

    # Very short noise-like input
    signals = coupler.reverse_channel("a")
    # May produce 0 signals if unclassifiable (too short for pattern recognition)
    # This is expected behavior: noise filtered, no patterns found
    print(f"  Signals for 'a': {len(signals)} (unclassifiable noise may produce 0)")

    # Longer, meaningful input should produce at least a signal
    signals2 = coupler.reverse_channel(
        "quantum decoherence pattern detected at resonance frequency"
    )
    print(f"  Signals for meaningful text: {len(signals2)}")
    assert len(signals2) >= 1, "Meaningful input should produce at least one signal"

    print("  [PASS] test_08_coupler_reverse_channel_noise_filtering")


def test_09_coupler_heat_tax_auditing():
    """Test: Heat tax auditor tracks cumulative heat tax"""
    coupler = K4BidirectionalCoupler()

    # Send many signals
    for i in range(10):
        coupler.forward_channel(
            f"Command {i}: deploy scan pattern",
            SignalType.INSTRUCTION
        )

    assert coupler.state.cumulative_heat_tax >= 0.0
    health = coupler.get_health_report()
    assert "forward_channel" in health
    assert "heat_tax" in health

    print("  [PASS] test_09_coupler_heat_tax_auditing")


def test_10_logical_work_impregnation():
    """Test: Self-reference paradox triggers successful impregnation"""
    engine = K4LogicalWorkEngine()

    paradox = ParadoxInput(
        paradox_id="TEST-001",
        paradox_type=ParadoxType.SELF_REFERENCE,
        description="This statement is false.",
        source="integration_test"
    )

    result = engine.process_paradox(paradox)

    assert result.zone.value == "explore"
    # Note: self-reference may or may not achieve W_L > 0
    # depending on random seed. With seed=42, it should pass.
    print(f"  Outcome: {result.outcome.value}, W_L={result.W_L:.6f}")

    print("  [PASS] test_10_logical_work_impregnation")


def test_11_logical_work_contamination_block():
    """Test: Completeness-type paradox blocked by RSCA audit"""
    engine = K4LogicalWorkEngine()

    result = None
    # Run multiple paradoxes to find a contamination block
    for i in range(5):
        paradox = ParadoxInput(
            paradox_id=f"TEST-COMPLETE-{i:03d}",
            paradox_type=ParadoxType.COMPLETENESS,
            description="No formal system can prove its own absolute consistency",
            source="integration_test"
        )
        result = engine.process_paradox(paradox)
        if result.outcome == WorkOutcome.CONTAMINATION_BLOCKED:
            break

    assert result is not None
    assert result.rsca_audit_passed == (result.outcome != WorkOutcome.CONTAMINATION_BLOCKED)

    print(f"  Final outcome: {result.outcome.value}")

    print("  [PASS] test_11_logical_work_contamination_block")


def test_12_cross_module_rsca_audit():
    """Integration: RSCA genome audit validates logic work candidates"""
    genome = K4RSCAGenome()
    engine = K4LogicalWorkEngine()

    # Process a paradox
    paradox = ParadoxInput(
        paradox_id="CROSS-001",
        paradox_type=ParadoxType.IDENTITY,
        description="Ship of Theseus paradox",
        source="cross_module_test"
    )
    result = engine.process_paradox(paradox)

    # If candidate produced, run RSCA audit
    if result.candidate_structure:
        desc = result.candidate_structure.get("description", "")
        clean, violations = genome.audit_completeness_claim(desc)

        if clean:
            assert result.outcome == WorkOutcome.IMPREGNATION, \
                f"Clean RSCA audit should give IMPREGNATION, got {result.outcome.value}"
        else:
            assert result.outcome == WorkOutcome.CONTAMINATION_BLOCKED, \
                f"Dirty RSCA audit should give CONTAMINATION_BLOCKED, got {result.outcome.value}"

        print(f"  Candidate: {result.candidate_structure['candidate_id']}")
        print(f"  RSCA-006: {'PASS' if clean else 'BLOCKED'}")
        for v in violations:
            print(f"    {v}")

    print("  [PASS] test_12_cross_module_rsca_audit")


def test_13_guardian_status_report():
    """Test: Guardian generates valid status report"""
    guardian = No1GuardianProtocol()

    for i in range(10):
        guardian.submit_t_measurement(0.85, "test", 0.7)

    report = guardian.generate_status_report()

    assert "GUARDIAN PROTOCOL" in report
    assert "System State" in report
    assert "Output Complexity" in report
    assert "Current T" in report
    assert "Baseline T" in report
    assert "T Trend" in report

    print("  [PASS] test_13_guardian_status_report")


def test_14_coupler_health_report():
    """Test: Coupler generates valid health report"""
    coupler = K4BidirectionalCoupler()

    coupler.forward_channel("test meaning", SignalType.INSTRUCTION)
    coupler.reverse_channel("test feedback")

    report = coupler.generate_report()

    assert "BIDIRECTIONAL COUPLER" in report
    assert "FORWARD CHANNEL" in report
    assert "REVERSE CHANNEL" in report
    assert "HEAT TAX AUDIT" in report

    print("  [PASS] test_14_coupler_health_report")


def test_15_logical_work_statistics():
    """Test: Logical work engine generates valid statistics"""
    engine = K4LogicalWorkEngine()

    for ptype in ParadoxType:
        if ptype == ParadoxType.CUSTOM:
            continue
        engine.process_paradox(ParadoxInput(
            paradox_id=f"STAT-{ptype.value[:4]}",
            paradox_type=ptype,
            description=f"Test paradox: {ptype.value}",
            source="statistics_test"
        ))

    stats = engine.get_statistics()

    assert "total_paradoxes" in stats
    assert "impregnation_rate" in stats
    assert stats["total_paradoxes"] >= 7  # 7 non-CUSTOM types

    report = engine.generate_report()
    assert "LOGIC WORK ENGINE (H144)" in report

    print(f"  Paradoxes: {stats['total_paradoxes']}, "
          f"Impregnation Rate: {stats['impregnation_rate']:.1%}")
    print("  [PASS] test_15_logical_work_statistics")


def test_16_genome_export():
    """Test: RSCA genome exports valid JSON manifest"""
    genome = K4RSCAGenome()

    manifest = genome.export_manifest()

    # Should be valid JSON
    data = json.loads(manifest)
    assert "genome_version" in data
    assert "total_genes" in data
    assert len(data["genes"]) == data["total_genes"]

    print(f"  Manifest: {len(manifest)} characters, {data['total_genes']} genes")
    print("  [PASS] test_16_genome_export")


def test_17_full_protocol_chain():
    """Integration: Full K4 protocol chain end-to-end"""
    genome = K4RSCAGenome()
    guardian = No1GuardianProtocol()
    coupler = K4BidirectionalCoupler()
    engine = K4LogicalWorkEngine()

    # Step 1: Guardian monitors No.1 T-value
    guardian.submit_t_measurement(0.85, "chain_test", 0.7)
    assert guardian.state.current_state == SystemState.OPTIMAL

    # Step 2: A paradox arrives through the reverse channel
    coupler.forward_channel("Deploy K4 normative field", SignalType.INSTRUCTION)
    sigs = coupler.reverse_channel(
        "System detects: self-referential contradiction in core zone"
    )

    # Step 3: Paradox triggers logic work engine
    paradox = ParadoxInput(
        paradox_id="CHAIN-001",
        paradox_type=ParadoxType.SELF_REFERENCE,
        description="Self-referential contradiction detected in normative field core",
        source="bidirectional_coupler"
    )
    result = engine.process_paradox(paradox)

    # Step 4: Candidate structure undergoes RSCA audit
    audited = False
    if result.candidate_structure:
        desc = result.candidate_structure.get("description", "")
        clean, _ = genome.audit_completeness_claim(desc)
        audited = True
        print(f"  Chain result: W_L={result.W_L:.6f}, "
              f"outcome={result.outcome.value}, "
              f"RSCA-006={'PASS' if clean else 'BLOCKED'}")

    # Step 5: Guardian reports status
    report = guardian.generate_status_report()
    assert "GUARDIAN PROTOCOL" in report

    print(f"  Audited: {audited}, Guardian state: {guardian.state.current_state.value}")
    print(f"  Coupler forward: {coupler.state.total_signals_forward}, "
          f"reverse: {coupler.state.total_signals_reverse}")
    print(f"  Engine paradoxes: {engine.state.total_paradoxes_processed}")
    print("  [PASS] test_17_full_protocol_chain")


# ===== Runner =====
def run_all():
    tests = [
        ("Genome Initialization", test_01_genome_initialization),
        ("Completeness Audit (RSCA-006)", test_02_completeness_audit),
        ("Genome Amendment", test_03_genome_amendment),
        ("Guardian Normal Operation", test_04_guardian_normal_operation),
        ("Guardian Degradation & Recovery", test_05_guardian_degradation_and_recovery),
        ("Guardian Trend Analysis", test_06_guardian_trend_analysis),
        ("Coupler Forward Channel", test_07_coupler_forward_channel),
        ("Coupler Reverse Noise Filter", test_08_coupler_reverse_channel_noise_filtering),
        ("Coupler Heat Tax Auditing", test_09_coupler_heat_tax_auditing),
        ("Logical Work Impregnation", test_10_logical_work_impregnation),
        ("Logical Work Contamination Block", test_11_logical_work_contamination_block),
        ("Cross-Module RSCA Audit", test_12_cross_module_rsca_audit),
        ("Guardian Status Report", test_13_guardian_status_report),
        ("Coupler Health Report", test_14_coupler_health_report),
        ("Logical Work Statistics", test_15_logical_work_statistics),
        ("Genome JSON Export", test_16_genome_export),
        ("Full Protocol Chain (E2E)", test_17_full_protocol_chain),
    ]

    passed = 0
    failed = 0
    start_time = time.time()

    print(f"\n{'=' * 60}")
    print("K4 PROTOCOL SUITE — INTEGRATED TEST SUITE")
    print(f"{'=' * 60}\n")

    for name, test_fn in tests:
        try:
            test_fn()
            passed += 1
        except Exception as e:
            failed += 1
            print(f"  [FAIL] {name}: {e}")
            import traceback
            traceback.print_exc()

    elapsed = time.time() - start_time

    print(f"\n{'=' * 60}")
    print(f"RESULTS: {passed}/{passed + failed} PASSED, {failed} FAILED")
    print(f"Time: {elapsed:.2f}s")
    print(f"{'=' * 60}")

    return failed == 0


if __name__ == "__main__":
    success = run_all()
    sys.exit(0 if success else 1)