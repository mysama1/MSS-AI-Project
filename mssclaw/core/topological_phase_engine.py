"""
Topological Phase Engine — 基于拓扑距离的锚点选择与θ驱动 (Sprint 146a).

核心原理:
  锚点不是随便放的 —— 它们在意义场拓扑中的位置决定相位机质量。
  选冲突盆地中"最深"的点作为锚点, θ由当前状态到两个锚点的拓扑距离之比决定。

三阶段:
  1. 盆地构建: 从稳定子出发沿意义边扩散, 直到遇到对方约束边界
  2. 锚点选择: 盆底最大离心度节点 = argmax Σ dist(v, other_node)
  3. 相位驱动: θ = d_A/(d_A + d_B), σ² = ((d_A-d_B)/(d_A+d_B))²

与MSS公理对齐:
  A5规范场 → 稳定子盆地 (吸引子)
  A2投影 → 拓扑距离 (最短路径)
  A3热税 → 切换代价 (Δφ_jump)
"""
from __future__ import annotations
import math, json
from typing import Dict, List, Tuple, Set, Optional
from dataclasses import dataclass, field
from collections import deque


# ═══ Layer 1: Meaning Field Graph ═══

@dataclass
class MeaningNode:
    """意义场节点."""
    id: str
    label: str
    stable_subfield_id: Optional[str] = None  # 所属稳定子
    attributes: Dict = field(default_factory=dict)


@dataclass
class MeaningEdge:
    """意义边 — 有向/无向."""
    source: str
    target: str
    weight: float = 1.0  # 距离权重 (默认1)
    directed: bool = False


class MeaningFieldGraph:
    """
    意义场拓扑图.

    支持:
      - 最短路径 (BFS/加权BFS)
      - 盆地识别 (稳定子扩散)
      - 锚点选择 (最大离心度)
    """

    def __init__(self):
        self.nodes: Dict[str, MeaningNode] = {}
        self.adj: Dict[str, List[Tuple[str, float]]] = {}  # node → [(neighbor, weight)]

    def add_node(self, node: MeaningNode):
        self.nodes[node.id] = node
        if node.id not in self.adj:
            self.adj[node.id] = []

    def add_edge(self, edge: MeaningEdge):
        self.adj.setdefault(edge.source, []).append((edge.target, edge.weight))
        if not edge.directed:
            self.adj.setdefault(edge.target, []).append((edge.source, edge.weight))

    def shortest_distances_from(self, source_id: str) -> Dict[str, float]:
        """Dijkstra: 从source到所有节点的最短拓扑距离."""
        import heapq
        dist = {nid: float('inf') for nid in self.nodes}
        dist[source_id] = 0.0
        pq = [(0.0, source_id)]
        while pq:
            d, u = heapq.heappop(pq)
            if d > dist[u]:
                continue
            for v, w in self.adj.get(u, []):
                nd = d + w
                if nd < dist[v]:
                    dist[v] = nd
                    heapq.heappush(pq, (nd, v))
        return dist

    def bfs_distances(self, source_id: str) -> Dict[str, int]:
        """无权BFS: 跳数距离."""
        dist = {nid: -1 for nid in self.nodes}
        dist[source_id] = 0
        q = deque([source_id])
        while q:
            u = q.popleft()
            for v, _ in self.adj.get(u, []):
                if dist[v] == -1:
                    dist[v] = dist[u] + 1
                    q.append(v)
        return dist

    def topological_distance(self, a: str, b: str) -> float:
        """两点间拓扑距离."""
        dists = self.shortest_distances_from(a)
        return dists.get(b, float('inf'))


# ═══ Layer 2: Basin Builder ═══

@dataclass
class ConflictBasin:
    """冲突盆地 — 一个稳定子的吸引子区域."""
    stable_subfield_name: str
    basin_nodes: Set[str]     # 盆地内所有节点
    boundary_nodes: Set[str]  # 边界节点 (与对方盆地接壤)
    anchor_id: Optional[str] = None  # 锚点 (盆底最深处)


