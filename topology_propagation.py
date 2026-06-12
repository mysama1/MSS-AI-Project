"""
topology_propagation.py - MSS拓扑传播引擎

核心功能：节点状态变更的级联传播
当节点A的状态变化时，自动标记所有依赖A的下游节点为STALE

设计原则（来自MTL工程化分析）：
- 寄生式进化：不替换Transformer，增强图谱结构
- 确定性传播：不依赖LLM，纯图遍历
- 跨层联动：L1变更→L2重算→L3重评估
- 状态机驱动：连续失败自动降级
"""

from dataclasses import dataclass, field
from typing import Dict, List, Set, Optional, Tuple, Any, Callable
from enum import Enum, auto
from collections import defaultdict, deque
import time
import json

from mssclaw.core.semantic.symbolic_engine import (
    MSSKnowledgeGraph, ConceptNode, RelationEdge,
    NodeType, RelationType, InferenceResult
)

class NodeStatus(Enum):
    """节点运行状态"""
    VALID = auto()       # 已验证，可信
    STALE = auto()       # 上游变更，需重算
    DEPRECATED = auto()  # 连续失败，已降级
    PENDING = auto()     # 等待验证
    ERROR = auto()       # 验证失败

class PropagationStrategy(Enum):
    """传播策略"""
    IMMEDIATE = auto()   # 立即传播（同步）
    DEFERRED = auto()    # 延迟传播（批量）
    SELECTIVE = auto()   # 选择性传播（按层过滤）

@dataclass
class StatusChange:
    """状态变更记录"""
    node_id: str
    old_status: NodeStatus
    new_status: NodeStatus
    timestamp: float
    reason: str
    triggered_by: Optional[str] = None  # 哪个节点触发的

@dataclass
class PropagationResult:
    """传播操作结果"""
    changed_nodes: List[str]  # 被变更的节点ID列表
    change_log: List[StatusChange]
    propagation_depth: int    # 最大传播深度
    time_ms: float           # 耗时

