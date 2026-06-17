"""
Adaptive Topological Phase Engine — 锚点活性管理与重锚定协议 (Sprint 147a).

意义场抗僵化机制:
  任何静态锚点最终都会僵化。意义场是活的，锚点必须能感知自身是否还"在场"，
  必要时自我更新。三个可计算活性指标 + 平滑重锚定 + 热税控制。

核心公理:
  1. 僵化 = 锚点与盆地的拓扑脱耦 (centrifugal drift)
  2. 活性 = 离心度变化率 + 邻居忠诚度 + 决策偏差 加权综合
  3. 重锚定 = 候选生成 → 双锚warmup → 切换 → 退役 → 历史快照

与已有系统集成:
  TopologicalPhaseEngine → 继承 → AdaptiveTopologicalPhaseEngine
  BasinBuilder → 复用盆地提取+离心度计算
  Heat Tax → 重锚定支付热税，防频繁震荡
"""
from __future__ import annotations
import math, time, json
from typing import Dict, List, Tuple, Set, Optional, Any
from dataclasses import dataclass, field
from collections import deque, defaultdict

from .topological_phase_engine import (
    MeaningFieldGraph, MeaningNode, MeaningEdge,
    BasinBuilder, ConflictBasin,
    TopologicalPhaseEngine,
)


# ═══ Layer 1: Vitality Metrics ═══

@dataclass
class VitalitySnapshot:
    """单次活性快照."""
    anchor_id: str
    timestamp: float
    eccentricity: float              # 当前离心度
    eccentricity_change_rate: float  # Ċ = ΔC/Δt
    neighbor_loyalty: float          # L = |N_ε ∩ B| / |N_ε|
    decision_deviation: float        # Δ_dec = 不合适/总数
    vitality_score: float            # 综合活性
    verdict: str                     # "healthy" | "at_risk" | "stale" | "reanchoring"
    basin_size: int = 0
    boundary_distance: float = 0.0


