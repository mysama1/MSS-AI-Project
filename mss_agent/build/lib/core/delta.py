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
    Δ 检测协议 (H528). 嵌入每个 Agent 实例.

    min_delta: Δ 最低阈值 (0.3). 低于此→告警
    molt_cycles: 连续下降 N 个周期→触发蜕壳
    """
    min_delta: float = 0.3
    molt_cycles: int = 2
    history: list = field(default_factory=list)  # [{ts, delta, task_hash}]
    molting_alert: bool = False

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

        # Check: 2 consecutive drops below min_delta
        self.molting_alert = False
        if len(self.history) >= 3:
            d2 = self.history[-3]["delta"]
            d1 = self.history[-2]["delta"]
            d0 = self.history[-1]["delta"]
            if d0 < d1 < d2 and d0 < self.min_delta:
                self.molting_alert = True

        return delta

    def health(self) -> str:
        if not self.history:
            return "UNKNOWN"
        current = self.history[-1]["delta"]
        if self.molting_alert:
            return "MOLTING"
        if current < self.min_delta:
            return "WARNING"
        return "HEALTHY"

    def snapshot(self) -> dict:
        return {
            "health": self.health(),
            "current_delta": self.history[-1]["delta"] if self.history else None,
            "molting_alert": self.molting_alert,
            "history_len": len(self.history),
            "avg_delta": round(sum(h["delta"] for h in self.history) / len(self.history), 4) if self.history else 0,
        }
