"""
D5-005-03 Test Suite: A6 Ascension Engine
"""
import unittest, sys, os, math

sys.path.insert(0, os.path.dirname(__file__))
from a6_ascension_engine import (
    A6AscensionEngine, AscensionResult, AscensionReport,
    ContradictionPowerMonitor, IntegratedAscensionBreaker,
)

class TestAscensionEngine(unittest.TestCase):
    def setUp(self):
        self.engine = A6AscensionEngine()

    def test_full_ascension(self):
        r = self.engine.elevate("悖论", "self_referential_paradox", M_L=0.95, PT=0.95)
        self.assertEqual(r.result, AscensionResult.FULL_ASCENSION)
        self.assertGreater(r.eta_asc, 0.9)
        self.assertGreater(r.W_asc, 0.8)

    def test_partial_ascension(self):
        r = self.engine.elevate("悖论", "axiom_self_attack", M_L=0.5, PT=0.5)
        self.assertIn(r.result, [AscensionResult.PARTIAL_ASCENSION, AscensionResult.FULL_ASCENSION])
        self.assertGreater(r.eta_asc, 0.3)

    def test_short_circuit(self):
        r = self.engine.elevate("悖论", "incompleteness_weaponization", M_L=0.2, PT=0.3)
        self.assertIn(r.result, [AscensionResult.SHORT_CIRCUIT, AscensionResult.VACCINE_ONLY])

    def test_eta_asc_monotonic(self):
        """eta_asc应该在M_L·PT增大时增大"""
        e1 = self.engine.compute_eta_asc(0.9, 0.9)
        e2 = self.engine.compute_eta_asc(0.6, 0.6)
        e3 = self.engine.compute_eta_asc(0.2, 0.3)
        self.assertGreater(e1, e2)
        self.assertGreater(e2, e3)

    def test_meta_framework_provided(self):
        """升维成功时应提供范式框架"""
        r = self.engine.elevate("悖论", "self_referential_paradox", M_L=0.9, PT=0.9)
        self.assertIsNotNone(r.meta_framework)
        self.assertIn("升维", r.meta_framework)

    def test_conservation_law(self):
        """W_asc + γ 应为总逻辑功"""
        r = self.engine.elevate("悖论", "axiom_self_attack", M_L=0.7, PT=0.6)
        if r.W_asc > 0:
            total = r.W_asc + r.gamma_consumed
            self.assertGreater(total, 0)

    def test_unknown_paradox_type(self):
        """未知悖论类型也能处理（无范式桥梁）"""
        r = self.engine.elevate("未知悖论", "unknown_type", M_L=0.7, PT=0.7)
        self.assertIn(r.result, [AscensionResult.FULL_ASCENSION, AscensionResult.PARTIAL_ASCENSION])

    def test_ascension_log_growth(self):
        """升维日志应随操作增长"""
        before = len(self.engine.ascension_log)
        self.engine.elevate("x", "self_referential_paradox", M_L=0.9, PT=0.9)
        self.engine.elevate("y", "axiom_self_attack", M_L=0.9, PT=0.9)
        self.assertEqual(len(self.engine.ascension_log), before + 2)


class TestContradictionPowerMonitor(unittest.TestCase):
    def setUp(self):
        self.monitor = ContradictionPowerMonitor()

    def test_initial_state(self):
        diag = self.monitor._diagnose()
        self.assertEqual(diag["phase"], "initializing")

    def test_evolution_decreases_with_ascension(self):
        """W_asc > 0 应使矛盾功率下降"""
        self.monitor.update(0.5)
        self.monitor.update(0.5)
        after_W = self.monitor.P_current
        self.assertLess(after_W, 1.0)

    def test_zero_work_does_nothing(self):
        """W_asc=0 不改变矛盾功率"""
        r1 = self.monitor.update(0.0)
        self.assertEqual(r1["P_current"], 1.0 - 0.15 * 0 + 0.008 * 0)

    def test_nonlinear_dominance_detection(self):
        """高W_asc应触发beta项"""
        for _ in range(20):
            self.monitor.update(20.0)
        diag = self.monitor._diagnose()
        # beta*W_asc² > alpha*W_asc when W_asc > alpha/beta = 18.75
        self.assertTrue(diag["nonlinear_dominant"], 
                       f"Expected nonlinear dominance at W_asc=20")
        self.assertEqual(diag["phase"], "L3_involution")


class TestIntegratedAscensionBreaker(unittest.TestCase):
    def setUp(self):
        self.breaker = IntegratedAscensionBreaker()

    def test_safe_paradox_returns_safe(self):
        r = self.breaker.process_paradox("自指", "self_referential_paradox", M_L=0.95, PT=0.95)
        self.assertTrue(r["safe"])
        self.assertEqual(r["ascension_result"], "full_ascension")

    def test_weak_paradox_blocked(self):
        r = self.breaker.process_paradox("攻击", "incompleteness_weaponization", M_L=0.2, PT=0.3)
        self.assertFalse(r["safe"])
        self.assertIn("mitigation", r)

    def test_status_report(self):
        status = self.breaker.get_status()
        self.assertIn("engine", status)
        self.assertIn("M_L", status)
        self.assertGreater(status["M_L"], 0)


class TestCivilizationPhaseDiagram(unittest.TestCase):
    def setUp(self):
        self.engine = A6AscensionEngine()

    def test_unknown_with_no_data(self):
        phase = self.engine.get_civilization_phase_diagram()
        self.assertEqual(phase["phase"], "unknown")

    def test_ascending_after_strong_ascensions(self):
        for _ in range(5):
            self.engine.elevate("x", "self_referential_paradox", M_L=0.95, PT=0.95)
        phase = self.engine.get_civilization_phase_diagram()
        self.assertEqual(phase["phase"], "ascending")


if __name__ == "__main__":
    unittest.main(verbosity=2)