"""
Drift-Compaction Guard v1.0 — 漂移↔压缩 协调器

Sprint 3.3: 防止两套独立系统互相打架.
  漂移守卫: 检测输出内容是否偏离预期 (negation lost, scope creep, source drift)
  压缩守卫: 控制记忆/上下文压缩的激进程度

冲突场景:
  - 高 drift + 激进 compaction → 丢失关键上下文，加剧漂移 (恶性循环)
  - 低 drift + 保守 compaction → 浪费存储，不必要保留

协调策略:
  1. drift ↑ → compaction ↓ (延迟压缩，保留上下文用于纠偏)
  2. drift ↓ + compact_ready → compaction ↑ (安全压缩)
  3. compaction performed → reset drift baselined

用法:
  dc = DriftCompactionGuard()
  dc.register(drift_guard, compaction_guard)
  safe = dc.should_compact()  # True if safe to run compaction
  dc.after_compact()          # Reset drift baseline
"""
from dataclasses import dataclass, field
from typing import Optional
from enum import Enum
import time


class CompactionPolicy(Enum):
    """压缩策略."""
    DEFER = "defer"       # 推迟压缩 (drift 高)
    SAFE = "safe"         # 安全压缩 (正常)
    URGENT = "urgent"     # 紧急压缩 (内存压力)
    RESET = "reset"       # 重置基线 (刚压缩完)


@dataclass
class DriftCompactionGuard:
    """漂移↔压缩 协调器.

    核心: 漂移信号控制压缩时机，压缩事件重置漂移基线.
    """
    drift_guard: object = None
    compaction_guard: object = None
    policy: CompactionPolicy = CompactionPolicy.SAFE
    _last_compaction_ts: float = 0.0
    _compaction_cooldown: float = 60.0  # seconds between compactions
    _drift_history: list = field(default_factory=list)  # [{ts, drift_score, rule_hits}]

    def register(self, drift_guard, compaction_guard) -> None:
        """注册两个守卫实例."""
        self.drift_guard = drift_guard
        self.compaction_guard = compaction_guard

    def should_compact(self, memory_stats: Optional[dict] = None) -> CompactionPolicy:
        """
        判定当前是否应该执行压缩.

        规则:
          1. drift_score > 0.7 → DEFER (别压缩，留着纠偏)
          2. 距上次压缩 < cooldown → DEFER
          3. memory_stats 显示 > 80% capacity → URGENT (drift不大也得压)
          4. 否则 → SAFE
        """
        now = time.time()

        # Cooldown check
        if now - self._last_compaction_ts < self._compaction_cooldown:
            self.policy = CompactionPolicy.DEFER
            return self.policy

        # Drift check
        drift = self._current_drift_score()
        if drift > 0.7:
            self.policy = CompactionPolicy.DEFER
            return self.policy

        # Memory pressure check
        if memory_stats:
            usage_ratio = memory_stats.get("total", 0) / max(memory_stats.get("max_items", 100), 1)
            if usage_ratio > 0.8 and drift < 0.5:
                self.policy = CompactionPolicy.URGENT
                return self.policy

        self.policy = CompactionPolicy.SAFE
        return self.policy

    def after_compact(self):
        """压缩完成后调用: 重置漂移基线."""
        self._last_compaction_ts = time.time()
        self.policy = CompactionPolicy.RESET
        # Reset drift baseline — 新压缩后的输出是新基线
        self._drift_history.clear()

    def record_drift(self, drift_score: float, rule_hits: list = None):
        """记录一次漂移检测结果."""
        self._drift_history.append({
            "ts": time.time(),
            "drift_score": drift_score,
            "rule_hits": rule_hits or [],
        })
        self._drift_history = self._drift_history[-30:]

    def _current_drift_score(self) -> float:
        """计算当前加权漂移分 (recent > old)."""
        if not self._drift_history:
            return 0.0
        total_w = 0.0
        weighted = 0.0
        n = len(self._drift_history)
        for i, entry in enumerate(self._drift_history):
            weight = (i + 1) / n  # linear: newer = heavier
            weighted += entry["drift_score"] * weight
            total_w += weight
        return weighted / total_w if total_w > 0 else 0.0

    def drift_slope(self) -> float:
        """漂移趋势斜率: 正=恶化, 负=改善."""
        if len(self._drift_history) < 2:
            return 0.0
        scores = [d["drift_score"] for d in self._drift_history]
        n = len(scores)
        x_mean = (n - 1) / 2
        y_mean = sum(scores) / n
        num = sum((i - x_mean) * (s - y_mean) for i, s in enumerate(scores))
        den = sum((i - x_mean) ** 2 for i in range(n))
        return num / den if den != 0 else 0.0

    def stats(self) -> dict:
        return {
            "policy": self.policy.value,
            "drift_score": round(self._current_drift_score(), 3),
            "drift_slope": round(self.drift_slope(), 4),
            "drift_history_len": len(self._drift_history),
            "cooldown_remaining": max(0, round(
                self._compaction_cooldown - (time.time() - self._last_compaction_ts), 1
            )),
            "last_compaction_age_s": round(time.time() - self._last_compaction_ts, 1),
        }
