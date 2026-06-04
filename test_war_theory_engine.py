"""
Test suite for War Theory Engine
热税战争理论引擎测试
"""

import unittest
from war_theory_engine import (
    WarTheoryEngine, HeatTaxExchangeRatio, SelfProofTrapDetector,
    HeatTaxCriticalPoint, MeaningContagionModel,
    TacticalMode, BattlefieldType
)

class TestHeatTaxExchangeRatio(unittest.TestCase):
    """测试热税交换比计算"""

    def test_damage_without_destroy(self):
        """测试打坏不摧毁"""
        result = HeatTaxExchangeRatio.calculate_damage_without_destroy(
            friendly_cost=500,
            enemy_repair_cost=50000,
            enemy_operational_loss=2000,
            duration_days=30
        )

        self.assertIn("R_gamma", result)
        self.assertGreater(result["R_gamma"], 0)
        self.assertEqual(result["tactical_mode"], "damage_without_destroy")

    def test_bait_and_trap(self):
        """测试诱导攻击"""
        result = HeatTaxExchangeRatio.calculate_bait_and_trap(
            bait_cost=100,
            enemy_interception_cost=5000,
            enemy_false_positive_rate=0.2
        )

        self.assertIn("R_gamma", result)
        self.assertGreater(result["R_gamma"], 0)

    def test_distributed_saturation(self):
        """测试分布式饱和"""
        result = HeatTaxExchangeRatio.calculate_distributed_saturation(
            unit_cost=500,
            unit_count=100,
            enemy_defense_cost_per_unit=1000,
            enemy_defense_capacity=50
        )

        self.assertIn("R_gamma", result)
        self.assertGreater(result["saturation_factor"], 1.0)

    def test_cognitive_pollution(self):
        """测试认知污染"""
        result = HeatTaxExchangeRatio.calculate_cognitive_pollution(
            forge_cost=10,
            enemy_verify_cost=1000,
            pollution_level=3
        )

        self.assertIn("R_gamma_c", result)
        self.assertEqual(result["level_multiplier"], 1000)

    def test_assess_ratio(self):
        """测试交换比评估"""
        self.assertIn("亏损", HeatTaxExchangeRatio._assess_ratio(0.5))
        self.assertIn("盈利", HeatTaxExchangeRatio._assess_ratio(5))
        self.assertIn("压倒性", HeatTaxExchangeRatio._assess_ratio(500))

class TestSelfProofTrapDetector(unittest.TestCase):
    """测试自证陷阱检测"""

    def test_detect_identity_trap(self):
        """检测身份自证陷阱"""
        result = SelfProofTrapDetector.detect_trap("你怎么证明你没有抄袭？")

        self.assertTrue(result["is_trap"])
        self.assertEqual(result["trap_type"], "identity_proof")
        self.assertIsNotNone(result["recommended_response"])

    def test_detect_negative_assertion(self):
        """检测绝对化表述陷阱"""
        result = SelfProofTrapDetector.detect_trap("我们绝对安全，百分之百可靠")

        self.assertTrue(result["is_trap"])
        self.assertEqual(result["trap_type"], "negative_assertion")

    def test_safe_message(self):
        """安全消息不应触发"""
        result = SelfProofTrapDetector.detect_trap("今天的项目进展如何？")

        self.assertFalse(result["is_trap"])

    def test_response_generation(self):
        """测试响应生成"""
        response = SelfProofTrapDetector._generate_response("identity_proof")
        self.assertIn("举证责任", response)

