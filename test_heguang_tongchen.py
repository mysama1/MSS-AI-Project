"""
He Guang Tong Chen (和光同尘) Tactical System Tests
测试"和光同尘"战术体系知识库条目
"""

import unittest
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from kb_loader import KBLoader


class TestHeguangTongchenKB(unittest.TestCase):
    """测试和光同尘战术知识库"""
    
    def setUp(self):
        self.loader = KBLoader("knowledge_base")
        self.count = self.loader.load_all()
    
    def test_entries_loaded(self):
        """测试战术条目已加载"""
        entries = [e for e in self.loader.entries.values() if e.id.startswith("THT-")]
        self.assertGreaterEqual(len(entries), 7, "应至少加载7条战术条目")
    
    def test_layer_distribution(self):
        """测试层级分布"""
        entries = [e for e in self.loader.entries.values() if e.id.startswith("THT-")]
        l2_count = sum(1 for e in entries if e.layer == "L2")
        l3_count = sum(1 for e in entries if e.layer == "L3")
        
        self.assertGreaterEqual(l2_count, 2, "L2保护带条目应≥2")
        self.assertGreaterEqual(l3_count, 3, "L3试探法条目应≥3")
    
    def test_core_concepts_present(self):
        """测试核心概念存在"""
        content = " ".join([e.content for e in self.loader.entries.values() if e.id.startswith("THT-")])
        
        core_concepts = [
            "热税", "工具理性", "意义毒素", "提纯", "防火墙",
            "套利", "ROI", "封装", "灌注", "离线"
        ]
        
        for concept in core_concepts:
            self.assertIn(concept, content, f"核心概念'{concept}'应在内容中")
    
    def test_module_sequence(self):
        """测试三个模块顺序正确"""
        entries = {e.id: e for e in self.loader.entries.values() if e.id.startswith("THT-")}
        
        # THT-002(收集器) → THT-003(离心机) → THT-004(封装)
        self.assertIn("THT-002", entries)
        self.assertIn("THT-003", entries)
        self.assertIn("THT-004", entries)
        
        # 检查依赖链
        self.assertIn("THT-001", entries["THT-002"].dependencies, "收集器依赖战术本质")
        self.assertIn("THT-002", entries["THT-003"].dependencies, "离心机依赖收集器")
        self.assertIn("THT-003", entries["THT-004"].dependencies, "封装依赖离心机")
    
    def test_firewall_layers(self):
        """测试防火墙三层结构"""
        entries = {e.id: e for e in self.loader.entries.values() if e.id.startswith("THT-")}
        
        firewall = entries.get("THT-005")
        self.assertIsNotNone(firewall, "防火墙条目应存在")
        
        content = firewall.content
        self.assertIn("物理层", content, "应包含物理层防火墙")
        self.assertIn("逻辑层", content, "应包含逻辑层防火墙")
        self.assertIn("热税层", content, "应包含热税层防火墙")
        self.assertIn("0.1γ₀", content, "应包含热税阈值0.1γ₀")
    
    def test_roi_quantification(self):
        """测试ROI量化指标"""
        content = " ".join([e.content for e in self.loader.entries.values() if e.id.startswith("THT-")])
        
        # 检查关键数字
        self.assertIn("1000倍", content, "应包含1000倍ROI")
        self.assertIn("70%", content, "应包含70%成本降低")
        self.assertIn("0.001%", content, "应包含0.001%毒素残留率")


class TestHeguangTongchenIntegration(unittest.TestCase):
    """和光同尘战术集成测试"""
    
    def test_kb_graph_conversion(self):
        """测试知识图谱转换"""
        loader = KBLoader("knowledge_base")
        loader.load_all()
        graph = loader.to_graph()
        
        # 检查战术节点存在
        tht_nodes = [n for n in graph.nodes if n.startswith("THT-")]
        self.assertGreaterEqual(len(tht_nodes), 7)
        
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
        
        # 测试从战术本质推导到收集器
        result = engine.reason("THT-001", "THT-002")
        self.assertIsNotNone(result)


if __name__ == "__main__":
    unittest.main(verbosity=2)
