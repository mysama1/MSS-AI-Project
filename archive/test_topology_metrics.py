"""
MSS Topology Metrics Engine - Test Suite
拓扑度量引擎测试套件

测试覆盖:
1. 连通分量分析
2. 桥边检测
3. 聚类系数
4. 层间连接分析
5. 综合拓扑度量
6. 脆弱点报告
7. 热税权重计算
8. 拓扑感知路径搜索
"""

import unittest
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from symbolic_engine import (
    MSSKnowledgeGraph, ConceptNode, RelationEdge,
    NodeType, RelationType
)
from topology_metrics import (
    TopologyMetricsEngine, TopologyAwarePathfinder,
    TopologyMetrics, VulnerabilityReport,
    enhance_graph_algorithms, SimplicialComplexMetrics
)

# RelationType mapping for tests
RT_IMPLIES = RelationType.IMPLIES
RT_ANALOG = RelationType.ANALOGOUS
RT_DERIVES = RelationType.DERIVES_FROM
RT_CONTRADICTS = RelationType.CONTRADICTS
RT_INSTANCE = RelationType.INSTANCE_OF
RT_TESTS = RelationType.TESTS
RT_REFINES = RelationType.REFINES

class TestTopologyMetricsEngine(unittest.TestCase):
    """测试拓扑度量引擎"""

    def setUp(self):
        """创建测试用的知识图谱"""
        self.graph = MSSKnowledgeGraph()

        # 构建一个具有明确拓扑结构的测试图谱
        # 结构:
        #   Component 1 (L1核心): A-B-C-D (链式+三角)
        #   Component 2 (L2): E-F-G (三角)
        #   Bridge: D-E (连接两个分量的唯一边)
        #   Component 3 (L3): H (孤立节点)

        # 节点
        nodes = [
            ("A", "L1", NodeType.CONCEPT),
            ("B", "L1", NodeType.CONCEPT),
            ("C", "L1", NodeType.CONCEPT),
            ("D", "L1", NodeType.CONCEPT),
            ("E", "L2", NodeType.CONCEPT),
            ("F", "L2", NodeType.CONCEPT),
            ("G", "L2", NodeType.CONCEPT),
            ("H", "L3", NodeType.CONCEPT),
        ]

        for node_id, layer, node_type in nodes:
            node = ConceptNode(
                id=node_id,
                name=node_id,
                node_type=node_type,
                layer=layer,
                content=f"Test content for {node_id}"
            )
            self.graph.add_node(node)

        # 边: Component 1 (A-B-C-D with triangle A-B-C)
        edges = [
            ("A", "B", RT_IMPLIES),
            ("B", "C", RT_IMPLIES),
            ("C", "A", RT_ANALOG),  # 形成三角
            ("C", "D", RT_IMPLIES),
            # Component 2 (E-F-G triangle)
            ("E", "F", RT_IMPLIES),
            ("F", "G", RT_IMPLIES),
            ("G", "E", RT_ANALOG),  # 形成三角
            # Bridge: D-E (唯一连接)
            ("D", "E", RT_DERIVES),
        ]

        for source, target, rel_type in edges:
            edge = RelationEdge(
                source=source,
                target=target,
                relation=rel_type
            )
            self.graph.add_edge(edge)

        self.engine = TopologyMetricsEngine(self.graph)

    # =========================================================
    # Test 1: 连通分量分析
    # =========================================================

    def test_find_connected_components(self):
        """测试连通分量检测"""
        components = self.engine.find_connected_components()

        # 应该找到2个连通分量: {A,B,C,D,E,F,G} 和 {H}
        self.assertEqual(len(components), 2)

        # 检查分量大小
        sizes = sorted([len(c) for c in components])
        self.assertEqual(sizes, [1, 7])

        # 检查H是孤立的
        h_component = self.engine.get_component_for_node("H")
        self.assertIsNotNone(h_component)
        self.assertEqual(len(h_component), 1)
        self.assertIn("H", h_component)

    def test_get_largest_component_size(self):
        """测试最大连通分量大小"""
        size = self.engine.get_largest_component_size()
        self.assertEqual(size, 7)

    # =========================================================
    # Test 2: 桥边检测
    # =========================================================

    def test_find_bridges(self):
        """测试桥边检测"""
        bridges = self.engine.find_bridges()

        # 应该有桥边(D-E是桥边，因为D和E之间只有一条连接)
        # 注意: 由于无向图处理，可能检测到D-E的两个方向
        self.assertGreaterEqual(len(bridges), 1)

        # 至少有一条桥边连接D和E
        de_bridges = [b for b in bridges if set(b) == {"D", "E"}]
        self.assertEqual(len(de_bridges), 1)

    def test_is_bridge(self):
        """测试桥边判断"""
        # D-E是桥边
        self.assertTrue(self.engine.is_bridge("D", "E"))
        self.assertTrue(self.engine.is_bridge("E", "D"))

        # A-B不是桥边(因为有A-C-B三角)
        self.assertFalse(self.engine.is_bridge("A", "B"))

    def test_get_bridge_between_components(self):
        """测试桥边分量信息"""
        bridges = self.engine.get_bridge_between_components()

        self.assertGreaterEqual(len(bridges), 1)

        # 至少有一条桥边连接D和E
        de_bridges = [b for b in bridges if set([b[0], b[1]]) == {"D", "E"}]
        self.assertEqual(len(de_bridges), 1)
        source, target, size1, size2 = de_bridges[0]

        # 桥边连接两个分量
        self.assertIn(source, {"D", "E"})
        self.assertIn(target, {"D", "E"})

    # =========================================================
    # Test 3: 聚类系数
    # =========================================================

    def test_local_clustering_coefficient(self):
        """测试局部聚类系数"""
        # A的邻居: B, C (通过outgoing: B, C; incoming: C)
        # B和C之间有边(B->C), 所以邻居间有1条边
        # 最大可能: 2*1/2 = 1
        # coeff = 1/1 = 1.0
        coeff_a = self.engine.local_clustering_coefficient("A")
        self.assertEqual(coeff_a, 1.0)

        # H是孤立节点，聚类系数为0
        coeff_h = self.engine.local_clustering_coefficient("H")
        self.assertEqual(coeff_h, 0.0)

    def test_global_clustering_coefficient(self):
        """测试全局聚类系数"""
        global_coeff = self.engine.global_clustering_coefficient()

        # 应该在0到1之间
        self.assertGreaterEqual(global_coeff, 0.0)
        self.assertLessEqual(global_coeff, 1.0)

        # 由于有三角结构，全局系数应该>0
        self.assertGreater(global_coeff, 0.0)

    def test_get_sparse_nodes(self):
        """测试稀疏节点检测"""
        sparse = self.engine.get_sparse_nodes(threshold=0.3)

        # H是孤立节点，应该是稀疏的
        h_sparse = [n for n, c in sparse if n == "H"]
        self.assertEqual(len(h_sparse), 1)

    # =========================================================
    # Test 4: 层间连接分析
    # =========================================================

    def test_analyze_layer_connections(self):
        """测试层间连接分析"""
        analysis = self.engine.analyze_layer_connections()

        # 应该有跨层连接(L1->L2 via D->E)
        self.assertGreater(analysis["total_crossings"], 0)

        # L1->L2桥边应该存在
        self.assertEqual(len(analysis["l1_l2_bridges"]), 1)

    def test_find_layer_gaps(self):
        """测试层间断裂检测"""
        # 我们的测试图L1和L2有连接，但L3(H)完全孤立
        gaps = self.engine.find_layer_gaps()

        # 应该检测到L2-L3断裂
        self.assertTrue(
            any(src == "L2" and tgt == "L3" for src, tgt in gaps) or
            any(src == "L3" and tgt == "L2" for src, tgt in gaps)
        )

    # =========================================================
    # Test 5: 综合拓扑度量
    # =========================================================

    def test_compute_all_metrics(self):
        """测试综合度量计算"""
        metrics = self.engine.compute_all_metrics()

        # 基本计数
        self.assertEqual(metrics.node_count, 8)
        self.assertEqual(metrics.edge_count, 8)

        # 连通分量
        self.assertEqual(metrics.connected_components, 2)

        # 桥边
        self.assertGreaterEqual(metrics.bridge_count, 1)

        # 孤立节点
        self.assertEqual(metrics.isolated_nodes, 1)

        # 健康度评分在0-100之间
        self.assertGreaterEqual(metrics.topology_health_score, 0)
        self.assertLessEqual(metrics.topology_health_score, 100)

        # 聚类系数在0-1之间
        self.assertGreaterEqual(metrics.avg_clustering_coefficient, 0)
        self.assertLessEqual(metrics.avg_clustering_coefficient, 1)

    # =========================================================
    # Test 6: 脆弱点报告
    # =========================================================

    def test_generate_vulnerability_report(self):
        """测试脆弱点报告生成"""
        report = self.engine.generate_vulnerability_report()

        # 应该有桥边
        self.assertGreaterEqual(len(report.bridge_edges), 1)

        # 应该有修复建议
        self.assertGreater(len(report.recommendations), 0)

        # 检查建议内容包含桥边信息
        bridge_mentioned = any("桥边" in r or "脆弱点" in r
                              for r in report.recommendations)
        self.assertTrue(bridge_mentioned)

    # =========================================================
    # Test 7: 热税权重计算
    # =========================================================

    def test_compute_heat_tax_weight(self):
        """测试热税权重计算"""
        # 普通节点权重应该>=1.0
        weight_a = self.engine.compute_heat_tax_weight("A")
        self.assertGreaterEqual(weight_a, 1.0)

        # 桥边端点应该有更高权重
        weight_d = self.engine.compute_heat_tax_weight("D")
        weight_e = self.engine.compute_heat_tax_weight("E")
        self.assertGreater(weight_d, 1.0)
        self.assertGreater(weight_e, 1.0)

        # 孤立节点权重应该最高
        weight_h = self.engine.compute_heat_tax_weight("H")
        self.assertGreaterEqual(weight_h, 2.0)

    def test_get_path_heat_tax(self):
        """测试路径热税计算"""
        path = ["A", "B", "C"]
        tax = self.engine.get_path_heat_tax(path)

        # 路径热税应该大于0
        self.assertGreater(tax, 0)

        # 应该等于各节点权重之和
        expected = sum(self.engine.compute_heat_tax_weight(n) for n in path)
        self.assertEqual(tax, expected)

    def test_unknown_node_heat_tax(self):
        """测试未知节点热税"""
        weight = self.engine.compute_heat_tax_weight("UNKNOWN_NODE")
        self.assertEqual(weight, 2.0)

