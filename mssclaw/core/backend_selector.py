"""
Smart Backend Selector — 壳用API(快) + 核用本地mss-ai(专)

策略:
  壳 (Shell): 优先 API → Ollama → dummy
  核 (Core):  优先 本地mss-ai → Ollama → 无核模式
  API来源: Vault 保险箱 (自动读取)

设计原则:
  - 壳要快: 90% 任务走 API
  - 核要专: 只在审核/升维时调用本地mss-ai
  - 自动降级: API不可用→本地Ollama→标记降级
"""
from __future__ import annotations
import time
from typing import Callable, Optional


class BackendSelector:
    """
    智能后端选择器.

    自动检测 + 从 Vault 读取 API keys.
    """

    def __init__(self, vault=None):
        self._vault = vault
        self._shell_backend: Optional[Callable] = None
        self._core_backend: Optional[Callable] = None
        self._available: dict = {"ollama": False, "api": False, "mss_local": False}
        self._scan()

    def _scan(self):
        """扫描可用后端."""
        # Check Ollama
        try:
            from mssclaw.core.llm_backend import OllamaBackend
            be = OllamaBackend("qwen2.5:7b", timeout=3)
            models = be.list_models()
            if models:
                self._available["ollama"] = True
                if any("mss" in m.lower() for m in models):
                    self._available["mss_local"] = True
        except Exception:
            pass

        # Check API keys in vault
        if self._vault and not self._vault.is_locked:
            api_key = self._vault.get("openai_key") or self._vault.get("deepseek_key")
            if api_key:
                self._available["api"] = True

    def select_shell(self, prefer: str = "api") -> Callable:
        """选择壳后端."""
        from mssclaw.core.llm_backend import OllamaBackend, OpenAIBackend

        # 1. Try API (from vault)
        if prefer == "api" and self._vault and not self._vault.is_locked:
            api_key = None
            base_url = "https://api.deepseek.com"
            model = "deepseek-chat"

            # Try deepseek first
            key = self._vault.get("deepseek_key")
            if key:
                api_key = key
            else:
                key = self._vault.get("openai_key")
                if key:
                    api_key = key
                    base_url = "https://api.openai.com"
                    model = "gpt-3.5-turbo"

            if api_key:
                return OpenAIBackend(model=model, api_key=api_key, base_url=base_url)

        # 2. Try Ollama
        if self._available["ollama"]:
            return OllamaBackend("qwen2.5:7b", timeout=30)

        # 3. Dummy fallback
        return lambda p: f"[dummy shell] {p[:80]}..."

    def select_core(self) -> Optional[Callable]:
        """选择核后端 (必须本地mss-ai)."""
        from mssclaw.core.llm_backend import OllamaBackend

        # 1. Try mss-ai local
        if self._available["mss_local"]:
            return OllamaBackend("mss-ai-v3.4.3-balanced", timeout=30)

        # 2. Fallback: any Ollama model
        if self._available["ollama"]:
            return OllamaBackend("qwen2.5:7b", timeout=30)

        # 3. No core available → return None (shell-only mode)
        return None

    def create_shell(self, vault=None, prefer="api"):
        """快速创建 MSS Shell (自动选择后端)."""
        from mssclaw.core.mss_shell import MSSShell, ShellConfig, CoreConfig

        if vault:
            self._vault = vault
        self._scan()

        shell_be = self.select_shell(prefer=prefer)
        core_be = self.select_core()

        # Configure based on available backends
        shell_config = ShellConfig(
            role="AI assistant",
            style="prose",
            system_prompt="Be helpful and accurate.",
        )
        core_config = CoreConfig()

        shell = MSSShell(
            shell_llm=shell_be,
            core_llm=core_be or shell_be,  # fallback: core = shell
            shell_config=shell_config,
            core_config=core_config,
        )

        # Tag which backend is being used
        shell._backend_info = {
            "shell_type": type(shell_be).__name__,
            "core_type": type(core_be).__name__ if core_be else "none",
            "shell_model": getattr(shell_be, 'model', 'dummy'),
            "core_model": getattr(core_be, 'model', 'none') if core_be else 'none',
        }

        return shell

    def status(self) -> dict:
        return {
            "available": self._available,
            "shell_type": type(self._shell_backend).__name__ if self._shell_backend else "unset",
            "core_type": type(self._core_backend).__name__ if self._core_backend else "unset",
            "recommendation": (
                "API Shell + Local Core" if self._available["api"] and self._available["mss_local"]
                else "Ollama only" if self._available["ollama"]
                else "No backend available"
            ),
        }