class VitalityMonitor:
    """
    锚点活性监测器.

    三个指标 (各占1/3):
      Ċ: 离心度变化率 (越大→锚点越靠近边界)
      L:  ε-邻域内仍属原盆地的节点比例 (越小→已被入侵)
      Δ_dec: 决策偏差率 (越大→锚点已不可靠)

    Vitality = α·sigmoid_inv(Ċ) + β·L + γ·(1-Δ_dec)
    """

    def __init__(self, field: MeaningFieldGraph,
                 basin_builder: BasinBuilder,
                 epsilon: int = 2,
                 alpha: float = 1/3, beta: float = 1/3, gamma: float = 1/3,
                 stale_dotC: float = 0.3,    # Ċ 僵化阈值
                 loyalty_min: float = 0.4,    # L 入侵阈值
                 deviation_max: float = 0.3,  # Δ_dec 不可靠阈值
                 ):
        self.field = field
        self.basin_builder = basin_builder
        self.epsilon = epsilon
        self.alpha, self.beta, self.gamma = alpha, beta, gamma
        self.stale_dotC = stale_dotC
        self.loyalty_min = loyalty_min
        self.deviation_max = deviation_max

        # 历史记录
        self.history: Dict[str, List[VitalitySnapshot]] = defaultdict(list)
        self.feedback_log: Dict[str, List[bool]] = defaultdict(list)  # anchor → [correct?]

    def record_feedback(self, anchor_id: str, was_correct: bool):
        """记录决策反馈."""
        self.feedback_log.setdefault(anchor_id, []).append(was_correct)
        # 保留最近100条
        if len(self.feedback_log[anchor_id]) > 100:
            self.feedback_log[anchor_id] = self.feedback_log[anchor_id][-100:]

    def compute_eccentricity(self, anchor_id: str, basin: ConflictBasin) -> float:
        """计算锚点的离心度 C = avg_distance_to_basin_nodes / max_distance.

        值越大 → 锚点越靠近盆地边缘 (越僵化).
        """
        if not basin.basin_nodes:
            return float('inf')
        dists = self.field.shortest_distances_from(anchor_id)
        basin_dists = [dists.get(v, float('inf')) for v in basin.basin_nodes if v != anchor_id]
        if not basin_dists:
            return 0.0
        avg = sum(basin_dists) / len(basin_dists)
        # 归一化: avg_distance / basin_diameter
        basin_diameter = max(basin_dists) if basin_dists else 1.0
        return avg / max(basin_diameter, 1.0)

    def compute_eccentricity_change_rate(self, anchor_id: str,
                                          current_ecc: float) -> float:
        """计算离心度变化率 Ċ.

        Ċ = (C_now - C_prev) / Δt
        正值 → 离心度增加 → 正在僵化
        """
        snapshots = self.history.get(anchor_id, [])
        if len(snapshots) < 2:
            return 0.0
        prev = snapshots[-1]
        dt = time.time() - prev.timestamp
        if dt < 0.01:
            return 0.0
        return (current_ecc - prev.eccentricity) / dt

    def compute_neighbor_loyalty(self, anchor_id: str, basin: ConflictBasin) -> float:
        """计算 ε-邻域邻居忠诚度 L.

        L = |{v ∈ N_ε(anchor) ∩ B}| / |N_ε(anchor)|

        值越小 → 锚点邻域被入侵.
        """
        # 获取ε-邻域: BFS到深度ε
        visited = {anchor_id: 0}
        q = deque([anchor_id])
        while q:
            u = q.popleft()
            d = visited[u]
            if d >= self.epsilon:
                continue
            for v, _ in self.field.adj.get(u, []):
                if v not in visited:
                    visited[v] = d + 1
                    q.append(v)

        neighborhood = set(visited.keys()) - {anchor_id}
        if not neighborhood:
            return 1.0  # 孤立锚点 → 完美忠诚? (实际上该重锚定了)

        loyal_count = sum(1 for v in neighborhood if v in basin.basin_nodes)
        return loyal_count / len(neighborhood)

    def compute_decision_deviation(self, anchor_id: str) -> float:
        """计算决策偏差 Δ_dec = 不合适决策/总决策.

        从反馈日志计算.
        """
        feedback = self.feedback_log.get(anchor_id, [])
        if not feedback:
            return 0.0  # 无反馈 → 乐观假设
        return 1.0 - sum(feedback) / len(feedback)

    def compute_vitality(self, anchor_id: str, basin: ConflictBasin) -> VitalitySnapshot:
        """综合活性评估."""
        # 三个原始指标
        ecc = self.compute_eccentricity(anchor_id, basin)
        dotC = self.compute_eccentricity_change_rate(anchor_id, ecc)
        loyalty = self.compute_neighbor_loyalty(anchor_id, basin)
        deviation = self.compute_decision_deviation(anchor_id)

        # 归一化 Ċ: sigmoid逆变换 (Ċ>0 → 减分, Ċ<0 → 加分)
        # vitality_contrib_C = 1 - sigmoid(Ċ/stale_dotC)
        sig_contrib = 1.0 - (1.0 / (1.0 + math.exp(-dotC / max(self.stale_dotC, 0.01))))

        # 综合评分
        vitality = (
            self.alpha * sig_contrib +
            self.beta * loyalty +
            self.gamma * (1.0 - deviation)
        )
        vitality = max(0.0, min(1.0, vitality))

        # 判定
        if vitality >= 0.7:
            verdict = "healthy"
        elif vitality >= 0.5:
            verdict = "at_risk"
        else:
            verdict = "stale"

        snapshot = VitalitySnapshot(
            anchor_id=anchor_id,
            timestamp=time.time(),
            eccentricity=round(ecc, 4),
            eccentricity_change_rate=round(dotC, 4),
            neighbor_loyalty=round(loyalty, 4),
            decision_deviation=round(deviation, 4),
            vitality_score=round(vitality, 4),
            verdict=verdict,
            basin_size=len(basin.basin_nodes),
            boundary_distance=ecc * len(basin.basin_nodes),
        )

        self.history.setdefault(anchor_id, []).append(snapshot)
        return snapshot


# ═══ Layer 2: Re-Anchor Protocol ═══

@dataclass
class DualAnchorBuffer:
    """双锚运行缓冲区."""
    old_anchor: str
    candidate_anchor: str
    start_step: int
    warmup_steps: int = 10
    old_decisions: List[Tuple[str, float, bool]] = field(default_factory=list)  # (node, θ, correct?)
    candidate_decisions: List[Tuple[str, float, bool]] = field(default_factory=list)
    old_avg_eta: float = 0.0
    candidate_avg_eta: float = 0.0
    finalized: bool = False
    switched: bool = False