class TestTopologyAwarePathfinder(unittest.TestCase):
    """测试拓扑感知路径搜索器"""

    def setUp(self):
        """创建测试图谱"""
        self.graph = MSSKnowledgeGraph()

        # 构建测试结构:
        # L1: A -> B -> C
        #      ↘   ↓  ↗
        #       D -> E
        # L2: F -> G -> H
        # Bridge: C -> F

        nodes = [
            ("A", "L1"), ("B", "L1"), ("C", "L1"),
            ("D", "L1"), ("E", "L1"),
            ("F", "L2"), ("G", "L2"), ("H", "L2"),
        ]

        for node_id, layer in nodes:
            node = ConceptNode(
                id=node_id,
                name=node_id,
                node_type=NodeType.CONCEPT,
                layer=layer,
                content=f"Test content for {node_id}"
            )
            self.graph.add_node(node)

        edges = [
            ("A", "B"), ("B", "C"), ("A", "D"),
            ("D", "E"), ("E", "C"),  # L1内部多路径
            ("C", "F"),  # 层间桥边
            ("F", "G"), ("G", "H"),  # L2链式
        ]

        for source, target in edges:
            edge = RelationEdge(
                source=source,
                target=target,
                relation=RT_IMPLIES
            )
            self.graph.add_edge(edge)

        self.metrics = TopologyMetricsEngine(self.graph)
        self.finder = TopologyAwarePathfinder(self.graph, self.metrics)

    # =========================================================
    # Test 8: 拓扑感知路径搜索
    # =========================================================

    def test_find_lowest_heat_tax_path(self):
        """测试最低热税路径搜索"""
        result = self.finder.find_lowest_heat_tax_path("A", "C")

        self.assertIsNotNone(result)
        path, tax = result

        # 路径应该从A开始，到C结束
        self.assertEqual(path[0], "A")
        self.assertEqual(path[-1], "C")

        # 热税应该大于0
        self.assertGreater(tax, 0)

    def test_find_lowest_heat_tax_path_avoid_bridges(self):
        """测试避开桥边的路径搜索"""
        # A到C不经过桥边(C-F是桥边，但A到C不需要经过它)
        result = self.finder.find_lowest_heat_tax_path(
            "A", "C", avoid_bridges=True
        )

        self.assertIsNotNone(result)
        path, tax = result
        self.assertEqual(path[-1], "C")

    def test_find_multiple_paths(self):
        """测试多路径搜索"""
        paths = self.finder.find_multiple_paths("A", "C", max_paths=3)

        # 应该找到至少1条路径
        self.assertGreaterEqual(len(paths), 1)

        # 所有路径都应该到达C
        for path, tax in paths:
            self.assertEqual(path[-1], "C")

    def test_find_layer_priority_path(self):
        """测试层优先路径"""
        result = self.finder._find_layer_priority_path("A", "H")

        self.assertIsNotNone(result)
        path, tax = result

        # 路径应该遵循L1->L2方向
        self.assertEqual(path[0], "A")
        self.assertEqual(path[-1], "H")

    def test_path_not_found(self):
        """测试不可达路径"""
        # 添加孤立节点
        isolated = ConceptNode(
            id="ISOLATED",
            name="ISOLATED",
            node_type=NodeType.CONCEPT,
            layer="L3",
            content="Isolated test node"
        )
        self.graph.add_node(isolated)

        result = self.finder.find_lowest_heat_tax_path("A", "ISOLATED")
        self.assertIsNone(result)

