"""
Test v3 engine integration into MSSTactic
"""

import unittest
from mss_tactic_integrated import MSSTactic

class TestV3Integration(unittest.TestCase):
    """测试v3引擎集成"""

    def setUp(self):
        self.tactic = MSSTactic(check_gpu=False)

    def test_symbolic_reasoning(self):
        """测试符号推理"""
        result = self.tactic.symbolic_reason("A1", "T1")
        self.assertEqual(result["result"], "PROVEN")
        self.assertEqual(result["certainty"], 1.0)

    def test_heat_tax_monitor(self):
        """测试热税监测"""
        result = self.tactic.monitor_heat_tax(O_d=0.7, phi=80.0)
        self.assertIn("status", result)
        self.assertIn("alerts", result)
        self.assertIn("recommendations", result)

    def test_axiom_system(self):
        """测试公理体系"""
        result = self.tactic.get_axiom_system()
        self.assertIn("axioms", result)
        self.assertIn("theorems", result)
        self.assertEqual(len(result["axioms"]), 3)
        self.assertEqual(len(result["theorems"]), 3)

    def test_knowledge_graph_integrity(self):
        """测试知识图谱完整性"""
        result = self.tactic.check_knowledge_graph_integrity()
        self.assertIn("integrity_score", result)
        self.assertIn("status", result)
        self.assertGreaterEqual(result["integrity_score"], 0.0)
        self.assertLessEqual(result["integrity_score"], 1.0)

    def test_organizational_resilience(self):
        """测试组织韧性扫描"""
        result = self.tactic.scan_organization()
        self.assertIn("global_metrics", result)
        self.assertIn("resilience_grade", result["global_metrics"])
        self.assertIn("resilience_score", result["global_metrics"])
        self.assertIn("departments", result)
        self.assertIn("diagnosis", result)
        self.assertIn("recommendations", result)

    def test_resilience_scan_with_custom_data(self):
        """测试自定义组织数据扫描"""
        org_data = {
            "org_name": "测试公司",
            "departments": [
                {
                    "dept_id": "D001",
                    "dept_name": "研发",
                    "dept_type": "RND",
                    "headcount": 30,
                    "approval_layers": 2,
                    "meeting_hours_weekly": 8.0,
                    "project_lead_time": 30.0,
                    "employee_satisfaction": 8.0
                }
            ]
        }

        result = self.tactic.scan_organization(org_data)
        self.assertEqual(result["org_name"], "测试公司")
        self.assertEqual(len(result["departments"]), 1)

    def test_multi_step_derivation(self):
        """测试多步推导 A1 -> T3"""
        result = self.tactic.symbolic_reason("A1", "T3")
        self.assertEqual(result["result"], "PROVEN")
        self.assertGreater(result["steps"], 0)

    def test_heat_tax_with_external_input(self):
        """测试带外部输入的热税更新"""
        result = self.tactic.monitor_heat_tax(O_d=0.5, phi=100.0, external_input=50.0)
        self.assertIn("status", result)
        self.assertIn("phi", result)

    def test_kg_integrity_with_cycles(self):
        """测试知识图谱完整性（含循环检测）"""
        result = self.tactic.check_knowledge_graph_integrity()
        self.assertIn("cycles_detected", result)
        self.assertIn("contradictions_detected", result)
        self.assertIn("isolated_nodes", result)

if __name__ == "__main__":
    unittest.main(verbosity=2)