class BasinBuilder:
    """
    盆地构建器.

    从稳定子定义出发, 沿意义边扩散, 直到遇到对方约束边界.
    """

    def __init__(self, field: MeaningFieldGraph):
        self.field = field

    def build_basin(self, seed_node_ids: List[str],
                    opposing_constraint_nodes: Set[str],
                    max_depth: int = 10) -> ConflictBasin:
        """
        从种子节点扩散构建盆地.

        Args:
            seed_node_ids: 稳定子直接约束的节点
            opposing_constraint_nodes: 对方约束节点 (遇到则停止)
            max_depth: 最大扩散深度
        """
        basin = set(seed_node_ids)
        boundary = set()
        frontier = deque(seed_node_ids)
        visited = set(seed_node_ids)
        depth = {n: 0 for n in seed_node_ids}

        while frontier:
            u = frontier.popleft()
            if depth[u] >= max_depth:
                boundary.add(u)
                continue
            for v, _ in self.field.adj.get(u, []):
                if v in opposing_constraint_nodes:
                    boundary.add(u)  # u是边界节点
                    continue
                if v not in visited:
                    visited.add(v)
                    basin.add(v)
                    depth[v] = depth[u] + 1
                    frontier.append(v)

        # 为边界节点标记对方邻居
        boundary_with_contact = set()
        for b in boundary:
            for v, _ in self.field.adj.get(b, []):
                if v in opposing_constraint_nodes:
                    boundary_with_contact.add(b)
                    break

        return ConflictBasin(
            stable_subfield_name="",
            basin_nodes=basin,
            boundary_nodes=boundary_with_contact,
        )

    def select_anchor(self, basin: ConflictBasin) -> str:
        """
        锚点选择: 最大离心度.

        eccentricity(v) = max dist(v, u) for u in basin
        锚点 = argmax eccentricity(v). 即盆底最深处.
        """
        if not basin.basin_nodes:
            return ""

        best_node = ""
        best_ecc = -1.0

        for v in basin.basin_nodes:
            dists = self.field.shortest_distances_from(v)
            # 离心度: 到盆地内最远节点的距离
            ecc = max((dists.get(u, 0) for u in basin.basin_nodes), default=0)
            if ecc > best_ecc:
                best_ecc = ecc
                best_node = v

        return best_node

    def select_anchor_v2(self, basin: ConflictBasin) -> Tuple[str, float]:
        """
        v2: 锚点选择 = 最大核心度 Coreness(v, S).

        Coreness = η_S(v) × (1 - dist_to_boundary_ratio)
        其中 η_S 是稳定子投影保真度, dist_to_boundary_ratio 归一化到边界距离.
        """
        if not basin.basin_nodes:
            return ("", 0.0)

        # 计算每个节点到边界的最短距离
        boundary_dist = {}
        for b in basin.boundary_nodes:
            b_dists = self.field.shortest_distances_from(b)
            for v in basin.basin_nodes:
                d = b_dists.get(v, float('inf'))
                if v not in boundary_dist or d < boundary_dist[v]:
                    boundary_dist[v] = d

        max_boundary = max(boundary_dist.values(), default=1.0)

        best_node = ""
        best_coreness = -1.0

        for v in basin.basin_nodes:
            d_boundary = boundary_dist.get(v, 0)
            ratio = d_boundary / max(max_boundary, 1.0)  # 归一化
            # η_S = 1.0 (节点在盆地内 → 投影保真度最高)
            coreness = 1.0 * ratio
            if coreness > best_coreness:
                best_coreness = coreness
                best_node = v

        return (best_node, round(best_coreness, 3))


# ═══ Layer 3: Topological Phase Engine ═══

