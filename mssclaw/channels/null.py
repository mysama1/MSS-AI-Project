"""
NullChannel — 零开销 pass-through 通道（默认）。

不做任何推理，返回空结果。用于纯库模式——core/scanner/cli
在没有外部进程增强时保持完全可用。
"""
from __future__ import annotations

from typing import Any

from .base import Channel


class NullChannel(Channel):
    """无外部依赖的直通通道。

    所有请求返回空字符串。
    CLI 默认使用此通道，确保在没有 OpenClaw Gateway 时
    mssclaw 仍可正常运行（纯库模式）。
    """

    def execute(self, prompt: str, **kwargs: Any) -> str:
        return ""

    @property
    def available(self) -> bool:
        return True

    def health(self) -> dict[str, Any]:
        return {"available": True, "mode": "passthrough"}
