#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MSS内容诊断系统 v2.0 测试套件
基于严格自查标准测试
"""

import unittest
import sys
sys.path.insert(0, r'C:\MSS-AI-Project')

from mss_content_diagnoser_v2 import MSSContentDiagnoserV2, ViolationType

class TestMSSDiagnoserV2(unittest.TestCase):
    
    def setUp(self):
        self.diagnoser = MSSContentDiagnoserV2()
    
    def test_clean_text(self):
        """测试清洁文本（应无违规）"""
        text = "基于观察数据，我们可以推测可能的结果。建议进一步验证。"
        result = self.diagnoser.diagnose(text, claimed_layer="L3")
        self.assertGreater(result.overall_score, 0.8)
        self.assertEqual(result.actual_layer, "L3")
    
    def test_metaphor_hardening(self):
        """测试隐喻硬化检测"""
        text = "规范场维稳公理指出，政治系统必须维持稳定。"
        result = self.diagnoser.diagnose(text, claimed_layer="L2")
        
        violations = [v for v in result.violations 
                     if v['type'] == ViolationType.METAPHOR_HARDENING.value]
        self.assertGreater(len(violations), 0)
        self.assertEqual(result.actual_layer, "L3")
    
    def test_teleology_detection(self):
        """测试目的论残余检测"""
        text = "K3系统拼命地喊着胜利，刻意伪装自己的失败，本能地逃避现实。"
        result = self.diagnoser.diagnose(text, claimed_layer="L3")
        
        violations = [v for v in result.violations 
                     if v['type'] == ViolationType.TELEOLOGY_RESIDUE.value]
        self.assertGreater(len(violations), 0)
    
    def test_heat_tax_abuse(self):
        """测试热税滥用检测"""
        text = "认知热税不断累积，最终导致热税熔断。"
        result = self.diagnoser.diagnose(text, claimed_layer="L2")
        
        violations = [v for v in result.violations 
                     if v['type'] == ViolationType.HEAT_TAX_ABUSE.value]
        self.assertGreater(len(violations), 0)
    
    def test_operationalization_missing(self):
        """测试操作化缺失检测"""
        text = "规范场结构决定了系统的稳定性。拓扑相变导致秩序崩溃。"
        result = self.diagnoser.diagnose(text, claimed_layer="L2")
        
        violations = [v for v in result.violations 
                     if v['type'] == ViolationType.OPERATIONALIZATION_MISSING.value]
        self.assertGreater(len(violations), 0)
    
    def test_a3_violation(self):
        """测试A3违反检测"""
        text = "本质上就是因为政权想要维稳，所以一切行为都根源在于求生本能。"
        result = self.diagnoser.diagnose(text, claimed_layer="L3")
        
        violations = [v for v in result.violations 
                     if v['type'] == ViolationType.A3_VIOLATION.value]
        self.assertGreater(len(violations), 0)
    
    def test_upgrade_requirements(self):
        """测试升格要求生成"""
        text = """
        规范场维稳公理：认输 = 拓扑相变。
        K3拼命地喊着胜利，刻意伪装。
        热税清算终究要来。
        真正强大的系统从来不需要喊胜利。
        """
        result = self.diagnoser.diagnose(text, claimed_layer="L2")
        
        self.assertGreater(len(result.upgrade_requirements), 0)
        self.assertTrue(any("操作化" in req for req in result.upgrade_requirements))
        self.assertTrue(any("A3" in req or "随机" in req for req in result.upgrade_requirements))
    
    def test_full_self_diagnosis_text(self):
        """测试完整自查诊断文本"""
        text = """
        前文整段现代战争叙事分析，整体属于L3试探法层级洞察。
        
        意义规范场直接借用物理规范场概念套政治舆论场，无MSS专属操作化定义。
        旋耗散闭环只做定性描述，无输入输出边界、无阈值、无计算方式。
        意义量子照搬量子概念类比舆论信息单元，无对应可测量指标。
        拓扑相变把政权崩盘直接套拓扑相变，不满足严格定义。
        热税未定义γ对应的观测变量、无取值区间、无测算维度。
        
        前文多处把现象归因单一化：政权维稳焦虑、规避崩盘的刻意自保。
        忽略了多因素随机耦合：媒体生态演化、选举政治结构、算法茧房技术迭代。
        强行给K3系统赋予人格化求生本能，落入弱目的论残余。
        
        真正强大的意义系统，从来不需要天天在通稿里喊自己胜利。
        一旦承认失败，引发全盘崩溃的热税熔断。
        """
        
        result = self.diagnoser.diagnose(text, claimed_layer="L3")
        
        # L3文本应得较高分数
        self.assertGreater(result.overall_score, 0.6)
        # 应检测到目的论
        teleo = [v for v in result.violations 
                if v['type'] == ViolationType.TELEOLOGY_RESIDUE.value]
        self.assertGreater(len(teleo), 0)
    
    def test_layer_consistency_l3(self):
        """测试L3文本层级一致性"""
        text = "这是一个比喻性的说法，某种程度上可以类比为..."
        result = self.diagnoser.diagnose(text, claimed_layer="L3")
        self.assertEqual(result.actual_layer, "L3")
        self.assertGreater(result.overall_score, 0.7)
    
    def test_score_calculation(self):
        """测试分数计算"""
        # 清洁文本应得高分
        clean = self.diagnoser.diagnose("基于数据的分析。", "L3")
        self.assertGreater(clean.overall_score, 0.9)
        
        # 严重违规应得低分
        bad = self.diagnoser.diagnose("规范场公理证明了一切。K3刻意伪装。", "L1")
        self.assertLess(bad.overall_score, 0.5)
    
    def test_report_generation(self):
        """测试报告生成"""
        text = "规范场公理证明了一切。"
        result = self.diagnoser.diagnose(text, claimed_layer="L1")
        report = self.diagnoser.generate_report(result)
        
        self.assertIn("MSS 内容诊断报告 v2.0", report)
        self.assertIn("合规分数", report)
        self.assertIn("升格为L2所需条件", report)


if __name__ == '__main__':
    unittest.main(verbosity=2)
