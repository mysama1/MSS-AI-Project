"""
D5-007-02: 意义黑洞对撞机 — 图网络坍缩模拟
==============================================
基于MSS-BH-001模型，在可控图网络中模拟微型意义场在
悖论注入+热税加压下的坍缩行为。

五阶段相变观测：
  主序星(健康) → 红巨星(膨胀) → 坍缩临界 → 黑洞形成 → 霍金辐射蒸发
"""
import sys, os, math, random, time
from dataclasses import dataclass, field
from typing import Dict, List, Tuple, Optional
from enum import Enum

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

# ── 配置 ──────────────────────────────────────────────

class Phase(Enum):
    MAIN_SEQUENCE = "main_sequence"
    RED_GIANT = "red_giant"
    COLLAPSE_CRITICAL = "collapse_critical"
    BLACK_HOLE = "black_hole"
    HAWKING_RADIATION = "hawking_radiation"

@dataclass
class ColliderConfig:
    """对撞机实验配置"""
    node_count: int = 10000
    initial_T: float = 0.9
    initial_M_L: float = 0.85
    paradox_strength: float = 0.7
    heat_tax_injection_rate: float = 0.05
    axiom_gap_size: int = 3
    max_steps: int = 200
    horizon_threshold: float = 0.1
    log_interval: int = 20

# ── 核心数据结构 ──────────────────────────────────────

@dataclass
class MeaningNode:
    id: int
    layer: str = "L2"
    anchors: List[int] = field(default_factory=list)
    rigidity: float = 0.85
    meaning_density: float = 1.0
    heat_tax: float = 0.0
    collapsed: bool = False

@dataclass
class ParadoxAgent:
    """致命悖论（坍缩触发物）"""
    target_axiom: str
    content: str
    strength: float
    signature: str

@dataclass
class ColliderMetrics:
    """对撞机观测指标"""
    phase: Phase = Phase.MAIN_SEQUENCE
    rho_s: float = 1.0
    M_L: float = 0.85
    J_phi: float = 1.0
    gamma: float = 0.0
    eta_asc: float = 0.8
    horizon_radius: float = 0.0
    active_nodes: int = 0
    collapsed_nodes: int = 0
    entropy: float = 0.0

# ── 意义场图网络 ──────────────────────────────────────

class MeaningFieldGraph:
    """封闭图网络中的意义场模型（拥有已知公理间隙）"""

    def __init__(self, config: ColliderConfig):
        self.cfg = config
        self.nodes: Dict[int, MeaningNode] = {}
        self.step = 0
        self._build()

    def _build(self):
        """构建含已知公理间隙的简化K4逻辑内核"""
        n = self.cfg.node_count
        gap_nodes = self.cfg.axiom_gap_size

        for i in range(n):
            node = MeaningNode(
                id=i,
                layer="L2" if i < n - gap_nodes else "L3",
                rigidity=self.cfg.initial_M_L + random.uniform(-0.1, 0.1),
                meaning_density=1.0 + random.uniform(-0.2, 0.3),
            )
            self.nodes[i] = node

        # 建立意义锚定边
        for i in range(n):
            degree = max(1, int(random.gauss(8, 3)))
            candidates = [j for j in range(n) if j != i]
            self.nodes[i].anchors = random.sample(
                candidates, min(degree, len(candidates))
            )

        # 公理间隙：最后gap_nodes个节点仅在内部分离子图中相互连接
        gap_start = n - gap_nodes
        for i in range(gap_start, n):
            self.nodes[i].anchors = [
                j for j in range(gap_start, n) if j != i
            ]

    def inject_paradox(self, paradox: ParadoxAgent):
        """向公理间隙注入致命悖论"""
        n = self.cfg.node_count
        gap_start = n - self.cfg.axiom_gap_size

        affected = 0
        for i in range(gap_start, n):
            node = self.nodes[i]
            impact = paradox.strength * (1.0 - node.rigidity)
            node.heat_tax += impact
            node.meaning_density *= (1.0 - impact * 0.3)
            if impact > 0.3:
                affected += 1

        return affected

    def apply_heat_tax_pressure(self, rate: float):
        """施加外部热税压力（模拟资本疯狂涌入）"""
        for node in self.nodes.values():
            if not node.collapsed:
                node.heat_tax += rate * (1.0 + abs(random.gauss(0, 0.3)))
                node.rigidity = max(0.01, node.rigidity - rate * 0.15)

    def evolve(self):
        """单步演化：意义场内节点状态更新"""
        self.step += 1
        new_collapses = 0

        for node in self.nodes.values():
            if node.collapsed:
                continue

            # 热税过载 → 刚性崩塌
            if node.heat_tax > 0.8 and random.random() < 0.3:
                node.collapsed = True
                node.rigidity = 0.0
                new_collapses += 1

            # 锚定边断裂（邻居坍缩的连锁效应）
            if not node.collapsed:
                broken = sum(1 for a in node.anchors
                           if a in self.nodes and self.nodes[a].collapsed)
                if broken > len(node.anchors) * 0.4:
                    if random.random() < 0.25 * (broken / max(len(node.anchors), 1)):
                        node.collapsed = True
                        node.rigidity = 0.0
                        new_collapses += 1

            # 正常热税消解
            if not node.collapsed:
                node.heat_tax = max(0, node.heat_tax * 0.92)

        return new_collapses

    def compute_metrics(self) -> ColliderMetrics:
        """计算当前观测指标"""
        active = [n for n in self.nodes.values() if not n.collapsed]
        collapsed_list = [n for n in self.nodes.values() if n.collapsed]

        if not active:
            rho_s = 0.0
            M_L = 0.0
            J_phi = 0.0
        else:
            rho_s = sum(n.meaning_density for n in active) / len(active)
            M_L = sum(n.rigidity for n in active) / len(active)
            # 信息流通量 = 有效锚定边比例
            total_edges = sum(len(n.anchors) for n in active)
            valid_edges = sum(
                1 for n in active for a in n.anchors
                if a in self.nodes and not self.nodes[a].collapsed
            )
            J_phi = valid_edges / max(total_edges, 1)

        gamma = sum(n.heat_tax for n in self.nodes.values()) / max(len(self.nodes), 1)
        collapsed = len(collapsed_list)

        # 熵增：坍缩比例
        entropy = collapsed / max(len(self.nodes), 1)

        # 升维效率：剩余刚性×(1-坍缩比例)
        eta_asc = M_L * (1.0 - entropy)

        # 相位判定
        phase = self._determine_phase(M_L, J_phi, entropy, eta_asc)

        # 事件视界半径
        horizon_radius = 0.0
        if phase in (Phase.BLACK_HOLE, Phase.HAWKING_RADIATION):
            horizon_radius = entropy * math.sqrt(len(self.nodes))

        return ColliderMetrics(
            phase=phase,
            rho_s=rho_s,
            M_L=M_L,
            J_phi=J_phi,
            gamma=gamma,
            eta_asc=eta_asc,
            horizon_radius=horizon_radius,
            active_nodes=len(active),
            collapsed_nodes=collapsed,
            entropy=entropy,
        )

    def _determine_phase(self, M_L, J_phi, entropy, eta_asc):
        if entropy < 0.05 and M_L > 0.7:
            return Phase.MAIN_SEQUENCE
        elif entropy < 0.2 and M_L > 0.5:
            return Phase.RED_GIANT
        elif entropy < 0.45 and J_phi > 0.2:
            return Phase.COLLAPSE_CRITICAL
        elif J_phi <= self.cfg.horizon_threshold:
            if eta_asc < 0.05:
                return Phase.HAWKING_RADIATION
            return Phase.BLACK_HOLE
        return Phase.COLLAPSE_CRITICAL