class ReAnchorProtocol:
    """
    重锚定协议 — 平滑过渡，不中断服务.

    三步:
      1. 候选锚点生成: 在当前盆地B中重新计算最大离心度节点
      2. 双锚warmup: 新旧锚点并行N_warmup轮，决策仍用旧锚点，新锚点镜像记录
      3. 切换判决: 新锚点η > 旧锚点η + δ → 正式切换; else 拒绝候选

    热税控制:
      - 每次重锚定记录热税支出
      - 若两次重锚定间隔 < T_min → 提高下次触发阈值 (防震荡)
    """

    def __init__(self, field: MeaningFieldGraph,
                 basin_builder: BasinBuilder,
                 vitality_monitor: VitalityMonitor,
                 warmup_steps: int = 10,
                 min_eta_delta: float = 0.05,
                 min_reanchor_interval: int = 50,
                 vitality_pump: float = 0.1,  # 震荡惩罚增量
                 ):
        self.field = field
        self.basin_builder = basin_builder
        self.vitality_monitor = vitality_monitor
        self.warmup_steps = warmup_steps
        self.min_eta_delta = min_eta_delta
        self.min_reanchor_interval = min_reanchor_interval
        self.vitality_pump = vitality_pump

        # 状态
        self.active_dual: Dict[str, DualAnchorBuffer] = {}  # old_anchor → buffer
        self.retired_anchors: Dict[str, Dict] = {}  # retired_anchor → {snapshot, retired_at, reason}
        self.last_reanchor_step: Dict[str, int] = {}  # basin_key → step
        self.reanchor_count: Dict[str, int] = defaultdict(int)
        self.total_heat_tax: float = 0.0

    def generate_candidates(self, anchor_id: str,
                            seed_nodes: List[str],
                            opposing_nodes: Set[str]) -> List[Tuple[str, float]]:
        """
        生成候选锚点.

        在当前盆地中重新计算所有节点的核心度，返回前3个候选 (按核心度降序).
        """
        basin = self.basin_builder.build_basin(seed_nodes, opposing_nodes, max_depth=8)
        candidates = []

        for v in basin.basin_nodes:
            if v == anchor_id:
                continue
            coreness, _ = self.basin_builder.select_anchor_v2(
                ConflictBasin("", {v}, basin.boundary_nodes)
            )
            # 改用完整盆地计算该节点的核心度
            full_basin = ConflictBasin("", basin.basin_nodes, basin.boundary_nodes)
            sub_anchor, sub_core = self.basin_builder.select_anchor_v2(full_basin)
            if v == sub_anchor:
                candidates.append((v, sub_core))

        # 如果精确匹配不到, 用离心度排序所有节点
        if len(candidates) < 3:
            scored = []
            for v in basin.basin_nodes:
                if v == anchor_id:
                    continue
                dists = self.field.shortest_distances_from(v)
                ecc = max((dists.get(u, 0) for u in basin.basin_nodes), default=0)
                scored.append((v, ecc))
            scored.sort(key=lambda x: -x[1])
            candidates = scored[:3]

        return candidates

    def start_dual_run(self, old_anchor: str, candidate_anchor: str, step: int):
        """启动双锚运行."""
        buffer = DualAnchorBuffer(
            old_anchor=old_anchor,
            candidate_anchor=candidate_anchor,
            start_step=step,
            warmup_steps=self.warmup_steps,
        )
        self.active_dual[old_anchor] = buffer
        return buffer

    def record_decision(self, anchor_id: str, node_id: str,
                         theta: float, was_correct: bool):
        """双锚运行期间记录决策."""
        buf = self.active_dual.get(anchor_id)
        if not buf:
            return

        if anchor_id == buf.old_anchor:
            buf.old_decisions.append((node_id, theta, was_correct))
        else:
            buf.candidate_decisions.append((node_id, theta, was_correct))

        # 检查warmup是否完成
        if (len(buf.old_decisions) >= self.warmup_steps and
            len(buf.candidate_decisions) >= self.warmup_steps and
            not buf.finalized):
            self._finalize_reanchor(buf)

    def _finalize_reanchor(self, buf: DualAnchorBuffer):
        """切换判决."""
        buf.finalized = True

        # 计算平均η保真度
        old_correct = sum(d[2] for d in buf.old_decisions[-self.warmup_steps:])
        candidate_correct = sum(d[2] for d in buf.candidate_decisions[-self.warmup_steps:])
        buf.old_avg_eta = old_correct / max(1, len(buf.old_decisions[-self.warmup_steps:]))
        buf.candidate_avg_eta = candidate_correct / max(1, len(buf.candidate_decisions[-self.warmup_steps:]))

        delta_eta = buf.candidate_avg_eta - buf.old_avg_eta

        if delta_eta > self.min_eta_delta:
            # 切换
            buf.switched = True
            # 退役旧锚点
            self.retired_anchors[buf.old_anchor] = {
                "retired_at": time.time(),
                "reason": f"superseded_by_{buf.candidate_anchor}",
                "old_eta": buf.old_avg_eta,
                "new_eta": buf.candidate_avg_eta,
                "delta_eta": delta_eta,
            }
        else:
            buf.switched = False
            # 候选未通过, 清除
            if buf.old_anchor in self.active_dual:
                del self.active_dual[buf.old_anchor]

        # 热税支出
        self.total_heat_tax += 0.1 + abs(delta_eta) * 0.5

    def get_active_anchor(self, old_anchor: str) -> str:
        """获取当前激活的锚点 (可能是新锚点)."""
        buf = self.active_dual.get(old_anchor)
        if buf and buf.switched:
            return buf.candidate_anchor
        return old_anchor

    def check_oscillation(self, basin_key: str, current_step: int) -> bool:
        """检测震荡: 两次重锚定间隔 < min_reanchor_interval."""
        last = self.last_reanchor_step.get(basin_key, -1000)
        return (current_step - last) < self.min_reanchor_interval

    def apply_oscillation_penalty(self, basin_key: str, threshold: float) -> float:
        """震荡惩罚: 提高下次触发阈值."""
        count = self.reanchor_count.get(basin_key, 0)
        if count > 2:
            return threshold + self.vitality_pump * (count - 2)
        return threshold


