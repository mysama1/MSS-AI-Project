"""
MSS记忆层单元测试
"""

import unittest
from datetime import datetime
from mss_memory_layer import (
    MSSMemoryLayer, MSSAnalysisResult, UserMSSProfile,
    create_memory_layer, MEM0_AVAILABLE
)

class TestMSSMemoryLayer(unittest.TestCase):
    
    def setUp(self):
        """测试前准备"""
        self.memory = create_memory_layer()
        self.test_user = "test_user_001"
    
    def test_initialization(self):
        """测试初始化"""
        self.assertIsNotNone(self.memory)
        self.assertIn(self.memory.backend, ["mem0", "memory"])
        print(f"后端类型：{self.memory.backend}")
    
    def test_store_analysis(self):
        """测试存储分析结果"""
        result = MSSAnalysisResult(
            user_id=self.test_user,
            timestamp=datetime.now().isoformat(),
            system_dimension=25.0,
            logic_entropy=80.0,
            heat_tax=0.35,
            meaning_flux=6.0,
            total_information=500.0,
            organization_degree=0.6,
            resilience_index=0.4,
            analysis_type="organization",
            raw_data={"departments": 5}
        )
        
        success = self.memory.store_analysis(result)
        self.assertTrue(success)
    
    def test_store_concept(self):
        """测试存储概念"""
        success = self.memory.store_concept(
            self.test_user,
            "逻辑熵增",
            "axiom",
            ["热税", "意义通量"]
        )
        self.assertTrue(success)
    
    def test_store_interaction(self):
        """测试存储交互"""
        success = self.memory.store_interaction(
            self.test_user,
            "测试查询",
            "测试回答",
            "test"
        )
        self.assertTrue(success)
    
    def test_retrieve_analysis_history(self):
        """测试检索分析历史"""
        # 先存储一些数据
        for i in range(3):
            result = MSSAnalysisResult(
                user_id=self.test_user,
                timestamp=datetime.now().isoformat(),
                system_dimension=20.0 + i,
                logic_entropy=70.0 + i,
                heat_tax=0.3 + i * 0.05,
                meaning_flux=5.0 + i,
                total_information=400.0 + i * 50,
                organization_degree=0.5 + i * 0.05,
                resilience_index=0.3 + i * 0.05,
                analysis_type="organization",
                raw_data={}
            )
            self.memory.store_analysis(result)
        
        # 检索
        history = self.memory.retrieve_analysis_history(self.test_user)
        self.assertGreaterEqual(len(history), 3)
    
    def test_retrieve_concepts(self):
        """测试检索概念"""
        # 存储概念
        self.memory.store_concept(self.test_user, "概念A", "axiom")
        self.memory.store_concept(self.test_user, "概念B", "definition")
        self.memory.store_concept(self.test_user, "概念C", "theorem")
        
        # 检索所有概念
        concepts = self.memory.retrieve_concepts(self.test_user)
        self.assertGreaterEqual(len(concepts), 3)
        
        # 按类型过滤
        axioms = self.memory.retrieve_concepts(self.test_user, "axiom")
        self.assertGreaterEqual(len(axioms), 1)
    
    def test_retrieve_relevant_context(self):
        """测试检索相关上下文"""
        # 存储交互
        self.memory.store_interaction(
            self.test_user,
            "热税系数是多少？",
            "您的热税系数是0.35",
            "consultation"
        )
        
        # 检索
        context = self.memory.retrieve_relevant_context(
            self.test_user, "热税", limit=5
        )
        self.assertIsInstance(context, str)
        self.assertGreater(len(context), 0)
    
    def test_get_user_profile(self):
        """测试获取用户画像"""
        # 存储多条分析
        for i in range(5):
            result = MSSAnalysisResult(
                user_id=self.test_user,
                timestamp=datetime.now().isoformat(),
                system_dimension=20.0 + i * 2,
                logic_entropy=70.0 + i * 5,
                heat_tax=0.3 + i * 0.02,
                meaning_flux=5.0 + i * 0.5,
                total_information=400.0 + i * 50,
                organization_degree=0.5 + i * 0.02,
                resilience_index=0.3 + i * 0.02,
                analysis_type="organization",
                raw_data={}
            )
            self.memory.store_analysis(result)
        
        # 获取画像
        profile = self.memory.get_user_profile(self.test_user)
        self.assertIsNotNone(profile)
        self.assertEqual(profile.user_id, self.test_user)
        self.assertEqual(profile.total_analyses, 5)
        self.assertIn(profile.trend, ["improving", "stable", "declining"])
    
    def test_heat_tax_categorization(self):
        """测试热税分类"""
        self.assertEqual(self.memory._categorize_heat_tax(0.1), "low")
        self.assertEqual(self.memory._categorize_heat_tax(0.3), "medium")
        self.assertEqual(self.memory._categorize_heat_tax(0.6), "high")
        self.assertEqual(self.memory._categorize_heat_tax(0.9), "critical")
    
    def test_dimension_categorization(self):
        """测试维度分类"""
        self.assertEqual(self.memory._categorize_dimension(5), "small")
        self.assertEqual(self.memory._categorize_dimension(20), "medium")
        self.assertEqual(self.memory._categorize_dimension(100), "large")
        self.assertEqual(self.memory._categorize_dimension(300), "enterprise")

class TestMSSAnalysisResult(unittest.TestCase):
    
    def test_to_dict(self):
        """测试转换为字典"""
        result = MSSAnalysisResult(
            user_id="user1",
            timestamp="2024-01-01",
            system_dimension=10.0,
            logic_entropy=50.0,
            heat_tax=0.2,
            meaning_flux=8.0,
            total_information=200.0,
            organization_degree=0.7,
            resilience_index=0.5,
            analysis_type="test",
            raw_data={}
        )
        
        d = result.to_dict()
        self.assertEqual(d["user_id"], "user1")
        self.assertEqual(d["heat_tax"], 0.2)
    
    def test_from_dict(self):
        """测试从字典创建"""
        data = {
            "user_id": "user2",
            "timestamp": "2024-01-02",
            "system_dimension": 15.0,
            "logic_entropy": 60.0,
            "heat_tax": 0.25,
            "meaning_flux": 7.0,
            "total_information": 250.0,
            "organization_degree": 0.6,
            "resilience_index": 0.4,
            "analysis_type": "test2",
            "raw_data": {"key": "value"}
        }
        
        result = MSSAnalysisResult.from_dict(data)
        self.assertEqual(result.user_id, "user2")
        self.assertEqual(result.raw_data, {"key": "value"})

if __name__ == "__main__":
    print("=" * 60)
    print("MSS记忆层单元测试")
    print("=" * 60)
    print(f"mem0可用：{MEM0_AVAILABLE}")
    print("=" * 60)
    
    unittest.main(verbosity=2)
