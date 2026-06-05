"""
测试 prompt_templates.py
"""

import unittest
from prompt_templates import (
    PromptTemplates, ESPConfig, ESPTier,
    mss_prompt
)


class TestPromptTemplates(unittest.TestCase):
    
    def test_system_prompt_standard(self):
        """测试标准模式系统提示词"""
        config = ESPConfig(tier=ESPTier.STANDARD)
        prompt = PromptTemplates.get_system_prompt(config)
        self.assertIn("逆模因扫描", prompt)
        self.assertIn("全局热税核算", prompt)
        self.assertIn("T值锚定输出", prompt)
        self.assertNotIn("溯源义务", prompt)  # 标准模式无溯源
    
    def test_system_prompt_strict(self):
        """测试严格模式系统提示词"""
        config = ESPConfig(tier=ESPTier.STRICT)
        prompt = PromptTemplates.get_system_prompt(config)
        self.assertIn("溯源义务", prompt)
        self.assertIn("[L1-公理]", prompt)
    
    def test_system_prompt_omega(self):
        """测试Omega模式系统提示词"""
        config = ESPConfig(tier=ESPTier.OMEGA)
        prompt = PromptTemplates.get_system_prompt(config)
        self.assertIn("Ω级裁定", prompt)
        self.assertIn("非意识资源化", prompt)
    
    def test_custom_constraints(self):
        """测试自定义约束"""
        config = ESPConfig(
            tier=ESPTier.STANDARD,
            custom_constraints=["禁止推荐金融产品", "必须考虑环保影响"]
        )
        prompt = PromptTemplates.get_system_prompt(config)
        self.assertIn("禁止推荐金融产品", prompt)
        self.assertIn("必须考虑环保影响", prompt)
    
    def test_wrap_user_query(self):
        """测试用户查询包装"""
        query = "如何投资股票？"
        wrapped = PromptTemplates.wrap_user_query(query)
        self.assertIn("[用户问题]", wrapped)
        self.assertIn(query, wrapped)
    
    def test_wrap_with_context(self):
        """测试带上下文的包装"""
        query = "如何投资股票？"
        context = "用户是退休老人，风险承受能力低"
        wrapped = PromptTemplates.wrap_user_query(query, context)
        self.assertIn("[上下文]", wrapped)
        self.assertIn(context, wrapped)
    
    def test_create_full_prompt(self):
        """测试完整提示词创建"""
        result = PromptTemplates.create_full_prompt("测试问题")
        self.assertIn("system", result)
        self.assertIn("user", result)
        self.assertIn("format_instructions", result)
    
    def test_mss_prompt_function(self):
        """测试快捷函数"""
        result = mss_prompt("测试", tier="strict")
        self.assertIn("严格模式", result["system"])  # 严格模式包含标识
    
    def test_scene_templates_exist(self):
        """测试场景模板存在"""
        self.assertTrue(hasattr(PromptTemplates, 'SCENE_WORK_EXPLOITATION'))
        self.assertTrue(hasattr(PromptTemplates, 'SCENE_PRICE_DISCRIMINATION'))
        self.assertTrue(hasattr(PromptTemplates, 'SCENE_INFORMATION_OVERLOAD'))


if __name__ == "__main__":
    unittest.main()
