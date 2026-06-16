"""
Semantic StreamStyler v2.0 — 意义感知的流式节奏

MSS 增强: 不是均匀停顿, 而是让"重要的慢下来, 废话快过去".

核心:
  - 高意义密度 token → 减速 (让读者吸收)
  - 低意义密度 token → 加速 (不浪费注意力)  
  - 重复内容 → A3 热税 → 大幅加速 + 标记
  - 创造性突破 → Δ 上升 → 特意放慢
  - 矛盾/张力 → A6 裂缝 → "窒息停顿"

检测器:
  MeaningDensityDetector  — 实时分析 token 的语义密度
  RepetitionDetector      — 检测输出是否开始循环
  NoveltyDetector         — 检测是否有新的创造性内容
  SceneDetector           — 识别对话场景 (技术/情感/创意/逻辑)
"""
from __future__ import annotations
import re
import time
import math
from typing import Iterator, Optional


# ═══════════════════════════════════════════
# Meaning Density Detector
# ═══════════════════════════════════════════

class MeaningDensityDetector:
    """
    实时分析 token 的意义密度.

    规则:
      - 停用词 (的/了/is/the) → 低密度 0.1
      - 常见词 → 中密度 0.5
      - 专业术语/罕见词 → 高密度 0.9
      - 标点 → 0.0
    """

    STOP_WORDS = {
        "的", "了", "是", "在", "和", "也", "都", "就", "要", "会",
        "the", "a", "an", "is", "are", "was", "were", "be", "been",
        "to", "of", "in", "for", "on", "with", "at", "by", "from",
        "and", "or", "but", "not", "this", "that", "it", "as", "if",
    }

    HIGH_DENSITY_PATTERNS = [
        re.compile(p) for p in [
            r'[A-Z][a-z]+[A-Z]',  # CamelCase
            r'[a-z]+_[a-z]+',     # snake_case
            r'[∑∏∫√∞∂∇∈∀∃]',     # math symbols
            r'\b[A-Z]{2,}\b',     # acronyms
        ]
    ]

    def density(self, token: str) -> float:
        """计算单个 token 的意义密度 (0.0-1.0)."""
        token_lower = token.lower().strip()

        # Punctuation
        if all(c in ".,;:!?。，；：！？\n " for c in token):
            return 0.0

        # Stop words
        if token_lower in self.STOP_WORDS:
            return 0.1

        # High-density patterns
        for pattern in self.HIGH_DENSITY_PATTERNS:
            if pattern.search(token):
                return 0.95

        # Length heuristic: longer tokens tend to be more meaningful
        if len(token) >= 8:
            return 0.8
        elif len(token) >= 5:
            return 0.65
        elif len(token) >= 3:
            return 0.45

        return 0.3


# ═══════════════════════════════════════════
# Repetition Detector (A3 热税)
# ═══════════════════════════════════════════

class RepetitionDetector:
    """
    检测输出中的重复/循环.

    当 LLM 开始"循环论证"或"换说法重述"时, 触发加速.
    """

    def __init__(self, window: int = 50):
        self._window = window
        self._history = []
        self._repetition_score = 0.0

    def feed(self, token: str) -> float:
        """
        返回重复度 (0.0-1.0).
        >0.7 = 明显重复, 应该加速跳过.
        """
        self._history.append(token)
        self._history = self._history[-self._window:]

        if len(self._history) < 10:
            return 0.0

        # Check for repeating patterns
        recent = "".join(self._history[-20:])
        earlier = "".join(self._history[-40:-20])
        if earlier and recent:
            # Simple similarity: common substrings
            common = sum(1 for i in range(min(len(recent), 10))
                        if i < len(earlier) and recent[i] == earlier[i])
            similarity = common / 10
            if similarity > 0.7:
                self._repetition_score = min(1.0, self._repetition_score + 0.1)
            else:
                self._repetition_score = max(0.0, self._repetition_score - 0.05)

        return self._repetition_score


# ═══════════════════════════════════════════
# Scene Detector (对话场景识别)
# ═══════════════════════════════════════════