class TopologicalPhaseEngine:
    """
    拓扑相位机.

    θ = d_A / (d_A + d_B)
    其中 d_A = 当前节点到锚点A的拓扑距离
          d_B = 当前节点到锚点B的拓扑距离

    σ² = ((d_A - d_B) / (d_A + d_B))²
    """

    def __init__(self, field: MeaningFieldGraph,
                 anchor_A_id: str, anchor_B_id: str,
                 hysteresis: float = 0.15):
        self.field = field
        self.anchor_A = anchor_A_id
        self.anchor_B = anchor_B_id
        self.hysteresis = hysteresis
        self.active = 'A'

        # 预计算: 所有节点到两个锚点的最短拓扑距离
        self.dist_to_A = field.shortest_distances_from(anchor_A_id)
        self.dist_to_B = field.shortest_distances_from(anchor_B_id)

        self.history: List[Dict] = []
        self.switch_count = 0
        self.total_heat_tax = 0.0

    def compute_theta_and_sigma(self, current_node_id: str) -> Tuple[float, float]:
        """计算θ和σ²."""
        dA = self.dist_to_A.get(current_node_id, float('inf'))
        dB = self.dist_to_B.get(current_node_id, float('inf'))

        if dA == float('inf') and dB == float('inf'):
            return (0.5, 0.0)  # 不可达 → 最大不确定

        denom = dA + dB
        if denom == 0:
            theta = 0.0 if dA == 0 else 1.0
            sigma_sq = 1.0
        else:
            theta = dA / denom
            sigma_sq = ((dA - dB) / denom) ** 2

        return (round(theta, 4), round(sigma_sq, 4))

    def decide(self, current_node_id: str) -> Tuple[str, float, float, Dict]:
        """执行一步拓扑相位决策."""
        theta, sigma_sq = self.compute_theta_and_sigma(current_node_id)

        previous_active = self.active
        switch_occurred = False
        delta_phi = 0.0

        # 滞回判决
        if self.active == 'A':
            if theta > 0.5 + self.hysteresis:
                self.active = 'B'
                switch_occurred = True
        else:
            if theta < 0.5 - self.hysteresis:
                self.active = 'A'
                switch_occurred = True

        if switch_occurred:
            self.switch_count += 1
            delta_phi = abs(theta - 0.5) * 2.0
            self.total_heat_tax += delta_phi

        record = {
            "step": len(self.history),
            "node": current_node_id,
            "theta": theta,
            "sigma_sq": sigma_sq,
            "dA": round(self.dist_to_A.get(current_node_id, -1), 2),
            "dB": round(self.dist_to_B.get(current_node_id, -1), 2),
            "decision": f"{previous_active}->{self.active}" if switch_occurred else f"stay_{self.active}",
            "delta_phi": round(delta_phi, 4),
        }
        self.history.append(record)

        audit = {
            "active": self.active,
            "theta": theta,
            "sigma_sq": sigma_sq,
            "dA": record['dA'],
            "dB": record['dB'],
            "switch": switch_occurred,
            "delta_phi_jump": round(delta_phi, 4),
            "total_heat_tax": round(self.total_heat_tax, 4),
            "hysteresis_band": (round(0.5 - self.hysteresis, 3), round(0.5 + self.hysteresis, 3)),
        }
        return self.active, theta, sigma_sq, audit

    def health(self) -> Dict:
        """健康诊断."""
        if not self.history:
            return {"status": "idle"}
        total = len(self.history)
        switch_rate = self.switch_count / total
        avg_theta = sum(r['theta'] for r in self.history) / total
        avg_sigma = sum(r['sigma_sq'] for r in self.history) / total

        issues = []
        if switch_rate > 0.3:
            issues.append(f"HIGH_SWITCH_RATE:{switch_rate:.1%}")
        if avg_sigma < 0.1:
            issues.append(f"PERSISTENT_AMBIGUITY:σ²={avg_sigma:.3f}")

        return {
            "status": "warning" if issues else "healthy",
            "total_steps": total,
            "switch_count": self.switch_count,
            "switch_rate": round(switch_rate, 3),
            "avg_theta": round(avg_theta, 3),
            "avg_sigma_sq": round(avg_sigma, 3),
            "total_heat_tax": round(self.total_heat_tax, 3),
            "issues": issues,
        }


# ═══ Layer 4: Unified Driver ═══

class UnifiedPhaseDriver:
    """
    统一相位驱动 — 自动选择拓扑θ或权重θ.

    当意义场拓扑已知且稳定 → 拓扑θ (更可靠)
    当拓扑未知或动态变化 → 权重θ (更灵活)
    """

    def __init__(self, field: Optional[MeaningFieldGraph] = None,
                 topology_engine: Optional[TopologicalPhaseEngine] = None,
                 weights: Optional[Dict[str, float]] = None):
        self.field = field
        self.topology_engine = topology_engine
        self.weights = weights or {'A': 0.5, 'B': 0.5}
        self.mode = 'topology' if topology_engine else 'weight'

    def mode_available(self) -> List[str]:
        modes = []
        if self.topology_engine:
            modes.append('topology')
        if self.weights:
            modes.append('weight')
        return modes

    def decide(self, current_node_id: Optional[str] = None,
               sigma_sq: float = 0.5) -> Dict:
        """统一决策: 自动选择模式."""
        if self.mode == 'topology' and self.topology_engine and current_node_id:
            active, theta, sig, audit = self.topology_engine.decide(current_node_id)
            return {"mode": "topology", "active": active, "theta": theta,
                    "sigma_sq": sig, "audit": audit}
        else:
            # 回退到权重θ
            from .conflict_phase_engine import ConflictPhaseEngine, AnchorPair, StableSubfield
            # 简化: 直接返回权重驱动结果
            w_diff = self.weights.get('B', 0.5) - self.weights.get('A', 0.5)
            raw = w_diff / (sigma_sq + 0.01)
            theta = 1.0 / (1.0 + math.exp(-raw))
            theta = max(0.0, min(1.0, theta))
            return {"mode": "weight", "active": 'A' if theta < 0.5 else 'B',
                    "theta": round(theta, 4), "sigma_sq": sigma_sq,
                    "audit": {"note": "fallback_weight_driven"}}


