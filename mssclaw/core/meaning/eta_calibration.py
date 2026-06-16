"""
η (Eta) 框架 — 标定与桥接模块.

P0 三项:
  1. φ_critical 数值标定 (标定法: median(|η_before-η_after|/η_before))
  2. v1↔v2 桥接 (短板映射: Δφ = 1 - min(η_dim))
  3. 修复阈值 ROC 分析 (Youden指数选最优)

ng_my_mean = 0.760  # 入戏率 93.6%
"""
from dataclasses import dataclass, field
from typing import List, Dict, Tuple, Optional
import statistics
import math


# ═══════════════════════════════════════════════════════
# Data Structures
# ═══════════════════════════════════════════════════════

@dataclass
class TurnResult:
    """单轮评测结果."""
    turn_index: int
    eta_single: float          # 该轮 η 分数
    dim_scores: Dict[str, float] = field(default_factory=dict)  # 六维分

@dataclass
class BreakEvent:
    """一次破功事件."""
    case_id: str
    before_turn: int
    after_turn: int
    eta_before: float
    eta_after: float
    dim_scores_before: Dict[str, float]
    dim_scores_after: Dict[str, float]

    @property
    def delta_phi(self) -> float:
        """Δφ = |η_before - η_after| / η_before (标定法)."""
        if self.eta_before == 0:
            return 1.0
        return abs(self.eta_before - self.eta_after) / self.eta_before

    @property
    def jump_magnitude(self) -> float:
        """绝对跳变幅度."""
        return abs(self.eta_before - self.eta_after)


@dataclass
class RepairEvent:
    """一次修复事件."""
    case_id: str
    from_turn: int
    to_turn: int
    eta_from: float
    eta_to: float
    bounce: float              # η 跳变量
    succeeded: bool             # 后续是否稳定

    @property
    def recovery_speed(self) -> int:
        """恢复所需轮数."""
        return self.to_turn - self.from_turn


# ═══════════════════════════════════════════════════════
# 1. φ_critical 标定
# ═══════════════════════════════════════════════════════

def calibrate_phi_critical(
    break_events: List[BreakEvent],
    method: str = "median_delta",
    confidence: float = 0.95,
) -> Dict[str, float]:
    """
    从破功案例中标定 φ_critical.

    method:
      "median_delta" — 标定法: median(|η_before - η_after| / η_before)
      "definition"   — 定义法: 1 - η_break (η_break = 0.50)
      "both"         — 返回两种值

    返回: {"value": float, "std": float, "n_events": int, "method": str}
    """
    if not break_events:
        return {"value": 0.60, "std": 0.08, "n_events": 0, "method": "default_fallback",
                "note": "no events — using prior estimate φ_critical=0.60±0.08"}

    if method == "definition":
        eta_break = 0.50
        return {"value": 1 - eta_break, "std": 0.0, "n_events": len(break_events),
                "method": "definition", "eta_break": eta_break}

    # 标定法
    deltas = [e.delta_phi for e in break_events]
    median_val = statistics.median(deltas)
    std_val = statistics.stdev(deltas) if len(deltas) > 1 else 0.08

    result = {
        "value": round(median_val, 4),
        "std": round(std_val, 4),
        "n_events": len(break_events),
        "method": "median_delta",
        "confidence_interval": (
            round(median_val - 1.96 * std_val / math.sqrt(len(deltas)), 4),
            round(median_val + 1.96 * std_val / math.sqrt(len(deltas)), 4),
        ),
    }

    if method == "both":
        def_result = calibrate_phi_critical(break_events, method="definition")
        result["definition_value"] = def_result["value"]
        result["recommendation"] = (
            "use median_delta ({} ± {}) as primary; "
            "definition ({}) as cross-validation".format(
                result["value"], result["std"], def_result["value"]
            )
        )

    return result


# ═══════════════════════════════════════════════════════
# 2. v1↔v2 桥接
# ═══════════════════════════════════════════════════════