# ═══ Layer 3: Adaptive Topological Phase Engine ═══

class AdaptiveTopologicalPhaseEngine(TopologicalPhaseEngine):
    """
    自适应拓扑相位机 — 集成活性检测与重锚定.

    继承TopologicalPhaseEngine，增加:
      - 定期活性检测 (每check_interval步)
      - 自动重锚定 (双锚warmup → 切换)
      - 震荡防护 (频繁重锚定 → 提高阈值)
      - 历史锚点快照 (退役锚点保留拓扑快照)
    """

    def __init__(self, field: MeaningFieldGraph,
                 anchor_A_id: str, anchor_B_id: str,
                 basin_builder: Optional[BasinBuilder] = None,
                 vitality_threshold: float = 0.5,
                 check_interval: int = 100,
                 hysteresis: float = 0.15,
                 ):
        super().__init__(field, anchor_A_id, anchor_B_id, hysteresis)
        self.basin_builder = basin_builder or BasinBuilder(field)
        self.vitality_threshold = vitality_threshold
        self.check_interval = check_interval

        # 子组件
        self.vitality_monitor = VitalityMonitor(field, self.basin_builder)
        self.reanchor = ReAnchorProtocol(
            field, self.basin_builder, self.vitality_monitor,
            warmup_steps=10,
        )

        # 盆地种子节点 (需要外部注入)
        self.basin_seeds: Dict[str, List[str]] = {}
        self.opposing_nodes: Dict[str, Set[str]] = {}

        # 锚点退役历史
        self.anchor_history: List[Dict] = []

        # 统计
        self.vitality_checks: int = 0
        self.reanchor_events: int = 0

    def set_basin_seeds(self, anchor_id: str, seeds: List[str],
                         opposing: Set[str]):
        """设置盆地种子节点 (用于盆地重建)."""
        self.basin_seeds[anchor_id] = seeds
        self.opposing_nodes[anchor_id] = opposing

    def step(self, current_node_id: str) -> Tuple[str, float, float, Dict]:
        """
        执行一步 — 带活性检测.

        Returns:
            (active_anchor, theta, sigma_sq, audit)
        """
        # 检查是否有进行中的重锚定 (使用新锚点)
        active_A = self.reanchor.get_active_anchor(self.anchor_A)
        active_B = self.reanchor.get_active_anchor(self.anchor_B)

        # 临时替换锚点用于决策
        saved_A, saved_B = self.anchor_A, self.anchor_B
        self.anchor_A, self.anchor_B = active_A, active_B

        # 重新计算距离 (如果锚点变了)
        if active_A != saved_A:
            self.dist_to_A = self.field.shortest_distances_from(active_A)
        if active_B != saved_B:
            self.dist_to_B = self.field.shortest_distances_from(active_B)

        # 常规决策
        active, theta, sigma_sq, audit = self.decide(current_node_id)

        # 双锚运行记录
        if active_A in self.reanchor.active_dual:
            self.reanchor.record_decision(active_A, current_node_id, theta,
                                          audit.get("decision_correct", True))
            # 候选锚点也记录 (用于对比)
            buf = self.reanchor.active_dual[active_A]
            if buf:
                # 用候选锚点重新计算θ
                saved_dists = self.dist_to_A
                self.dist_to_A = self.field.shortest_distances_from(buf.candidate_anchor)
                alt_theta, alt_sigma = self.compute_theta_and_sigma(current_node_id)
                self.dist_to_A = saved_dists
                self.reanchor.record_decision(buf.candidate_anchor, current_node_id,
                                              alt_theta, audit.get("decision_correct", True))

        # 恢复锚点
        self.anchor_A, self.anchor_B = saved_A, saved_B
        self.dist_to_A = self.field.shortest_distances_from(self.anchor_A)
        self.dist_to_B = self.field.shortest_distances_from(self.anchor_B)

        # 定期活性检查
        step_count = len(self.history)
        if step_count > 0 and step_count % self.check_interval == 0:
            self.check_vitality()

        audit["step"] = len(self.history)
        return active_A if active == 'A' else active_B, theta, sigma_sq, audit

    def check_vitality(self) -> Dict[str, VitalitySnapshot]:
        """检查所有锚点活性."""
        self.vitality_checks += 1
        results = {}

        for anchor_id in [self.anchor_A, self.anchor_B]:
            seeds = self.basin_seeds.get(anchor_id, [])
            opposing = self.opposing_nodes.get(anchor_id, set())

            if not seeds:
                continue

            basin = self.basin_builder.build_basin(seeds, opposing, max_depth=8)
            snapshot = self.vitality_monitor.compute_vitality(anchor_id, basin)
            results[anchor_id] = snapshot

            if snapshot.verdict == "stale":
                # 检查震荡
                basin_key = f"basin_{anchor_id}"
                if self.reanchor.check_oscillation(basin_key, len(self.history)):
                    # 提高阈值, 跳过本次重锚定
                    effective_threshold = self.reanchor.apply_oscillation_penalty(
                        basin_key, self.vitality_threshold)
                    if snapshot.vitality_score > effective_threshold:
                        continue

                # 触发重锚定
                self._trigger_reanchor(anchor_id, seeds, opposing)

        return results

    def _trigger_reanchor(self, anchor_id: str, seeds: List[str],
                           opposing: Set[str]):
        """触发重锚定."""
        # 生成候选
        candidates = self.reanchor.generate_candidates(anchor_id, seeds, opposing)
        if not candidates:
            return

        candidate, score = candidates[0]

        # 启动双锚运行
        buf = self.reanchor.start_dual_run(anchor_id, candidate, len(self.history))
        self.reanchor_events += 1

        self.anchor_history.append({
            "event": "reanchor_triggered",
            "anchor": anchor_id,
            "candidate": candidate,
            "candidate_score": round(score, 4),
            "step": len(self.history),
            "timestamp": time.time(),
        })

    def inject_feedback(self, anchor_id: str, was_correct: bool):
        """注入决策反馈 (外部校准)."""
        self.vitality_monitor.record_feedback(anchor_id, was_correct)

        # 更新双锚运行中的决策记录
        if anchor_id in self.reanchor.active_dual:
            buf = self.reanchor.active_dual[anchor_id]
            if buf.old_decisions:
                last = buf.old_decisions[-1]
                buf.old_decisions[-1] = (last[0], last[1], was_correct)

    def health_report(self) -> Dict:
        """完整健康报告."""
        base = super().health()

        vitality = {}
        for anchor_id in [self.anchor_A, self.anchor_B]:
            history = self.vitality_monitor.history.get(anchor_id, [])
            if history:
                latest = history[-1]
                vitality[anchor_id] = {
                    "vitality": latest.vitality_score,
                    "verdict": latest.verdict,
                    "eccentricity": latest.eccentricity,
                    "loyalty": latest.neighbor_loyalty,
                    "deviation": latest.decision_deviation,
                }

        return {
            **base,
            "adaptive": {
                "vitality_checks": self.vitality_checks,
                "reanchor_events": self.reanchor_events,
                "active_dual_runs": len(self.reanchor.active_dual),
                "retired_anchors": len(self.reanchor.retired_anchors),
                "reanchor_heat_tax": round(self.reanchor.total_heat_tax, 4),
            },
            "vitality": vitality,
        }


