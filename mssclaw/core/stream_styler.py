"""
StreamStyler — 流式输出节奏控制器

让 LLM 输出不是冷冰冰的打字机, 而是有呼吸感的表达:
  - 标点后停顿 (。→200ms, ,→80ms)
  - 段落间深呼吸
  - 代码块慢速精准
  - 中英文自适应节奏
  - 长 token 慢, 短 token 快

用法:
    raw_stream = agent.llm.stream("写一首诗")
    styled = StreamStyler(raw_stream, mode="poetry")
    for chunk in styled:
        print(chunk, end="", flush=True)

模式:
  - "prose":    散文 (中等节奏, 标点停顿)
  - "code":     代码 (慢速精准, 缩进停顿)
  - "poetry":   诗歌 (极慢, 每句大停顿)
  - "chat":     对话 (快节奏, 短停顿)
  - "explain":  解释 (关键词强调)
"""
from __future__ import annotations
import time
import re
from typing import Iterator


class StreamStyler:
    """流式输出节拍器."""

    # 标点停顿表 (秒)
    PUNCTUATION_PAUSE = {
        # 中文
        "。": 0.25, "！": 0.20, "？": 0.20, "；": 0.15,
        "，": 0.08, "、": 0.05, "：": 0.12, "…": 0.30,
        # 英文
        ".": 0.20, "!": 0.18, "?": 0.18, ";": 0.12,
        ",": 0.06, ":": 0.10, "-": 0.04,
    }

    # 段落停顿 (秒)
    PARAGRAPH_PAUSE = 0.35

    # 模式预设
    MODES = {
        "prose":   {"base_speed": 0.015, "punct_mult": 1.0, "para_pause": 0.35},
        "code":    {"base_speed": 0.025, "punct_mult": 0.5, "para_pause": 0.20},
        "poetry":  {"base_speed": 0.040, "punct_mult": 1.5, "para_pause": 0.60},
        "chat":    {"base_speed": 0.008, "punct_mult": 0.6, "para_pause": 0.15},
        "explain": {"base_speed": 0.020, "punct_mult": 1.0, "para_pause": 0.40},
    }

    def __init__(self, token_stream: Iterator[str], mode: str = "prose",
                 min_delay: float = 0.002, max_delay: float = 0.08):
        self._stream = token_stream
        self._mode = mode
        self._min_delay = min_delay
        self._max_delay = max_delay
        self._buffer = ""
        self._total_chars = 0

    def __iter__(self):
        return self._generate()

    def _generate(self):
        config = self.MODES.get(self._mode, self.MODES["prose"])
        base = config["base_speed"]
        punct_mult = config["punct_mult"]
        para_pause = config["para_pause"]

        for raw_token in self._stream:
            if raw_token.startswith("[") and raw_token.endswith("]"):
                yield raw_token
                continue

            for char in raw_token:
                self._total_chars += 1
                yield char
                self._buffer = (self._buffer + char)[-50:]

                delay = base

                # 标点停顿
                if char in self.PUNCTUATION_PAUSE:
                    delay = self.PUNCTUATION_PAUSE[char] * punct_mult

                # 换行 = 段落
                elif char == "\n":
                    # Check if paragraph break (double newline)
                    if self._buffer.endswith("\n\n") or self._buffer.endswith("\n"):
                        delay = para_pause
                    else:
                        delay = base * 3  # single newline = light pause

                # 自适应: 短 token 快, 长 token 慢
                else:
                    token_len = len(raw_token)
                    if token_len > 6:
                        delay = base * 1.5
                    elif token_len <= 2:
                        delay = max(self._min_delay, base * 0.5)

                delay = max(self._min_delay, min(self._max_delay, delay))
                if delay > 0.001:
                    time.sleep(delay)

    def stats(self) -> dict:
        return {
            "mode": self._mode,
            "total_chars": self._total_chars,
            "estimated_time": round(self._total_chars * self.MODES[self._mode]["base_speed"], 1),
        }
