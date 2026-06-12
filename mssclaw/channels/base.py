"""
MSSclaw 通道抽象基类。

所有执行通道（null / openclaw / future: wsl2 / pipe）继承此基类。
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class Channel(ABC):
    """MSSclaw 的执行通道基类。

    子类只需实现 execute() 和 available 属性。
    不可用时不得抛异常——返回空结果或 NotImplementedError，
    由调用方决定降级策略。
    """

    @abstractmethod
    def execute(self, prompt: str, **kwargs: Any) -> str:
        """执行一次推理请求。

        Returns:
            推理结果字符串。不可用时返回空字符串 ""，不抛异常。
        """
        ...

    @property
    def available(self) -> bool:
        """通道当前是否可用。

        子类应做轻量探测（如检查可执行文件路径），
        不应在此方法中执行推理。
        """
        return True

    def health(self) -> dict[str, Any]:
        """通道健康状态（可选覆盖）。"""
        return {"available": self.available}