# ═══ Demo + Test ═══

def _build_demo_field() -> Tuple[MeaningFieldGraph, str, str]:
    """构建演示意义场: 公平 vs 贡献."""
    field = MeaningFieldGraph()

    # 公平盆地节点 (value-driven)
    fair_nodes = [
        MeaningNode("f1", "equality", stable_subfield_id="fair"),
        MeaningNode("f2", "need", stable_subfield_id="fair"),
        MeaningNode("f3", "dignity", stable_subfield_id="fair"),
        MeaningNode("f4", "universal_access", stable_subfield_id="fair"),
        MeaningNode("f5", "social_justice", stable_subfield_id="fair"),
        # 桥梁节点 (双盆地模糊区)
        MeaningNode("b1", "resource", stable_subfield_id=None),
        MeaningNode("b2", "distribution", stable_subfield_id=None),
    ]
    for n in fair_nodes:
        field.add_node(n)

    # 贡献盆地节点 (merit-driven)
    merit_nodes = [
        MeaningNode("m1", "contribution", stable_subfield_id="merit"),
        MeaningNode("m2", "excellence", stable_subfield_id="merit"),
        MeaningNode("m3", "efficiency", stable_subfield_id="merit"),
        MeaningNode("m4", "reward", stable_subfield_id="merit"),
        MeaningNode("m5", "meritocracy", stable_subfield_id="merit"),
    ]
    for n in merit_nodes:
        field.add_node(n)

    # 边: 公平盆地内部
    for a, b in [("f1","f2"),("f2","f3"),("f3","f4"),("f4","f5"),("f1","f4")]:
        field.add_edge(MeaningEdge(a, b))

    # 边: 贡献盆地内部
    for a, b in [("m1","m2"),("m2","m3"),("m3","m4"),("m4","m5"),("m1","m3")]:
        field.add_edge(MeaningEdge(a, b))

    # 边: 桥梁 (两个盆地通过b1,b2连接)
    field.add_edge(MeaningEdge("f5", "b1"))
    field.add_edge(MeaningEdge("b1", "b2"))
    field.add_edge(MeaningEdge("b2", "m1"))
    field.add_edge(MeaningEdge("f4", "b2"))  # 加强连接

    # 选择锚点
    builder = BasinBuilder(field)
    fair_seeds = ["f1","f2","f3","f4","f5"]
    merit_seeds = ["m1","m2","m3","m4","m5"]

    fair_basin = builder.build_basin(fair_seeds, set(merit_seeds), max_depth=5)
    merit_basin = builder.build_basin(merit_seeds, set(fair_seeds), max_depth=5)

    anchor_A = builder.select_anchor_v2(fair_basin)[0] or "f3"
    anchor_B = builder.select_anchor_v2(merit_basin)[0] or "m3"

    return field, anchor_A, anchor_B


def cmd_topophase(args_rest):
    """CLI: mssclaw topophase"""
    if not args_rest or args_rest[0] == "--help":
        print("mssclaw topophase — Topological Phase Engine (锚点拓扑选择+θ驱动)")
        print("  mssclaw topophase demo    # 演示: 公平 vs 贡献 (拓扑θ)")
        print("  mssclaw topophase test    # 测试套件")
        return

    if args_rest[0] == "demo":
        _demo_topophase()
    elif args_rest[0] == "test":
        _test_topophase()


