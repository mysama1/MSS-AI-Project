"""
OpenClawChannel — 通过 exec 调用 OpenClaw Gateway。

⚠️ 这是 channels/ 层唯一带外部依赖的通道。
如果 Gateway 因 Job Object SIGKILL 不可用，此通道静默降级为 NullChannel 行为。

设计约束：
  - subprocess 导入放在函数内，避免顶层 import 将依赖污染到纯库主进程
  - 所有异常在 execute() 内部捕获，不向外传播
  - available 属性通过 shutil.which 做轻量探测
"""
from __future__ import annotations

from typing import Any

from .base import Channel


class OpenClawChannel(Channel):
    """通过 OpenClaw CLI 调用 Gateway 的执行通道。

    仅在 Gateway 可用时使用。不可用时静默降级——返回空字符串，
    由上层 CLI 继续使用纯库模式工作。
    """

    def __init__(self, timeout: int = 30) -> None:
        self._timeout = timeout

    def execute(self, prompt: str, **kwargs: Any) -> str:
        try:
            subprocess = self._import_subprocess()
            binary = self._resolve_binary()
            if not binary:
                return ""
            result = subprocess.run(
                [binary, "ask", "--no-stream", prompt],
                capture_output=True,
                text=True,
                timeout=self._timeout,
                shell=True,
                creationflags=self._creation_flags(),
            )
            return result.stdout.strip() if result.returncode == 0 else ""
        except Exception:
            # 通道降级：不抛异常，返回空结果。
            # 上层 CLI 继续用纯库模式工作。
            return ""

    @property
    def available(self) -> bool:
        try:
            import shutil
            return shutil.which("openclaw") is not None
        except Exception:
            return False

    def health(self) -> dict[str, Any]:
        import shutil
        path = shutil.which("openclaw")
        return {
            "available": self.available,
            "mode": "openclaw",
            "binary": path or "(not found)",
            "timeout_s": self._timeout,
        }

    # ── 内部 helpers ──

    @staticmethod
    def _resolve_binary() -> str | None:
        """解析 openclaw 可执行文件路径。
        Windows 上 openclaw 可能是 .CMD 文件，
        需要 shell=True 或直接用绝对路径。
        """
        import shutil
        return shutil.which("openclaw")

    @staticmethod
    def _import_subprocess():
        """延迟导入 subprocess，避免顶层 import 副作用。"""
        import subprocess
        return subprocess

    @staticmethod
    def _creation_flags() -> int:
        """Windows 下隐藏控制台窗口。"""
        try:
            import subprocess
            return subprocess.CREATE_NO_WINDOW  # type: ignore[attr-defined]
        except Exception:
            return 0