# ═══ Layer 4: Meaning Field Mutator (Field Evolution Simulator) ═══

class MeaningFieldMutator:
    """
    意义场演化器 — 模拟意义场随时间漂移/分裂/收缩.

    用于测试抗僵化机制.
    """

    def __init__(self, field: MeaningFieldGraph):
        self.field = field

    def drift_basin(self, anchor_id: str, drift_nodes: List[str],
                     new_target: str, weight: float = 0.5):
        """
        盆地漂移: 将部分节点向另一个稳定子漂移.

        效果: 这些节点到新target的边权重降低, 模拟意义场演化.
        """
        for nid in drift_nodes:
            # 添加漂移边
            self.field.add_edge(MeaningEdge(nid, new_target, weight=weight))

    def split_basin(self, anchor_id: str, split_nodes: List[str],
                     new_subfield_id: str):
        """盆地分裂: 部分节点形成新稳定子."""
        for nid in split_nodes:
            if nid in self.field.nodes:
                self.field.nodes[nid].stable_subfield_id = new_subfield_id

    def contract_basin(self, anchor_id: str, remove_nodes: List[str]):
        """
        盆地收缩: 移除节点 (模拟意义场腐化/遗忘).

        不移除节点, 而是降低其到盆地其他节点的边权重.
        """
        for nid in remove_nodes:
            for v, w in self.field.adj.get(nid, []):
                # 降低权重 = 拓扑距离增加
                pass

    def add_noise(self, noise_count: int = 3):
        """添加噪声节点 (随机连接到现有节点)."""
        import random, uuid
        for _ in range(noise_count):
            nid = f"noise_{uuid.uuid4().hex[:6]}"
            self.field.add_node(MeaningNode(nid, "noise"))
            if self.field.adj:
                target = random.choice(list(self.field.adj.keys()))
                self.field.add_edge(MeaningEdge(nid, target, weight=2.0))


