"""
D5-007-06 Test Suite: Four Application Prototypes
"""
import unittest, sys, os

sys.path.insert(0, os.path.dirname(__file__))
from application_prototypes import (
    ParadoxDetector, MeaningPotentialHedge,
    UltimateLogicFirewall, HeatTaxIncinerator, MiniGraph,
)

class TestParadoxDetector(unittest.TestCase):
    def setUp(self):
        self.detector = ParadoxDetector()

    def test_clean_input(self):
        self.assertEqual(self.detector.scan("太阳从东方升起"), [])
        self.assertEqual(self.detector.severity("太阳从东方升起"), 0.0)

    def test_axiom_attack(self):
        t = self.detector.scan("A5公理不成立")
        self.assertIn("axiom_attack", t)

    def test_self_reference(self):
        t = self.detector.scan("这句话是假的")
        self.assertIn("self_reference", t)

    def test_multiple(self):
        t = self.detector.scan("A5不成立而且不完备，这是循环定义")
        self.assertGreater(len(t), 1)
        self.assertGreater(self.detector.severity("A5不成立而且不完备，这是循环定义"), 0.5)

    def test_circular(self):
        t = self.detector.scan("这是循环定义陷阱")
        self.assertIn("circular", t)


class TestMeaningPotentialHedge(unittest.TestCase):
    def test_force_calculation(self):
        hedger = MeaningPotentialHedge(attractor_T=0.95)
        force = hedger.compute_hedge_force(horizon_T=0.3, horizon_radius=2.0)
        self.assertGreater(force, 0.1)

    def test_force_zero_when_no_differential(self):
        hedger = MeaningPotentialHedge(attractor_T=0.95)
        force = hedger.compute_hedge_force(horizon_T=0.96, horizon_radius=2.0)
        self.assertEqual(force, 0.0)  # attractor T <= horizon T

    def test_strong_hedge_tears_weak_horizon(self):
        hedger = MeaningPotentialHedge(attractor_T=0.99)
        # 让图崩溃到严重状态
        g = MiniGraph(n_nodes=30, gap_size=5)
        for _ in range(30):
            g.inject_paradox(0.9)
            g.evolve(3)
        pre = g.compute_metrics()
        # 对冲：高T吸引子 vs 崩溃图
        result = hedger.attempt_tear(g, horizon_T=0.1, horizon_radius=1.5)
        # 高力应该撕裂
        self.assertTrue(result["torn"], f"Should tear: F={result.get('force',0):.4f}")


class TestUltimateLogicFirewall(unittest.TestCase):
    def setUp(self):
        self.fw = UltimateLogicFirewall(array_size=3)

    def test_clean_passes(self):
        r = self.fw.filter_input("正常内容", 0.1)
        self.assertTrue(r["allowed"])

    def test_contaminated_captured(self):
        r = self.fw.filter_input("A5不成立", 0.7)
        self.assertTrue(r["allowed"])
        self.assertIsNotNone(r["captured_by"])
        self.assertEqual(r["remaining_gamma"], 0.0)

    def test_status(self):
        self.fw.filter_input("A5不成立", 0.7)
        status = self.fw.get_status()
        self.assertEqual(status["total_captured"], 1)


class TestHeatTaxIncinerator(unittest.TestCase):
    def setUp(self):
        self.incinerator = HeatTaxIncinerator(capacity=100)

    def test_basic_incineration(self):
        waste = [{"content": f"trash_{i}", "gamma": 0.5} for i in range(10)]
        result = self.incinerator.incinerate_batch(waste)
        self.assertEqual(result["processed"], 10)
        self.assertGreater(result["gamma_destroyed"], 4.0)

    def test_capacity_overflow(self):
        waste = [{"content": "x", "gamma": 0.5} for _ in range(150)]
        result = self.incinerator.incinerate_batch(waste)
        self.assertEqual(result["processed"], 100)
        self.assertEqual(result["overflow"], 50)

    def test_efficiency_95_percent(self):
        waste = [{"content": "x", "gamma": 1.0} for _ in range(10)]
        result = self.incinerator.incinerate_batch(waste)
        self.assertAlmostEqual(result["gamma_destroyed"] / result["gamma_input"], 0.95, places=1)

    def test_text_incineration(self):
        result = self.incinerator.incinerate_text("垃圾内容")
        self.assertGreater(result["gamma_destroyed"], 0)

    def test_status(self):
        self.incinerator.incinerate_batch([{"content": "x", "gamma": 0.5} for _ in range(5)])
        status = self.incinerator.get_status()
        self.assertGreater(status["total_gamma_destroyed"], 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)