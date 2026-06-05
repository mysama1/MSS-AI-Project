"""
Tests for Resilience Visualizer
"""

import unittest
import os
import json
from organizational_resilience import OrganizationalResilienceScanner, create_demo_organization
from resilience_visualizer import ResilienceVisualizer, VisualConfig

class TestResilienceVisualizer(unittest.TestCase):

    def setUp(self):
        self.scanner = OrganizationalResilienceScanner()
        self.visualizer = ResilienceVisualizer()
        self.org_data = create_demo_organization()
        self.snapshot = self.scanner.scan_organization(self.org_data)

    def test_visual_config_defaults(self):
        """测试可视化配置默认值"""
        config = VisualConfig()
        self.assertIn('L1', config.colors)
        self.assertIn('critical', config.colors)
        self.assertEqual(config.dpi, 150)

    def test_markdown_report_generation(self):
        """测试Markdown报告生成"""
        report = self.visualizer.generate_markdown_report(self.snapshot)

        # 验证报告包含关键部分
        self.assertIn("组织韧性扫描报告", report)
        self.assertIn(self.snapshot.snapshot_id, report)
        self.assertIn(f"{self.snapshot.resilience_score:.4f}", report)
        self.assertIn(self.snapshot.resilience_grade, report)

        # 验证包含所有部门
        for dept_id, metrics in self.snapshot.departments.items():
            self.assertIn(metrics.dept_name, report)

        # 验证包含诊断和建议
        self.assertIn("诊断结果", report)
        self.assertIn("改进建议", report)

    def test_markdown_report_export(self):
        """测试Markdown报告导出到文件"""
        test_path = "test_report.md"
        result = self.visualizer.generate_markdown_report(self.snapshot, test_path)

        self.assertEqual(result, test_path)
        self.assertTrue(os.path.exists(test_path))

        # 验证文件内容
        with open(test_path, 'r', encoding='utf-8') as f:
            content = f.read()
            self.assertIn("组织韧性扫描报告", content)

        # 清理
        os.remove(test_path)

    def test_text_radar_generation(self):
        """测试文本版雷达图"""
        text = self.visualizer._generate_text_radar(self.snapshot)

        self.assertIn("组织韧性雷达图", text)
        self.assertIn(str(self.snapshot.resilience_grade), text)
        self.assertIn(f"{self.snapshot.global_O_d:.4f}", text)
        self.assertIn(f"{self.snapshot.global_phi:.2f}", text)

    def test_text_heatmap_generation(self):
        """测试文本版热力图"""
        text = self.visualizer._generate_text_heatmap(self.snapshot)

        self.assertIn("部门指标热力图", text)

        # 验证包含所有部门
        for dept_id, metrics in self.snapshot.departments.items():
            self.assertIn(metrics.dept_name, text)

    def test_full_report_package(self):
        """测试完整报告包生成"""
        output_dir = "test_reports"
        files = self.visualizer.generate_full_report_package(self.snapshot, output_dir)

        # 验证生成了关键文件
        self.assertIn('markdown', files)
        self.assertIn('json', files)
        self.assertTrue(os.path.exists(files['markdown']))
        self.assertTrue(os.path.exists(files['json']))

        # 验证JSON数据完整性
        with open(files['json'], 'r', encoding='utf-8') as f:
            data = json.load(f)
            self.assertIn('global_metrics', data)
            self.assertIn('departments', data)
            self.assertIn('diagnosis', data)
            self.assertIn('recommendations', data)

        # 清理
        import shutil
        if os.path.exists(output_dir):
            shutil.rmtree(output_dir)

    def test_grade_color_mapping(self):
        """测试等级颜色映射"""
        self.assertEqual(
            self.visualizer._get_grade_color('A'),
            self.visualizer.config.colors['good']
        )
        self.assertEqual(
            self.visualizer._get_grade_color('D'),
            self.visualizer.config.colors['critical']
        )

    def test_snapshot_with_no_diagnosis(self):
        """测试无诊断情况的报告"""
        # 创建一个理想状态的组织（应该无诊断）
        ideal_org = {
            "org_name": "理想组织",
            "departments": [
                {
                    "dept_id": "D001",
                    "dept_name": "理想部门",
                    "dept_type": "RND",
                    "headcount": 20,
                    "approval_layers": 1,
                    "meeting_hours_weekly": 2.0,
                    "project_lead_time": 20.0,
                    "employee_satisfaction": 9.5
                }
            ]
        }

        snapshot = self.scanner.scan_organization(ideal_org)
        report = self.visualizer.generate_markdown_report(snapshot)

        # 理想组织应该没有严重诊断
        self.assertIn("组织韧性扫描报告", report)

class TestResilienceVisualizerEdgeCases(unittest.TestCase):

    def setUp(self):
        self.scanner = OrganizationalResilienceScanner()
        self.visualizer = ResilienceVisualizer()

    def test_empty_organization(self):
        """测试空组织"""
        empty_org = {"org_name": "空组织", "departments": []}
        snapshot = self.scanner.scan_organization(empty_org)

        # 应该能生成报告而不崩溃
        report = self.visualizer.generate_markdown_report(snapshot)
        self.assertIn("组织韧性扫描报告", report)

    def test_single_department(self):
        """测试单部门组织"""
        single_org = {
            "org_name": "单部门",
            "departments": [
                {
                    "dept_id": "D001",
                    "dept_name": "唯一部门",
                    "dept_type": "RND",
                    "headcount": 10,
                    "approval_layers": 2,
                    "meeting_hours_weekly": 5.0,
                    "project_lead_time": 30.0,
                    "employee_satisfaction": 7.0
                }
            ]
        }

        snapshot = self.scanner.scan_organization(single_org)
        files = self.visualizer.generate_full_report_package(snapshot, "test_single")

        self.assertIn('markdown', files)

        # 清理
        import shutil
        if os.path.exists("test_single"):
            shutil.rmtree("test_single")

if __name__ == "__main__":
    unittest.main(verbosity=2)