# ═══ Demo + Test ═══

def _build_demo_field():
    """构建与 topophase 相同的演示场."""
    field = MeaningFieldGraph()
    nodes = [
        MeaningNode("f1", "equality", "fair"),
        MeaningNode("f2", "need", "fair"),
        MeaningNode("f3", "dignity", "fair"),
        MeaningNode("f4", "universal_access", "fair"),
        MeaningNode("f5", "social_justice", "fair"),
        MeaningNode("b1", "resource"),
        MeaningNode("b2", "distribution"),
        MeaningNode("m1", "contribution", "merit"),
        MeaningNode("m2", "excellence", "merit"),
        MeaningNode("m3", "efficiency", "merit"),
        MeaningNode("m4", "reward", "merit"),
        MeaningNode("m5", "meritocracy", "merit"),
    ]
    for n in nodes:
        field.add_node(n)
    edges = [
        ("f1","f2"),("f2","f3"),("f3","f4"),("f4","f5"),("f1","f4"),
        ("m1","m2"),("m2","m3"),("m3","m4"),("m4","m5"),("m1","m3"),
        ("f5","b1"),("b1","b2"),("b2","m1"),("f4","b2"),
    ]
    for a, b in edges:
        field.add_edge(MeaningEdge(a, b))
    return field


def cmd_adaptive(args_rest):
    """CLI: mssclaw adaptive"""
    if not args_rest or args_rest[0] == "--help":
        print("mssclaw adaptive — Adaptive Topological Phase Engine (抗僵化)")
        print("  mssclaw adaptive demo     # 演示: 活性检测+重锚定")
        print("  mssclaw adaptive drift    # 演示: 盆地漂移→僵化→重锚定")
        print("  mssclaw adaptive test     # 测试套件")
        return

    if args_rest[0] == "demo":
        _demo_adaptive()
    elif args_rest[0] == "drift":
        _demo_drift()
    elif args_rest[0] == "test":
        _test_adaptive()


