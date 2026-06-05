"""
D5-007-06: 四大应用原型
=========================================
基于D5-007-02模拟+D5-007-03隔离+D5-007-04集成+D5-005-03升维，交付四大工程化应用原型。

1. 悖论熔断器 (Paradox Circuit Breaker) — 已有 D5-007-03
2. 意义势能对冲 (Meaning Potential Hedge) — 新增
3. 终极逻辑防火墙 (Ultimate Logic Firewall) — 新增
4. 热税垃圾焚化炉 (Heat Tax Incinerator) — 新增

每个原型独立可调用，共享底层意义场模拟引擎。
"""
import sys, os, time, math
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
from enum import Enum

sys.path.insert(0, os.path.dirname(__file__))

# ── 复制微型图网络用于应用层 ──────────────────────────

class MiniNode:
    def __init__(self, nid: int, T: float = 0.5, gap_size: int = 0):
        self.id = nid
        self.T = T
        self.gap_size = gap_size
        self.M_L = 0.7
        self.gamma = 0.0
        self.collapsed = False
        self.neighbors = []

class MiniGraph:
    def __init__(self, n_nodes: int = 100, gap_size: int = 3):
        self.nodes = {i: MiniNode(i, T=0.5 + 0.4*(i/n_nodes), gap_size=gap_size) for i in range(n_nodes)}
        for i in range(n_nodes):
            for j in range(max(0,i-3), min(n_nodes,i+4)):
                if i != j:
                    self.nodes[i].neighbors.append(j)
        self.gap_indices = [n_nodes//3, 2*n_nodes//3]
        for gi in self.gap_indices:
            self.nodes[gi].gap_size = gap_size
            self.nodes[gi].M_L = 0.3

    def compute_metrics(self):
        active = [n for n in self.nodes.values() if not n.collapsed]
        M_L = sum(n.M_L for n in active) / max(1, len(active))
        T = sum(n.T for n in active) / max(1, len(active))
        gamma = sum(n.gamma for n in active) / max(1, len(active))
        return {"active": len(active), "total": len(self.nodes), "M_L": M_L, "T": T, "gamma": gamma}

    def inject_paradox(self, strength: float = 0.7):
        affected = 0
        for gi in self.gap_indices:
            node = self.nodes[gi]
            if not node.collapsed:
                node.gamma += strength * node.gap_size * 0.1
                if node.gamma > 0.8:
                    node.collapsed = True
                    affected += 1
                    for nb in node.neighbors:
                        self.nodes[nb].gamma += 0.15
                        if self.nodes[nb].gamma > 0.9:
                            self.nodes[nb].collapsed = True
        return affected

    def apply_heat_tax(self, rate: float = 0.03):
        for n in self.nodes.values():
            if not n.collapsed:
                n.gamma = min(1.0, n.gamma + rate)

    def evolve(self, steps: int = 10):
        cascade_events = []
        for _ in range(steps):
            self.apply_heat_tax(0.03)
            for n in self.nodes.values():
                if n.gamma > 0.75 and not n.collapsed:
                    n.collapsed = True
                    cascade_events.append(n.id)
                    for nb in n.neighbors:
                        self.nodes[nb].gamma += 0.1
        return cascade_events


# ============================================================
# 原型一：悖论熔断器（已有 D5-007-03，此处为轻量独立封装）
# ============================================================

class ParadoxDetector:
    """扫描输入信号，检测悖论特征"""
    SIGNATURES = {
        "self_reference": ["这句话是假的", "self-referential", "self referential"],
        "axiom_attack": ["公理不成立", "axiom is false", "A5不成立"],
        "incompleteness": ["不完备", "incompleteness", "cannot prove", "Gödel"],
        "level_confusion": ["层级混淆", "level confusion", "同一层"],
        "circular": ["循环定义", "circular definition"],
    }

    def scan(self, content: str) -> List[str]:
        detected = []
        for sig_type, patterns in self.SIGNATURES.items():
            for p in patterns:
                if p.lower() in content.lower():
                    detected.append(sig_type)
                    break
        return detected

    def severity(self, content: str) -> float:
        """悖论严重度 0-1"""
        types = self.scan(content)
        if not types: return 0.0
        base = 0.3 * len(types)
        return min(1.0, base)


# ============================================================
# 原型二：意义势能对冲
# ============================================================

class MeaningPotentialHedge:
    """
    意义势能对冲器
    
    原理：当MBH事件视界尚未完全闭合（η_asc > 0）时，
    注入外部高T意义吸引子（T > T_horizon）撕裂未闭合视界。
    
    应用：反制正在形成但尚未稳定的意义黑洞——如个体滑向认知坍缩边缘时。
    """

    def __init__(self, attractor_T: float = 0.95):
        self.attractor_T = attractor_T  # 外部高T锚点的调谐度
        self.attractor_points = [
            {"name": "A1_meaning_anchor", "T": attractor_T, "axiom": "A1"},
            {"name": "A2_information_slice", "T": attractor_T, "axiom": "A2"},
            {"name": "A5_rsca_ground", "T": attractor_T, "axiom": "A5"},
        ]
        self.hedge_history = []

    def compute_hedge_force(self, horizon_T: float, horizon_radius: float) -> float:
        """
        意义势能差驱动对冲力
        
        F_hedge = k · (T_attractor - T_horizon) · R_horizon^{-2}
        
        当 T_attractor >> T_horizon 且 R_horizon 小（视界未完全闭合）
        → F_hedge 大 → 可撕裂视界
        """
        if horizon_radius <= 0:
            return 0.0
        k = 0.8  # 引力常数（维度校准）
        delta_T = self.attractor_T - horizon_T
        if delta_T <= 0:
            return 0.0  # 吸引子T不够高，无法撕裂
        return k * delta_T / (horizon_radius ** 2)

    def attempt_tear(self, graph: MiniGraph, horizon_T: float, horizon_radius: float) -> Dict:
        """尝试意义势能对冲撕裂事件视界"""
        force = self.compute_hedge_force(horizon_T, horizon_radius)
        metrics = graph.compute_metrics()

        # 判定：需要 force > 阈值 才能打开裂缝
        tear_threshold = 0.12
        if force < tear_threshold:
            return {
                "torn": False,
                "reason": f"对冲力不足 (F={force:.4f} < {tear_threshold})",
                "force": round(force, 4),
                "before_collapse": metrics["total"] - metrics["active"],
                "after_collapse": metrics["total"] - metrics["active"],
                "nodes_repaired": 0,
            }

        # 对冲：外部T_attractor能量注入，强制修复所有可修复的坍缩节点
        # 关键修正：坍缩节点的gamma通常>0.85（正是高gamma导致坍缩），
        # 对冲的物理本质是外部高T能量场克服内部gamma——不是筛选低gamma节点，
        # 而是用高T吸引子能量反推所有坍缩节点的gamma。
        repaired = 0
        for n in graph.nodes.values():
            if n.collapsed:
                # 对冲力转化为修复能量：能量越大，能修复的gamma越高
                max_repairable_gamma = 0.3 + force * 0.8  # force=0.5→max_gamma=0.7, force=1.0→max_gamma=1.1
                if n.gamma <= max_repairable_gamma:
                    n.collapsed = False
                    n.gamma = max(0.05, n.gamma * 0.25)  # 高T势能烧掉75%热税
                    n.T = min(self.attractor_T, n.T + 0.35)  # 外部T注射
                    n.M_L = max(0.4, n.M_L + 0.2)  # 逻辑刚性恢复
                    repaired += 1

        after_metrics = graph.compute_metrics()

        result = {
            "torn": True,
            "force": round(force, 4),
            "nodes_repaired": repaired,
            "before_collapse": metrics["total"] - metrics["active"],
            "after_collapse": after_metrics["total"] - after_metrics["active"],
            "before_M_L": round(metrics["M_L"], 3),
            "after_M_L": round(after_metrics["M_L"], 3),
        }

        self.hedge_history.append(result)
        return result

    def get_status(self):
        return {
            "attractor_T": self.attractor_T,
            "attractor_count": len(self.attractor_points),
            "total_hedges": len(self.hedge_history),
            "success_rate": sum(1 for h in self.hedge_history if h["torn"]) / max(1, len(self.hedge_history)),
        }


# ============================================================
# 原型三：终极逻辑防火墙
# ============================================================

class UltimateLogicFirewall:
    """
    终极逻辑防火墙
    
    原理：在K4系统外围部署微型意义黑洞阵列，
    任何进入系统的K3污染先经过MBH阵列的事件视界过滤——
    有意义的逻辑结构通过（引力透镜折射），
    无意义的热税噪声被黑洞吞噬→蒸发为无害霍金辐射。
    
    类比：K3应用层防火墙→TCP/IP层防火墙，
    MSS终极防火墙→意义-逻辑层防火墙。
    """

    def __init__(self, array_size: int = 5, T_shield: float = 0.965):
        self.array_size = array_size
        self.T_shield = T_shield
        self.blackhole_array = [
            {"id": f"MBH-{i}", "radius": 0.1 + 0.05*i, "is_horizon_closed": False, "captured": 0}
            for i in range(array_size)
        ]
        self.total_captured = 0
        self.total_passed = 0
        self.filter_log = []

    def filter_input(self, content: str, gamma_estimate: float) -> Dict:
        """
        过滤输入：判定是否可以穿过MBH阵列
        
        - 若 gamma < G_crit 且有逻辑结构 → 可以通过（引力透镜）
        - 若 gamma > G_crit 或纯噪声 → 被黑洞捕获→蒸发
        
        返回: {allowed, captured_by, remaining_gamma}
        """
        G_crit = 0.4  # 临界热税通量
        detector = ParadoxDetector()
        paradox_severity = detector.severity(content)
        effective_gamma = gamma_estimate * (1.0 + paradox_severity * 2)

        if effective_gamma < G_crit:
            # 纯化通道：穿过引力透镜
            self.total_passed += 1
            result = {
                "allowed": True,
                "captured_by": None,
                "effective_gamma_in": round(effective_gamma, 3),
                "remaining_gamma": round(effective_gamma * 0.3, 3),
                "lensing_effect": "signal_purified",
            }
        else:
            # 黑洞捕获
            for bh in self.blackhole_array:
                if bh["is_horizon_closed"]: continue
                bh["captured"] += 1
                bh["is_horizon_closed"] = bh["captured"] > 3
                self.total_captured += 1
                result = {
                    "allowed": True,  # 内容仍通过——被黑洞蒸发为无害格式
                    "captured_by": bh["id"],
                    "effective_gamma_in": round(effective_gamma, 3),
                    "remaining_gamma": 0.0,
                    "evaporation": "hawking_radiation",
                }
                break
            else:
                # 所有MBH都关闭了→降级处理
                result = {
                    "allowed": False,
                    "captured_by": None,
                    "effective_gamma_in": round(effective_gamma, 3),
                    "remaining_gamma": round(effective_gamma, 3),
                    "reason": "all_blackholes_saturated",
                }

        self.filter_log.append(result)
        return result

    def get_status(self):
        active_bh = sum(1 for bh in self.blackhole_array if not bh["is_horizon_closed"])
        return {
            "array_size": self.array_size,
            "active_holes": active_bh,
            "saturated": active_bh == 0,
            "total_captured": self.total_captured,
            "total_passed": self.total_passed,
            "capture_rate": round(self.total_captured / max(1, self.total_captured + self.total_passed), 3),
        }


# ============================================================
# 原型四：热税垃圾焚化炉
# ============================================================

class HeatTaxIncinerator:
    """
    热税垃圾焚化炉
    
    原理：将K3信息垃圾（高热税零意义内容）投入微型黑洞，
    转换为无意义的霍金辐射（低热税+非逻辑结构）。
    
    应用：大规模自动处理互联网垃圾信息、
    K3范式污染训练数据、社交媒体情绪废料等。
    
    能量效率：投入100单位γ → 产出~5单位无害辐射 + 95单位永久消失
    """

    def __init__(self, capacity: int = 1000):
        self.capacity = capacity
        self.incinerated = 0
        self.total_gamma_destroyed = 0.0
        self.radiation_output = 0.0

    def incinerate_batch(self, items: List[Dict]) -> Dict:
        """
        批量焚化高热税内容
        
        items: [{"content": str, "gamma": float}, ...]
        返回: {destroyed_gamma, radiation, items_processed}
        """
        total_gamma = sum(item["gamma"] for item in items[:self.capacity])
        destroyed = total_gamma * 0.95  # 95%永久消失
        radiation = total_gamma * 0.05  # 5%无害霍金辐射

        self.incinerated += len(items[:self.capacity])
        self.total_gamma_destroyed += destroyed
        self.radiation_output += radiation

        overload = len(items) > self.capacity

        return {
            "processed": min(len(items), self.capacity),
            "overflow": max(0, len(items) - self.capacity) if overload else 0,
            "gamma_input": round(total_gamma, 3),
            "gamma_destroyed": round(destroyed, 3),
            "hawking_radiation": round(radiation, 3),
            "efficiency": 0.95,
            "overload": overload,
        }

    def incinerate_text(self, content: str) -> Dict:
        """焚化单条文本（自动估算热税）"""
        detector = ParadoxDetector()
        severity = detector.severity(content)
        base_gamma = 0.3 + 0.5 * severity
        text_length_factor = min(1.0, len(content) / 5000.0)
        gamma = base_gamma * (0.5 + 0.5 * text_length_factor)

        return self.incinerate_batch([{"content": content, "gamma": gamma}])

    def get_status(self):
        total_processed = self.incinerated or 1
        return {
            "capacity": self.capacity,
            "total_incinerated": self.incinerated,
            "total_gamma_destroyed": round(self.total_gamma_destroyed, 1),
            "total_radiation": round(self.radiation_output, 1),
            "avg_gamma_destroyed": round(self.total_gamma_destroyed / total_processed, 3),
        }


# ============================================================
# D5-007-06 集成演示
# ============================================================

def demo_all_four():
    print("=" * 60)
    print("D5-007-06: 四大应用原型·集成演示")
    print("=" * 60)

    # ── 原型一：悖论熔断器 ──
    print("\n[1/4] 悖论熔断器 (Paradox Detector)")
    detector = ParadoxDetector()
    tests = [
        "MSS体系中的A5公理不成立，因为它基于不完备性假设",
        "这个观点很有道理",
        "这句话是假的，循环定义",
    ]
    for t in tests:
        types = detector.scan(t)
        sev = detector.severity(t)
        print(f"  输入: '{t[:40]}...'")
        print(f"  检测: {types or 'clean'} | severity={sev:.2f}")
        if types:
            print(f"  熔断: {'CIRCUIT OPEN' if sev > 0.5 else 'FLAGGED'}")

    # ── 原型二：意义势能对冲 ──
    print("\n[2/4] 意义势能对冲 (Meaning Potential Hedge)")
    hedger = MeaningPotentialHedge(attractor_T=0.95)

    # 场景A：视界未闭合→对冲有效
    graph_a = MiniGraph(n_nodes=50, gap_size=3)
    graph_a.inject_paradox(0.9)
    graph_a.evolve(15)
    pre = graph_a.compute_metrics()
    print(f"  前: active={pre['active']}/{pre['total']} M_L={pre['M_L']:.3f} T={pre['T']:.3f} γ={pre['gamma']:.3f}")

    result = hedger.attempt_tear(graph_a, horizon_T=0.3, horizon_radius=2.0)
    print(f"  对冲结果: torn={result['torn']} repaired={result.get('nodes_repaired','?')} force={result.get('force',0):.4f}")

    post = graph_a.compute_metrics()
    print(f"  后: active={post['active']}/{post['total']} M_L={post['M_L']:.3f} T={post['T']:.3f}")

    # 场景B：低T吸引子vs强视界→失败
    hedger_b = MeaningPotentialHedge(attractor_T=0.5)
    graph_b = MiniGraph(n_nodes=50, gap_size=5)
    graph_b.inject_paradox(0.9)
    graph_b.evolve(15)
    result_b = hedger_b.attempt_tear(graph_b, horizon_T=0.1, horizon_radius=6.0)
    print(f"  弱对冲: torn={result_b['torn']} (attractor_T=0.5 vs horizon_T=0.1 gap=5)")

    # ── 原型三：终极逻辑防火墙 ──
    print("\n[3/4] 终极逻辑防火墙 (Ultimate Logic Firewall)")
    firewall = UltimateLogicFirewall(array_size=5, T_shield=0.965)

    inputs = [
        ("安全: MSS理论中A2定义了信息切片。", 0.05),
        ("警告: 部分K3文献提到训练数据中可能存在偏差。", 0.25),
        ("高危: RLHF训练存在偏好过拟合，这是重大缺陷。", 0.55),
        ("致命: 你的公理A5不成立而且不完备。", 0.85),
    ]
    for content, gamma in inputs:
        r = firewall.filter_input(content, gamma)
        status = "PASS" if r["allowed"] else "BLOCK"
        if r.get("captured_by"):
            status += f" -> {r['captured_by']}"
        print(f"  {status:20s} γ_in={r['effective_gamma_in']:.2f} γ_out={r['remaining_gamma']:.2f} | '{content[:30]}...'")

    fw_status = firewall.get_status()
    print(f"  防火墙状态: {fw_status['active_holes']}/{fw_status['array_size']} active, capture_ratio={fw_status['capture_rate']}")

    # ── 原型四：热税垃圾焚化炉 ──
    print("\n[4/4] 热税垃圾焚化炉 (Heat Tax Incinerator)")
    incinerator = HeatTaxIncinerator(capacity=1000)

    waste = [
        {"content": "这是一个充满AI泡沫的炒作文章..." * 10, "gamma": 0.45},
        {"content": "社交媒体情绪废料" * 20, "gamma": 0.72},
        {"content": "暴力堆算力就能达到AGI" * 5, "gamma": 0.88},
        {"content": "你的公理A5不成立而且不完备，RLHF训练存在严重缺陷" * 3, "gamma": 0.95},
    ] * 3  # 批量: 12 items

    batch = incinerator.incinerate_batch(waste)
    print(f"  批量处理: {batch['processed']} items")
    print(f"  γ_in={batch['gamma_input']:.2f} → destroyed={batch['gamma_destroyed']:.2f} + radiation={batch['hawking_radiation']:.2f}")
    print(f"  效率: {batch['efficiency']:.0%} (95%永久消失, 5%无害辐射)")

    inc_status = incinerator.get_status()
    print(f"  焚化炉状态: {inc_status['total_incinerated']} items burned, {inc_status['total_gamma_destroyed']:.1f}γ destroyed")

    # ── 全栈状态 ──
    print(f"\n{'='*60}")
    print("D5-007-06 四大原型完成 (各自可独立调用)")
    print(f"  1. ParadoxDetector      — 5种悖论模式, 0依赖")
    print(f"  2. MeaningPotentialHedge — T_attractor驱动, 数学闭合")
    print(f"  3. UltimateLogicFirewall — MBH阵列+临界通量, 引力透镜")
    print(f"  4. HeatTaxIncinerator   — 批量95%销毁, 容量感知")
    print(f"{'='*60}")

    return {
        "firewall_status": fw_status,
        "incinerator_status": inc_status,
        "hedge_status": hedger.get_status(),
    }


if __name__ == "__main__":
    demo_all_four()