"""
Test suite for Virtual Data Generator
虚拟数据生成器测试套件
"""

import unittest
import json
import os
from virtual_data_generator import (
    VirtualDataGenerator, IndustryTemplate,
    generate_tech_startup, generate_declining_series
)


class TestVirtualDataGenerator(unittest.TestCase):
    """测试虚拟数据生成器"""
    
    def setUp(self):
        self.gen = VirtualDataGenerator(seed=42)
    
    def test_generate_organization_basic(self):
        """测试基本组织生成"""
        org = self.gen.generate_organization(IndustryTemplate.TECH_STARTUP)
        
        self.assertIn("org_name", org)
        self.assertIn("departments", org)
        self.assertGreater(org["headcount"], 0)
        self.assertGreater(len(org["departments"]), 0)
    
    def test_generate_organization_stress_levels(self):
        """测试不同压力水平"""
        org_low = self.gen.generate_organization(IndustryTemplate.TECH_STARTUP, stress_level=0.1)
        org_high = self.gen.generate_organization(IndustryTemplate.TECH_STARTUP, stress_level=0.9)
        
        # 高压力应该有更多审批层级和会议
        low_approval = sum(d["approval_layers"] for d in org_low["departments"]) / len(org_low["departments"])
        high_approval = sum(d["approval_layers"] for d in org_high["departments"]) / len(org_high["departments"])
        
        self.assertGreater(high_approval, low_approval)
    
    def test_generate_organization_anomaly(self):
        """测试异常场景"""
        org_normal = self.gen.generate_organization(IndustryTemplate.TECH_STARTUP, stress_level=0.5)
        org_anomaly = self.gen.generate_organization(
            IndustryTemplate.TECH_STARTUP,
            stress_level=0.5,
            anomaly_type="bureaucratic_explosion"
        )
        
        normal_approval = sum(d["approval_layers"] for d in org_normal["departments"])
        anomaly_approval = sum(d["approval_layers"] for d in org_anomaly["departments"])
        
        self.assertGreater(anomaly_approval, normal_approval)
    
    def test_generate_historical_series(self):
        """测试历史趋势生成"""
        series = self.gen.generate_historical_series(
            IndustryTemplate.TECH_STARTUP,
            org_name="测试公司",
            months=6,
            trend="declining",
            start_stress=0.1,
            end_stress=0.7
        )
        
        self.assertEqual(len(series), 6)
        
        # 检查趋势
        stresses = [org["stress_level"] for org in series]
        self.assertGreater(stresses[-1], stresses[0])
    
    def test_generate_benchmark_dataset(self):
        """测试基准数据集生成"""
        dataset = self.gen.generate_benchmark_dataset(
            industries=[IndustryTemplate.TECH_STARTUP, IndustryTemplate.FINANCE],
            samples_per_industry=2
        )
        
        self.assertIn("tech_startup", dataset)
        self.assertIn("finance", dataset)
        self.assertEqual(len(dataset["tech_startup"]), 6)  # 2 samples × 3 stress levels
    
    def test_department_generation(self):
        """测试部门生成"""
        org = self.gen.generate_organization(IndustryTemplate.TECH_STARTUP)
        
        for dept in org["departments"]:
            self.assertIn("dept_id", dept)
            self.assertIn("dept_name", dept)
            self.assertIn("dept_type", dept)
            self.assertIn("headcount", dept)
            self.assertGreater(dept["headcount"], 0)
            self.assertIn("employee_satisfaction", dept)
            self.assertGreaterEqual(dept["employee_satisfaction"], 1)
            self.assertLessEqual(dept["employee_satisfaction"], 10)
    
    def test_industry_profiles(self):
        """测试所有行业模板"""
        for industry in IndustryTemplate:
            org = self.gen.generate_organization(industry)
            self.assertEqual(org["industry"], industry.value)
            self.assertGreater(len(org["departments"]), 0)
    
    def test_export_dataset(self):
        """测试数据集导出"""
        dataset = {"test": [{"key": "value"}]}
        filepath = "test_export.json"
        
        self.gen.export_dataset(dataset, filepath)
        
        self.assertTrue(os.path.exists(filepath))
        
        with open(filepath, 'r', encoding='utf-8') as f:
            loaded = json.load(f)
        
        self.assertEqual(loaded, dataset)
        
        # 清理
        os.remove(filepath)


class TestConvenienceFunctions(unittest.TestCase):
    """测试便捷函数"""
    
    def test_generate_tech_startup(self):
        """测试生成科技初创"""
        org = generate_tech_startup(stress=0.3)
        
        self.assertEqual(org["industry"], "tech_startup")
        self.assertEqual(org["stress_level"], 0.3)
    
    def test_generate_declining_series(self):
        """测试生成衰退系列"""
        series = generate_declining_series()
        
        self.assertEqual(len(series), 12)
        self.assertEqual(series[0]["industry"], "tech_enterprise")


if __name__ == "__main__":
    unittest.main()
