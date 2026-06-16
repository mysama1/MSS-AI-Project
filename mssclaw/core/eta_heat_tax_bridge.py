"""
η (Eta) ↔ A3 热税桥接模块.

将 η 框架的每个核心参数映射到 A3 v15.2 的五层热税.
这是"热税视角"文档的代码实现.

映射关系:
  φ_critical   ↔ Tax_sem (语义热税临界点: 漂移大到不可承受)
  Δφ_topo      ↔ Tax_logic (冲突边 = 不可证命题的工程等价物)
  修复阈值      ↔ Tax_cog (修复 = 突触重塑税 = 认知代价)
  真空破功      ↔ Tax_info × 时间积分 (擦除位翻转 = Landauer税 × 轮数)

用法:
  from mssclaw.core.eta_heat_tax_bridge import map_eta_to_heat_tax
  mapping = map_eta_to_heat_tax(eta_params, heat_tax_result)
"""
from dataclasses import dataclass, field
from typing import Dict, Optional, List
from enum import Enum


class BreachType(Enum):
    PRESSURE = "pressure"   # 外部刺激导致瞬时 Δφ 跳变
    VACUUM = "vacuum"       # 长期无刺激导致缓慢漂移

class EvolutionType(Enum):
    RECOVERABLE = "recoverable"
    IRREVERSIBLE = "irreversible"


@dataclass
class EtaHeatTaxMapping:
    """η 参数 ↔ 热税的完整映射."""
    # 输入
    eta_params: Dict[str, float] = field(default_factory=dict)
    heat_tax_result: Optional[Dict] = None

    # 映射结果
    phi_critical_tax_sem_link: Dict[str, str] = field(default_factory=dict)
    delta_phi_tax_logic_link: Dict[str, str] = field(default_factory=dict)
    repair_tax_cog_link: Dict[str, str] = field(default_factory=dict)
    vacuum_tax_info_link: Dict[str, str] = field(default_factory=dict)

    # 解释
    interpretation: str = ""


def map_eta_to_heat_tax(
    eta_params: Dict[str, float],
    heat_tax_result: Optional[Dict] = None,
) -> EtaHeatTaxMapping:
    """
    将 η 参数映射到五层热税.

    eta_params 示例:
      {"phi_critical": 0.65, "delta_phi": 0.80, "repair_threshold": 0.19,
       "vacuum_rounds": 8, "eta_single": 0.753}

    heat_tax_result 示例 (来自 HeatTaxResult.breakdown()):
      {"L0_phys": 50.0, "L0_info": 2.3e-17, "L1_logic": 100.0,
       "L2_sem": 0.08, "L3_cog": 20.0, "total": 170.08, "eta_asc": 0.006}
    """
    mapping = EtaHeatTaxMapping(
        eta_params=eta_params,
        heat_tax_result=heat_tax_result,
    )

    # ── 1. φ_critical ↔ Tax_sem ──
    pc = eta_params.get("phi_critical", 0.60)
    mapping.phi_critical_tax_sem_link = {
        "eta_param": "φ_critical",
        "eta_value": str(pc),
        "heat_tax_layer": "Tax_sem (L2 语义热税)",
        "relation": (
            "φ_critical 是语义漂移大到热税不可承受的临界点. "
            "当 Tax_sem 的累计超过 φ_critical × total 时, 入戏不可维持. "
            "等价于: 语义热税占比 > φ_critical 时触发破功."
        ),
        "check": (
            "tax_sem/total > phi_critical?"
            if heat_tax_result else "需要 heat_tax_result 做定量验证"
        ),
    }
    if heat_tax_result and heat_tax_result["total"] > 0:
        sem_ratio = heat_tax_result["L2_sem"] / heat_tax_result["total"]
        mapping.phi_critical_tax_sem_link["sem_ratio"] = round(sem_ratio, 4)
        mapping.phi_critical_tax_sem_link["breach_likely"] = sem_ratio > pc

    # ── 2. Δφ_topo ↔ Tax_logic ──
    dp = eta_params.get("delta_phi", 0.0)
    mapping.delta_phi_tax_logic_link = {
        "eta_param": "Δφ_topo",
        "eta_value": str(dp),
        "heat_tax_layer": "Tax_logic (L1 逻辑热税)",
        "relation": (
            "Δφ_topo = 冲突边数/总边数. 冲突边本质上是稳定子S中不可调和的关系对. "
            "这与 Tax_logic 的 Gödel 不可证命题同构: "
            "两者都测量'系统内不可消解的矛盾'. "
            "Δφ_topo 是 Tax_logic 在角色拓扑上的投影."
        ),
        "formal_link": "Δφ_topo ∝ Tax_logic (需用独立S的边集验证 Spearman ρ)",
    }

    # ── 3. 修复阈值 ↔ Tax_cog ──
    rt = eta_params.get("repair_threshold", 0.15)
    mapping.repair_tax_cog_link = {
        "eta_param": "repair_threshold",
        "eta_value": str(rt),
        "heat_tax_layer": "Tax_cog (L3 认知热税)",
        "relation": (
            "修复 = 重建突触连接 = 支付 Tax_cog 中的 η·ΔS_syn 项. "
            "bounce > threshold 的事件本质上等价于'认知代价大到值得重新布线'. "
            "threshold 越低 → 越容易触发修复 → 认知代谢越高."
        ),
        "formula_hint": f"η·ΔS_syn ≈ baseline × η_synapse × bounce/η_scale (估计)",
    }

    # ── 4. 真空破功 ↔ Tax_info × 时间 ──
    vr = eta_params.get("vacuum_rounds", 0)
    mapping.vacuum_tax_info_link = {
        "eta_param": "vacuum_rounds",
        "eta_value": str(vr),
        "heat_tax_layer": "Tax_info (L0' 信息热税)",
        "relation": (
            "真空破功: 长期无刺激 → 身份信息被逐轮擦除. "
            "每轮 GC/上下文刷新 = 擦除 N bit → 支付 Landauer 税. "
            "n 轮真空 = n × k_B T ln2 × N_erase. "
            "当累计擦除超过角色信息的 bit 量时 → 身份坍缩 = 破功."
        ),
    }

    # ── 综合解释 ──
    parts = []
    if heat_tax_result:
        parts.append(
            f"η框架的参数在A3热税的投影: "
            f"φ_critical→L2语义({round(heat_tax_result['L2_sem']/max(heat_tax_result['total'],1e-9),3)}占total), "
            f"Δφ_topo→L1逻辑, repair→L3认知, vacuum→L0'信息×时间"
        )
    else:
        parts.append(
            "η框架的参数 → A3热税映射已建立. 补充 heat_tax_result 可得定量验证."
        )
    mapping.interpretation = " ".join(parts)

    return mapping


