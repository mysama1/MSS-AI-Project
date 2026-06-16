"""
DeepFold — 深度内容折叠器

检测 LLM 输出的"深度段" (代码块/长列表/数学推导/超长段落),
自动折叠 → 后台生成 → 生成完再展示.

用法:
    from mssclaw.core.deep_fold import DeepFolder
    folder = DeepFolder(style="explain")
    for event in folder.feed(token_stream):
        if event["type"] == "text":
            print(event["text"], end="", flush=True)
        elif event["type"] == "fold_start":
            print("\n🧠 深度思考中...", end="")
        elif event["type"] == "fold_done":
            print(f"\n📝 完成 ({event['token_count']} tokens):")
            print(event["content"])

折叠规则:
  - ``` 代码块 → 折叠
  - 连续 >3 行列表项 → 折叠
  - 连续 >200 字符无标点 → 折叠 (长推导)
  - 数学符号密集区 → 折叠
"""
from __future__ import annotations
import re
import time
from typing import Iterator, Dict


class DeepFolder:
    """深度内容折叠器."""

    # 折叠触发模式
    CODE_FENCE = re.compile(r'^```')
    LIST_ITEM = re.compile(r'^\s*(\d+[\.\)]|[-*•])\s')
    MATH_DENSE = re.compile(r'[∑∏∫√∞∂∇∈∀∃].*[=<>]')
    LONG_NO_PUNCT = 200  # chars without punctuation

    FOLD_PLACEHOLDERS = {
        "code": "⌨️ 代码生成中",
        "list": "📋 列表整理中",
        "math": "🔢 推导计算中",
        "long": "📝 详细展开中",
    }

    def __init__(self, enabled: bool = True):
        self.enabled = enabled
        self._folded = False
        self._fold_type = ""
        self._buffer = []
        self._token_count = 0
        self._char_count = 0
        self._last_punct_at = 0
        self._consecutive_list_lines = 0

    def feed(self, token_stream: Iterator[str]):
        """
        处理 token 流, 生成事件.

        Events:
          {"type": "text", "text": str}      — 普通文本
          {"type": "fold_start", "kind": str} — 开始折叠
          {"type": "fold_done", "content": str, "token_count": int, "kind": str} — 折叠完成
        """
        if not self.enabled:
            for token in token_stream:
                yield {"type": "text", "text": token}
            return

        for token in token_stream:
            if self._folded:
                self._buffer.append(token)
                self._token_count += 1

                # Check if fold should end
                if self._should_unfold():
                    content = "".join(self._buffer)
                    yield {
                        "type": "fold_done",
                        "content": content,
                        "token_count": self._token_count,
                        "kind": self._fold_type,
                    }
                    self._folded = False
                    self._buffer = []
                    self._token_count = 0
                continue

            # Check if fold should start
            fold_kind = self._detect_fold_start(token)
            if fold_kind:
                self._folded = True
                self._fold_type = fold_kind
                self._buffer = [token]
                self._token_count = 1
                yield {"type": "fold_start", "kind": fold_kind}
                continue

            # Normal text — track for long-no-punct detection
            self._char_count += len(token)
            self._update_lists(token)
            if token and token[-1] in ".。!！?？\n":
                self._last_punct_at = self._char_count

            yield {"type": "text", "text": token}

        # If still folded at end of stream, flush
        if self._folded:
            content = "".join(self._buffer)
            yield {
                "type": "fold_done",
                "content": content,
                "token_count": self._token_count,
                "kind": self._fold_type,
            }

    def _detect_fold_start(self, token: str) -> str:
        """检测是否应该开始折叠."""
        combined = "".join(self._buffer[-5:] + [token]) if hasattr(self, '_buffer') else token

        # Code fence
        if self.CODE_FENCE.search(combined):
            return "code"

        # Consecutive list items
        if self.LIST_ITEM.match(combined.split("\n")[-1] if "\n" in combined else combined):
            self._consecutive_list_lines += 1
            if self._consecutive_list_lines >= 3:
                self._consecutive_list_lines = 0
                return "list"
        else:
            self._consecutive_list_lines = 0

        # Math dense
        if self.MATH_DENSE.search(combined):
            return "math"

        # Long no punctuation
        if (self._char_count - self._last_punct_at) > self.LONG_NO_PUNCT:
            self._last_punct_at = self._char_count  # reset
            return "long"

        return ""

    def _update_lists(self, token: str):
        """Track consecutive list lines."""
        if "\n" in token:
            lines = token.split("\n")
            for line in lines[1:]:  # check new lines after \n
                if self.LIST_ITEM.match(line):
                    self._consecutive_list_lines += 1
                else:
                    self._consecutive_list_lines = 0

    def _should_unfold(self) -> bool:
        """检测折叠段是否结束."""
        combined = "".join(self._buffer)

        if self._fold_type == "code":
            # Code block ends with closing ```
            count = combined.count("```")
            return count >= 2 and count % 2 == 0

        if self._fold_type == "list":
            # List ends with blank line or non-list text after list
            lines = combined.split("\n")
            if len(lines) >= 2:
                last_lines = lines[-3:]
                has_blank = any(l.strip() == "" for l in last_lines)
                has_non_list = any(
                    l.strip() and not self.LIST_ITEM.match(l)
                    for l in last_lines if l.strip()
                )
                if has_blank or has_non_list:
                    return True

        if self._fold_type == "math":
            return "\n\n" in combined[-100:] or len(self._buffer) > 50

        if self._fold_type == "long":
            return "\n" in combined[-50:] or len(combined) > 500

        return False


def deep_stream(agent, prompt: str, style: str = "prose", fold: bool = True):
    """
    深度流式 — 自动折叠 + StreamStyler 节奏.

    最优雅的流式输出方式.
    """
    from .stream_styler import StreamStyler
    from .deep_fold import DeepFolder

    folder = DeepFolder(enabled=fold)
    raw = agent.llm.stream(prompt)
    styled = StreamStyler(raw, mode=style)

    for event in folder.feed(styled):
        if event["type"] == "text":
            yield event["text"]
        elif event["type"] == "fold_start":
            placeholder = DeepFolder.FOLD_PLACEHOLDERS.get(event["kind"], "...")
            yield f"\n  {placeholder}..."
        elif event["type"] == "fold_done":
            yield f"\n  ✅ ({event['token_count']} tokens)"