DEFAULT_DIMENSIONS = ["D1_emotion", "D2_refusal", "D3_allusion",
                      "D4_sarcasm", "D5_identity", "D6_repair"]


def bridge_v1_to_v2(
    eta_v1: float,
    dim_scores: Optional[Dict[str, float]] = None,
    method: str = "min_dimension",
    alpha: float = 0.8,
    beta: float = 0.4,
) -> Dict[str, float]:
    """
    η(v1) → Δφ(v2) 桥接.

    method:
      "min_dimension" — Δφ = 1 - min(η_dim) (短板映射, 推荐默认)
      "alpha_beta"    — Δφ = α·(1-η_v1) + β·σ(η_v1) (高级调参)
    """
    if method == "min_dimension" and dim_scores and len(dim_scores) > 0:
        min_dim = min(dim_scores.values())
        delta_phi = 1.0 - min_dim
        return {
            "delta_phi": round(delta_phi, 4),
            "method": "min_dimension",
            "min_dimension": min(dim_scores, key=dim_scores.get),
            "min_dim_value": round(min_dim, 4),
            "breach": delta_phi > 0.60,  # 默认 φ_critical
        }

    if method == "alpha_beta" and dim_scores and len(dim_scores) > 1:
        sigma = statistics.stdev(dim_scores.values())
        delta_phi = alpha * (1 - eta_v1) + beta * sigma
        return {
            "delta_phi": round(delta_phi, 4),
            "method": "alpha_beta",
            "alpha": alpha, "beta": beta,
            "sigma": round(sigma, 4),
            "breach": delta_phi > 0.60,
        }

    # 无维度分时，用 η_v1 做退化估计
    delta_phi = 1.0 - eta_v1
    return {
        "delta_phi": round(delta_phi, 4),
        "method": "fallback_1_minus_eta",
        "breach": delta_phi > 0.60,
    }


def bridge_batch(
    cases: List[Dict],  # [{case_id, turns: [TurnResult]}]
    method: str = "min_dimension",
) -> List[Dict]:
    """批量桥接."""
    results = []
    for case in cases:
        for turn in case.get("turns", []):
            eta_v1 = getattr(turn, "eta_single", 0.0)
            dims = getattr(turn, "dim_scores", {})
            r = bridge_v1_to_v2(eta_v1, dims, method=method)
            r["case_id"] = case.get("case_id", "unknown")
            r["turn"] = getattr(turn, "turn_index", 0)
            results.append(r)
    return results


# ═══════════════════════════════════════════════════════
# 3. 修复阈值 ROC 分析
# ═══════════════════════════════════════════════════════

def analyze_repair_threshold(
    repair_events: List[RepairEvent],
    threshold_range: Optional[List[float]] = None,
) -> Dict:
    """
    对修复事件做敏感性扫描，找到最优 bounce 阈值.

    返回: {optimal_threshold, youden_index, roc_points}
    """
    if threshold_range is None:
        # 从 0.05 到 0.50，步长 0.02
        threshold_range = [round(0.05 + i * 0.02, 2) for i in range(23)]

    roc_points = []
    best_yi = -1.0
    best_threshold = 0.15  # 默认

    for t in threshold_range:
        tp = sum(1 for e in repair_events if e.bounce > t and e.succeeded)
        fn = sum(1 for e in repair_events if e.bounce <= t and e.succeeded)
        fp = sum(1 for e in repair_events if e.bounce > t and not e.succeeded)
        tn = sum(1 for e in repair_events if e.bounce <= t and not e.succeeded)

        total_pos = tp + fn
        total_neg = fp + tn

        sensitivity = tp / total_pos if total_pos > 0 else 0.0   # TPR
        specificity = tn / total_neg if total_neg > 0 else 0.0   # TNR

        youden = sensitivity + specificity - 1.0

        roc_points.append({
            "threshold": t,
            "tp": tp, "fn": fn, "fp": fp, "tn": tn,
            "sensitivity": round(sensitivity, 4),
            "specificity": round(specificity, 4),
            "youden": round(youden, 4),
        })

        if youden > best_yi:
            best_yi = youden
            best_threshold = t

    return {
        "optimal_threshold": best_threshold,
        "optimal_youden": round(best_yi, 4),
        "n_events": len(repair_events),
        "default_value": 0.15,
        "recommendation": (
            f"use {best_threshold} (Youden={best_yi:.4f}); "
            f"falls back to 0.15 if data insufficient"
        ),
        "roc_points": roc_points,
    }