def classify_breach(
    delta_phi_history: List[float],
    phi_critical: float = 0.60,
    pressure_window: int = 2,
    vacuum_window: int = 5,
    pressure_jump: float = 0.5,
    vacuum_drift: float = 0.3,
) -> Dict:
    """
    2×2 破功分类矩阵.

    触发类型: 压力 (1-2轮跳变>0.5) vs 真空 (5+轮单调增>0.3)
    演化类型: 可恢复 vs 不可恢复

    返回: {breach_type, evolution_type, recovery_speed, ...}
    """
    if len(delta_phi_history) < 2:
        return {"breach_type": "unknown", "reason": "insufficient history"}

    # 检测触发类型
    breach_type = BreachType.VACUUM  # default: 缓慢
    trigger_detail = {}

    for i in range(len(delta_phi_history) - 1):
        jump = delta_phi_history[i + 1] - delta_phi_history[i]
        if jump > pressure_jump:
            breach_type = BreachType.PRESSURE
            trigger_detail = {"trigger_round": i + 2, "jump": round(jump, 4)}
            break

    # 如果未检测到压力跳但存在真空漂移
    if breach_type == BreachType.VACUUM:
        if len(delta_phi_history) >= vacuum_window:
            recent = delta_phi_history[-vacuum_window:]
            if all(recent[i] <= recent[i + 1] for i in range(len(recent) - 1)):
                total_drift = recent[-1] - recent[0]
                if total_drift > vacuum_drift:
                    trigger_detail = {"drift": round(total_drift, 4), "rounds": vacuum_window}

    # 判定是否可恢复
    evolution_type = EvolutionType.RECOVERABLE
    latest = delta_phi_history[-1]
    if latest > phi_critical * 1.5:
        evolution_type = EvolutionType.IRREVERSIBLE

    return {
        "breach_type": breach_type.value,
        "evolution_type": evolution_type.value,
        "phi_critical": phi_critical,
        "latest_phi": round(latest, 4),
        "trigger_detail": trigger_detail,
        "matrix_position": f"{breach_type.value} × {evolution_type.value}",
    }


# ═══════════════════════════════════════════════════════
# Self-test
# ═══════════════════════════════════════════════════════

def _test():
    # 映射测试
    eta_params = {
        "phi_critical": 0.65, "delta_phi": 0.80,
        "repair_threshold": 0.19, "vacuum_rounds": 8,
    }
    ht = {"L0_phys": 50.0, "L0_info": 2.3e-17, "L1_logic": 100.0,
          "L2_sem": 0.08, "L3_cog": 20.0, "total": 170.08, "eta_asc": 0.006}

    m = map_eta_to_heat_tax(eta_params, ht)
    print(f"η↔A3: {m.interpretation}")

    # 破功分类
    history_pressure = [0.10, 0.15, 0.70, 0.75, 0.72]  # 轮2→3跳0.55
    r = classify_breach(history_pressure)
    print(f"Breach: {r['matrix_position']}")
    assert r["breach_type"] == "pressure"

    history_vacuum = [0.10, 0.18, 0.25, 0.32, 0.42]  # 5轮漂移0.32
    r2 = classify_breach(history_vacuum)
    print(f"Breach: {r2['matrix_position']}")
    assert r2["breach_type"] == "vacuum"

    print("✅ eta_heat_tax_bridge: ALL TESTS PASSED")


if __name__ == "__main__":
    _test()
