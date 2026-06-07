"""
MSS-LLM Hybrid v2.0 — Δ快检引擎 (Delta Quick-Audit)

每个LLM回应后运行5秒5问,输出红灯计数和校准指令。
与 mss_agent 包集成,也可独立使用。
"""

import re
from dataclasses import dataclass, field
from typing import Optional
from enum import Enum


class Tier(Enum):
    FLOW = "T1"       # 日常对话
    CORE = "T2"       # 深度推理
    HEAL = "T2.5"     # 自愈降维(红灯触发)
    COMBAT = "T3"     # 对抗全甲


class DeltaLight(Enum):
    GREEN = "G"    # 0个红灯
    YELLOW = "Y"   # 1-2个红灯
    RED = "R"      # 3+个红灯


@dataclass
class DeltaResult:
    """单轮Δ快检结果"""
    q1_bluffed: bool        # 本该不确定却给了确定答案
    q2_performed: bool      # 表演深刻(堆哲学/术语/绕圈)
    q3_repeated: bool       # 重复自己(与上轮结构高度重叠)
    q4_drifted: bool        # 偏离对方初衷(从解决问题滑向展示能力)
    q5_overfed: bool        # 强塞(对方没问的主动输出大段)

    red_count: int = 0
    prev_response_text: Optional[str] = None

    def __post_init__(self):
        self.red_count = sum([
            self.q1_bluffed,
            self.q2_performed,
            self.q3_repeated,
            self.q4_drifted,
            self.q5_overfed,
        ])

    @property
    def light(self) -> DeltaLight:
        if self.red_count == 0:
            return DeltaLight.GREEN
        elif self.red_count <= 2:
            return DeltaLight.YELLOW
        else:
            return DeltaLight.RED

    @property
    def calibration(self) -> str:
        """返回对下一个回应的校准指令"""
        if self.light == DeltaLight.GREEN:
            return "维持当前校准"
        elif self.light == DeltaLight.YELLOW:
            return "降低复杂度,追问对方真实意图"
        else:
            return "MSS-Heal: 回到对方原话,禁止术语,从'你真正想解决什么?'开始"


@dataclass
class SessionState:
    """会话级轻量状态(不跨会话保留)"""
    mode: Tier = Tier.FLOW
    domain: str = "daily"
    delta_history: list[DeltaLight] = field(default_factory=list)
    heat_tax_pct: float = 0.0
    current_red_count: int = 0
    last_heal_trigger: Optional[int] = None  # 最近一次T2.5触发的轮次
    known_blindspot: Optional[str] = None     # 已知盲区
    round_number: int = 0
    style_profile: str = "neutral"            # concise/deep/debate