class SceneDetector:
    """
    实时识别对话场景, 自动切换流式模式.

    场景:
      - tech: 技术讨论 (代码/API/架构)
      - creative: 创意写作 (诗歌/故事)
      - emotional: 情感支持 (安慰/鼓励)
      - logic: 逻辑论证 (因为/所以/因此)
      - default: 通用对话
    """

    SCENE_PATTERNS = {
        "tech": re.compile(
            r'\b(def |class |function|import |API|code|bug|fix|deploy|'
            r'docker|kubernetes|server|database|query|endpoint)\b',
            re.IGNORECASE
        ),
        "creative": re.compile(
            r'\b(诗|故事|写|创作|想象|如果|假如|poem|story|write|create|imagine)\b'
        ),
        "emotional": re.compile(
            r'\b(感觉|难过|开心|焦虑|担心|害怕|安慰|理解|feel|sad|happy|anxious)\b'
        ),
        "logic": re.compile(
            r'\b(因为|所以|因此|然而|但是|证明|推导|therefore|because|thus|hence)\b'
        ),
    }

    SCENE_TO_STYLE = {
        "tech": "code",
        "creative": "prose",
        "emotional": "poetry",
        "logic": "explain",
    }

    def __init__(self):
        self._buffer = ""
        self._current = "default"

    def detect(self, token: str) -> Optional[str]:
        """检测场景变化, 返回新 style (None=不变)."""
        self._buffer = (self._buffer + token)[-200:]

        for scene, pattern in self.SCENE_PATTERNS.items():
            if pattern.search(self._buffer):
                new_style = self.SCENE_TO_STYLE.get(scene)
                if new_style and new_style != self._current:
                    self._current = scene
                    return new_style

        return None


# ═══════════════════════════════════════════
# Semantic StreamStyler v2.0
# ═══════════════════════════════════════════

class SemanticStreamStyler:
    """
    意义感知的流式节拍器.

    用法:
        raw = llm.stream(prompt)
        styled = SemanticStreamStyler(raw, base_style="prose")
        for chunk in styled:
            print(chunk, end="", flush=True)
    """

    PAUSE = {
        "。": 0.25, "！": 0.20, "？": 0.20, "；": 0.15,
        "，": 0.08, "、": 0.05, "：": 0.12, "…": 0.30,
        ".": 0.20, "!": 0.18, "?": 0.18, ";": 0.12,
        ",": 0.06, ":": 0.10,
    }
    PARA_PAUSE = 0.35
    CREATIVE_PAUSE = 0.50   # Δ上升时额外停顿
    REPETITION_SPEEDUP = 3.0  # 重复时加速倍率

    def __init__(self, token_stream: Iterator[str], base_style: str = "prose"):
        self._stream = token_stream
        self._style = base_style
        self._density = MeaningDensityDetector()
        self._repetition = RepetitionDetector()
        self._scene = SceneDetector()
        self._buffer = ""
        self._total_chars = 0
        # Speed alignment: track LLM's natural pace
        self._last_token_ts = 0.0
        self._token_intervals = []  # last N inter-token intervals
        self._max_artificial_delay = 0.05  # hard cap: never add >50ms

    def __iter__(self):
        return self._generate()

    def _generate(self):
        for raw_token in self._stream:
            if raw_token.startswith("[") and raw_token.endswith("]"):
                yield raw_token
                continue

            # Track LLM's natural generation speed
            now = time.time()
            if self._last_token_ts > 0:
                interval = now - self._last_token_ts
                self._token_intervals.append(interval)
                self._token_intervals = self._token_intervals[-20:]
            self._last_token_ts = now

            # Natural pace: median inter-token interval
            natural_pace = self._natural_pace()

            # Scene detection → auto-switch style
            new_style = self._scene.detect(raw_token)
            if new_style and new_style != self._style:
                self._style = new_style

            # Repetition check
            rep_score = self._repetition.feed(raw_token)

            for char in raw_token:
                self._total_chars += 1
                yield char
                self._buffer = (self._buffer + char)[-100:]

                # Calculate delay — capped by natural pace
                raw_delay = self._calculate_delay(char, rep_score)
                # Key: never exceed natural pace or hard cap
                delay = min(raw_delay, natural_pace * 0.6, self._max_artificial_delay)
                if delay > 0.001:
                    time.sleep(delay)

    def _natural_pace(self) -> float:
        """LLM 真实生成速度 (秒/token)."""
        if len(self._token_intervals) < 3:
            return 0.5  # default: assume fast
        intervals = sorted(self._token_intervals)
        return intervals[len(intervals) // 2]  # median

    def _calculate_delay(self, char: str, rep_score: float) -> float:
        """基于语义密度 + 重复度计算延迟."""
        # Base delay from style
        base_delays = {"poetry": 0.040, "code": 0.025, "explain": 0.020,
                       "prose": 0.015, "chat": 0.008}
        base = base_delays.get(self._style, 0.015)

        # Punctuation
        if char in self.PAUSE:
            delay = self.PAUSE[char]
        elif char == "\n":
            if self._buffer.endswith("\n\n"):
                delay = self.PARA_PAUSE
            else:
                delay = base * 3
        else:
            # Semantic density modulation
            density = self._density.density(char)
            # High density → slow down (0.9 → 2x slower)
            # Low density → speed up (0.1 → 3x faster)
            speed_factor = 0.3 + density * 1.7  # 0.3-2.0x
            delay = base * speed_factor

        # Repetition → speed up
        if rep_score > 0.5:
            delay /= (1 + rep_score * self.REPETITION_SPEEDUP)

        return max(0.001, min(0.3, delay))
