"""
Δ 维持条件 — MSS-Agent 的第二道防线.

Δ 不是优化目标, 是存活条件 (心率>0, 不是最大化心率).
Δ<0 → Agent 闭合于旧模式 → 触发蜕壳.
"""
import time
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class DeltaProtocol:
    """
    Δ 检测协议 v2 (H528). 嵌入每个 Agent 实例.

    从简单连续下降 → 上下文感知的模式多样性评分.
    区分四种模式：真下降、探索周期、停滞平台、模式塌陷.

    min_delta: Δ 最低阈值 (0.3). 低于此→告警
    molt_cycles: 连续下降 N 个周期→触发蜕壳
    plateau_window: 平台检测窗口 (连续低于阈值 N 次→平台告警)
    """
    min_delta: float = 0.3
    molt_cycles: int = 2
    plateau_window: int = 5
    history: list = field(default_factory=list)  # [{ts, delta, task_hash}]
    molting_alert: bool = False
    plateau_alert: bool = False
    _pattern: str = "unknown"  # 当前模式分类

    def tick(self, task_hash: str, novelty_score: float, diversity_score: float):
        """
        每个任务周期调用一次.

        task_hash: 当前任务的 hash (用于检测重复)
        novelty_score: 0=完全重复, 1=全新
        diversity_score: 0=单一模式, 1=多模式

        Δ = novelty * 0.6 + diversity * 0.4
        """
        delta = novelty_score * 0.6 + diversity_score * 0.4
        delta = round(delta, 4)

        entry = {
            "ts": time.time(),
            "delta": delta,
            "task_hash": task_hash[:8],
            "novelty": novelty_score,
            "diversity": diversity_score,
        }
        self.history.append(entry)

        # Keep last 30 entries
        self.history = self.history[-30:]

        # Pattern analysis (replaces simple consecutive-drop check)
        self._analyze_pattern()

        return delta

    # ── 模式分析 ──

    def _analyze_pattern(self) -> None:
        """上下文感知模式分类：下降/探索/平台/塌陷."""
        self.molting_alert = False
        self.plateau_alert = False

        if len(self.history) < 3:
            self._pattern = "warming"
            return

        deltas = [h["delta"] for h in self.history]
        recent = deltas[-5:] if len(deltas) >= 5 else deltas

        # 1. 模式塌陷检测: 近 N 次 diversity 全为 0
        if len(self.history) >= 5:
            divs = [h["diversity"] for h in self.history[-5:]]
            if all(d == 0 for d in divs) and self.history[-1]["delta"] < self.min_delta:
                self._pattern = "collapse"
                self.molting_alert = True
                return

        # 2. 探索周期: 当前低但历史有回升 (交替高低 → 不触发告警)
        # 必须在 decline 之前检查，因为有回升历史说明模式未被"困住"
        if len(self.history) >= 4 and recent[-1] < self.min_delta:
            older = deltas[-8:-4] if len(deltas) >= 8 else deltas[:-4]
            # 有回升历史: 曾经低于阈值后回升过
            rebound = False
            for i in range(1, len(self.history)):
                if self.history[i]["delta"] >= self.min_delta and self.history[i-1]["delta"] < self.min_delta:
                    rebound = True
                    break
            if rebound:
                self._pattern = "exploring"
                return

        # 3. 真下降检测: 单调递减趋势 (近5点斜率 < -0.05)
        if len(self.history) >= 5 and recent[-1] < self.min_delta:
            slope = self._linear_slope(range(len(recent)), recent)
            if slope < -0.05:
                self._pattern = "decline"
                self.molting_alert = True
                return

        # 4. 停滞平台: 连续 plateau_window 次低于阈值
        if len(self.history) >= self.plateau_window:
            plat = deltas[-self.plateau_window:]
            if all(d < self.min_delta for d in plat):
                self._pattern = "plateau"
                self.plateau_alert = True
                return

        # 5. 正常
        self._pattern = "healthy" if recent[-1] >= self.min_delta else "warning"

    @staticmethod
    def _linear_slope(x: list, y: list) -> float:
        """计算线性回归斜率 (简化版)."""
        n = len(x)
        if n < 2:
            return 0.0
        x_mean = sum(x) / n
        y_mean = sum(y) / n
        numerator = sum((xi - x_mean) * (yi - y_mean) for xi, yi in zip(x, y))
        denominator = sum((xi - x_mean) ** 2 for xi in x)
        return numerator / denominator if denominator != 0 else 0.0

    def uniqueness_ratio(self) -> float:
        """任务唯一性比率: 不同 hash / 总周期."""
        if len(self.history) < 2:
            return 1.0
        hashes = [h["task_hash"] for h in self.history]
        return len(set(hashes)) / len(hashes)

    def health(self) -> str:
        if not self.history:
            return "UNKNOWN"
        current = self.history[-1]["delta"]
        if self.molting_alert:
            return f"MOLTING({self._pattern})"
        if self.plateau_alert:
            return f"PLATEAU({self._pattern})"
        if current < self.min_delta:
            return f"WARNING({self._pattern})"
        return f"HEALTHY({self._pattern})"

    def snapshot(self) -> dict:
        return {
            "health": self.health(),
            "pattern": self._pattern,
            "current_delta": self.history[-1]["delta"] if self.history else None,
            "molting_alert": self.molting_alert,
            "plateau_alert": self.plateau_alert,
            "history_len": len(self.history),
            "avg_delta": round(sum(h["delta"] for h in self.history) / len(self.history), 4) if self.history else 0,
            "uniqueness_ratio": round(self.uniqueness_ratio(), 4),
        }
