"""MSS-Agent DeepSeek LLM Provider.

Native DeepSeek API integration (V4-Pro / V4-Flash).

Usage:
    from mss_agent.llm.deepseek import DeepSeekLLM
    agent = MSSAgent(name="test", llm=DeepSeekLLM(model="deepseek-chat"))
"""
import json
import os
from typing import Optional, Callable

try:
    from openai import OpenAI
except ImportError:
    OpenAI = None


class DeepSeekLLM:
    """DeepSeek API 适配器。OpenAI 兼容协议。"""

    BASE_URL = "https://api.deepseek.com"

    def __init__(
        self,
        model: str = "deepseek-chat",
        api_key: Optional[str] = None,
        temperature: float = 0.0,
        max_tokens: int = 4096,
    ):
        if OpenAI is None:
            raise ImportError("openai package required. Install: pip install openai")
        self.model = model
        self.api_key = api_key or os.environ.get("DEEPSEEK_API_KEY", "")
        self.temperature = temperature
        self.max_tokens = max_tokens
        self._client = OpenAI(
            api_key=self.api_key,
            base_url=self.BASE_URL,
        )

    def __call__(self, prompt: str) -> str:
        response = self._client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            temperature=self.temperature,
            max_tokens=self.max_tokens,
        )
        return response.choices[0].message.content or ""

    @classmethod
    def from_env(cls, model: str = "deepseek-chat") -> "DeepSeekLLM":
        """从环境变量 DEEPSEEK_API_KEY 创建。"""
        return cls(
            model=model,
            api_key=os.environ.get("DEEPSEEK_API_KEY", ""),
        )


class DeepSeekReasoner:
    """DeepSeek Reasoner (V4-Pro) — 支持 reasoning_content。"""

    BASE_URL = "https://api.deepseek.com"

    def __init__(
        self,
        model: str = "deepseek-reasoner",
        api_key: Optional[str] = None,
    ):
        if OpenAI is None:
            raise ImportError("openai package required. Install: pip install openai")
        self.model = model
        self.api_key = api_key or os.environ.get("DEEPSEEK_API_KEY", "")
        self._client = OpenAI(
            api_key=self.api_key,
            base_url=self.BASE_URL,
        )

    def __call__(self, prompt: str) -> str:
        response = self._client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
        )
        msg = response.choices[0].message
        # Some versions include reasoning_content
        reasoning = getattr(msg, "reasoning_content", None)
        content = msg.content or ""
        if reasoning:
            return f"[Reasoning]\n{reasoning}\n\n[Answer]\n{content}"
        return content
