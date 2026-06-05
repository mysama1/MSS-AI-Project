"""
L1 IMPLIES Connection Completion
自动补全L1公理之间的IMPLIES逻辑推导关系
"""

import json
from pathlib import Path
from typing import Dict, List, Set, Tuple
from dataclasses import dataclass

from kb_loader import KBLoader
from symbolic_engine import MSSKnowledgeGraph, ConceptNode, RelationEdge, RelationType


@dataclass
class L1AxiomCluster:
    """L1公理簇——语义相关的公理组"""
    name: str
    axioms: List[str]  # 节点ID列表
    core_concept: str


class L1ImpliesCompleter:
    """
    L1 IMPLIES连接补全器
    
    策略：
    1. 基于dependencies字段显式连接
    2. 基于语义聚类自动推导
    3. 基于命名前缀分组（如AXIOM-*, AMFI-*, K4-*）
    """
    
    def __init__(self, kb_dir: str = "knowledge_base"):
        self.loader = KBLoader(kb_dir)
        self.graph: MSSKnowledgeGraph = None
        self.l1_nodes: Dict[str, ConceptNode] = {}
        self.new_edges: List[RelationEdge] = []
    
    def load(self) -> int:
        """加载知识库"""
        count = self.loader.load_all()
        self.graph = self.loader.to_graph()
        self.l1_nodes = {
            n.id: n for n in self.graph.nodes.values()
            if n.layer == "L1"
        }
        print(f"Loaded {count} entries, {len(self.l1_nodes)} L1 nodes")
        return count
    
    def complete(self) -> List[RelationEdge]:
        """
        执行补全，返回新增边列表
        """
        self.new_edges = []
        
        # 策略1: 基于dependencies显式连接
        self._add_dependency_edges()
        
        # 策略2: 基于前缀分组建立组内IMPLIES链
        self._add_prefix_chain_edges()
        
        # 策略3: 基于核心公理（A1-A6）作为根节点连接相关公理
        self._add_core_axiom_edges()
        
        print(f"Added {len(self.new_edges)} new IMPLIES edges")
        return self.new_edges
    
    def _add_dependency_edges(self):
        """基于dependencies字段添加边"""
        l1_ids = set(self.l1_nodes.keys())
        
        for entry in self.loader.entries.values():
            if entry.layer != "L1" or not entry.dependencies:
                continue
            
            for dep_id in entry.dependencies:
                # 只连接L1->L1
                if dep_id in l1_ids and dep_id != entry.id:
                    edge = RelationEdge(
                        source=dep_id,
                        target=entry.id,
                        relation=RelationType.IMPLIES,
                        strength=0.9,
                        evidence=f"dependency_ref:{entry.id}"
                    )
                    if not self._edge_exists(edge):
                        self.new_edges.append(edge)
                        self.graph.edges.append(edge)
    
    def _add_prefix_chain_edges(self):
        """基于前缀建立组内IMPLIES链"""
        # 按前缀分组
        prefix_groups: Dict[str, List[str]] = {}
        for node_id in self.l1_nodes:
            prefix = node_id.split("-")[0]
            if prefix not in prefix_groups:
                prefix_groups[prefix] = []
            prefix_groups[prefix].append(node_id)
        
        # 为每组建立链式连接（按ID排序）
        for prefix, node_ids in prefix_groups.items():
            if len(node_ids) <= 1:
                continue
            
            sorted_ids = sorted(node_ids)
            # 基础→衍生 的 IMPLIES 链
            for i in range(len(sorted_ids) - 1):
                source = sorted_ids[i]
                target = sorted_ids[i + 1]
                
                edge = RelationEdge(
                    source=source,
                    target=target,
                    relation=RelationType.IMPLIES,
                    strength=0.7,
                    evidence=f"prefix_chain:{prefix}"
                )
                if not self._edge_exists(edge):
                    self.new_edges.append(edge)
                    self.graph.edges.append(edge)
    
    def _add_core_axiom_edges(self):
        """基于核心公理A1-A6连接相关公理"""
        core_axioms = {
            "AXIOM-001": "信息本体论",
            "AXIOM-002": "意义原子",
            "AXIOM-003": "终极热税",
            "AXIOM-004": "规范场",
            "AXIOM-005": "矛盾升维",
            "AXIOM-006": "自指完备",
        }
        
        # 关键词映射
        keyword_map = {
            "AXIOM-001": ["信息", "本体", "意义", "存在"],
            "AXIOM-002": ["原子", "切片", "基本单元", "不可分"],
            "AXIOM-003": ["热税", "熵增", "耗散", "代价", "成本"],
            "AXIOM-004": ["规范", "场", "耦合", "BCT", "拓扑"],
            "AXIOM-005": ["矛盾", "升维", "悖论", "辩证"],
            "AXIOM-006": ["自指", "完备", "循环", "递归", "RSCA"],
        }
        
        for axiom_id, keywords in keyword_map.items():
            if axiom_id not in self.l1_nodes:
                continue
            
            for node_id, node in self.l1_nodes.items():
                if node_id == axiom_id:
                    continue
                
                # 检查标题/内容是否包含关键词
                text = (node.name or "") + " " + (node.content or "")
                match_count = sum(1 for kw in keywords if kw in text)
                
                if match_count >= 2:
                    edge = RelationEdge(
                        source=axiom_id,
                        target=node_id,
                        relation=RelationType.IMPLIES,
                        strength=min(0.5 + 0.1 * match_count, 0.8),
                        evidence=f"core_axiom_match:{axiom_id}"
                    )
                    if not self._edge_exists(edge):
                        self.new_edges.append(edge)
                        self.graph.edges.append(edge)
    
    def _edge_exists(self, edge: RelationEdge) -> bool:
        """检查边是否已存在"""
        for e in self.graph.edges:
            if (e.source == edge.source and 
                e.target == edge.target and
                e.relation == edge.relation):
                return True
        return False
    
    def get_stats(self) -> Dict:
        """获取补全统计"""
        l1_ids = set(self.l1_nodes.keys())
        
        l1_to_l1 = [e for e in self.graph.edges 
                    if e.source in l1_ids and e.target in l1_ids]
        l1_to_l1_implies = [e for e in l1_to_l1 
                           if e.relation == RelationType.IMPLIES]
        
        # 计算连通性
        connected = set()
        for e in l1_to_l1_implies:
            connected.add(e.source)
            connected.add(e.target)
        
        return {
            "total_l1": len(l1_ids),
            "l1_to_l1_edges": len(l1_to_l1),
            "l1_to_l1_implies": len(l1_to_l1_implies),
            "connected_l1": len(connected),
            "isolated_l1": len(l1_ids) - len(connected),
            "new_edges_added": len(self.new_edges),
        }
    
    def export_new_edges(self, filepath: str):
        """导出新增边为JSONL"""
        with open(filepath, 'w', encoding='utf-8') as f:
            for edge in self.new_edges:
                record = {
                    "source": edge.source,
                    "target": edge.target,
                    "relation": edge.relation.name,
                    "strength": edge.strength,
                    "evidence": edge.evidence,
                }
                f.write(json.dumps(record, ensure_ascii=False) + "\n")
        print(f"Exported {len(self.new_edges)} edges to {filepath}")


def main():
    """主函数"""
    completer = L1ImpliesCompleter(r"C:\MSS-AI-Project\knowledge_base")
    completer.load()
    
    # 补全前统计
    print("\n=== Before Completion ===")
    stats_before = completer.get_stats()
    for k, v in stats_before.items():
        print(f"  {k}: {v}")
    
    # 执行补全
    new_edges = completer.complete()
    
    # 补全后统计
    print("\n=== After Completion ===")
    stats_after = completer.get_stats()
    for k, v in stats_after.items():
        print(f"  {k}: {v}")
    
    # 导出
    completer.export_new_edges(r"C:\MSS-AI-Project\knowledge_base\l1_implies_completion.jsonl")
    
    return completer


if __name__ == "__main__":
    main()
