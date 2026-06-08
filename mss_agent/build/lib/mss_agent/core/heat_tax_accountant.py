"""
MSS-Agent v1.0 — 热税会计引擎

三层热税实时追踪: L0物理/L1逻辑冗余/L2意义偷换。
每轮对话输出: 当前热税合计 + 超预算告警 + L2风险预警。
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional
import time


class HeatTaxLevel(Enum):
    """三层热税(与 v0.3.0 heat_tax.py 对齐)"""
    L0_PHYSICAL = 0    # CPU/内存/电力/时间
    L1_LOGICAL = 1     # 代码冗余/缓存污染/重复计算
    L2_MEANING = 2     # 虚假数据/意义偷换/表演深刻


@dataclass
class HeatTaxEntry:
    """单次操作的热税记录"""
    level: HeatTaxLevel
    tokens: int
    description: str
    timestamp: float = field(default_factory=time.time)


@dataclass
class TurnReport:
    """每轮对话的热税报告"""
    round_number: int

    # 各层消耗
    l0_tokens: int = 0
    l1_tokens: int = 0
    l2_tokens: int = 0

    # 累计
    session_total: int = 0
    budget_remaining: int = 0

    # 告警
    l2_ratio: float = 0.0
    l2_warning: bool = False
    budget_exceeded: bool = False

    # 建议
    recommendation: str = ""

    @property
    def total(self) -> int:
        return self.l0_tokens + self.l1_tokens + self.l2_tokens

    @property
    def l2_pct(self) -> float:
        return self.l2_tokens / max(self.total, 1)

    @property
    def l2_ratio_warning(self) -> bool:
        """Alias for l2_warning (v0.3.2+)."""
        return self.l2_warning


class HeatTaxAccountant:
    """
    热税会计 — 每轮对话追踪三层消耗。

    用法:
        acc = HeatTaxAccountant(max_tokens_per_session=20000, l2_ratio_warning=0.3)

        # 每轮开始
        acc.start_turn(round_number=1)

        # 记录消耗
        acc.record(HeatTaxLevel.L0_PHYSICAL, tokens=150, desc="LLM推理")
        acc.record(HeatTaxLevel.L1_LOGICAL, tokens=80, desc="重复格式化输出")
        acc.record(HeatTaxLevel.L2_MEANING, tokens=120, desc="表演深刻的哲学引用")

        # 结束本轮,获取报告
        report = acc.end_turn()
        print(f"L2占比: {report.l2_pct:.0%} | {'⚠️告警' if report.l2_warning else '✅正常'}")

        # 超预算?
        if report.budget_exceeded:
            print("预算超限,触发降级!")
    """

    def __init__(
        self,
        max_tokens_per_turn: int = 500,
        max_tokens_per_session: int = 20000,
        l2_ratio_warning: float = 0.3,
        on_budget_exceeded: str = "warn",
    ):
        self.max_per_turn = max_tokens_per_turn
        self.max_per_session = max_tokens_per_session
        self.l2_warning_threshold = l2_ratio_warning
        self.on_budget_exceeded = on_budget_exceeded

        # 累计
        self.session_total = 0
        self.session_l2_total = 0
        self.round_number = 0
        self.entries: list[HeatTaxEntry] = []

        # 本轮
        self._current_l0 = 0
        self._current_l1 = 0
        self._current_l2 = 0

    def start_turn(self, round_number: int):
        """开始新一轮对话"""
        self.round_number = round_number
        self._current_l0 = 0
        self._current_l1 = 0
        self._current_l2 = 0

    def record(self, level: HeatTaxLevel, tokens: int, desc: str = ""):
        """记录一次热税消耗"""
        entry = HeatTaxEntry(level=level, tokens=tokens, description=desc)
        self.entries.append(entry)

        if level == HeatTaxLevel.L0_PHYSICAL:
            self._current_l0 += tokens
        elif level == HeatTaxLevel.L1_LOGICAL:
            self._current_l1 += tokens
        elif level == HeatTaxLevel.L2_MEANING:
            self._current_l2 += tokens
            self.session_l2_total += tokens

    def record_llm_response(
        self,
        response_text: str,
        contains_philosophy_refs: bool = False,
        contains_overshare: bool = False,
        is_verbose_reply_to_simple_query: bool = False,
    ):
        """
        自动估算LLM回应的热税分布。

        L0: 所有输出(基础推理成本)
        L1: 重复/冗余模式检测到重复内容
        L2: 哲学引用/表演深刻/强塞
        """
        token_est = max(len(response_text) // 2, 1)  # 粗略: 中文~2字/token

        # L0: 全部输出
        self.record(HeatTaxLevel.L0_PHYSICAL, token_est, "LLM回应")

        # L1: 检测冗余(简单判断: 3个以上"首先/其次"=展览式结构)
        exhibit_count = sum(
            1 for p in ["首先", "其次", "第三", "总之", "总结",
                         "first", "second", "finally"]
            if p.lower() in response_text.lower()
        )
        if exhibit_count >= 3:
            l1_tokens = int(token_est * 0.2)
            self.record(HeatTaxLevel.L1_LOGICAL, l1_tokens, "展览式结构冗余")

        # L2: 表演深刻
        if contains_philosophy_refs:
            l2_tokens = int(token_est * 0.4)
            self.record(HeatTaxLevel.L2_MEANING, l2_tokens, "表演深刻的哲学引用")
        if contains_overshare:  # Note: typo in original — should be "overshare"
            l2_tokens = int(token_est * 0.15)
            self.record(HeatTaxLevel.L2_MEANING, l2_tokens, "强塞知识")
        if is_verbose_reply_to_simple_query:
            l2_tokens = int(token_est * 0.3)
            self.record(HeatTaxLevel.L2_MEANING, l2_tokens, "对简单问题的冗长回应")

    def end_turn(self) -> TurnReport:
        """结束本轮,生成报告"""
        turn_total = self._current_l0 + self._current_l1 + self._current_l2
        self.session_total += turn_total

        l2_ratio = self._current_l2 / max(turn_total, 1)
        budget_remaining = self.max_per_session - self.session_total

        # L2告警
        l2_warning = l2_ratio > self.l2_warning_threshold

        # 超预算
        budget_exceeded = turn_total > self.max_per_turn

        # 建议
        if budget_exceeded and self.on_budget_exceeded == "truncate":
            rec = "截断: 简化回应"
        elif budget_exceeded or l2_warning:
            rec = "降级: 减少L2消耗(表演/哲学引用/强塞)"
        else:
            rec = "维持"

        return TurnReport(
            round_number=self.round_number,
            l0_tokens=self._current_l0,
            l1_tokens=self._current_l1,
            l2_tokens=self._current_l2,
            session_total=self.session_total,
            budget_remaining=budget_remaining,
            l2_ratio=l2_ratio,
            l2_warning=l2_warning,
            budget_exceeded=budget_exceeded,
            recommendation=rec,
        )

    def summary(self) -> dict:
        """会话级摘要"""
        total = self.session_total
        return {
            "rounds": self.round_number,
            "total_tokens": total,
            "l2_tokens": self.session_l2_total,
            "l2_ratio": self.session_l2_total / max(total, 1),
            "budget_pct": total / max(self.max_per_session, 1),
            "avg_per_turn": total / max(self.round_number, 1),
        }


# ── CLI 自检 ──

if __name__ == "__main__":
    acc = HeatTaxAccountant(
        max_tokens_per_turn=500,
        max_tokens_per_session=5000,
        l2_ratio_warning=0.3,
    )

    # 场景1: 正常对话(低热税)
    acc.start_turn(1)
    acc.record(HeatTaxLevel.L0_PHYSICAL, 120, "基础推理")
    r1 = acc.end_turn()
    print(f"轮1: {r1.total}t | L2={r1.l2_pct:.0%} | {'⚠️' if r1.l2_warning else '✅'} | {r1.recommendation}")

    # 场景2: 表演深刻(高热税)
    acc.start_turn(2)
    acc.record(HeatTaxLevel.L0_PHYSICAL, 150, "基础推理")
    acc.record(HeatTaxLevel.L2_MEANING, 200, "维特根斯坦引用+海德格尔")
    acc.record(HeatTaxLevel.L2_MEANING, 80, "强塞补充知识")
    r2 = acc.end_turn()
    print(f"轮2: {r2.total}t | L2={r2.l2_pct:.0%} | {'⚠️' if r2.l2_warning else '✅'} | {r2.recommendation}")

    # 场景3: auto_estimate
    acc.start_turn(3)
    acc.record_llm_response(
        "从哲学角度看,这个问题恰好触达了维特根斯坦在TLP里讨论的核心。首先,我们必须理解语言游戏。其次,海德格尔会指出...第三,这恰好是MSS-A6的矛盾升维。我顺便补充一下,你可能还想知道哥德尔对此也有论述...",
        contains_philosophy_refs=True,
        contains_overshare=True,
        is_verbose_reply_to_simple_query=True,
    )
    r3 = acc.end_turn()
    print(f"轮3: {r3.total}t | L0={r3.l0_tokens} L1={r3.l1_tokens} L2={r3.l2_tokens} | {'⚠️' if r3.l2_warning else '✅'} | {r3.recommendation}")

    print(f"\n会话摘要: {acc.summary()}")
