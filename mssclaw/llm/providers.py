"""
mssclaw/llm/providers.py — Multi-provider LLM abstraction (Chatbox pattern).

Base class LLMProvider with implementations:
  - OllamaProvider (本地)
  - OpenAIProvider (远程, API key)
  - DeepSeekProvider (远程)
  - StubProvider (测试/降级)

Usage:
    from mssclaw.llm.providers import get_provider
    llm = get_provider("ollama", model="mss-ai-v3.4.3-balanced")
    llm = get_provider("deepseek", model="deepseek-chat", api_key="...")
"""
from abc import ABC, abstractmethod
from typing import Optional
import json

try:
    import httpx
    _HAS_HTTPX = True
except ImportError:
    _HAS_HTTPX = False

if not _HAS_HTTPX:
    import urllib.request as _urllib
    import urllib.error as _urlerror


class LLMProvider(ABC):
    """LLM Provider 抽象基类."""
    
    def __init__(self, model: str, timeout: float = 60.0):
        self.model = model
        self.timeout = timeout
    
    @abstractmethod
    def generate(self, prompt: str, **kwargs) -> str:
        """生成文本响应."""
        ...
    
    @abstractmethod
    def health(self) -> dict:
        """健康检查."""
        ...
    
    def __call__(self, prompt: str, **kwargs) -> str:
        return self.generate(prompt, **kwargs)


class OllamaProvider(LLMProvider):
    """Ollama 本地 LLM Provider."""
    
    def __init__(self, model="mss-ai-v3.4.3-balanced", host="http://127.0.0.1:11434",
                 temperature=0.7, max_tokens=2048, system=""):
        super().__init__(model)
        self.host = host
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.system = system
        self._base = f"{host}/api"
    
    def generate(self, prompt: str, **kwargs) -> str:
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": kwargs.get("temperature", self.temperature),
                "num_predict": kwargs.get("max_tokens", self.max_tokens),
            },
        }
        if self.system:
            payload["system"] = self.system
        
        data = json.dumps(payload).encode("utf-8")
        if _HAS_HTTPX:
            with httpx.Client(timeout=self.timeout) as c:
                r = c.post(f"{self._base}/generate", content=data)
                r.raise_for_status()
                return r.json().get("response", "")
        else:
            req = _urllib.Request(f"{self._base}/generate", data=data,
                                  headers={"Content-Type": "application/json"})
            resp = _urllib.urlopen(req, timeout=self.timeout)
            return json.loads(resp.read()).get("response", "")
    
    def health(self) -> dict:
        try:
            if _HAS_HTTPX:
                with httpx.Client(timeout=3) as c:
                    r = c.get(f"{self._base}/tags")
                    models = r.json().get("models", [])
            else:
                r = _urllib.urlopen(f"{self._base}/tags", timeout=3)
                models = json.loads(r.read()).get("models", [])
            return {"ok": True, "model_available": any(
                m["name"].startswith(self.model.split(":")[0]) for m in models
            ), "model_count": len(models)}
        except Exception as e:
            return {"ok": False, "error": str(e)}


class OpenAIProvider(LLMProvider):
    """OpenAI / OpenAI-compatible API Provider."""
    
    def __init__(self, model="gpt-4o", api_key="", base_url="https://api.openai.com/v1",
                 temperature=0.7, max_tokens=2048):
        super().__init__(model)
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.temperature = temperature
        self.max_tokens = max_tokens
    
    def generate(self, prompt: str, **kwargs) -> str:
        payload = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": kwargs.get("temperature", self.temperature),
            "max_tokens": kwargs.get("max_tokens", self.max_tokens),
        }
        headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}
        data = json.dumps(payload).encode("utf-8")
        
        if _HAS_HTTPX:
            with httpx.Client(timeout=self.timeout) as c:
                r = c.post(f"{self.base_url}/chat/completions", content=data, headers=headers)
                r.raise_for_status()
                return r.json()["choices"][0]["message"]["content"]
        else:
            req = _urllib.Request(f"{self.base_url}/chat/completions", data=data, headers=headers)
            resp = _urllib.urlopen(req, timeout=self.timeout)
            return json.loads(resp.read())["choices"][0]["message"]["content"]
    
    def health(self) -> dict:
        return {"ok": bool(self.api_key), "provider": "openai"}


class DeepSeekProvider(OpenAIProvider):
    """DeepSeek API Provider (OpenAI-compatible endpoint)."""
    
    def __init__(self, model="deepseek-chat", api_key=""):
        super().__init__(model=model, api_key=api_key,
                        base_url="https://api.deepseek.com/v1")


class AnthropicProvider(LLMProvider):
    """Anthropic Claude API Provider."""

    def __init__(self, model="claude-sonnet-4-20250514", api_key="",
                 max_tokens=4096, temperature=0.7):
        super().__init__(model, timeout=120.0)
        self.api_key = api_key
        self.max_tokens = max_tokens
        self.temperature = temperature
        self._base = "https://api.anthropic.com/v1"

    def generate(self, prompt: str, **kwargs) -> str:
        payload = {
            "model": self.model,
            "max_tokens": kwargs.get("max_tokens", self.max_tokens),
            "temperature": kwargs.get("temperature", self.temperature),
            "messages": [{"role": "user", "content": prompt}],
        }
        headers = {
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
            "Content-Type": "application/json",
        }
        data = json.dumps(payload).encode("utf-8")
        if _HAS_HTTPX:
            with httpx.Client(timeout=self.timeout) as c:
                r = c.post(f"{self._base}/messages", content=data, headers=headers)
                r.raise_for_status()
                return r.json()["content"][0]["text"]
        else:
            req = _urllib.Request(f"{self._base}/messages", data=data, headers=headers)
            resp = _urllib.urlopen(req, timeout=self.timeout)
            return json.loads(resp.read())["content"][0]["text"]

    def health(self) -> dict:
        return {"ok": bool(self.api_key), "provider": "anthropic", "model": self.model}


class StubProvider(LLMProvider):
    """测试/降级 Provider. 返回固定文本."""
    
    def generate(self, prompt: str, **kwargs) -> str:
        return f"[STUB:{self.model}] Echo: {prompt[:60]}"
    
    def health(self) -> dict:
        return {"ok": True, "provider": "stub"}


# ── Provider Registry ──
PROVIDER_REGISTRY = {
    "ollama": OllamaProvider,
    "openai": OpenAIProvider,
    "anthropic": AnthropicProvider,
    "deepseek": DeepSeekProvider,
    "stub": StubProvider,
}

def get_provider(name: str, **kwargs) -> LLMProvider:
    """工厂函数: 按名称获取 LLM Provider."""
    cls = PROVIDER_REGISTRY.get(name.lower())
    if not cls:
        raise ValueError(f"Unknown provider: {name}. Available: {list(PROVIDER_REGISTRY.keys())}")
    return cls(**kwargs)

def list_providers() -> list[str]:
    return list(PROVIDER_REGISTRY.keys())
