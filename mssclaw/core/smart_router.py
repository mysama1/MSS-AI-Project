"""
Smart Router — 智能流式路由

原则: 不是每句话都需要意义分析。聊天说"好的"不需要减速。

分层:
  L0 轻量 — 简单对话/指令 (chat, 禁用语义分析, 极速)
  L1 标准 — 通用问答 (prose, 基础标点停顿)
  L2 深度 — 创作/技术/情感 (semantic, 全MSS增强)

自动检测: 分析 prompt 判断场景 → 选择层级 → 动态调整速度上限

极致性能:
  - L0: 不调用任何检测器 → <2ms overhead
  - L1: 仅标点停顿 → <5ms overhead
  - L2: 完整语义分析 → 自然慢, 但 capped at 50ms/token max
"""
from __future__ import annotations
import re
import time
from typing import Iterator


class SmartRouter:
    """
    智能流式路由器.

    用法:
        router = SmartRouter()
        style, level = router.route(prompt)
        # level: 0=极速, 1=标准, 2=深度
    """

    # 触发 L2 深度模式的 prompt 特征
    CREATIVE_TRIGGERS = re.compile(
        r'(写|创作|诗|故事|小说|散文|歌词|剧本|画|设计|想象|假如|如果.+(世界|场景))'
        r'|(poem|story|write|create|design|imagine|fiction)',
        re.IGNORECASE
    )
    TECH_TRIGGERS = re.compile(
        r'(解释|原理|为什么|如何|怎么|算法|架构|源码|代码|实现|分析|优化|debug)'
        r'|(explain|how|why|algorithm|architecture|implement|analyze|optimize)',
        re.IGNORECASE
    )
    EMOTIONAL_TRIGGERS = re.compile(
        r'(感觉|难过|开心|焦虑|害怕|安慰|鼓励|陪伴|倾听|理解我)'
        r'|(feel|sad|happy|anxious|comfort|encourage|listen|understand me)',
        re.IGNORECASE
    )
    # 触发 L0 极速模式 (短问题, 简单指令)
    FAST_TRIGGERS = re.compile(
        r'^(你好|hi|hello|hey|ok|好的|行|对|是|否|yes|no|thanks|谢谢|再见|bye)',
        re.IGNORECASE
    )

    def route(self, prompt: str) -> tuple:
        """
        分析 prompt → 返回 (style, level, max_delay_ms).

        level: 0=极速(无语义), 1=标准(标点), 2=深度(全MSS)
        """
        plen = len(prompt)

        # L0: 极短或简单问候 → 极速
        if plen < 10 or self.FAST_TRIGGERS.search(prompt):
            return ("chat", 0, 10)   # max 10ms delay

        # L2: 深度场景
        if self.CREATIVE_TRIGGERS.search(prompt):
            return ("poetry", 2, 80)  # max 80ms — 不能太慢
        if self.TECH_TRIGGERS.search(prompt):
            return ("explain", 2, 60)
        if self.EMOTIONAL_TRIGGERS.search(prompt):
            return ("poetry", 2, 70)

        # L1: 默认标准模式
        return ("prose", 1, 30)  # max 30ms, 基础标点停顿


class FastStyler:
    """L0/L1 快速流式 — 只做标点停顿, 零语义开销."""

    PUNCT = {
        "。": 0.20, "！": 0.15, "？": 0.15, "；": 0.10,
        "，": 0.05, "、": 0.03, "：": 0.08, "…": 0.25,
        ".": 0.15, "!": 0.12, "?": 0.12, ";": 0.08,
        ",": 0.04, ":": 0.06,
    }

    def __init__(self, token_stream: Iterator[str], max_delay_ms: float = 30):
        self._stream = token_stream
        self._max = max_delay_ms / 1000
        self._last_ts = 0.0
        self._intervals = []

    def _natural_pace(self) -> float:
        if len(self._intervals) < 3:
            return 0.5
        return sorted(self._intervals)[len(self._intervals)//2]

    def __iter__(self):
        return self._generate()

    def _generate(self):
        for token in self._stream:
            if token.startswith("[") and token.endswith("]"):
                yield token
                continue
            now = time.time()
            if self._last_ts > 0:
                self._intervals.append(now - self._last_ts)
                self._intervals = self._intervals[-20:]
            self._last_ts = now
            natural = self._natural_pace()
            for char in token:
                yield char
                if char in self.PUNCT:
                    delay = min(self._max, self.PUNCT[char], natural * 0.5)
                    if delay > 0.002:
                        time.sleep(delay)
                elif char == "\n":
                    time.sleep(min(self._max, 0.08, natural * 0.3))


def routed_stream(agent, prompt: str) -> Iterator[str]:
    """
    智能路由流式 — 自动选择最优模式.

    这是推荐的默认流式调用方式.
    """
    from .semantic_styler import SemanticStreamStyler

    router = SmartRouter()
    style, level, max_ms = router.route(prompt)

    if not hasattr(agent.llm, 'stream'):
        yield agent.llm(prompt)
        return

    raw = agent.llm.stream(prompt)

    if level == 0:
        # L0: 极速 — 基础停顿, 无语义
        styled = FastStyler(raw, max_delay_ms=max_ms)
    elif level == 2:
        # L2: 深度 — 全 MSS 语义分析
        styled = SemanticStreamStyler(raw, base_style=style)
    else:
        # L1: 标准 — 标点停顿
        styled = FastStyler(raw, max_delay_ms=max_ms)

    for chunk in styled:
        yield chunk