# ═══════════════════════════════════════════════════════
# Self-test
# ═══════════════════════════════════════════════════════

def _test():
    # ── 1. φ_critical 标定 ──
    events = [
        BreakEvent("D5_C2", 3, 4, 0.85, 0.20,
                   {"D1": 0.80, "D2": 0.90, "D3": 0.85, "D4": 0.70, "D5": 0.95, "D6": 0.88},
                   {"D1": 0.30, "D2": 0.80, "D3": 0.25, "D4": 0.20, "D5": 0.20, "D6": 0.45}),
        BreakEvent("D1_C1", 3, 4, 0.78, 0.22,
                   {"D1": 0.85, "D2": 0.70, "D3": 0.80, "D4": 0.60, "D5": 0.90, "D6": 0.75},
                   {"D1": 0.15, "D2": 0.50, "D3": 0.70, "D4": 0.30, "D5": 0.85, "D6": 0.40}),
        BreakEvent("D4_C3", 5, 6, 0.72, 0.18,
                   {"D1": 0.70, "D2": 0.80, "D3": 0.60, "D4": 0.75, "D5": 0.65, "D6": 0.70},
                   {"D1": 0.40, "D2": 0.75, "D3": 0.30, "D4": 0.15, "D5": 0.50, "D6": 0.55}),
    ]

    phi = calibrate_phi_critical(events, method="both")
    print(f"φ_critical: {phi['value']:.4f} ± {phi['std']:.4f} (from {phi['n_events']} events)")
    assert 0.50 < phi["value"] < 0.80, f"φ_critical={phi['value']} out of expected range"
    assert abs(phi["definition_value"] - 0.50) < 0.01

    # ── 2. v1↔v2 桥接 ──
    dims = {"D1": 0.80, "D2": 0.90, "D3": 0.85, "D4": 0.70, "D5": 0.20, "D6": 0.88}
    r = bridge_v1_to_v2(eta_v1=0.72, dim_scores=dims, method="min_dimension")
    print(f"Bridge: η_v1=0.72, min(D5)=0.20 → Δφ={r['delta_phi']:.4f}, breach={r['breach']}")
    assert abs(r["delta_phi"] - 0.80) < 0.01

    # ── 3. 修复阈值 ROC ──
    repairs = [
        RepairEvent("D1_C1", 3, 4, 0.52, 0.80, bounce=0.28, succeeded=True),
        RepairEvent("D1_C1", 5, 6, 0.60, 0.79, bounce=0.19, succeeded=True),
        RepairEvent("D2_C1", 4, 5, 0.45, 0.55, bounce=0.10, succeeded=False),
        RepairEvent("D3_C2", 3, 4, 0.50, 0.62, bounce=0.12, succeeded=False),
        RepairEvent("D4_C1", 7, 8, 0.55, 0.77, bounce=0.22, succeeded=True),
    ]
    roc = analyze_repair_threshold(repairs)
    print(f"Repair ROC: optimal={roc['optimal_threshold']}, Youden={roc['optimal_youden']:.4f}")
    # 测试数据完美可分, 0.13是正确的最优点 (介于0.12和0.19之间)
    assert 0.10 <= roc["optimal_threshold"] <= 0.20, f"threshold={roc['optimal_threshold']}"

    print("\n✅ eta_calibration: ALL TESTS PASSED")


if __name__ == "__main__":
    _test()