class TopologyPropagator:
    """
    拓扑传播引擎

    功能：
    1. 节点状态变更的级联传播
    2. 跨层依赖追踪（L1→L2→L3）
    3. 失败计数与自动降级
    4. 传播历史记录
    """

    def __init__(self, graph: MSSKnowledgeGraph):
        self.graph = graph
        # 节点当前状态
        self._status: Dict[str, NodeStatus] = {}
        # 失败计数器（用于自动降级）
        self._failure_count: Dict[str, int] = defaultdict(int)
        # 状态变更历史
        self._history: List[StatusChange] = []
        # 依赖缓存：node_id -> 依赖它的节点集合（反向边）
        self._dependents: Dict[str, Set[str]] = defaultdict(set)
        # 降级阈值
        self.deprecation_threshold = 3
        # 初始化所有节点为VALID
        self._init_status()
        self._build_dependents_cache()

    def _init_status(self):
        """初始化所有节点状态"""
        for node_id in self.graph.nodes:
            self._status[node_id] = NodeStatus.VALID

    def _build_dependents_cache(self):
        """构建反向依赖缓存"""
        self._dependents.clear()
        for edge in self.graph.edges:
            # edge.source -> edge.target 表示source推导出target
            # 所以target依赖source
            self._dependents[edge.source].add(edge.target)

    def get_status(self, node_id: str) -> Optional[NodeStatus]:
        """获取节点当前状态"""
        return self._status.get(node_id)

    def set_status(self, node_id: str, status: NodeStatus, reason: str = "",
                   triggered_by: Optional[str] = None) -> bool:
        """
        设置节点状态，记录变更历史

        Returns:
            True if status actually changed
        """
        if node_id not in self._status:
            return False

        old_status = self._status[node_id]
        if old_status == status:
            return False

        self._status[node_id] = status
        change = StatusChange(
            node_id=node_id,
            old_status=old_status,
            new_status=status,
            timestamp=time.time(),
            reason=reason,
            triggered_by=triggered_by
        )
        self._history.append(change)
        return True

    def propagate(self, source_node: str, strategy: PropagationStrategy = PropagationStrategy.IMMEDIATE,
                  max_depth: int = 10, layer_filter: Optional[Set[str]] = None) -> PropagationResult:
        """
        从源节点开始传播状态变更

        传播规则：
        - VALID → STALE: 上游变更，下游标记为待重算
        - 不传播到L1（L1是公理，不会被下游影响）
        - 跨层传播：L1变更影响L2，L2变更影响L3

        Args:
            source_node: 变更源节点ID
            strategy: 传播策略
            max_depth: 最大传播深度
            layer_filter: 只传播到指定层（如{"L2", "L3"}）

        Returns:
            PropagationResult with all changed nodes
        """
        start_time = time.time()
        changed_nodes = []
        change_log = []

        if source_node not in self.graph.nodes:
            return PropagationResult([], [], 0, 0.0)

        # BFS传播
        visited = {source_node}
        queue = deque([(source_node, 0)])
        max_reached_depth = 0

        while queue:
            current_id, depth = queue.popleft()
            max_reached_depth = max(max_reached_depth, depth)

            if depth >= max_depth:
                continue

            # 获取依赖current_id的所有节点
            dependents = self._dependents.get(current_id, set())

            for dep_id in dependents:
                if dep_id in visited:
                    continue

                dep_node = self.graph.nodes.get(dep_id)
                if not dep_node:
                    continue

                # 层过滤
                if layer_filter and dep_node.layer not in layer_filter:
                    continue

                # L1节点不会被下游变更影响（公理不变）
                if dep_node.layer == "L1":
                    continue

                # 检查当前状态，决定是否标记为STALE
                current_status = self._status.get(dep_id)
                if current_status == NodeStatus.VALID:
                    # 标记为STALE
                    if self.set_status(dep_id, NodeStatus.STALE,
                                      reason=f"Upstream {current_id} changed",
                                      triggered_by=source_node):
                        changed_nodes.append(dep_id)
                        change_log.append(self._history[-1])
                        visited.add(dep_id)
                        queue.append((dep_id, depth + 1))
                elif current_status == NodeStatus.DEPRECATED:
                    # 已降级的节点不再传播
                    continue
                else:
                    # 其他状态也加入队列继续传播
                    visited.add(dep_id)
                    queue.append((dep_id, depth + 1))

        elapsed = (time.time() - start_time) * 1000
        return PropagationResult(changed_nodes, change_log, max_reached_depth, elapsed)

    def mark_stale(self, node_id: str, reason: str = "") -> List[str]:
        """
        标记节点为STALE并传播

        便捷方法：先设置源节点为STALE，然后传播
        """
        self.set_status(node_id, NodeStatus.STALE, reason)
        result = self.propagate(node_id)
        return result.changed_nodes

    def verify_node(self, node_id: str, verifier: Callable[[str], bool]) -> bool:
        """
        验证节点，失败计数自动降级

        Args:
            node_id: 要验证的节点
            verifier: 验证函数，接收node_id返回bool

        Returns:
            验证是否通过
        """
        if node_id not in self.graph.nodes:
            return False

        try:
            passed = verifier(node_id)
        except Exception:
            passed = False

        if passed:
            # 验证通过，重置失败计数
            self._failure_count[node_id] = 0
            self.set_status(node_id, NodeStatus.VALID, "Verification passed")
            return True
        else:
            # 验证失败，增加计数
            self._failure_count[node_id] += 1
            count = self._failure_count[node_id]

            if count >= self.deprecation_threshold:
                # 达到降级阈值
                self.set_status(node_id, NodeStatus.DEPRECATED,
                              reason=f"Failed {count} times, deprecated")
                # 传播DEPRECATED状态
                self.propagate(node_id, layer_filter={"L2", "L3"})
            else:
                self.set_status(node_id, NodeStatus.ERROR,
                              reason=f"Verification failed ({count}/{self.deprecation_threshold})")

            return False

    def get_stale_nodes(self) -> List[str]:
        """获取所有STALE节点"""
        return [nid for nid, status in self._status.items() if status == NodeStatus.STALE]

    def get_deprecated_nodes(self) -> List[str]:
        """获取所有DEPRECATED节点"""
        return [nid for nid, status in self._status.items() if status == NodeStatus.DEPRECATED]

    def get_layer_status_summary(self) -> Dict[str, Dict[str, int]]:
        """按层统计状态分布"""
        summary = defaultdict(lambda: defaultdict(int))
        for node_id, status in self._status.items():
            node = self.graph.nodes.get(node_id)
            if node:
                layer = node.layer
                summary[layer][status.name] += 1
        return dict(summary)

    def get_propagation_history(self, node_id: Optional[str] = None,
                                since: Optional[float] = None) -> List[StatusChange]:
        """获取状态变更历史"""
        results = self._history
        if node_id:
            results = [c for c in results if c.node_id == node_id]
        if since:
            results = [c for c in results if c.timestamp >= since]
        return results

    def reset_node(self, node_id: str) -> bool:
        """重置节点到VALID状态"""
        if node_id not in self._status:
            return False
        self._failure_count[node_id] = 0
        return self.set_status(node_id, NodeStatus.VALID, "Manual reset")

    def export_state(self) -> Dict[str, Any]:
        """导出当前状态为JSON可序列化字典"""
        return {
            "status": {k: v.name for k, v in self._status.items()},
            "failure_counts": dict(self._failure_count),
            "history": [
                {
                    "node_id": c.node_id,
                    "old": c.old_status.name,
                    "new": c.new_status.name,
                    "time": c.timestamp,
                    "reason": c.reason,
                    "triggered_by": c.triggered_by
                }
                for c in self._history[-100:]  # 只保留最近100条
            ]
        }

    def import_state(self, state: Dict[str, Any]):
        """从字典恢复状态"""
        if "status" in state:
            for nid, sname in state["status"].items():
                try:
                    self._status[nid] = NodeStatus[sname]
                except KeyError:
                    pass
        if "failure_counts" in state:
            self._failure_count = defaultdict(int, state["failure_counts"])

