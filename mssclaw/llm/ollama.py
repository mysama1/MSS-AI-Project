"""
mssclaw/llm/ollama.py — Ollama LLM connector for MSS-Agent.
Linux-compatible (uses httpx instead of urllib).

Usage:
    from mssclaw.llm.ollama import OllamaClient
    llm = OllamaClient(model="mss-ai-v3.4.3-balanced")
    response = llm("Write a function that validates tokens")
"""
from dataclasses import dataclass, field
from typing import Optional
import json

try:
    import httpx
    _HAS_HTTPX = True
except ImportError:
    import urllib.request as _urllib
    import urllib.error as _urlerror
    _HAS_HTTPX = False


@dataclass
class OllamaClient:
    """Ollama API 客户端 (跨平台: Windows + Linux)."""
    
    model: str = "mss-ai-v3.4.3-balanced"
    host: str = "http://127.0.0.1:11434"
    timeout: float = 60.0
    temperature: float = 0.7
    max_tokens: int = 2048
    system: str = ""
    
    def __post_init__(self):
        self._base = f"{self.host}/api"
    
    def __call__(self, prompt: str) -> str:
        """同步调用 Ollama, 返回文本响应."""
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": self.temperature,
                "num_predict": self.max_tokens,
            },
        }
        if self.system:
            payload["system"] = self.system
        
        data = json.dumps(payload).encode("utf-8")
        
        if _HAS_HTTPX:
            with httpx.Client(timeout=self.timeout) as client:
                resp = client.post(f"{self._base}/generate", content=data)
                resp.raise_for_status()
                result = resp.json()
        else:
            req = _urllib.Request(
                f"{self._base}/generate",
                data=data,
                headers={"Content-Type": "application/json"},
            )
            try:
                resp = _urllib.urlopen(req, timeout=self.timeout)
                result = json.loads(resp.read())
            except _urlerror.URLError as e:
                raise ConnectionError(f"Ollama not reachable at {self.host}: {e}")
        
        return result.get("response", "")

    def health(self) -> dict:
        """健康检查."""
        try:
            if _HAS_HTTPX:
                with httpx.Client(timeout=3) as c:
                    r = c.get(f"{self._base}/tags")
                    models = r.json().get("models", [])
            else:
                r = _urllib.urlopen(f"{self._base}/tags", timeout=3)
                models = json.loads(r.read()).get("models", [])
            
            return {
                "ok": True,
                "model_available": any(m["name"].startswith(self.model.split(":")[0]) for m in models),
                "model_count": len(models),
            }
        except Exception as e:
            return {"ok": False, "error": str(e)}
    
    def chat(self, messages: list[dict]) -> str:
        """Chat 模式调用 (多轮对话)."""
        payload = {
            "model": self.model,
            "messages": messages,
            "stream": False,
            "options": {
                "temperature": self.temperature,
                "num_predict": self.max_tokens,
            },
        }
        data = json.dumps(payload).encode("utf-8")
        
        if _HAS_HTTPX:
            with httpx.Client(timeout=self.timeout) as client:
                resp = client.post(f"{self._base}/chat", content=data)
                resp.raise_for_status()
                result = resp.json()
        else:
            req = _urllib.Request(
                f"{self._base}/chat",
                data=data,
                headers={"Content-Type": "application/json"},
            )
            resp = _urllib.urlopen(req, timeout=self.timeout)
            result = json.loads(resp.read())
        
        return result.get("message", {}).get("content", "")


# ── Factory ──

def get_llm(model: str = "mss-ai-v3.4.3-balanced", **kwargs) -> OllamaClient:
    """工厂函数: 获取配置好的 Ollama 客户端."""
    return OllamaClient(model=model, **kwargs)