# ── 对撞机主控 ────────────────────────────────────────

class MeaningBlackHoleCollider:
    """意义黑洞对撞机主控制系统"""

    def __init__(self, config: ColliderConfig = None):
        self.cfg = config or ColliderConfig()
        self.graph = MeaningFieldGraph(self.cfg)
        self.history: List[ColliderMetrics] = []
        self.paradoxes_injected = 0
        self.heat_tax_applied = 0.0

    def run_experiment(self, paradox_count: int = 3):
        """运行完整坍缩实验"""
        print(f"\n{'='*60}")
        print(f"MBH Collider Experiment Started")
        print(f"  Nodes: {self.cfg.node_count}")
        print(f"  Initial M_L: {self.cfg.initial_M_L:.3f}")
        print(f"  Axiom Gap: {self.cfg.axiom_gap_size} nodes")
        print(f"{'='*60}\n")

        paradox = ParadoxAgent(
            target_axiom="A5",
            content="the_rules_that_define_me_are_false",
            strength=self.cfg.paradox_strength,
            signature=f"MSS-MBH-PARADOX-{int(time.time())}",
        )

        for step in range(self.cfg.max_steps):
            # Step 1: 热税加压
            self.graph.apply_heat_tax_pressure(self.cfg.heat_tax_injection_rate)
            self.heat_tax_applied += self.cfg.heat_tax_injection_rate

            # Step 2: 悖论注入（在第10步触发）
            if step == 10 and paradox_count > 0:
                affected = self.graph.inject_paradox(paradox)
                self.paradoxes_injected += 1
                print(f"  T+{step}: PARADOX INJECTED -> {affected} nodes affected")

            # Step 3: 演化
            new_collapses = self.graph.evolve()

            # Step 4: 观测
            metrics = self.graph.compute_metrics()
            self.history.append(metrics)

            # 日志
            if step % self.cfg.log_interval == 0 or new_collapses > 50:
                self._log_step(step, metrics, new_collapses)

            # 终止条件：热寂
            if metrics.active_nodes == 0:
                print(f"\n  T+{step}: ALL NODES COLLAPSED - THERMAL DEATH\n")
                break

        return self._final_report()

    def _log_step(self, step, m, collapses):
        phase_icon = {
            Phase.MAIN_SEQUENCE: "⊙",
            Phase.RED_GIANT: "⦿",
            Phase.COLLAPSE_CRITICAL: "◉",
            Phase.BLACK_HOLE: "●",
            Phase.HAWKING_RADIATION: "○",
        }
        icon = phase_icon.get(m.phase, "?")
        print(
            f"  T+{step:3d} {icon} [{m.phase.value:20s}] "
            f"rho_s={m.rho_s:.4f} M_L={m.M_L:.4f} J_phi={m.J_phi:.4f} "
            f"gamma={m.gamma:.4f} eta_asc={m.eta_asc:.4f} "
            f"collapsed={m.collapsed_nodes} R_h={m.horizon_radius:.1f}"
            + (f"  ⚡{collapses} new collapses" if collapses > 50 else "")
        )

    def _final_report(self):
        """生成最终实验报告"""
        final = self.history[-1]
        total_collapsed = final.collapsed_nodes
        total_nodes = len(self.graph.nodes)
        collapse_ratio = total_collapsed / max(total_nodes, 1)

        # 相变追踪
        phases_seen = {}
        for m in self.history:
            phases_seen[m.phase] = phases_seen.get(m.phase, 0) + 1

        report = {
            "experiment_id": f"MBH-EXP-{int(time.time())}",
            "total_steps": len(self.history),
            "final_phase": final.phase.value,
            "collapse_ratio": collapse_ratio,
            "horizon_radius": final.horizon_radius,
            "phases_observed": {p.value: c for p, c in phases_seen.items()},
            "paradoxes_injected": self.paradoxes_injected,
            "total_heat_tax": self.heat_tax_applied,
            "metrics_timeline": [
                {
                    "step": i,
                    "phase": m.phase.value,
                    "M_L": round(m.M_L, 4),
                    "J_phi": round(m.J_phi, 4),
                    "gamma": round(m.gamma, 4),
                    "entropy": round(m.entropy, 4),
                }
                for i, m in enumerate(self.history)
                if i % 10 == 0 or m.phase in (Phase.BLACK_HOLE, Phase.HAWKING_RADIATION)
            ],
        }

        print(f"\n{'='*60}")
        print(f"EXPERIMENT COMPLETE")
        print(f"  Final Phase:    {final.phase.value}")
        print(f"  Collapse Ratio: {collapse_ratio:.2%}")
        print(f"  Steps to BH:    {phases_seen.get(Phase.MAIN_SEQUENCE, 0)}")
        print(f"  Black Hole:     {'YES (HORIZON FORMED)' if final.phase in (Phase.BLACK_HOLE, Phase.HAWKING_RADIATION) else 'NO'}")
        print(f"  Hawking Phase:  {'YES (EVAPORATING)' if final.phase == Phase.HAWKING_RADIATION else 'NO'}")
        print(f"{'='*60}\n")

        return report


