"""
Test suite for Organizational Resilience Scanner
"""

import unittest
import os
import json
from organizational_resilience import (
    OrganizationalResilienceScanner,
    DepartmentMetrics, OrganizationSnapshot,
    DepartmentType,
    create_demo_organization
)

class TestDepartmentMetrics(unittest.TestCase):
    """测试部门指标计算"""

    def setUp(self):
        self.scanner = OrganizationalResilienceScanner()

    def test_compute_rnd_department(self):
        """测试研发部门计算"""
        dept_data = {
            "dept_id": "D001",
            "dept_name": "研发中心",
            "dept_type": "RND",
            "headcount": 45,
            "approval_layers": 2,
            "meeting_hours_weekly": 8.0,
            "project_lead_time": 35.0,
            "employee_satisfaction": 8.2
        }

        metrics = self.scanner.compute_department_metrics(dept_data)

        self.assertEqual(metrics.dept_id, "D001")
        self.assertEqual(metrics.dept_type, DepartmentType.RND)
        self.assertGreater(metrics.O_d, 0.0)
        self.assertLess(metrics.O_d, 1.0)
        self.assertGreater(metrics.phi, 0.0)
        self.assertGreater(metrics.innovation_rate, 0.0)

    def test_compute_admin_department(self):
        """测试行政部门计算（低意义密度）"""
        dept_data = {
            "dept_id": "D004",
            "dept_name": "行政支撑",
            "dept_type": "ADMIN",
            "headcount": 15,
            "approval_layers": 5,
            "meeting_hours_weekly": 6.0,
            "project_lead_time": 7.0,
            "employee_satisfaction": 6.5
        }

        metrics = self.scanner.compute_department_metrics(dept_data)

        # 行政部门应该有更高的O_d（更多审批层）
        self.assertGreater(metrics.O_d, 0.3)
        # 但phi应该较低（低意义密度权重）
        self.assertLess(metrics.phi, 150.0)

    def test_approval_layers_impact(self):
        """测试审批层级对O_d的影响"""
        dept_low = {
            "dept_id": "D001",
            "dept_name": "低审批",
            "dept_type": "RND",
            "headcount": 10,
            "approval_layers": 1,
            "meeting_hours_weekly": 2.0,
            "project_lead_time": 20.0,
            "employee_satisfaction": 8.0
        }

        dept_high = dept_low.copy()
        dept_high["dept_id"] = "D002"
        dept_high["dept_name"] = "高审批"
        dept_high["approval_layers"] = 5

        metrics_low = self.scanner.compute_department_metrics(dept_low)
        metrics_high = self.scanner.compute_department_metrics(dept_high)

        self.assertLess(metrics_low.O_d, metrics_high.O_d)

    def test_satisfaction_impact(self):
        """测试满意度对phi的影响"""
        dept_low = {
            "dept_id": "D001",
            "dept_name": "低满意",
            "dept_type": "RND",
            "headcount": 10,
            "approval_layers": 2,
            "meeting_hours_weekly": 5.0,
            "project_lead_time": 30.0,
            "employee_satisfaction": 3.0
        }

        dept_high = dept_low.copy()
        dept_high["dept_id"] = "D002"
        dept_high["dept_name"] = "高满意"
        dept_high["employee_satisfaction"] = 9.0

        metrics_low = self.scanner.compute_department_metrics(dept_low)
        metrics_high = self.scanner.compute_department_metrics(dept_high)

        self.assertLess(metrics_low.phi, metrics_high.phi)

class TestOrganizationScan(unittest.TestCase):
    """测试组织扫描"""

    def setUp(self):
        self.scanner = OrganizationalResilienceScanner()
        self.org_data = create_demo_organization()

    def test_scan_organization(self):
        """测试完整组织扫描"""
        snapshot = self.scanner.scan_organization(self.org_data)

        self.assertIsNotNone(snapshot.snapshot_id)
        self.assertIsNotNone(snapshot.timestamp)
        self.assertEqual(len(snapshot.departments), 5)

        # 全局指标应该在合理范围内
        self.assertGreaterEqual(snapshot.global_O_d, 0.0)
        self.assertLessEqual(snapshot.global_O_d, 1.0)
        self.assertGreater(snapshot.global_phi, 0.0)

        # 韧性指数应该在0-1之间
        self.assertGreaterEqual(snapshot.resilience_score, 0.0)
        self.assertLessEqual(snapshot.resilience_score, 1.0)

        # 应该有诊断结果
        self.assertIsInstance(snapshot.diagnosis, list)
        self.assertIsInstance(snapshot.recommendations, list)

    def test_resilience_grade(self):
        """测试韧性等级"""
        snapshot = self.scanner.scan_organization(self.org_data)

        self.assertIn(snapshot.resilience_grade, ["A", "B", "C", "D"])

        # 等级与分数应该一致
        if snapshot.resilience_score >= 0.8:
            self.assertEqual(snapshot.resilience_grade, "A")
        elif snapshot.resilience_score >= 0.5:
            self.assertEqual(snapshot.resilience_grade, "B")
        elif snapshot.resilience_score >= 0.3:
            self.assertEqual(snapshot.resilience_grade, "C")
        else:
            self.assertEqual(snapshot.resilience_grade, "D")

    def test_department_weights(self):
        """测试部门权重影响"""
        snapshot = self.scanner.scan_organization(self.org_data)

        # 研发部门权重最高，应该对全局指标有较大影响
        rnd = snapshot.departments.get("D001")
        admin = snapshot.departments.get("D004")

        if rnd and admin:
            # 研发应该有更高的phi（意义密度权重）
            self.assertGreater(rnd.phi, admin.phi)

    def test_history_tracking(self):
        """测试历史记录"""
        self.assertEqual(len(self.scanner.history), 0)

        snapshot1 = self.scanner.scan_organization(self.org_data)
        self.assertEqual(len(self.scanner.history), 1)

        snapshot2 = self.scanner.scan_organization(self.org_data)
        self.assertEqual(len(self.scanner.history), 2)

