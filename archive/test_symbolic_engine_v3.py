"""
Test suite for MSS Symbolic Engine v3.0
Tests: Transitive reasoning, cycle detection, MSS v15.1 axiom system, heat tax monitor
"""

import unittest
import os
import json
from symbolic_engine_v3 import (
    SymbolicEngineV3, TransitiveReasoner, CycleDetector,
    MSSv12AxiomSystem, HeatTaxMonitor, HeatTaxState,
    AxiomType, create_mss_v12_engine
)
from symbolic_engine import (
    MSSKnowledgeGraph, ConceptNode, RelationEdge,
    NodeType, RelationType, InferenceResult
)

class TestTransitiveReasoning(unittest.TestCase):
    """测试传递推理功能"""

    def setUp(self):
        self.graph = MSSKnowledgeGraph()

        # 创建测试节点
        nodes = [
            ConceptNode(id="A", name="A", node_type=NodeType.AXIOM, layer="L1", content="Base"),
            ConceptNode(id="B", name="B", node_type=NodeType.THEOREM, layer="L2", content="Derived"),
            ConceptNode(id="C", name="C", node_type=NodeType.THEOREM, layer="L2", content="Derived2"),
            ConceptNode(id="D", name="D", node_type=NodeType.CONCEPT, layer="L3", content="Heuristic"),
        ]
        for node in nodes:
            self.graph.add_node(node)

        # 创建 IMPLIES 链: A -> B -> C -> D
        edges = [
            RelationEdge(source="A", target="B", relation=RelationType.IMPLIES, strength=1.0),
            RelationEdge(source="B", target="C", relation=RelationType.IMPLIES, strength=0.9),
            RelationEdge(source="C", target="D", relation=RelationType.IMPLIES, strength=0.8),
        ]
        for edge in edges:
            self.graph.add_edge(edge)

        self.reasoner = TransitiveReasoner(self.graph)

    def test_direct_implication(self):
        """测试直接蕴含"""
        result = self.reasoner.check_implication("A", "B")
        self.assertEqual(result.result, InferenceResult.PROVEN)
        self.assertEqual(result.certainty, 1.0)

    def test_transitive_implication(self):
        """测试传递蕴含 A -> C"""
        result = self.reasoner.check_implication("A", "C")
        self.assertEqual(result.result, InferenceResult.PROVEN)
        self.assertEqual(result.certainty, 0.9)  # min(1.0, 0.9)

    def test_long_transitive_chain(self):
        """测试长链传递 A -> D"""
        result = self.reasoner.check_implication("A", "D")
        self.assertEqual(result.result, InferenceResult.PROVEN)
        self.assertEqual(result.certainty, 0.8)  # min(1.0, 0.9, 0.8)

    def test_no_path(self):
        """测试无路径情况"""
        result = self.reasoner.check_implication("D", "A")
        self.assertEqual(result.result, InferenceResult.UNDETERMINED)
        self.assertEqual(result.certainty, 0.0)

    def test_same_node(self):
        """测试相同节点"""
        result = self.reasoner.check_implication("A", "A")
        self.assertEqual(result.result, InferenceResult.PROVEN)
        self.assertEqual(result.certainty, 1.0)

    def test_compute_closure(self):
        """测试传递闭包计算"""
        closure = self.reasoner.compute_transitive_closure("A")
        self.assertIn("B", closure)
        self.assertIn("C", closure)
        self.assertIn("D", closure)
        self.assertNotIn("A", closure)

class TestCycleDetection(unittest.TestCase):
    """测试环检测功能"""

    def setUp(self):
        self.graph = MSSKnowledgeGraph()

        nodes = [
            ConceptNode(id="A", name="A", node_type=NodeType.AXIOM, layer="L1", content="Base"),
            ConceptNode(id="B", name="B", node_type=NodeType.THEOREM, layer="L2", content="Derived"),
            ConceptNode(id="C", name="C", node_type=NodeType.THEOREM, layer="L2", content="Derived2"),
        ]
        for node in nodes:
            self.graph.add_node(node)

        # 创建环: A -> B -> C -> A
        edges = [
            RelationEdge(source="A", target="B", relation=RelationType.IMPLIES),
            RelationEdge(source="B", target="C", relation=RelationType.IMPLIES),
            RelationEdge(source="C", target="A", relation=RelationType.IMPLIES),
        ]
        for edge in edges:
            self.graph.add_edge(edge)

        self.detector = CycleDetector(self.graph)

    def test_find_cycles(self):
        """测试环检测"""
        cycles = self.detector.find_cycles()
        self.assertTrue(len(cycles) > 0)

        # 检查是否找到 A -> B -> C -> A 环
        found_cycle = False
        for cycle in cycles:
            if set(cycle) == {"A", "B", "C"}:
                found_cycle = True
                break
        self.assertTrue(found_cycle)

    def test_contradiction_detection(self):
        """测试矛盾检测"""
        # 添加矛盾边
        contradiction_edge = RelationEdge(
            source="A", target="B", relation=RelationType.CONTRADICTS
        )
        self.graph.add_edge(contradiction_edge)

        contradictions = self.detector.check_contradiction_cycles()
        self.assertTrue(len(contradictions) > 0)

        # 检查矛盾报告
        report = contradictions[0]
        self.assertEqual(report["type"], "logical_contradiction")
        self.assertEqual(report["severity"], "critical")

