"""
MSSclaw 通道层入口。

默认不导入任何通道实现。调用方通过 get_channel(name) 按需获取：
  - get_channel("null")    → NullChannel（零开销，默认）
  - get_channel("openclaw") → OpenClawChannel（延迟导入，失败回退 null）

设计原则：
  1. 顶层 import 不触发任何外部依赖（subprocess / shutil 等）
  2. 通道注册是懒加载的——只在 get_channel 被调用时才 import 具体模块
  3. 任何通道加载失败都静默降级为 NullChannel
"""
from __future__ import annotations

from .base import Channel
from .null import NullChannel

# 已确认安全的通道直接注册
_CHANNEL_FACTORIES: dict[str, "() -> Channel"] = {
    "null": lambda: NullChannel(),
}


def get_channel(name: str) -> Channel:
    """按名称获取通道实例。

    支持的通道名：
      "null"     — 零开销 pass-through（默认）
      "openclaw" — 通过 OpenClaw CLI 调用 Gateway（延迟导入，失败回退 null）

    未识别的名称返回 NullChannel，不抛异常。
    """
    if name in _CHANNEL_FACTORIES:
        return _CHANNEL_FACTORIES[name]()

    if name == "openclaw":
        return _try_load_openclaw()

    return NullChannel()


def list_channels() -> list[str]:
    """列出所有已注册和可探测的通道名。"""
    names = list(_CHANNEL_FACTORIES.keys())

    # 探测 openclaw
    try:
        from .openclaw import OpenClawChannel
        if OpenClawChannel().available:
            names.append("openclaw")
    except Exception:
        pass

    return names


def register_channel(name: str, factory: "() -> Channel") -> None:
    """运行时注册新通道。

    第三方可通过此接口注册自定义通道，
    无需修改 channels/ 源码。
    """
    _CHANNEL_FACTORIES[name] = factory


# ── 内部 ──

def _try_load_openclaw() -> Channel:
    """延迟导入 OpenClawChannel，失败回退 NullChannel。"""
    try:
        from .openclaw import OpenClawChannel
        ch = OpenClawChannel()
        if ch.available:
            return ch
    except Exception:
        pass
    return NullChannel()