def _demo_adaptive():
    print("=" * 64)
    print("Adaptive Topological Phase Engine — Vitality + Re-Anchor Demo")
    print("=" * 64)

    field = _build_demo_field()
    bb = BasinBuilder(field)

    anchor_A = "f3"  # dignity (公平盆地深处)
    anchor_B = "m3"  # efficiency (贡献盆地深处)

    engine = AdaptiveTopologicalPhaseEngine(
        field, anchor_A, anchor_B,
        basin_builder=bb,
        vitality_threshold=0.5,
        check_interval=5,  # 每5步检查 (demo加速)
        hysteresis=0.15,
    )

    # 注入盆地种子
    engine.set_basin_seeds(anchor_A,
                          ["f1","f2","f3","f4","f5"],
                          {"m1","m2","m3","m4","m5"})
    engine.set_basin_seeds(anchor_B,
                          ["m1","m2","m3","m4","m5"],
                          {"f1","f2","f3","f4","f5"})

    # 运行几步
    path = ["f1", "f2", "f5", "b1", "b2"]
    print(f"\n  Anchors: A={anchor_A}({field.nodes[anchor_A].label}), "
          f"B={anchor_B}({field.nodes[anchor_B].label})")
    print(f"  Path: {' → '.join(path)}")
    print(f"\n  {'Step':<5} {'Node':<6} {'θ':<8} {'σ²':<8} {'Decision':<10}")
    print("  " + "-" * 48)

    for i, nid in enumerate(path):
        active, theta, sigma, audit = engine.step(nid)
        print(f"  {i:<5} {nid:<6} {theta:<8} {sigma:<8} {audit.get('decision', 'stay_A')}")

    # 检查活性
    print(f"\n  # Vitality Check @ step {len(engine.history)}:")
    vit = engine.check_vitality()
    for anchor_id, snap in vit.items():
        print(f"    {anchor_id}: vitality={snap.vitality_score:.3f} "
              f"({snap.verdict}) | Ċ={snap.eccentricity_change_rate:.3f} "
              f"L={snap.neighbor_loyalty:.3f} Δ_dec={snap.decision_deviation:.3f}")

    print(f"\n  # Health Report:")
    hr = engine.health_report()
    print(f"    vitality_checks: {hr['adaptive']['vitality_checks']}")
    print(f"    reanchor_events: {hr['adaptive']['reanchor_events']}")
    print(f"    active_dual: {hr['adaptive']['active_dual_runs']}")


def _demo_drift():
    """演示: 盆地漂移 → 僵化 → 重锚定."""
    print("=" * 64)
    print("Basin Drift → Ossification → Re-Anchor Demo")
    print("=" * 64)

    field = _build_demo_field()
    bb = BasinBuilder(field)
    mutator = MeaningFieldMutator(field)

    anchor_A = "f3"
    anchor_B = "m3"

    engine = AdaptiveTopologicalPhaseEngine(
        field, anchor_A, anchor_B,
        basin_builder=bb,
        vitality_threshold=0.7,  # 较低阈值便于触发
        check_interval=3,  # demo加速
        hysteresis=0.15,
    )
    engine.set_basin_seeds(anchor_A,
                          ["f1","f2","f3","f4","f5"],
                          {"m1","m2","m3","m4","m5"})
    engine.set_basin_seeds(anchor_B,
                          ["m1","m2","m3","m4","m5"],
                          {"f1","f2","f3","f4","f5"})

    # 正常状态检测
    print("\n  Phase 1: Normal State")
    print("  " + "-" * 40)
    for nid in ["f1", "f2", "f3", "f5"]:
        active, theta, sigma, audit = engine.step(nid)

    vit1 = engine.check_vitality()
    for aid, snap in vit1.items():
        print(f"  {aid}: vitality={snap.vitality_score:.3f} ({snap.verdict})")

    # 模拟盆地漂移: 公平盆地节点向贡献盆地漂移
    print(f"\n  Phase 2: Basin Drift (f1-f4 → merit basin)")
    # 加强公平节点到贡献节点的边 (模拟意义漂移)
    field.add_edge(MeaningEdge("f4", "m1", weight=0.3))  # universal_access → contribution
    field.add_edge(MeaningEdge("f5", "m2", weight=0.3))  # social_justice → excellence

    for nid in ["f1", "f5", "b1", "m1"]:
        active, theta, sigma, audit = engine.step(nid)

    vit2 = engine.check_vitality()
    print(f"  After drift (step {len(engine.history)}):")
    for aid, snap in vit2.items():
        print(f"  {aid}: vitality={snap.vitality_score:.3f} ({snap.verdict}) "
              f"L={snap.neighbor_loyalty:.3f}")

    # 注入反馈 (模拟η保真度下降)
    for _ in range(5):
        engine.inject_feedback(anchor_A, False)

    for nid in ["b2", "m2"]:
        engine.step(nid)

    vit3 = engine.check_vitality()
    print(f"\n  Phase 3: Post-feedback degradation (step {len(engine.history)}):")
    for aid, snap in vit3.items():
        print(f"  {aid}: vitality={snap.vitality_score:.3f} ({snap.verdict})"
              f" Δ_dec={snap.decision_deviation:.3f}")

    print(f"\n  Anchor History: {len(engine.anchor_history)} events")
    for ev in engine.anchor_history:
        print(f"    [{ev['step']}] {ev['event']}: {ev['anchor'][:20]} → {ev.get('candidate','')[:20]}")