class TestHeatTaxCriticalPoint(unittest.TestCase):
    """测试热税临界点"""

    def test_safe_status(self):
        """测试安全状态"""
        result = HeatTaxCriticalPoint.check_critical_point(
            system_level="organization",
            current_gamma=0.2,
            stress_duration_days=30
        )

        self.assertEqual(result["status"], "safe")

    def test_warning_status(self):
        """测试预警状态"""
        result = HeatTaxCriticalPoint.check_critical_point(
            system_level="organization",
            current_gamma=0.35,
            stress_duration_days=30
        )

        self.assertEqual(result["status"], "warning")

    def test_critical_status(self):
        """测试危急状态"""
        result = HeatTaxCriticalPoint.check_critical_point(
            system_level="organization",
            current_gamma=0.48,
            stress_duration_days=90,
            gamma_trend=0.01
        )

        self.assertEqual(result["status"], "critical")

    def test_collapse_status(self):
        """测试崩溃状态"""
        result = HeatTaxCriticalPoint.check_critical_point(
            system_level="organization",
            current_gamma=0.55,
            stress_duration_days=100
        )

        self.assertEqual(result["status"], "collapse")

    def test_different_system_levels(self):
        """测试不同系统级别"""
        individual = HeatTaxCriticalPoint.check_critical_point(
            "individual", 0.5, 10
        )
        nation = HeatTaxCriticalPoint.check_critical_point(
            "nation", 0.7, 20
        )

        # 个人级别0.5是safe（阈值0.8），国家级别0.7是critical（阈值0.3）
        self.assertEqual(individual["status"], "safe")
        self.assertEqual(nation["status"], "collapse")

class TestMeaningContagionModel(unittest.TestCase):
    """测试意义传染模型"""

    def test_decay_phase(self):
        """测试衰减阶段"""
        result = MeaningContagionModel.calculate_R0(
            contact_rate=5,
            conversion_rate=0.1,
            retention_rate=0.5
        )

        self.assertLess(result["R0"], 1)
        self.assertEqual(result["phase"], "decay")

    def test_explosive_phase(self):
        """测试爆发阶段"""
        result = MeaningContagionModel.calculate_R0(
            contact_rate=50,
            conversion_rate=0.5,
            retention_rate=0.9,
            amplification_factor=3.0
        )

        self.assertGreater(result["R0"], 3)
        self.assertEqual(result["phase"], "explosive")

    def test_amplification_effect(self):
        """测试放大因子效果"""
        base = MeaningContagionModel.calculate_R0(10, 0.3, 0.7, 1.0)
        amplified = MeaningContagionModel.calculate_R0(10, 0.3, 0.7, 5.0)

        self.assertAlmostEqual(amplified["R0"], base["R0"] * 5, places=3)

class TestWarTheoryEngine(unittest.TestCase):
    """测试战争理论引擎统一接口"""

    def setUp(self):
        self.engine = WarTheoryEngine()

    def test_simulate_scenario(self):
        """测试场景模拟"""
        result = self.engine.simulate_tactical_scenario(
            mode=TacticalMode.DAMAGE_WITHOUT_DESTROY,
            friendly_params={"cost": 1000},
            enemy_params={"repair_cost": 10000, "daily_loss": 500}
        )

        self.assertIn("R_gamma", result)

    def test_detect_and_counter(self):
        """测试检测与反制"""
        result = self.engine.detect_and_counter_trap("你怎么证明你没有抄袭？")

        self.assertTrue(result["threat_detected"])
        self.assertIn("counter_strategy", result)

    def test_assess_health(self):
        """测试健康评估"""
        result = self.engine.assess_system_health(
            system_level="team",
            current_gamma=0.4,
            stress_duration=30
        )

        self.assertIn("status", result)
        self.assertIn("recommendations", result)

    def test_project_contagion(self):
        """测试传染预测"""
        result = self.engine.project_meaning_contagion(
            contact_rate=20,
            conversion_rate=0.4,
            retention_rate=0.85
        )

        self.assertIn("R0", result)
        self.assertIn("contagion_timeline", result)

class TestQuickFunctions(unittest.TestCase):
    """测试便捷函数"""

    def test_quick_tactical(self):
        """测试快速战术评估"""
        from war_theory_engine import quick_tactical_assessment

        result = quick_tactical_assessment("damage", 500, 5000)
        self.assertIn("R_gamma", result)

    def test_check_message(self):
        """测试消息检查"""
        from war_theory_engine import check_message_for_traps

        result = check_message_for_traps("你怎么证明")
        self.assertTrue(result["threat_detected"])

if __name__ == "__main__":
    unittest.main()
