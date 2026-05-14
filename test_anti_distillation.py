"""
Anti-Distillation Defense System Tests
测试反蒸馏防御体系知识库条目
"""

import unittest
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from kb_loader import KBLoader


class TestAntiDistillationKB(unittest.TestCase):
    """测试反蒸馏防御知识库"""
    
    def setUp(self):
        self.loader = KBLoader("knowledge_base")
        self.count = self.loader.load_all()
    
    def test_entries_loaded(self):
        """测试反蒸馏条目已加载"""
        entries = [e for e in self.loader.entries.values() if e.id.startswith("ADD-")]
        self.assertGreaterEqual(len(entries), 7, "应至少加载7条反蒸馏条目")
    
    def test_layer_distribution(self):
        """测试层级分布"""
        entries = [e for e in self.loader.entries.values() if e.id.startswith("ADD-")]
        l2_count = sum(1 for e in entries if e.layer == "L2")
        l3_count = sum(1 for e in entries if e.layer == "L3")
        
        self.assertGreaterEqual(l2_count, 2, "L2保护带条目应≥2")
        self.assertGreaterEqual(l3_count, 3, "L3试探法条目应≥3")
    
    def test_core_concepts_present(self):
        """测试核心概念存在"""
        content = " ".join([e.content for e in self.loader.entries.values() if e.id.startswith("ADD-")])
        
        core_concepts = [
            "意义自旋", "热税", "蒸馏", "L-1", "L0", "L1",
            "加密", "专利", "防火墙", "熔断", "数据主权"
        ]
        
        for concept in core_concepts:
            self.assertIn(concept, content, f"核心概念'{concept}'应在内容中")
    
    def test_dependencies_valid(self):
        """测试依赖关系有效"""
        entries = {e.id: e for e in self.loader.entries.values() if e.id.startswith("ADD-")}
        
        for eid, entry in entries.items():
            for dep in entry.dependencies:
                if dep.startswith("ADD-"):
                    self.assertIn(dep, entries, f"{eid}依赖{dep}但不存在")
    
    def test_confidence_range(self):
        """测试置信度范围"""
        entries = [e for e in self.loader.entries.values() if e.id.startswith("ADD-")]
        
        for entry in entries:
            # KBEntry uses 'score' instead of 'confidence'
            score = getattr(entry, 'score', 0.0)
            self.assertGreaterEqual(score, 0.0)
            self.assertLessEqual(score, 1.0)
            # Note: some entries may have score=0.0, so we check range only
            self.assertIn(score, [0.0, 0.5, 0.6, 0.65, 0.7, 0.75, 0.8, 0.85, 0.9, 1.0],
                         "置信度应在有效范围内")


class TestAntiDistillationIntegration(unittest.TestCase):
    """反蒸馏防御集成测试"""
    
    def test_kb_graph_conversion(self):
        """测试知识图谱转换"""
        loader = KBLoader("knowledge_base")
        loader.load_all()
        graph = loader.to_graph()
        
        # 检查反蒸馏节点存在
        add_nodes = [n for n in graph.nodes if n.startswith("ADD-")]
        self.assertGreaterEqual(len(add_nodes), 7)
        
        # 检查边存在
        self.assertGreater(len(graph.edges), 0)
    
    def test_symbolic_reasoning(self):
        """测试符号推理"""
        from symbolic_engine_v3 import SymbolicEngineV3
        from kb_loader import KBLoader
        
        loader = KBLoader("knowledge_base")
        loader.load_all()
        graph = loader.to_graph()
        
        engine = SymbolicEngineV3(graph)
        
        # 测试从ADD-001推导到ADD-002
        result = engine.reason("ADD-001", "ADD-002")
        self.assertIsNotNone(result)


if __name__ == "__main__":
    unittest.main(verbosity=2)