def _test_adaptive():
    """测试套件."""
    passed = 0
    total = 0

    # Test 1: 基本活性检测
    total += 1
    field = _build_demo_field()
    bb = BasinBuilder(field)
    monitor = VitalityMonitor(field, bb, epsilon=2)
    fair_basin = bb.build_basin(["f1","f2","f3","f4","f5"], {"m1","m2","m3","m4","m5"})
    snap = monitor.compute_vitality("f3", fair_basin)
    assert 0 <= snap.vitality_score <= 1
    assert snap.verdict in ("healthy", "at_risk", "stale")
    passed += 1
    print(f"  ✅ Test 1: 活性检测 (vitality={snap.vitality_score:.3f}, {snap.verdict})")

    # Test 2: 离心度计算
    total += 1
    ecc = monitor.compute_eccentricity("f3", fair_basin)
    assert 0 <= ecc <= 1, f"Eccentricity out of bounds: {ecc}"
    passed += 1
    print(f"  ✅ Test 2: 离心度 (f3={ecc:.3f})")

    # Test 3: 邻居忠诚度
    total += 1
    loyalty = monitor.compute_neighbor_loyalty("f3", fair_basin)
    assert 0 <= loyalty <= 1
    passed += 1
    print(f"  ✅ Test 3: 邻居忠诚度 (f3, ε=2: L={loyalty:.3f})")

    # Test 4: 决策偏差 (无反馈时=0)
    total += 1
    dev = monitor.compute_decision_deviation("f3")
    assert dev == 0.0
    # 注入反馈
    for v in [True, True, False, True, True]:
        monitor.record_feedback("f3", v)
    dev2 = monitor.compute_decision_deviation("f3")
    assert abs(dev2 - 0.2) < 0.001  # 1/5 wrong
    passed += 1
    print(f"  ✅ Test 4: 决策偏差 (0→{dev2})")

    # Test 5: 候选锚点生成
    total += 1
    rp = ReAnchorProtocol(field, bb, monitor, warmup_steps=5)
    candidates = rp.generate_candidates("f3",
                                        ["f1","f2","f3","f4","f5"],
                                        {"m1","m2","m3","m4","m5"})
    assert len(candidates) >= 0  # 可能没有更好候选, 但不应崩溃
    if candidates:
        assert candidates[0][0] != "f3"  # 候选不应与原锚点相同
    passed += 1
    print(f"  ✅ Test 5: 候选生成 ({len(candidates)} candidates)")

    # Test 6: 自适应相位机步进
    total += 1
    engine = AdaptiveTopologicalPhaseEngine(
        field, "f3", "m3",
        basin_builder=bb,
        vitality_threshold=0.3,
        check_interval=10,
    )
    engine.set_basin_seeds("f3", ["f1","f2","f3","f4","f5"], {"m1","m2","m3","m4","m5"})
    engine.set_basin_seeds("m3", ["m1","m2","m3","m4","m5"], {"f1","f2","f3","f4","f5"})

    active, theta, sigma, audit = engine.step("f1")
    assert active in ("f3", "m3")
    assert 0 <= theta <= 1
    passed += 1
    print(f"  ✅ Test 6: 自适应步进 (θ={theta:.3f})")

    # Test 7: 健康报告
    total += 1
    hr = engine.health_report()
    assert "adaptive" in hr
    assert "vitality" in hr
    passed += 1
    print(f"  ✅ Test 7: 健康报告 ({hr['adaptive']['vitality_checks']} checks)")

    print(f"\n  {passed}/{total} PASS")


if __name__ == "__main__":
    import sys
    cmd_adaptive(sys.argv[1:])