# --- Demo ---

def demo():
    """演示拓扑传播引擎"""
    print("=" * 60)
    print("MSS Topology Propagation Engine Demo")
    print("=" * 60)

    from mssclaw.core.semantic.symbolic_engine import MSSKnowledgeGraph, ConceptNode, RelationEdge, NodeType, RelationType

    # 创建示例图谱（MTL映射示例）
    graph = MSSKnowledgeGraph()

    nodes = [
        # L1: 公理层
        ConceptNode("A1", "Information Ontology", NodeType.AXIOM, "L1",
                   "Information is fundamental", confidence=1.0),
        ConceptNode("A2", "0/1 Critical", NodeType.AXIOM, "L1",
                   "0/1 is phase transition", confidence=1.0),

        # L2: 理论层
        ConceptNode("T1", "BCT Coupling", NodeType.THEOREM, "L2",
                   "BCT theorem", confidence=0.9),
        ConceptNode("T2", "Resilience", NodeType.THEOREM, "L2",
                   "R = T/phi", confidence=0.85),
        ConceptNode("T3", "Entropy Tax", NodeType.THEOREM, "L2",
                   "Meaning dilution formula", confidence=0.8),

        # L3: 试探法层
        ConceptNode("H1", "Redshift", NodeType.CONCEPT, "L3",
                   "Metaphor for meaning dilution", confidence=0.7),
        ConceptNode("H2", "Topology Winding", NodeType.CONCEPT, "L3",
                   "Non-local connections", confidence=0.6),
        ConceptNode("H3", "Phase Transition", NodeType.CONCEPT, "L3",
                   "Critical point prediction", confidence=0.65),
    ]

    for n in nodes:
        graph.add_node(n)

    # 构建依赖关系（边表示推导/影响）
    edges = [
        # L1 → L2
        RelationEdge("A1", "T1", RelationType.IMPLIES, 1.0),
        RelationEdge("A2", "T1", RelationType.IMPLIES, 0.9),
        RelationEdge("A1", "T2", RelationType.IMPLIES, 0.8),
        RelationEdge("T1", "T3", RelationType.DERIVES_FROM, 0.85),

        # L2 → L3
        RelationEdge("T2", "H1", RelationType.ANALOGOUS, 0.7),
        RelationEdge("T3", "H2", RelationType.ANALOGOUS, 0.6),
        RelationEdge("T1", "H3", RelationType.IMPLIES, 0.75),
        RelationEdge("H2", "H3", RelationType.DERIVES_FROM, 0.5),
    ]

    for e in edges:
        graph.add_edge(e)

    # 创建传播引擎
    propagator = TopologyPropagator(graph)

    print("\n1. 初始状态分布:")
    summary = propagator.get_layer_status_summary()
    for layer, counts in summary.items():
        print(f"   {layer}: {dict(counts)}")

    print("\n2. 模拟A1公理变更 → 传播到下游:")
    result = propagator.mark_stale("A1", "Axiom revised with new evidence")
    print(f"   受影响节点: {result}")
    print(f"   STALE节点: {propagator.get_stale_nodes()}")

    print("\n3. 状态分布（传播后）:")
    summary = propagator.get_layer_status_summary()
    for layer, counts in summary.items():
        print(f"   {layer}: {dict(counts)}")

    print("\n4. 验证T1（模拟失败3次触发降级）:")
    for i in range(3):
        passed = propagator.verify_node("T1", lambda nid: False)  # 总是失败
        status = propagator.get_status("T1")
        print(f"   尝试{i+1}: passed={passed}, status={status.name if status else 'N/A'}")

    print(f"\n   DEPRECATED节点: {propagator.get_deprecated_nodes()}")

    print("\n5. 传播历史（最近5条）:")
    for change in propagator._history[-5:]:
        print(f"   {change.node_id}: {change.old_status.name} → {change.new_status.name} ({change.reason})")

    print("\n6. 导出状态:")
    state = propagator.export_state()
    print(f"   状态条目: {len(state['status'])}")
    print(f"   历史记录: {len(state['history'])}")

    print("\n" + "=" * 60)
    print("Demo complete")
    print("=" * 60)

if __name__ == "__main__":
    demo()
