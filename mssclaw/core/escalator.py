"""
MSS Dimension Escalator — 矛盾升维器 (H623落地工具 #3).

检测开发中的'苍蝇打转'模式,自动触发A6升维。
基于规则: 同一行为重复N次且无进展 → 不是工具问题,是需要换维度。

用法:
    from mssclaw.core.escalator import DimensionEscalator
    esc = DimensionEscalator()
    esc.record("debugging", "NullPointerException at line 42")
    esc.record("debugging", "NullPointerException at line 42")  # 第二次
    # ... 第5次
    if esc.is_stuck():
        print(esc.suggest())
"""
from __future__ import annotations
import time, hashlib
from typing import List, Dict, Optional, Tuple
from collections import defaultdict


class DimensionEscalator:
    """
    A6矛盾升维器.

    检测模式: 同一行为(activity+context hash)重复阈值次 → 卡住
    升维策略: 换工具→换角度→换人→换问题→休息
    """

    def __init__(self, repeat_threshold: int = 3, window_minutes: int = 30):
        self.repeat_threshold = repeat_threshold
        self.window_minutes = window_minutes
        self._history: List[Dict] = []
        self._escalation_level = 0  # 当前升维级别 0-4

    def record(self, activity: str, context: str, outcome: str = "no_progress") -> dict:
        """
        记录一次开发行为.

        activity: 'debugging' | 'coding' | 'refactoring' | 'testing'
        context: 当前上下文(错误信息/代码位置/问题描述)
        outcome: 'progress' | 'partial' | 'no_progress'
        """
        entry = {
            "time": time.time(),
            "activity": activity,
            "context_hash": self._hash(context),
            "context": context[:80],
            "outcome": outcome,
        }
        self._history.append(entry)
        self._prune()

        result = {
            "is_stuck": False,
            "suggestions": [],
            "pattern": None,
            "level": self._escalation_level,
        }

        if self.is_stuck():
            self._escalation_level = min(4, self._escalation_level + 1)
            result["is_stuck"] = True
            result["suggestions"] = self.suggest()
            result["pattern"] = self._detect_pattern()
            result["level"] = self._escalation_level
        elif self._count_recent("progress") > 2:
            # Progress being made → reset escalation level
            self._escalation_level = max(0, self._escalation_level - 1)

        return result

    def is_stuck(self) -> bool:
        """检测是否陷入低效循环."""
        recent = self._get_recent(self.window_minutes)

        # Pattern 1: Same activity with same context hash, repeated
        hash_counts = defaultdict(int)
        for e in recent:
            if e["outcome"] == "no_progress":
                key = f"{e['activity']}:{e['context_hash']}"
                hash_counts[key] += 1

        if any(c >= self.repeat_threshold for c in hash_counts.values()):
            return True

        # Pattern 2: High ratio of no_progress in recent window
        if len(recent) >= 5:
            no_progress_ratio = sum(1 for e in recent if e["outcome"] == "no_progress") / len(recent)
            if no_progress_ratio > 0.8:
                return True

        return False

    def suggest(self) -> List[str]:
        """A6升维建议 — 随升维级别逐级提升."""
        level = self._escalation_level

        suggestions = []

        if level == 1:
            suggestions = [
                "🔧 换工具: 试试用不同的调试工具/方法",
                "📖 换角度: 重新审视问题, 可能问题边界定义有误",
                "📝 记录当前状态: 写清楚你试了什么、观察到了什么",
            ]
        elif level == 2:
            suggestions = [
                "👥 换人: 邀请同事 pair programming (15分钟)",
                "🔄 换方法: 如果一直在"修", 试试"拆" — 把问题拆成更小的子问题",
                "🧪 先写测试: 用测试缩小问题范围, 而不是在调试器中漫游",
            ]
        elif level == 3:
            suggestions = [
                "❓ 换问题: 这个功能真的需要现在实现吗? 考虑推迟到下一个迭代",
                "💤 换节奏: 休息15分钟, 大脑的默认模式网络会帮你处理",
                "📚 查资料: 搜索 StackOverflow/GitHub Issues 看看有没有人遇到过",
            ]
        else:  # level >= 4
            suggestions = [
                "🎯 降维拆解: 当前问题太大了, 拆成3个子任务逐个击破",
                "📄 输出文档: 把当前状态写成文档, 明天带着新视角回来",
                "🏗️ 重构方案: 如果同一段代码被修了3次以上, 考虑整体重写而非修补",
            ]

        return suggestions

    def _detect_pattern(self) -> Optional[str]:
        """识别重复模式."""
        recent = self._get_recent(self.window_minutes)
        hash_counts = defaultdict(list)
        for e in recent:
            if e["outcome"] == "no_progress":
                key = f"{e['activity']}:{e['context_hash']}"
                hash_counts[key].append(e)

        most_common = max(hash_counts.values(), key=len, default=[])
        if len(most_common) >= self.repeat_threshold:
            return (
                f"检测到重复模式: {most_common[0]['activity']} "
                f"({len(most_common)}次) — {most_common[0]['context'][:50]}"
            )
        return None

    def _get_recent(self, minutes: int) -> List[Dict]:
        cutoff = time.time() - minutes * 60
        return [e for e in self._history if e["time"] > cutoff]

    def _count_recent(self, outcome: str, minutes: int = 30) -> int:
        return sum(1 for e in self._get_recent(minutes) if e["outcome"] == outcome)

    def _prune(self):
        """清理1小时前的记录."""
        cutoff = time.time() - 3600
        self._history = [e for e in self._history if e["time"] > cutoff]

    def _hash(self, s: str) -> str:
        return hashlib.md5(s.encode()).hexdigest()[:8]

    def reset(self):
        """重置升维级别(换任务时调用)."""
        self._escalation_level = 0
        self._history = []

    def report(self) -> str:
        """生成升维审计报告."""
        lines = ["=" * 40, "MSS Dimension Escalator Report", "=" * 40]
        lines.append(f"当前升维级别: {self._escalation_level}/4")
        lines.append(f"记录总数: {len(self._history)}")
        lines.append(f"卡住: {'是' if self.is_stuck() else '否'}")

        if self.is_stuck():
            lines.append(f"\n检测到模式: {self._detect_pattern()}")
            lines.append(f"升维建议:")
            for s in self.suggest():
                lines.append(f"  {s}")

        return "\n".join(lines)


# ═══ CLI ═══
def cmd_escalate(args_rest):
    """CLI入口: mssclaw escalate [record|check|reset|report]"""
    esc = DimensionEscalator()

    if not args_rest:
        print(esc.report())
        return

    cmd = args_rest[0]

    if cmd == "record":
        activity = args_rest[1] if len(args_rest) > 1 else "debugging"
        context = " ".join(args_rest[2:]) if len(args_rest) > 2 else "Unknown issue"
        result = esc.record(activity, context)
        print(f"📝 记录: [{activity}] {context[:50]}")
        if result["is_stuck"]:
            print(f"\n🆘 检测到苍蝇打转!")
            print(f"   {result['pattern']}")
            print(f"   升维级别: {result['level']}/4")
            print(f"   建议:")
            for s in result["suggestions"]:
                print(f"     {s}")

    elif cmd == "check":
        if esc.is_stuck():
            print(f"🆘 当前处于卡住状态 — 升维级别 {esc._escalation_level}/4")
            for s in esc.suggest():
                print(f"  {s}")
        else:
            print("✅ 当前无卡住模式")

    elif cmd == "reset":
        esc.reset()
        print("✅ 升维级别已重置")

    elif cmd == "report":
        print(esc.report())

    else:
        print("mssclaw escalate [record|check|reset|report]")