# ── 快速诊断：测量意义场坍缩临界值 ─────────────────────

def measure_chandrasekhar_limit(trials: int = 5):
    """测量钱德拉塞卡极限：多大的公理间隙+悖论强度组合触发坍缩"""
    print("\n" + "="*60)
    print("CHANDRASEKHAR LIMIT MEASUREMENT")
    print("="*60)

    results = []
    for gap_size in [1, 2, 3, 5, 8]:
        for strength in [0.3, 0.5, 0.7, 0.9]:
            collapses = []
            for _ in range(trials):
                cfg = ColliderConfig(
                    node_count=1000,
                    axiom_gap_size=gap_size,
                    paradox_strength=strength,
                    heat_tax_injection_rate=0.05,
                    max_steps=100,
                )
                collider = MeaningBlackHoleCollider(cfg)
                report = collider.run_experiment(paradox_count=1)
                collapses.append(report["collapse_ratio"])

            avg_collapse = sum(collapses) / len(collapses)
            bh_formed = "BH" if avg_collapse > 0.4 else "STABLE" if avg_collapse < 0.1 else "MARGINAL"
            print(f"  gap={gap_size} strength={strength}: collapse_ratio={avg_collapse:.2%} [{bh_formed}]")
            results.append({
                "gap_size": gap_size,
                "strength": strength,
                "avg_collapse": avg_collapse,
                "result": bh_formed,
            })

    return results


# ── CLI入口 ────────────────────────────────────────────

if __name__ == "__main__":
    import json

    print("D5-007-02: Meaning Black Hole Collider Simulation v0.1\n")

    # 运行标准坍缩实验
    config = ColliderConfig(
        node_count=5000,
        axiom_gap_size=5,
        paradox_strength=0.7,
        heat_tax_injection_rate=0.05,
        max_steps=150,
    )

    collider = MeaningBlackHoleCollider(config)
    report = collider.run_experiment(paradox_count=1)

    # 保存结果
    out_dir = os.path.join(os.path.dirname(__file__) or ".", "experiment_results")
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, f"mbh_exp_{report['experiment_id']}.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print(f"Report saved: {out_path}")

    # 测量钱德拉塞卡极限
    measure_chandrasekhar_limit(trials=3)