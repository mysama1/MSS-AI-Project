#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MSS内容诊断系统测试
"""

import unittest
import sys
sys.path.insert(0, r'C:\MSS-AI-Project')

from mss_content_diagnoser import MSSContentDiagnoser, ViolationType

class TestMSSDiagnoser(unittest.TestCase):
    
    def setUp(self):
        self.diagnoser = MSSContentDiagnoser()
    
    def test_clean_text(self):
        """测试清洁文本（应无违规）"""
        text = "这是一个普通的分析。基于观察，我们可以推测可能的结果。"
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
    
    def test_layer_confusion_l1_to_l3(self):
        """测试L1术语被L3使用"""
        text = "物理层就像一个大舞台，各种力量在上面表演。"
        result = self.diagnoser.diagnose(text, claimed_layer="L1")
        
        self.assertLess(result.overall_score, 0.5)
        self.assertEqual(result.actual_layer, "L3")
    
    def test_unfalsifiable_statements(self):
        """测试不可证伪检测"""
        text = "真正的强者从来不会失败。这注定会发生。"
        result = self.diagnoser.diagnose(text, claimed_layer="L3")
        
        violations = [v for v in result.violations 
                     if v['type'] == ViolationType.UNFALSIFIABLE.value]
        self.assertGreater(len(violations), 0)
    
    def test_concept_spinning(self):
        """测试概念空转检测"""
        text = "意义的本质在于存在的价值，真理的意义是永恒的。" * 5
        result = self.diagnoser.diagnose(text, claimed_layer="L3")
        
        violations = [v for v in result.violations 
                     if v['type'] == ViolationType.CONCEPT_SPINNING.value]
        self.assertGreater(len(violations), 0)
    
    def test_score_calculation(self):
        """测试分数计算"""
        # 清洁文本应得高分
        clean = self.diagnoser.diagnose("基于数据的分析。", "L3")
        self.assertGreater(clean.overall_score, 0.9)
        
        # 严重违规应得低分
        bad = self.diagnoser.diagnose("规范场公理证明了一切。", "L1")
        self.assertLess(bad.overall_score, 0.5)
    
    def test_full_analysis_text(self):
        """测试完整分析文本（现代战争案例）"""
        text = """
        现代战争的"全员胜利"，本质上是各方在认知维度上集体作弊的结果。
        
        1. 规范场维稳公理：认输 = 拓扑相变的"奇点爆破"
        在MSS体系中，每一个现代国家都是一个"意义规范场"。
        
        2. 旋耗散闭环公理：赢，是维持系统运转的唯一"意义燃料"
        K3系统不断地注入高势能的"正向意义量子"。
        
        3. 热税最小化公理：用"认知热税"逃避"物理热税"
        在物理层，你丢了100架战机是无法掩盖的。
        
        4. 拓扑投影畸变公理：茧房壁垒造就的"全能自恋"幻象
        就像缸中之脑，永远会觉得自己在天堂。
        
        真正强大的意义系统，从来不需要天天喊自己胜利。
        """
        
        result = self.diagnoser.diagnose(text, claimed_layer="L2")
        
        # 应检测到多个违规
        self.assertGreater(len(result.violations), 3)
        # 实际层级应为L3
        self.assertEqual(result.actual_layer, "L3")
        # 分数应较低
        self.assertLess(result.overall_score, 0.6)
        # 置信度应为HIGH（文本足够长）
        self.assertEqual(result.confidence, "HIGH")
    
    def test_report_generation(self):
        """测试报告生成"""
        text = "规范场公理证明了一切。"
        result = self.diagnoser.diagnose(text, claimed_layer="L1")
        report = self.diagnoser.generate_report(result)
        
        self.assertIn("MSS 内容诊断报告", report)
        self.assertIn("合规分数", report)
        self.assertIn("违规", report)


if __name__ == '__main__':
    unittest.main(verbosity=2)
