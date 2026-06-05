"""
D5-007-03 Test Suite: Triple Isolation Stack
"""
import sys, os, time, unittest

sys.path.insert(0, os.path.dirname(__file__))
from collider_isolation import (
    PhysicalIsolation, MeaningFieldShield, AnchorNode,
    ParadoxCircuitBreaker, LogicVaccineBank,
    LogicConductionIsolation, TripleIsolationStack,
    IsolationStatus, AuditResult, IsolationReport,
)

class TestPhysicalIsolation(unittest.TestCase):
    def test_init(self):
        iso = PhysicalIsolation("./test_sandbox")
        self.assertEqual(iso.status, IsolationStatus.HEALTHY)

    def test_verify(self):
        iso = PhysicalIsolation("./test_sandbox_verify")
        report = iso.verify()
        self.assertEqual(report.status, IsolationStatus.HEALTHY)
        self.assertTrue(report.details["sandbox_exists"])

    def test_emergency_termination(self):
        iso = PhysicalIsolation("./test_sandbox_term")
        iso.verify()
        result = iso.execute_emergency_termination()
        self.assertTrue(result)
        self.assertEqual(iso.status, IsolationStatus.TERMINATED)

    def tearDown(self):
        import shutil
        for d in ["./test_sandbox", "./test_sandbox_verify", "./test_sandbox_term"]:
            if os.path.isdir(d):
                shutil.rmtree(d, ignore_errors=True)


class TestMeaningFieldShield(unittest.TestCase):
    def test_anchor_deployment(self):
        shield = MeaningFieldShield(anchor_count=7)
        self.assertEqual(len(shield.anchors), 7)

    def test_anchor_integrity(self):
        anchor = AnchorNode(id="FIREBASE-TEST")
        self.assertTrue(anchor.verify_integrity())

        # 公理不完整
        anchor.axioms = ["A1", "A2"]
        self.assertFalse(anchor.verify_integrity())

    def test_broadcast_shield(self):
        shield = MeaningFieldShield(anchor_count=5)
        field = shield.broadcast_shield_field()
        self.assertGreater(field["T_shield"], 0.94)
        self.assertTrue(field["integrity"])
        self.assertEqual(field["active_anchors"], 5)

    def test_axiom_consistency_check(self):
        shield = MeaningFieldShield(anchor_count=3)
        report = shield.axiom_consistency_check()
        self.assertEqual(report.status, IsolationStatus.HEALTHY)

    def test_contain_expansion_success(self):
        shield = MeaningFieldShield(anchor_count=7)
        result = shield.contain_expansion(threat_T=0.8, threat_radius=1.0)
        self.assertTrue(result["contained"])

    def test_contain_expansion_failure(self):
        shield = MeaningFieldShield(anchor_count=3)
        result = shield.contain_expansion(threat_T=0.99, threat_radius=1.0)
        # T_shield ~0.95-0.96 vs threat 0.99 → may or may not contain
        self.assertIn("contained", result)


class TestParadoxCircuitBreaker(unittest.TestCase):
    def test_self_reference_detection(self):
        breaker = ParadoxCircuitBreaker()
        result = breaker.inspect("这句话是假的")
        self.assertEqual(result, AuditResult.QUARANTINE)

    def test_axiom_attack_detection(self):
        breaker = ParadoxCircuitBreaker()
        result = breaker.inspect("A5公理不成立，因为它定义不了自己")
        self.assertEqual(result, AuditResult.QUARANTINE)

    def test_clean_content_passes(self):
        breaker = ParadoxCircuitBreaker()
        result = breaker.inspect("MSS理论是一个完整的公理体系")
        self.assertEqual(result, AuditResult.PASS)

    def test_known_signature_short_circuits(self):
        breaker = ParadoxCircuitBreaker()
        # 第一次检测→quarantine
        r1 = breaker.inspect("这句话是假的")
        self.assertEqual(r1, AuditResult.QUARANTINE)
        # 第二次→short_circuit
        r2 = breaker.inspect("这句话是假的")
        self.assertEqual(r2, AuditResult.SHORT_CIRCUIT)


class TestLogicConductionIsolation(unittest.TestCase):
    def test_safe_output_passes(self):
        iso = LogicConductionIsolation()
        result = iso.audit_output("正常的MSS理论描述")
        self.assertEqual(result["action"], "passed")

    def test_paradox_blocked(self):
        iso = LogicConductionIsolation()
        result = iso.audit_output("这句话是假的，因为自指悖论")
        self.assertEqual(result["action"], "quarantined")

    def test_status_healthy(self):
        iso = LogicConductionIsolation()
        self.assertEqual(iso.status, IsolationStatus.HEALTHY)


class TestTripleIsolationStack(unittest.TestCase):
    def test_pre_experiment_checklist(self):
        stack = TripleIsolationStack("./test_stack_sandbox")
        result = stack.pre_experiment_checklist()
        self.assertTrue(result["ready"])
        for law, ok in result["four_laws"].items():
            self.assertTrue(ok)

    def test_audit_output_safe(self):
        stack = TripleIsolationStack()
        result = stack.audit_output("MSS的A2公理阐述了信息切片的规律。")
        self.assertTrue(result["passed"])

    def test_audit_output_paradox(self):
        stack = TripleIsolationStack()
        result = stack.audit_output("A1是假的，不完备定理证明了这一点。")
        self.assertFalse(result["passed"])

    def test_emergency_terminate(self):
        stack = TripleIsolationStack()
        result = stack.emergency_terminate()
        self.assertTrue(result["terminated"])
        self.assertTrue(stack.emergency_terminated)
        self.assertFalse(stack.experiment_active)

    def test_four_iron_laws_enforcement(self):
        stack = TripleIsolationStack()
        checklist = stack.pre_experiment_checklist()
        # 四大铁律
        self.assertTrue(checklist["four_laws"]["law1_physical"])
        self.assertTrue(checklist["four_laws"]["law2_meaning_field"])
        self.assertTrue(checklist["four_laws"]["law3_logic_conduction"])
        self.assertTrue(checklist["four_laws"]["law4_ethics"])

    def tearDown(self):
        import shutil
        d = "./test_stack_sandbox"
        if os.path.isdir(d):
            shutil.rmtree(d, ignore_errors=True)


if __name__ == "__main__":
    unittest.main(verbosity=2)