class TestIntegration(unittest.TestCase):
    """集成测试"""

    def test_enhance_graph_algorithms(self):
        """测试与现有GraphAlgorithms的集成"""
        from symbolic_engine_v2 import GraphAlgorithms

        graph = MSSKnowledgeGraph()

        # 添加简单节点
        for i in range(3):
            node = ConceptNode(
                id=f"N{i}",
                name=f"Node{i}",
                node_type=NodeType.CONCEPT,
                layer="L1",
                content=f"Test content for N{i}"
            )
            graph.add_node(node)

        # 添加边形成链
        for i in range(2):
            edge = RelationEdge(
                source=f"N{i}",
                target=f"N{i+1}",
                relation=RT_IMPLIES
            )
            graph.add_edge(edge)

        # 使用增强函数
        ga = GraphAlgorithms(graph)
        topo = enhance_graph_algorithms(ga)

        # 验证返回的是TopologyMetricsEngine
        self.assertIsInstance(topo, TopologyMetricsEngine)

        # 验证可以计算度量
        metrics = topo.compute_all_metrics()
        self.assertEqual(metrics.node_count, 3)

    def test_alias_compatibility(self):
        """测试别名兼容性"""
        # SimplicialComplexMetrics应该是TopologyMetricsEngine的别名
        self.assertIs(SimplicialComplexMetrics, TopologyMetricsEngine)

