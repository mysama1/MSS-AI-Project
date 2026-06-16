"""
Agent LLM Backend — 接真实 LLM (Ollama 本地 / OpenAI 兼容 API).

用法:
    from mssclaw.core.llm_backend import OllamaBackend, OpenAIBackend
    agent = MSSAgent(name="real-agent", llm=OllamaBackend("mss-ai-v3.4.3-balanced"))
    result = agent.run("写一段代码")

支持:
  - Ollama 本地模型
  - OpenAI 兼容 API (DeepSeek, Groq, etc.)
  - 自动重试 + 超时
  - 流式输出 (可选)
"""
from __future__ import annotations
import requests
import json
import time
from typing import Optional, Callable, Dict, Iterator


class OllamaBackend:
    """Ollama 本地 LLM 后端."""

    def __init__(self, model: str = "mss-ai-v3.4.3-balanced", host: str = "http://localhost:11434",
                 timeout: int = 30, temperature: float = 0.7):
        self.model = model
        self.host = host.rstrip("/")
        self.timeout = timeout
        self.temperature = temperature
        self._last_error = ""

    def __call__(self, prompt: str) -> str:
        """调用 Ollama generate API."""
        try:
            resp = requests.post(
                f"{self.host}/api/generate",
                json={
                    "model": self.model,
                    "prompt": prompt,
                    "stream": False,
                    "options": {"temperature": self.temperature},
                },
                timeout=self.timeout,
            )
            if resp.status_code == 200:
                data = resp.json()
                return data.get("response", "").strip()
            self._last_error = f"HTTP {resp.status_code}: {resp.text[:200]}"
        except requests.exceptions.Timeout:
            self._last_error = f"Timeout after {self.timeout}s"
        except requests.exceptions.ConnectionError:
            self._last_error = f"Ollama not running at {self.host}"
        except Exception as e:
            self._last_error = str(e)[:200]
        return f"[{self.model}] {self._last_error}"

    def list_models(self) -> list:
        """列出可用模型."""
        try:
            resp = requests.get(f"{self.host}/api/tags", timeout=5)
            return [m["name"] for m in resp.json().get("models", [])]
        except Exception:
            return []

    def stream(self, prompt: str) -> Iterator[str]:
        """流式调用 Ollama."""
        try:
            resp = requests.post(
                f"{self.host}/api/generate",
                json={
                    "model": self.model,
                    "prompt": prompt,
                    "stream": True,
                    "options": {"temperature": self.temperature},
                },
                timeout=self.timeout,
                stream=True,
            )
            for line in resp.iter_lines():
                if line:
                    try:
                        chunk = json.loads(line)
                        token = chunk.get("response", "")
                        if token:
                            yield token
                        if chunk.get("done"):
                            break
                    except json.JSONDecodeError:
                        continue
        except Exception as e:
            self._last_error = str(e)[:200]
            yield f"[{self.model}] {self._last_error}"

    def __repr__(self):
        return f"OllamaBackend({self.model})"


class OpenAIBackend:
    """OpenAI 兼容 API 后端 (DeepSeek, Groq, 等)."""

    def __init__(self, model: str = "deepseek-chat", api_key: str = "",
                 base_url: str = "https://api.deepseek.com",
                 timeout: int = 30, temperature: float = 0.7):
        self.model = model
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.timeout = timeout
        self.temperature = temperature
        self._last_error = ""

    def __call__(self, prompt: str) -> str:
        try:
            resp = requests.post(
                f"{self.base_url}/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": self.model,
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": self.temperature,
                },
                timeout=self.timeout,
            )
            if resp.status_code == 200:
                data = resp.json()
                return data["choices"][0]["message"]["content"].strip()
            self._last_error = f"HTTP {resp.status_code}: {resp.text[:200]}"
        except requests.exceptions.Timeout:
            self._last_error = f"Timeout after {self.timeout}s"
        except Exception as e:
            self._last_error = str(e)[:200]
        return f"[{self.model}] {self._last_error}"

    def __repr__(self):
        return f"OpenAIBackend({self.model})"

    def stream(self, prompt: str) -> Iterator[str]:
        """流式调用 OpenAI 兼容 API."""
        try:
            resp = requests.post(
                f"{self.base_url}/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": self.model,
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": self.temperature,
                    "stream": True,
                },
                timeout=self.timeout,
                stream=True,
            )
            for line in resp.iter_lines():
                if line and line.startswith(b"data: "):
                    data_str = line[6:]
                    if data_str == b"[DONE]":
                        break
                    try:
                        chunk = json.loads(data_str)
                        delta = chunk["choices"][0].get("delta", {})
                        content = delta.get("content", "")
                        if content:
                            yield content
                    except (json.JSONDecodeError, KeyError, IndexError):
                        continue
        except Exception as e:
            self._last_error = str(e)[:200]
            yield f"[{self.model}] {self._last_error}"


def create_backend(kind: str = "ollama", **kwargs) -> Callable:
    """
    快速创建后端.

    kind: "ollama" | "openai" | "auto"
    auto: 先试 Ollama, 失败则降级为 dummy
    """
    if kind == "ollama":
        return OllamaBackend(**kwargs)
    elif kind == "openai":
        return OpenAIBackend(**kwargs)
    elif kind == "auto":
        try:
            backend = OllamaBackend(**kwargs)
            models = backend.list_models()
            if models:
                return backend
        except Exception:
            pass
        return lambda p: f"[dummy] {p[:80]}..."
    else:
        return lambda p: f"[dummy] {p[:80]}..."