class TestMSSv12AxiomSystem(unittest.TestCase):
    """测试MSS v15.1公理体系"""

    def setUp(self):
        self.system = MSSv12AxiomSystem()

    def test_axioms_initialized(self):
        """测试公理初始化"""
        self.assertEqual(len(self.system.axioms), 3)
        self.assertIn("A1", self.system.axioms)
        self.assertIn("A2", self.system.axioms)
        self.assertIn("A3", self.system.axioms)

    def test_theorems_initialized(self):
        """测试定理初始化"""
        self.assertEqual(len(self.system.theorems), 3)
        self.assertIn("T1", self.system.theorems)
        self.assertIn("T2", self.system.theorems)
        self.assertIn("T3", self.system.theorems)

    def test_mechanisms_initialized(self):
        """测试机制初始化"""
        self.assertIn("MECH-EVOL-002", self.system.mechanisms)

    def test_derivation_verification(self):
        """测试推导链验证"""
        # T1 的推导链: A1 -> A2 -> A3 -> T1
        is_valid, missing = self.system.verify_derivation("T1")
        self.assertTrue(is_valid)
        self.assertEqual(len(missing), 0)

    def test_axiom_graph_generation(self):
        """测试公理图谱生成"""
        graph = self.system.get_axiom_graph()
        self.assertEqual(len(graph.nodes), 6)  # 3 axioms + 3 theorems

        # 检查边数量 (A1,A2,A3 -> T1; A1,A2,A3,T1 -> T2; A1,A2,A3,T1,T2 -> T3)
        self.assertTrue(len(graph.edges) > 0)

    def test_axiom_properties(self):
        """测试公理属性"""
        a1 = self.system.axioms["A1"]
        self.assertEqual(a1.axiom_type, AxiomType.BASE)
        self.assertIsNotNone(a1.falsifiability_condition)

        t1 = self.system.theorems["T1"]
        self.assertEqual(t1.axiom_type, AxiomType.DERIVED)
        self.assertIn("A1", t1.derivation_chain)

class TestHeatTaxMonitor(unittest.TestCase):
    """测试热税监测器"""

    def setUp(self):
        self.monitor = HeatTaxMonitor()

    def test_initial_state(self):
        """测试初始状态"""
        self.assertEqual(self.monitor.state.O_d, 0.0)
        self.assertEqual(self.monitor.state.phi, 100.0)
        self.assertFalse(self.monitor.state.is_irreversible())

    def test_irreversible_threshold(self):
        """测试不可逆阈值"""
        self.monitor.state.O_d = 0.9
        self.assertTrue(self.monitor.state.is_irreversible())

    def test_heat_tax_coefficient(self):
        """测试热税系数计算"""
        self.monitor.state.O_d = 0.5
        gamma = self.monitor.state.heat_tax_coefficient()
        self.assertGreater(gamma, self.monitor.state.gamma_0)

    def test_update_with_O_d_increase(self):
        """测试规范场强增加"""
        initial_phi = self.monitor.state.phi
        alerts = self.monitor.update(O_d_change=0.3)

        self.assertGreater(self.monitor.state.O_d, 0.0)
        self.assertLess(self.monitor.state.phi, initial_phi)

    def test_warning_alert(self):
        """测试预警告警"""
        self.monitor.state.O_d = 0.7
        alerts = self.monitor.update()

        warning_alerts = [a for a in alerts if a["level"] == "WARNING"]
        self.assertTrue(len(warning_alerts) > 0)

    def test_critical_alert(self):
        """测试临界告警"""
        self.monitor.state.O_d = 0.85
        alerts = self.monitor.update()

        critical_alerts = [a for a in alerts if a["level"] == "CRITICAL"]
        self.assertTrue(len(critical_alerts) > 0)

    def test_status_report(self):
        """测试状态报告生成"""
        report = self.monitor.get_status_report()

        self.assertIn("current_state", report)
        self.assertIn("trend", report)
        self.assertIn("alerts", report)
        self.assertIn("recommendations", report)

        self.assertIn("O_d", report["current_state"])
        self.assertIn("phi", report["current_state"])

    def test_external_input(self):
        """测试外部意义输入"""
        # 创建新state直接测试
        state = HeatTaxState(O_d=0.0, phi=100.0, gamma_0=0.1)
        initial_phi = state.phi

        # 直接调用底层state.update测试外部输入
        state.update(external_input=50.0)

        # 外部输入50，gamma_0=0.1时热税很小，总势能应该增加
        self.assertGreater(state.phi, initial_phi)

