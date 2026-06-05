"""
Test suite for Resilience Historical Tracker
组织韧性历史趋势追踪器测试
"""

import unittest
import os
import shutil
from datetime import datetime
from resilience_historical_tracker import (
    ResilienceHistory, TrendAnalysis, ResilienceTrackerManager,
    track_organization_scans
)
from organizational_resilience import (
    OrganizationalResilienceScanner, OrganizationSnapshot
)
from virtual_data_generator import VirtualDataGenerator, IndustryTemplate


class TestResilienceHistory(unittest.TestCase):
    """测试韧性历史记录"""
    
    def setUp(self):
        self.history = ResilienceHistory(org_id="TEST001", org_name="测试组织")
        
        # 创建模拟快照
        for i in range(5):
            snap = OrganizationSnapshot(
                snapshot_id=f"SNAP{i}",
                timestamp=datetime.now().isoformat()
            )
            snap.global_O_d = 0.3 + i * 0.1  # 递增
            snap.global_phi = 100 - i * 10   # 递减
            snap.global_gamma = 0.1 + i * 0.05
            snap.global_innovation_rate = 0.8 - i * 0.1
            snap.resilience_score = 0.7 - i * 0.15
            snap.resilience_grade = "B"
            
            self.history.add_snapshot(snap)
    
    def test_add_snapshot(self):
        """测试添加快照"""
        self.assertEqual(len(self.history.snapshots), 5)
    
    def test_get_metric_series(self):
        """测试获取指标序列"""
        series = self.history.get_metric_series("O_d")
        self.assertEqual(len(series), 5)
        
        # 检查排序
        values = [v for _, v in series]
        self.assertEqual(values, sorted(values))
    
    def test_analyze_trend_declining(self):
        """测试恶化趋势分析"""
        analysis = self.history.analyze_trend("resilience_score")
        
        self.assertEqual(analysis.metric_name, "resilience_score")
        self.assertEqual(analysis.trend_direction, "declining")
        self.assertLess(analysis.forecast_next, analysis.values[-1])
    
    def test_analyze_trend_improving(self):
        """测试改善趋势（O_d上升=恶化，所以方向是declining）"""
        analysis = self.history.analyze_trend("O_d")
        
        # O_d上升对组织是恶化
        self.assertEqual(analysis.trend_direction, "declining")
    
    def test_alert_levels(self):
        """测试预警级别"""
        # 创建一个危急状态（需要至少2个数据点才能分析趋势）
        history = ResilienceHistory(org_id="TEST002", org_name="危急组织")
        
        for i in range(3):
            snap = OrganizationSnapshot(
                snapshot_id=f"CRITICAL{i}",
                timestamp=datetime.now().isoformat()
            )
            snap.global_O_d = 0.8
            snap.global_phi = 30
            snap.global_gamma = 1.5
            snap.global_innovation_rate = 0.05
            snap.resilience_score = 0.1
            snap.resilience_grade = "D"
            history.add_snapshot(snap)
        
        analysis_od = history.analyze_trend("O_d")
        self.assertEqual(analysis_od.alert_level, "critical")
        
        analysis_phi = history.analyze_trend("phi")
        self.assertEqual(analysis_phi.alert_level, "critical")
        
        analysis_res = history.analyze_trend("resilience_score")
        self.assertEqual(analysis_res.alert_level, "critical")
    
    def test_generate_trend_report(self):
        """测试生成趋势报告"""
        report = self.history.generate_trend_report()
        
        self.assertIn("trends", report)
        self.assertIn("overall_assessment", report)
        self.assertIn("recommendations", report)
        self.assertGreater(len(report["recommendations"]), 0)


class TestResilienceTrackerManager(unittest.TestCase):
    """测试追踪管理器"""
    
    def setUp(self):
        self.test_dir = "test_resilience_history"
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)
        self.manager = ResilienceTrackerManager(storage_dir=self.test_dir)
    
    def tearDown(self):
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)
    
    def test_record_and_load(self):
        """测试记录和加载"""
        scanner = OrganizationalResilienceScanner()
        
        # 创建模拟组织数据
        org_data = {
            "org_name": "测试公司",
            "departments": [
                {
                    "dept_id": "D001",
                    "dept_name": "研发",
                    "dept_type": "RND",
                    "headcount": 20,
                    "approval_layers": 2,
                    "meeting_hours_weekly": 8,
                    "project_lead_time": 30,
                    "employee_satisfaction": 7.5
                }
            ]
        }
        
        snapshot = scanner.scan_organization(org_data)
        self.manager.record_scan("TEST003", "测试公司", snapshot)
        
        # 重新加载
        history = self.manager.get_or_create_history("TEST003", "测试公司")
        self.assertEqual(len(history.snapshots), 1)
    
    def test_list_organizations(self):
        """测试列出组织"""
        scanner = OrganizationalResilienceScanner()
        org_data = {"org_name": "A", "departments": []}
        
        snapshot = scanner.scan_organization(org_data)
        self.manager.record_scan("ORG1", "组织A", snapshot)
        self.manager.record_scan("ORG2", "组织B", snapshot)
        
        orgs = self.manager.list_organizations()
        self.assertEqual(len(orgs), 2)


class TestIntegration(unittest.TestCase):
    """集成测试"""
    
    def test_full_workflow(self):
        """测试完整工作流"""
        gen = VirtualDataGenerator(seed=42)
        
        # 生成6个月数据
        series = gen.generate_historical_series(
            IndustryTemplate.TECH_STARTUP,
            org_name="集成测试公司",
            months=6,
            trend="declining",
            start_stress=0.1,
            end_stress=0.6
        )
        
        # 追踪（使用唯一ID避免加载之前测试的数据）
        import tempfile
        test_dir = tempfile.mkdtemp(prefix="test_resilience_")
        
        # 手动追踪避免manager缓存问题
        from resilience_historical_tracker import ResilienceTrackerManager
        manager = ResilienceTrackerManager(storage_dir=test_dir)
        scanner = OrganizationalResilienceScanner()
        
        for org_data in series:
            snapshot = scanner.scan_organization(org_data)
            manager.record_scan("INT999", "集成测试", snapshot)
        
        history = manager.get_or_create_history("INT999", "集成测试")
        
        self.assertEqual(len(history.snapshots), 6)
        
        # 分析趋势
        analysis = history.analyze_trend("resilience_score")
        self.assertEqual(analysis.trend_direction, "declining")
        
        # 生成报告
        report = history.generate_trend_report()
        self.assertIn("trends", report)


if __name__ == "__main__":
    unittest.main()
