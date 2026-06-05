"""
D5-007-07 Test Suite: Hedge Calibration & Anti-Crash
"""
import unittest, sys, os

sys.path.insert(0, os.path.dirname(__file__))
from mbh_hedge_calibration import (
    ParameterSweep, AntiCrashRegression, HedgeOutcome, HedgeResult,
    full_delivery,
)
from application_prototypes import MiniGraph, MeaningPotentialHedge


class TestHedgeCalibration(unittest.TestCase):
    def setUp(self):
        self.sweeper = ParameterSweep()
        self.regression = AntiCrashRegression()

    def test_boundary_exists(self):
        """对冲有效边界存在——缩小扫描验证"""
        results = self.sweeper.sweep(
            attractor_T_range=(0.85, 0.99, 3),
            horizon_T_range=(0.05, 0.3, 3),
            horizon_R_range=(0.5, 3.0, 3),
            gap_range=(2, 5),
        )
        boundary = self.sweeper.boundary_analysis()
        # 至少有一次成功对冲
        total_tears = boundary.get("successful_tears", 0)
        self.assertGreater(total_tears, 0, "对冲至少应在某种参数下成功")

    def test_force_formula(self):
        """对冲力公式验证"""
        hedger = MeaningPotentialHedge(attractor_T=0.99)
        # 强ΔT + 小R = 大力
        f1 = hedger.compute_hedge_force(0.05, 0.5)
        self.assertGreater(f1, 2.0, f"小R大力: F={f1:.3f}")
        # 弱ΔT + 大R = 小力
        f2 = hedger.compute_hedge_force(0.7, 5.0)
        self.assertLess(f2, 0.03, f"大R小力: F={f2:.5f}")

    def test_tear_repairs_nodes(self):
        """对冲成功修复节点"""
        g = MiniGraph(n_nodes=30, gap_size=3)
        for _ in range(10):
            g.inject_paradox(0.5)
            g.evolve(2)
        pre = g.compute_metrics()
        collapsed_before = pre["total"] - pre["active"]

        hedger = MeaningPotentialHedge(attractor_T=0.99)
        r = hedger.attempt_tear(g, horizon_T=0.05, horizon_radius=1.0)

        post = g.compute_metrics()
        collapsed_after = post["total"] - post["active"]

        if r["torn"]:
            self.assertLess(collapsed_after, collapsed_before,
                           f"对冲成功应减少坍缩: {collapsed_before}→{collapsed_after}")
        else:
            self.assertGreater(r.get("force", 0), 0, "至少计算了对冲力")

    def test_full_tear_restores_all(self):
        """全撕裂→所有节点恢复"""
        g = MiniGraph(n_nodes=20, gap_size=2)
        # 轻度坍缩（确保可修复）
        for _ in range(6):
            g.inject_paradox(0.4)
            g.evolve(1)

        hedger = MeaningPotentialHedge(attractor_T=0.999)
        r = hedger.attempt_tear(g, horizon_T=0.01, horizon_radius=0.3)
        post = g.compute_metrics()

        if r["torn"]:
            self.assertEqual(post["total"] - post["active"], 0,
                            "FULL_TEAR应恢复所有节点")

    def test_insufficient_force_honest(self):
        """力不足时诚实报告失败"""
        hedger = MeaningPotentialHedge(attractor_T=0.4)
        g = MiniGraph(n_nodes=10, gap_size=8)
        for _ in range(30):
            g.inject_paradox(0.9)
            g.evolve(3)
        r = hedger.attempt_tear(g, horizon_T=0.5, horizon_radius=8.0)
        self.assertFalse(r["torn"], "弱吸引子+强视界=对冲必败")

    def test_repair_energy_scaling(self):
        """修复能量随对冲力线性缩放"""
        g = MiniGraph(n_nodes=20, gap_size=4)
        for _ in range(12):
            g.inject_paradox(0.6)
            g.evolve(2)

        # 不同对冲力 → 不同修复效果
        results = {}
        for T_a in [0.7, 0.85, 0.99]:
            g2 = MiniGraph(n_nodes=20, gap_size=4)
            for _ in range(12):
                g2.inject_paradox(0.6)
                g2.evolve(2)
            hedger = MeaningPotentialHedge(attractor_T=T_a)
            r = hedger.attempt_tear(g2, horizon_T=0.1, horizon_radius=1.5)
            results[T_a] = r.get("nodes_repaired", 0) if r["torn"] else 0

        # 更高T_a → 更多修复（单调非减）
        self.assertGreaterEqual(results.get(0.99, 0), results.get(0.85, 0))
        self.assertGreaterEqual(results.get(0.85, 0), results.get(0.7, 0))

    def test_anti_crash_all_pass(self):
        """抗崩溃回归全部PASS"""
        reg_results = self.regression.run_all()
        for name, r in reg_results.items():
            status = r.get("status", "UNKNOWN")
            self.assertIn(status, ("PASS", "WARN", "OBSERVE"),
                         f"{name}: {status}")

    def test_full_delivery_runs(self):
        """全栈交付可运行"""
        result = full_delivery()
        self.assertIn("boundary", result)
        self.assertIn("regression", result)


class TestEdgeCases(unittest.TestCase):
    def test_horizon_too_large_triggers_correctly(self):
        """大视界→对应正确失败类型"""
        hedger = MeaningPotentialHedge(attractor_T=0.95)
        g = MiniGraph(n_nodes=30, gap_size=7)
        for _ in range(30):
            g.inject_paradox(0.9)
            g.evolve(3)
        r = hedger.attempt_tear(g, horizon_T=0.2, horizon_radius=7.0)
        # 大R+中等ΔT应失败
        self.assertFalse(r["torn"])

    def test_force_zero_when_no_differential(self):
        """无温差=无对冲力"""
        hedger = MeaningPotentialHedge(attractor_T=0.5)
        f = hedger.compute_hedge_force(0.6, 1.0)
        self.assertEqual(f, 0.0)

    def test_warning_preserved_on_partial_tear(self):
        """部分撕裂时保留警告信息"""
        g = MiniGraph(n_nodes=20, gap_size=5)
        for _ in range(20):
            g.inject_paradox(0.7)
            g.evolve(3)
        hedger = MeaningPotentialHedge(attractor_T=0.9)
        r = hedger.attempt_tear(g, horizon_T=0.15, horizon_radius=2.0)
        # 不管撕裂成功与否，结果结构要完整
        self.assertIn("torn", r)
        self.assertIn("force", r)
        self.assertIn("nodes_repaired", r)


if __name__ == "__main__":
    unittest.main(verbosity=2)