def _demo_topophase():
    """演示拓扑相位机."""
    print("=" * 64)
    print("Topological Phase Engine — Fair vs Merit (Topology-Driven θ)")
    print("=" * 64)

    field, anchor_A, anchor_B = _build_demo_field()
    print(f"\n  Meaning Field: {len(field.nodes)} nodes, {sum(len(v) for v in field.adj.values())//2} edges")
    print(f"  Anchor A (fair): {anchor_A} ({field.nodes[anchor_A].label})")
    print(f"  Anchor B (merit): {anchor_B} ({field.nodes[anchor_B].label})")

    engine = TopologicalPhaseEngine(field, anchor_A, anchor_B, hysteresis=0.15)

    # 从公平盆地深处走到贡献盆地的路径
    path = ["f1", "f2", "f5", "b1", "b2", "m1", "m2", "m4", "m5"]
    print(f"\n  Path: {' → '.join(path)}")
    print(f"\n  {'Node':<6} {'dA':<6} {'dB':<6} {'θ':<8} {'σ²':<8} {'Decision':<12} {'Δφ':<6}")
    print("  " + "-" * 58)

    for nid in path:
        active, theta, sigma_sq, audit = engine.decide(nid)
        print(f"  {nid:<6} {audit['dA']:<6} {audit['dB']:<6} "
              f"{theta:<8} {sigma_sq:<8} {engine.history[-1]['decision']:<12} "
              f"{audit['delta_phi_jump']:<6}")

    print(f"\n  # Health: {json.dumps(engine.health(), indent=2)}")


def _test_topophase():
    """测试套件."""
    passed = 0
    total = 0

    # Test 1: 意义场构建
    total += 1
    field, anchor_A, anchor_B = _build_demo_field()
    assert len(field.nodes) == 12
    assert anchor_A in field.nodes
    assert anchor_B in field.nodes
    passed += 1
    print(f"  ✅ Test 1: 意义场构建 ({len(field.nodes)} nodes)")

    # Test 2: 最短拓扑距离
    total += 1
    dists = field.shortest_distances_from(anchor_A)
    assert dists[anchor_A] == 0.0
    assert dists[anchor_B] > 0  # 公共盆地应有路径
    passed += 1
    print(f"  ✅ Test 2: 拓扑距离 (A→A=0, A→B={dists[anchor_B]:.1f})")

    # Test 3: θ计算 — 靠近A
    total += 1
    engine = TopologicalPhaseEngine(field, anchor_A, anchor_B, hysteresis=0.15)
    theta, sigma = engine.compute_theta_and_sigma("f1")  # 公平盆地深处
    assert theta < 0.5, f"Near A → θ should be <0.5, got {theta}"
    passed += 1
    print(f"  ✅ Test 3: θ近A (f1: θ={theta}<0.5)")

    # Test 4: θ计算 — 靠近B
    total += 1
    theta_b, sigma_b = engine.compute_theta_and_sigma("m5")  # 贡献盆地深处
    assert theta_b > 0.5, f"Near B → θ should be >0.5, got {theta_b}"
    passed += 1
    print(f"  ✅ Test 4: θ近B (m5: θ={theta_b}>0.5)")

    # Test 5: θ计算 — 桥梁 (模糊)
    total += 1
    theta_br, sigma_br = engine.compute_theta_and_sigma("b1")
    assert abs(theta_br - 0.5) < 0.3, f"Bridge → θ near 0.5, got {theta_br}"
    passed += 1
    print(f"  ✅ Test 5: θ桥梁 (b1: θ={theta_br}≈0.5)")

    # Test 6: 滞回不抖动
    total += 1
    engine2 = TopologicalPhaseEngine(field, anchor_A, anchor_B, hysteresis=0.15)
    for _ in range(20):
        engine2.decide("b1")  # 模糊节点
    assert engine2.switch_count <= 2, f"Too many switches: {engine2.switch_count}"
    passed += 1
    print(f"  ✅ Test 6: 滞回防抖 ({engine2.switch_count} switches in 20)")

    # Test 7: 盆地锚点选择
    total += 1
    builder = BasinBuilder(field)
    fair_basin = builder.build_basin(["f1","f2","f3","f4","f5"], {"m1","m2","m3","m4","m5"})
    anchor, coreness = builder.select_anchor_v2(fair_basin)
    assert anchor != ""
    assert coreness > 0
    passed += 1
    print(f"  ✅ Test 7: 锚点选择 (anchor={anchor}, coreness={coreness})")

    # Test 8: σ²在深度盆底大(清晰)，在桥梁小(模糊)
    total += 1
    _, sig_deep = engine2.compute_theta_and_sigma("f1")
    _, sig_br = engine2.compute_theta_and_sigma("b1")
    assert sig_deep > sig_br, f"Deep basin σ² should be higher: {sig_deep} vs {sig_br}"
    passed += 1
    print(f"  ✅ Test 8: σ²清晰度 (deep={sig_deep} > bridge={sig_br})")

    print(f"\n  {passed}/{total} PASS")


if __name__ == "__main__":
    import sys
    cmd_topophase(sys.argv[1:])