class TestEdgeCases(unittest.TestCase):
    """边界情况测试"""

    def test_empty_graph(self):
        """测试空图谱"""
        graph = MSSKnowledgeGraph()
        engine = TopologyMetricsEngine(graph)

        metrics = engine.compute_all_metrics()
        self.assertEqual(metrics.node_count, 0)
        # 空图谱健康度为0(所有子项为0，但公式可能产生非零值)
        # 实际上空图谱node_count=0导致除零保护，返回0
        self.assertEqual(metrics.node_count, 0)
        self.assertEqual(metrics.connected_components, 0)

    def test_single_node(self):
        """测试单节点图谱"""
        graph = MSSKnowledgeGraph()
        node = ConceptNode(
            id="solo",
            name="Solo",
            node_type=NodeType.CONCEPT,
            layer="L1",
            content="Test content for solo"
        )
        graph.add_node(node)

        engine = TopologyMetricsEngine(graph)
        metrics = engine.compute_all_metrics()

        self.assertEqual(metrics.node_count, 1)
        self.assertEqual(metrics.isolated_nodes, 1)
        self.assertEqual(metrics.connected_components, 1)

    def test_fully_connected_triangle(self):
        """测试完全连接的三角"""
        graph = MSSKnowledgeGraph()

        for i in range(3):
            node = ConceptNode(
                id=f"T{i}",
                name=f"Triangle{i}",
                node_type=NodeType.CONCEPT,
                layer="L1",
                content=f"Test content for T{i}"
            )
            graph.add_node(node)

        # 完全连接
        for i in range(3):
            for j in range(3):
                if i != j:
                    edge = RelationEdge(
                        source=f"T{i}",
                        target=f"T{j}",
                        relation=RT_ANALOG
                    )
                    graph.add_edge(edge)

        engine = TopologyMetricsEngine(graph)

        # 完全连接图没有桥边
        bridges = engine.find_bridges()
        self.assertEqual(len(bridges), 0)

        # 聚类系数应该很高
        coeff = engine.global_clustering_coefficient()
        self.assertEqual(coeff, 1.0)

if __name__ == "__main__":
    # Run tests with verbose output
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    # Add all test classes
    suite.addTests(loader.loadTestsFromTestCase(TestTopologyMetricsEngine))
    suite.addTests(loader.loadTestsFromTestCase(TestTopologyAwarePathfinder))
    suite.addTests(loader.loadTestsFromTestCase(TestIntegration))
    suite.addTests(loader.loadTestsFromTestCase(TestEdgeCases))

    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    # Print summary
    print(f"\n{'='*60}")
    print(f"Test Summary: {result.testsRun} tests run")
    print(f"Success: {result.wasSuccessful()}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    print(f"{'='*60}")

    # Exit with appropriate code
    sys.exit(0 if result.wasSuccessful() else 1)