class TestDiagnosis(unittest.TestCase):
    """测试诊断功能"""

    def setUp(self):
        self.scanner = OrganizationalResilienceScanner()

    def test_high_od_diagnosis(self):
        """测试高O_d诊断"""
        org_data = {
            "org_name": "高规范场组织",
            "departments": [
                {
                    "dept_id": "D001",
                    "dept_name": "行政部",
                    "dept_type": "ADMIN",
                    "headcount": 100,
                    "approval_layers": 10,
                    "meeting_hours_weekly": 40.0,
                    "project_lead_time": 90.0,
                    "employee_satisfaction": 3.0
                }
            ]
        }

        snapshot = self.scanner.scan_organization(org_data)

        # 应该有CRITICAL级别诊断
        critical_diags = [d for d in snapshot.diagnosis if d["level"] == "CRITICAL"]
        self.assertTrue(len(critical_diags) > 0)

    def test_healthy_organization(self):
        """测试健康组织"""
        org_data = {
            "org_name": "健康组织",
            "departments": [
                {
                    "dept_id": "D001",
                    "dept_name": "研发",
                    "dept_type": "RND",
                    "headcount": 50,
                    "approval_layers": 1,
                    "meeting_hours_weekly": 3.0,
                    "project_lead_time": 21.0,
                    "employee_satisfaction": 9.0
                }
            ]
        }

        snapshot = self.scanner.scan_organization(org_data)

        # 应该有较少的诊断
        self.assertLess(len(snapshot.diagnosis), 3)

        # 韧性等级应该至少为C（单部门测试受限于创新率阈值）
        self.assertIn(snapshot.resilience_grade, ["A", "B", "C"])

class TestRecommendations(unittest.TestCase):
    """测试建议生成"""

    def setUp(self):
        self.scanner = OrganizationalResilienceScanner()

    def test_critical_recommendations(self):
        """测试危急状态建议"""
        org_data = {
            "org_name": "危急组织",
            "departments": [
                {
                    "dept_id": "D001",
                    "dept_name": "行政",
                    "dept_type": "ADMIN",
                    "headcount": 200,
                    "approval_layers": 15,
                    "meeting_hours_weekly": 60.0,
                    "project_lead_time": 180.0,
                    "employee_satisfaction": 2.0
                }
            ]
        }

        snapshot = self.scanner.scan_organization(org_data)

        # 应该有紧急建议
        emergency_recs = [r for r in snapshot.recommendations if "紧急" in r or "生死线" in r]
        self.assertTrue(len(emergency_recs) > 0)

    def test_healthy_recommendations(self):
        """测试健康组织建议"""
        org_data = {
            "org_name": "健康组织",
            "departments": [
                {
                    "dept_id": "D001",
                    "dept_name": "研发",
                    "dept_type": "RND",
                    "headcount": 30,
                    "approval_layers": 1,
                    "meeting_hours_weekly": 2.0,
                    "project_lead_time": 14.0,
                    "employee_satisfaction": 9.5
                }
            ]
        }

        snapshot = self.scanner.scan_organization(org_data)

        # 健康组织应该有建议（即使是健康的也需要保持）
        self.assertTrue(len(snapshot.recommendations) > 0)

class TestExport(unittest.TestCase):
    """测试报告导出"""

    def setUp(self):
        self.scanner = OrganizationalResilienceScanner()
        self.org_data = create_demo_organization()

    def test_export_report(self):
        """测试报告导出"""
        snapshot = self.scanner.scan_organization(self.org_data)
        test_file = "test_resilience_report.json"

        filepath = self.scanner.export_report(snapshot, test_file)

        self.assertTrue(os.path.exists(test_file))

        with open(test_file, 'r', encoding='utf-8') as f:
            data = json.load(f)

        self.assertIn("snapshot_id", data)
        self.assertIn("global_metrics", data)
        self.assertIn("departments", data)
        self.assertIn("diagnosis", data)
        self.assertIn("recommendations", data)
        self.assertIn("mss_framework", data)

        # 清理
        os.remove(test_file)

class TestComparison(unittest.TestCase):
    """测试快照对比"""

    def setUp(self):
        self.scanner = OrganizationalResilienceScanner()
        self.org_data = create_demo_organization()

    def test_compare_snapshots(self):
        """测试快照对比"""
        snapshot1 = self.scanner.scan_organization(self.org_data)

        # 修改组织数据（模拟改善）
        improved_org = self.org_data.copy()
        improved_org["departments"] = [
            {
                **dept,
                "approval_layers": max(1, dept.get("approval_layers", 3) - 1),
                "employee_satisfaction": min(10.0, dept.get("employee_satisfaction", 5.0) + 1.0)
            }
            for dept in self.org_data["departments"]
        ]

        snapshot2 = self.scanner.scan_organization(improved_org)

        comparison = self.scanner.compare_snapshots(
            snapshot1.snapshot_id,
            snapshot2.snapshot_id
        )

        self.assertIn("time_delta", comparison)
        self.assertIn("O_d_change", comparison)
        self.assertIn("phi_change", comparison)
        self.assertIn("resilience_change", comparison)
        self.assertIn("trend", comparison)

if __name__ == "__main__":
    unittest.main(verbosity=2)
