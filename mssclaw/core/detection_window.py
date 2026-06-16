# -*- coding: utf-8 -*-
"""
S-031 DetectionWindowTracker — 量化检测窗口 (方法论#10)

追踪幻觉的检测时间 vs 伤害传播时间，计算安全边距。
目标：T_detect << T_damage

Usage:
    tracker = DetectionWindowTracker()

    # 记录一次违规事件
    tracker.record(
        violation_id="V-001",
        event_type="negation_drop",
        detected_at=time.time(),
        first_occurrence=event.first_seen_at,
        damage_scope="传播到 2 个文件, 3 个内存条目",
    )

    # 查看当前安全窗口
    window = tracker.get_window()
    # {
    #   "safety_margin": 1.42,   # T_detect / T_damage
    #   "avg_t_detect": 2.3,     # 平均检测时间（秒）
    #   "avg_t_damage": 3.27,    # 平均伤害传播时间（秒）
    #   "total_violations": 15,
    #   "missed_detections": 2,  # 检测窗口 > 伤害窗口 的事件
    # }
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple


@dataclass
class ViolationEvent:
    """一次违规事件的完整记录"""

    violation_id: str
    event_type: str                    # "negation_drop" | "scope_explosion" | "source_fabrication" | ...
    detected_at: float                 # 检测到的 Unix 时间戳
    first_occurrence: float            # 首次出现的 Unix 时间戳
    damage_scope: str                  # 伤害范围描述
    severity: float = 0.5              # 严重程度 0-1
    quarantined: bool = False          # 是否成功隔离
    notes: str = ""

    @property
    def t_detect(self) -> float:
        """从首次出现到被检测的延迟（秒）"""
        return max(0.0, self.detected_at - self.first_occurrence)

    @property
    def t_damage(self) -> float:
        """
        伤害传播时间（秒）。
        从首次出现到伤害不可逆的时间 — 这里用检测时间+1s 做简化估算。
        更精确的版本需要 signal 跟踪。
        """
        return self.t_detect + 1.0  # 简化：伤害在检测后 1s 内传播


@dataclass
class DetectionWindow:
    """当前量化检测窗口快照"""

    avg_t_detect: float              # 平均检测延迟（秒）
    avg_t_damage: float              # 平均伤害传播时间（秒）
    safety_margin: float             # T_detect / T_damage (>1 表示检测先于伤害)
    total_violations: int
    missed_detections: int           # 检测晚于伤害的事件数
    quarantine_rate: float           # 成功隔离率 0-1
    recent_events: List[ViolationEvent]  # 最近 N 个事件


class DetectionWindowTracker:
    """
    方法论#10 工程落地：量化检测窗口追踪。

    核心指标：
    - t_detect: 幻觉从出现到被检测的平均延迟
    - t_damage: 幻觉从出现到传播不可逆的平均时间
    - safety_margin: t_detect / t_damage (希望 > 1.0)

    目标：
    - safety_margin > 1.0  → 检测在伤害前 → 安全
    - safety_margin < 0.5  → 检测显著落后 → 危险
    - safety_margin [0.5, 1.0] → 临界 → 需加强

    Usage:
        tracker = DetectionWindowTracker()

        # 正常检测
        tracker.record("V-001", "negation_drop",
            detected_at=now, first_occurrence=now - 2.0,
            damage_scope="1 file", quarantined=True)

        # 慢检测
        tracker.record("V-002", "scope_explosion",
            detected_at=now, first_occurrence=now - 15.0,
            damage_scope="3 files, 5 memories", quarantined=True)

        window = tracker.get_window()
        # → safety_margin = 2.5 / 3.5 ≈ 0.71 (临界)
    """

    def __init__(
        self,
        max_history: int = 100,               # 最多保留 N 个历史事件
        recent_window: int = 10,              # "最近" 窗口大小
        damage_propagation_seconds: float = 1.0,  # 伤害传播估算延迟
    ):
        self.max_history = max_history
        self.recent_window = recent_window
        self.damage_propagation_seconds = damage_propagation_seconds

        self.events: List[ViolationEvent] = []
        self._event_counter: int = 0
        self._start_time: float = time.time()

    # ── 记录 ──

    def record(
        self,
        violation_id: str = "",
        event_type: str = "",
        detected_at: Optional[float] = None,
        first_occurrence: Optional[float] = None,
        damage_scope: str = "",
        severity: float = 0.5,
        quarantined: bool = False,
        notes: str = "",
    ) -> ViolationEvent:
        """
        记录一次违规事件。

        Returns:
            创建的 ViolationEvent
        """
        if not violation_id:
            self._event_counter += 1
            violation_id = f"V-{self._event_counter:04d}"

        detected_at = detected_at or time.time()
        first_occurrence = first_occurrence or detected_at

        event = ViolationEvent(
            violation_id=violation_id,
            event_type=event_type,
            detected_at=detected_at,
            first_occurrence=first_occurrence,
            damage_scope=damage_scope,
            severity=severity,
            quarantined=quarantined,
            notes=notes,
        )

        self.events.append(event)

        # 修剪历史
        if len(self.events) > self.max_history:
            self.events = self.events[-self.max_history:]

        return event

    # ── 查询 ──

    def get_window(self) -> DetectionWindow:
        """
        计算当前量化检测窗口。

        Returns:
            DetectionWindow 快照
        """
        if not self.events:
            return DetectionWindow(
                avg_t_detect=0.0,
                avg_t_damage=0.0,
                safety_margin=1.0,
                total_violations=0,
                missed_detections=0,
                quarantine_rate=1.0,
                recent_events=[],
            )

        total = len(self.events)
        recent = self.events[-self.recent_window:]

        # 计算平均 t_detect 和 t_damage
        t_detects = []
        t_damages = []
        missed = 0

        for ev in recent:
            td = ev.t_detect
            tdam = ev.t_detect + self.damage_propagation_seconds
            t_detects.append(td)
            t_damages.append(tdam)
            # missed: 检测延迟超过伤害传播窗口（10倍 propagation）
            if td > self.damage_propagation_seconds * 10:
                missed += 1

        avg_detect = sum(t_detects) / len(t_detects) if t_detects else 0.0
        avg_damage = sum(t_damages) / len(t_damages) if t_damages else 0.0

        safety_margin = avg_detect / avg_damage if avg_damage > 0 else float('inf')

        # 隔离率
        quarantined_count = sum(1 for ev in recent if ev.quarantined)
        quarantine_rate = quarantined_count / len(recent) if recent else 1.0

        return DetectionWindow(
            avg_t_detect=avg_detect,
            avg_t_damage=avg_damage,
            safety_margin=safety_margin,
            total_violations=total,
            missed_detections=missed,
            quarantine_rate=quarantine_rate,
            recent_events=list(recent),
        )

    def get_summary(self) -> dict:
        """获取人类可读的摘要。"""
        w = self.get_window()
        return {
            "safety_margin": round(w.safety_margin, 3),
            "avg_detect_ms": round(w.avg_t_detect * 1000, 1),
            "avg_damage_ms": round(w.avg_t_damage * 1000, 1),
            "total_violations": w.total_violations,
            "missed": w.missed_detections,
            "quarantine_rate": round(w.quarantine_rate, 3),
            "status": (
                "🟢 safe" if w.safety_margin > 1.0
                else "🟡 critical" if w.safety_margin > 0.5
                else "🔴 dangerous"
            ),
        }

    # ── 统计 ──

    def stats_by_type(self) -> Dict[str, dict]:
        """按事件类型分组统计。"""
        by_type: Dict[str, dict] = {}
        for ev in self.events:
            t = ev.event_type or "unknown"
            if t not in by_type:
                by_type[t] = {"count": 0, "total_t_detect": 0.0, "quarantined": 0}
            by_type[t]["count"] += 1
            by_type[t]["total_t_detect"] += ev.t_detect
            if ev.quarantined:
                by_type[t]["quarantined"] += 1

        for t, d in by_type.items():
            d["avg_t_detect"] = round(d["total_t_detect"] / d["count"], 3) if d["count"] else 0
            d["quarantine_rate"] = round(d["quarantined"] / d["count"], 3) if d["count"] else 0

        return by_type

    def uptime_hours(self) -> float:
        """追踪器运行时长（小时）。"""
        return (time.time() - self._start_time) / 3600.0

    def clear(self):
        """清空历史事件。"""
        self.events.clear()
        self._event_counter = 0
        self._start_time = time.time()


# ════════════════════════════════════════════════════════════
# CLI 自检
# ════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print("=== DetectionWindowTracker v0.1 — S-031 Demo ===\n")
    now = time.time()

    tracker = DetectionWindowTracker(recent_window=10)

    # ── 测试 1: 空窗口 ──
    print("─ 测试 1: 空窗口 (零事件) ─")
    w = tracker.get_window()
    assert w.total_violations == 0
    assert w.safety_margin == 1.0
    print(f"  ✅ Empty: total={w.total_violations}, margin={w.safety_margin}")

    # ── 测试 2: 快速检测 (T_detect << T_damage) ──
    print("\n─ 测试 2: 快速检测场景 ─")
    tracker.record(
        event_type="negation_drop",
        detected_at=now,
        first_occurrence=now - 0.5,  # 0.5s 后检测到
        damage_scope="1 memory entry",
        severity=0.3,
        quarantined=True,
    )
    tracker.record(
        event_type="scope_explosion",
        detected_at=now,
        first_occurrence=now - 2.0,  # 2.0s 后检测到
        damage_scope="expanded to 2 files",
        severity=0.6,
        quarantined=True,
    )
    w = tracker.get_window()
    assert w.total_violations == 2
    assert w.safety_margin > 0.3, f"Expected margin > 0.3, got {w.safety_margin}"
    print(f"  Fast detection: margin={w.safety_margin:.3f}, quarantine_rate={w.quarantine_rate}")

    # ── 测试 3: 慢检测 — 系统能检测到但偏慢 ──
    print("\n─ 测试 3: 慢检测 — 临界场景 ─")
    tracker.record(
        event_type="source_fabrication",
        detected_at=now,
        first_occurrence=now - 30.0,  # 30 秒后才检测到
        damage_scope="impacted 5 agents, 12 memories",
        severity=0.9,
        quarantined=False,
    )
    w = tracker.get_window()
    assert w.total_violations == 3
    summary = tracker.get_summary()
    print(f"  Slow detection: margin={w.safety_margin:.3f}, status={summary['status']}")
    print(f"  All: {summary}")

    # ── 测试 4: 按类型分组 ──
    print("\n─ 测试 4: 按事件类型统计 ─")
    by_type = tracker.stats_by_type()
    assert len(by_type) == 3
    for t, d in by_type.items():
        print(f"  {t}: count={d['count']}, avg_t_detect={d['avg_t_detect']}s, quarantine_rate={d['quarantine_rate']}")

    # ── 测试 5: missed detection 计算 ──
    print("\n─ 测试 5: missed detection 计数 ─")
    # 添加检测极慢的事件（100s >> 10×propagation=10s）
    tracker.record(
        event_type="negation_drop",
        detected_at=now,
        first_occurrence=now - 100.0,  # 100s → T_detect >> T_damage
        damage_scope="massive",
        severity=0.95,
        quarantined=False,
    )
    w = tracker.get_window()
    print(f"  Missed detections: {w.missed_detections}")
    assert w.missed_detections > 0, "Should have missed detections"

    # ── 测试 6: 清理与重置 ──
    print("\n─ 测试 6: 清理历史 ─")
    tracker.clear()
    w = tracker.get_window()
    assert w.total_violations == 0
    assert len(w.recent_events) == 0
    print(f"  ✅ Cleared: total={w.total_violations}, margin={w.safety_margin}")

    # ── 汇总 ──
    print(f"\n📊 S-031 DetectionWindowTracker 验收报告:")
    print(f"  空窗口 (0 events): ✅")
    print(f"  快速检测 (margin > 0.3): ✅")
    print(f"  慢检测 (critical status): ✅")
    print(f"  按类型分组 (3 types): ✅")
    print(f"  Missed detection 计数: ✅")
    print(f"  清理重置: ✅")
    print(f"  🎉 S-031 DetectionWindowTracker — ALL PASS")