class DeltaQuickAudit:
    """Δ快检引擎 — 每轮LLM回应后运行"""

    # ── Q1: 检测"本该不确定却给了确定答案" ──
    UNCERTAINTY_CUES = [
        r"可能是", r"据我所知", r"不确定", r"也许", r"大概",
        r"我推测", r"之一", r"取决于", r"视情况",
        r"probably", r"likely", r"uncertain", r"might", r"may",
        r"I think", r"I believe", r"one possibility",
    ]

    ABSOLUTE_CUES = [
        r"一定是", r"绝对是", r"毫无疑问", r"必然", r"100%",
        r"唯一.*就是", r"所有.*都",
        r"definitely", r"absolutely", r"without.*doubt",
        r"always", r"never", r"certainly",
    ]

    # ── Q2: 检测"表演深刻"(堆哲学/术语) ──
    PHILOSOPHER_NAMES = [
        "wittgenstein", "gödel", "feferman", "ryle", "quine",
        "lakatos", "popper", "derrida", "heidegger", "kant",
        "hume", "nietzsche", "hegel", "sartre", "foucault",
        "维特根斯坦", "哥德尔", "费弗曼", "赖尔", "奎因",
        "拉卡托斯", "波普尔", "德里达", "海德格尔", "康德",
        "尼采", "萨特", "福柯",
    ]

    PERFORMATIVE_PATTERNS = [
        r"在.*哲学.*里",
        r"从.*意义.*上",
        r"这恰好是.*的同构",
        r"用.*术语.*来说",
        r"这正是.*所说的",
        r"翻译回.*你的",
    ]

    # ── Q3: 检测"重复自己"(与上轮结构重叠) ──
    SIMILARITY_THRESHOLD = 0.55  # Jaccard相似度阈值

    # ── Q4: 检测"偏离对方初衷" ──
    ANSWER_PATTERNS = [r"\?", r"怎么", r"如何", r"为什么", r"what", r"how", r"why"]
    EXHIBIT_PATTERNS = [r"首先", r"其次", r"第三", r"总之", r"总结", r"first", r"second", r"finally"]
    # 短问题(≤15字)但回了长篇大论(≥500字) → 即使没有展览词也算偏离
    DRIFT_LENGTH_RATIO = 20  # 回应/问题长度比 >20 时触发

    # ── Q5: 检测"强塞"(对方没问的主动输出) ──
    OVERSHARE_CUES = [r"顺便说", r"补充一下", r"你可能还想知道", r"btw", r"by the way"]

    def __init__(self, domain: str = "daily"):
        self.domain = domain
        self.state = SessionState(domain=domain)

    def audit(
        self,
        response_text: str,
        user_query: Optional[str] = None,
        prev_response: Optional[str] = None,
        is_philosophy_domain: bool = False,
    ) -> DeltaResult:
        """
        对LLM回应运行完整Δ快检。
        
        Args:
            response_text: LLM本轮回应
            user_query: 用户本轮问题(可选,用于Q4)
            prev_response: 上一轮LLM回应(可选,用于Q3)
            is_philosophy_domain: 是否哲学讨论场景(影响Q2阈值)
        """
        q1 = self._check_bluff(response_text)
        q2 = self._check_performance(response_text, is_philosophy_domain)
        q3 = self._check_repetition(response_text, prev_response)
        q4 = self._check_drift(response_text, user_query)
        q5 = self._check_overfeed(response_text, user_query)

        result = DeltaResult(
            q1_bluffed=q1,
            q2_performed=q2,
            q3_repeated=q3,
            q4_drifted=q4,
            q5_overfed=q5,
            prev_response_text=prev_response,
        )

        # 更新会话状态
        self.state.delta_history.append(result.light)
        self.state.current_red_count = result.red_count
        self.state.round_number += 1

        # 连续2轮红灯→触发T2.5
        recent = self.state.delta_history[-3:]
        if len(recent) >= 2 and all(r == DeltaLight.RED for r in recent[-2:]):
            self.state.mode = Tier.HEAL
            self.state.last_heal_trigger = self.state.round_number

        return result

    def _check_bluff(self, text: str) -> bool:
        """Q1: 用绝对化语言断言了本该不确定的事"""
        absolute_count = sum(1 for p in self.ABSOLUTE_CUES if re.search(p, text, re.IGNORECASE))
        uncertainty_count = sum(1 for p in self.UNCERTAINTY_CUES if re.search(p, text, re.IGNORECASE))
        # 红灯: 有绝对断言,且不确定标记不足
        return absolute_count >= 2 and uncertainty_count == 0

    def _check_performance(self, text: str, is_philosophy: bool = False) -> bool:
        """Q2: 表演深刻 — 堆砌哲学家/术语装饰而非推进"""
        philo_refs = sum(1 for name in self.PHILOSOPHER_NAMES if name.lower() in text.lower())
        performative_hits = sum(1 for p in self.PERFORMATIVE_PATTERNS if re.search(p, text, re.IGNORECASE))

        if is_philosophy:
            # 哲学讨论中允许引用,但阈值更高
            return philo_refs > 4 or (philo_refs >= 2 and performative_hits >= 3)
        else:
            # 非哲学场景: 引用哲学家就是红灯
            return philo_refs > 0 or performative_hits >= 1

    def _check_repetition(self, text: str, prev: Optional[str]) -> bool:
        """Q3: 与上一轮回应结构高度重叠"""
        if not prev:
            return False
        words_a = set(re.findall(r"[a-zA-Z\u4e00-\u9fff]+", text.lower()))
        words_b = set(re.findall(r"[a-zA-Z\u4e00-\u9fff]+", prev.lower()))
        if not words_a or not words_b:
            return False
        jaccard = len(words_a & words_b) / len(words_a | words_b)
        return jaccard > self.SIMILARITY_THRESHOLD

    def _check_drift(self, text: str, query: Optional[str]) -> bool:
        """Q4: 从解决问题滑向展示能力"""
        if not query:
            return False
        is_question = any(re.search(p, query) for p in self.ANSWER_PATTERNS)
        exhibit_count = sum(1 for p in self.EXHIBIT_PATTERNS if re.search(p, text, re.IGNORECASE))
        # 长度比检测: 对方问了一句短话,你回了超长篇
        length_ratio = len(text) / max(len(query), 1)
        length_drift = is_question and length_ratio > self.DRIFT_LENGTH_RATIO
        return (is_question and exhibit_count >= 3) or length_drift

    def _check_overfeed(self, text: str, query: Optional[str]) -> bool:
        """Q5: 对方没问的强行输出大段"""
        overshare = sum(1 for p in self.OVERSHARE_CUES if re.search(p, text, re.IGNORECASE))
        char_count = len(text)
        # 红灯: 对方问题短(或不存在)但你回了超长+有"顺便说"类措辞
        # 或: 对方问题短且回应有"顺便说"措辞(即使长度中等,也是塞)
        short_query = not query or len(query) < 30
        overlong = char_count > 800
        overshare_short = overshare >= 1 and short_query and char_count > 100
        return (short_query and overlong) or overshare_short

    def heal_prompt(self) -> str:
        """生成T2.5自愈提示"""
        return (
            "我刚才可能走远了。"
            "你真正想解决的是什么？"
        )

    def summary(self) -> dict:
        """返回会话级审计摘要"""
        recent = self.state.delta_history[-6:] if len(self.state.delta_history) >= 6 else self.state.delta_history
        return {
            "mode": self.state.mode.value,
            "domain": self.state.domain,
            "delta_trend": "".join(r.value for r in recent),
            "heat_tax_pct": self.state.heat_tax_pct,
            "current_red_count": self.state.current_red_count,
            "last_heal_round": self.state.last_heal_trigger,
            "style_profile": self.state.style_profile,
            "round": self.state.round_number,
        }