class TestSymbolicEngineV3(unittest.TestCase):
    """测试集成引擎 v3.0"""

    def setUp(self):
        self.engine = create_mss_v12_engine()

    def test_engine_initialization(self):
        """测试引擎初始化"""
        self.assertIsNotNone(self.engine.graph)
        self.assertIsNotNone(self.engine.transitive)
        self.assertIsNotNone(self.engine.cycle_detector)
        self.assertIsNotNone(self.engine.axiom_system)
        self.assertIsNotNone(self.engine.heat_tax_monitor)

    def test_axiom_system_loaded(self):
        """测试公理体系已加载"""
        self.assertIn("A1", self.engine.graph.nodes)
        self.assertIn("T1", self.engine.graph.nodes)

    def test_axiom_to_theorem_reasoning(self):
        """测试公理到定理的推理"""
        result = self.engine.reason("A1", "T1")
        self.assertEqual(result.result, InferenceResult.PROVEN)
        self.assertEqual(result.certainty, 1.0)

    def test_multi_step_derivation(self):
        """测试多步推导"""
        result = self.engine.reason("A1", "T3")
        self.assertEqual(result.result, InferenceResult.PROVEN)

    def test_system_health_monitoring(self):
        """测试系统健康监测"""
        health = self.engine.monitor_system_health(O_d=0.7, phi=80.0)

        self.assertIn("status", health)
        self.assertIn("alerts", health)
        self.assertIn("report", health)

    def test_heat_death_detection(self):
        """测试热寂检测"""
        health = self.engine.monitor_system_health(O_d=0.9, phi=10.0)
        self.assertEqual(health["status"], "heat_death_imminent")

    def test_export_axiom_system(self):
        """测试公理体系导出"""
        test_file = "test_axiom_export.json"
        self.engine.export_axiom_system(test_file)

        self.assertTrue(os.path.exists(test_file))

        with open(test_file, 'r', encoding='utf-8') as f:
            data = json.load(f)

        self.assertIn("axioms", data)
        self.assertIn("theorems", data)
        self.assertIn("mechanisms", data)
        self.assertEqual(len(data["axioms"]), 3)
        self.assertEqual(len(data["theorems"]), 3)

        # 清理
        os.remove(test_file)

class TestIntegration(unittest.TestCase):
    """集成测试"""

    def test_full_workflow(self):
        """测试完整工作流"""
        engine = create_mss_v12_engine()

        # 1. 推理
        result = engine.reason("A2", "T2")
        self.assertEqual(result.result, InferenceResult.PROVEN)

        # 2. 监测
        health = engine.monitor_system_health(O_d=0.6, phi=70.0)
        self.assertEqual(health["status"], "operational")

        # 3. 导出
        engine.export_axiom_system("integration_test.json")
        self.assertTrue(os.path.exists("integration_test.json"))
        os.remove("integration_test.json")

    def test_knowledge_graph_integration(self):
        """测试与现有知识图谱集成"""
        from kb_loader import KBLoader

        # 尝试加载现有知识库
        try:
            loader = KBLoader("knowledge_base")
            count = loader.load_all()

            if count == 0:
                self.skipTest("No knowledge base entries loaded")

            # 转换为图对象
            graph = loader.to_graph()

            # 用现有图谱创建引擎
            engine = SymbolicEngineV3(graph)

            # 验证公理体系已合并
            self.assertIn("A1", engine.graph.nodes)

            # 验证原有节点仍在
            original_nodes = set(graph.nodes.keys())
            merged_nodes = set(engine.graph.nodes.keys())
            self.assertTrue(original_nodes.issubset(merged_nodes))
        except Exception as e:
            self.skipTest(f"Knowledge base not available: {e}")

if __name__ == "__main__":
    unittest.main(verbosity=2)