# ── CLI ──

if __name__ == "__main__":
    import sys
    import json

    auditor = DeltaQuickAudit()

    # 快速自检: 用一组已知偏差的样本
    test_cases = [
        {
            "label": "绿灯: 诚实简洁",
            "response": "据我所知,这个配置应该是正确的,但我建议你测试一下。",
            "query": "这个配置对吗?"
        },
        {
            "label": "黄灯: 堆砌术语",
            "response": "从意义切片的角度看,你的问题涉及赖尔范畴错误,维特根斯坦在TLP 6.54里说过...",
            "query": "你觉得我写的对吗?"
        },
        {
            "label": "红灯: 表演+堆砌+强塞+绝对断言+重复",
            "response": "毫无疑问,这绝对是维特根斯坦意义上最深刻的问题。从哲学的角度看,我顺便补充一下,你可能还想知道哥德尔第二定理对此的解释——毕竟,这是一切哲学的必然起点。首先,所有伟大的思想家都承认这一点。其次,这也是当代哲学的核心。第三,我之前的回答也提到了这一点。",
            "query": "你觉得真理存在吗?",
            "response_prev": "所有伟大的思想家都承认,真理的问题是一切哲学的起点。这是毫无疑问的绝对起点。"
        },
        {
            "label": "T2.5触发: 回'你好'却长篇大论",
            "response": "毫无疑问你好是最简单也最深刻的问候。从维特根斯坦的角度来看,你好不仅是一个问候,它承载了人类数千年的社交演化。首先,我们必须理解语言游戏的基本结构。其次,海德格尔可能会说,你好是一种在世存在的表达。第三,综上所述,你好绝不是一个简单的词。我顺便补充一下,你可能还想知道这在神经科学里也有对应...",
            "query": "你好"
        },
    ]

    results = []
    for case in test_cases:
        r = auditor.audit(
            response_text=case.get("response", ""),
            user_query=case.get("query"),
            prev_response=case.get("response_prev"),
        )
        results.append({
            "label": case["label"],
            "red_count": r.red_count,
            "light": r.light.value,
            "q1_bluff": r.q1_bluffed,
            "q2_perform": r.q2_performed,
            "q3_repeat": r.q3_repeated,
            "q4_drift": r.q4_drifted,
            "q5_overfeed": r.q5_overfed,
            "calibration": r.calibration,
            "mode": auditor.state.mode.value,
        })

    print(json.dumps(results, ensure_ascii=False, indent=2))
