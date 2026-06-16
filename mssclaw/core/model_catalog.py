"""
Global Model Catalog — 全球流行模型 + 本地模型自动发现

外部模型 (云端API):
  GPT-4o, Claude 3.5, Gemini 2.0, DeepSeek V3, Grok, Qwen-Max, etc.

本地模型 (Ollama):
  自动扫描 + 自定义注册

用法:
    catalog = ModelCatalog()
    catalog.list_by_provider("deepseek")
    catalog.list_local()
    catalog.search("mss")
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Optional, Dict
from enum import Enum


class ModelProvider(Enum):
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    GOOGLE = "google"
    DEEPSEEK = "deepseek"
    META = "meta"
    MICROSOFT = "microsoft"
    XAI = "xai"
    ALIBABA = "alibaba"
    ZHIPU = "zhipu"
    MOONSHOT = "moonshot"
    BYTEDANCE = "bytedance"
    BAIDU = "baidu"
    LOCAL = "local"
    MSS = "mss"


@dataclass
class ModelSpec:
    name: str
    provider: ModelProvider
    type: str = "cloud"       # cloud | local
    context_length: int = 4096
    cost_input: float = 0.0   # $/1M tokens
    cost_output: float = 0.0
    strengths: List[str] = field(default_factory=list)
    api_endpoint: str = ""
    available_locally: bool = False


class ModelCatalog:
    """全球模型目录."""

    # ═══ 全球流行模型清单 ═══

    GLOBAL_MODELS: List[ModelSpec] = [
        # OpenAI
        ModelSpec("gpt-4o", ModelProvider.OPENAI, "cloud", 128000, 2.50, 10.00,
                  ["reasoning", "multimodal", "coding"],
                  "https://api.openai.com/v1"),
        ModelSpec("gpt-4o-mini", ModelProvider.OPENAI, "cloud", 128000, 0.15, 0.60,
                  ["fast", "cheap", "general"]),
        ModelSpec("o3-mini", ModelProvider.OPENAI, "cloud", 200000, 1.10, 4.40,
                  ["reasoning", "math", "science"]),

        # Anthropic
        ModelSpec("claude-3.5-sonnet", ModelProvider.ANTHROPIC, "cloud", 200000, 3.00, 15.00,
                  ["reasoning", "coding", "safety"]),
        ModelSpec("claude-3.5-haiku", ModelProvider.ANTHROPIC, "cloud", 200000, 0.80, 4.00,
                  ["fast", "cheap"]),

        # Google
        ModelSpec("gemini-2.0-flash", ModelProvider.GOOGLE, "cloud", 1000000, 0.10, 0.40,
                  ["multimodal", "fast", "long-context"]),
        ModelSpec("gemini-2.5-pro", ModelProvider.GOOGLE, "cloud", 1000000, 1.25, 10.00,
                  ["reasoning", "coding", "multimodal"]),

        # DeepSeek
        ModelSpec("deepseek-chat", ModelProvider.DEEPSEEK, "cloud", 128000, 0.14, 0.28,
                  ["reasoning", "coding", "cheap", "chinese"]),
        ModelSpec("deepseek-reasoner", ModelProvider.DEEPSEEK, "cloud", 128000, 0.55, 2.19,
                  ["reasoning", "math", "deep-think"]),

        # Meta (via API)
        ModelSpec("llama-3.3-70b", ModelProvider.META, "cloud", 128000, 0.59, 0.79,
                  ["general", "coding"]),
        ModelSpec("llama-3.2-3b", ModelProvider.META, "local", 128000, 0, 0,
                  ["small", "fast", "edge"]),

        # xAI
        ModelSpec("grok-2", ModelProvider.XAI, "cloud", 128000, 2.00, 10.00,
                  ["reasoning", "real-time"]),

        # Chinese providers
        ModelSpec("qwen-max", ModelProvider.ALIBABA, "cloud", 32768, 2.00, 6.00,
                  ["chinese", "reasoning", "coding"]),
        ModelSpec("qwen-turbo", ModelProvider.ALIBABA, "cloud", 1000000, 0.30, 0.60,
                  ["fast", "cheap", "chinese"]),
        ModelSpec("glm-4", ModelProvider.ZHIPU, "cloud", 128000, 50.00, 50.00,
                  ["chinese", "reasoning"]),
        ModelSpec("moonshot-v1", ModelProvider.MOONSHOT, "cloud", 128000, 12.00, 12.00,
                  ["chinese", "long-context"]),
        ModelSpec("doubao-pro", ModelProvider.BYTEDANCE, "cloud", 128000, 0.80, 2.00,
                  ["chinese", "fast", "cheap"]),
    ]

    def __init__(self):
        self._local_models: List[ModelSpec] = []
        self._scan_local()

    # ── Scan ──

    def _scan_local(self):
        """扫描本地 Ollama 模型."""
        try:
            import requests
            resp = requests.get("http://localhost:11434/api/tags", timeout=5)
            if resp.status_code == 200:
                for m in resp.json().get("models", []):
                    name = m.get("name", "unknown")
                    details = m.get("details", {})
                    size_gb = m.get("size", 0) / (1024 ** 3)

                    # Determine provider
                    provider = ModelProvider.LOCAL
                    if "mss" in name.lower():
                        provider = ModelProvider.MSS
                    elif "qwen" in name.lower():
                        provider = ModelProvider.ALIBABA
                    elif "llama" in name.lower():
                        provider = ModelProvider.META
                    elif "phi" in name.lower():
                        provider = ModelProvider.MICROSOFT

                    spec = ModelSpec(
                        name=name,
                        provider=provider,
                        type="local",
                        context_length=details.get("context_length", 2048),
                        cost_input=0,
                        cost_output=0,
                        strengths=[f"{size_gb:.1f}GB"],
                        available_locally=True,
                    )
                    self._local_models.append(spec)
        except Exception:
            pass

    def register_local(self, name: str, provider: str = "local",
                       context_length: int = 2048, strengths: list = None):
        """手动注册本地模型."""
        try:
            prov = ModelProvider(provider)
        except ValueError:
            prov = ModelProvider.LOCAL

        self._local_models.append(ModelSpec(
            name=name, provider=prov, type="local",
            context_length=context_length, strengths=strengths or [],
            available_locally=True,
        ))

    # ── Query ──

    def list_all(self) -> List[ModelSpec]:
        return self.GLOBAL_MODELS + self._local_models

    def list_cloud(self) -> List[ModelSpec]:
        return [m for m in self.GLOBAL_MODELS if m.type == "cloud"]

    def list_local(self) -> List[ModelSpec]:
        return self._local_models

    def list_by_provider(self, provider: str) -> List[ModelSpec]:
        try:
            prov = ModelProvider(provider)
        except ValueError:
            return []
        return [m for m in self.list_all() if m.provider == prov]

    def list_by_strength(self, strength: str) -> List[ModelSpec]:
        return [m for m in self.list_all() if strength in m.strengths]

    def list_mss(self) -> List[ModelSpec]:
        return [m for m in self.list_all() if m.provider == ModelProvider.MSS]

    def search(self, query: str) -> List[ModelSpec]:
        q = query.lower()
        return [
            m for m in self.list_all()
            if q in m.name.lower() or q in m.provider.value.lower()
            or any(q in s for s in m.strengths)
        ]

    # ── Stats ──

    def stats(self) -> dict:
        all_models = self.list_all()
        cloud = self.list_cloud()
        local = self.list_local()
        providers = {}
        for m in all_models:
            p = m.provider.value
            providers[p] = providers.get(p, 0) + 1

        return {
            "total": len(all_models),
            "cloud": len(cloud),
            "local": len(local),
            "mss_models": len(self.list_mss()),
            "providers": len(providers),
            "by_provider": providers,
            "top_cheap": sorted(
                [m for m in cloud if m.cost_input < 1.0],
                key=lambda m: m.cost_input,
            )[:5],
        }


def cmd_models(args_rest):
    """CLI: 模型目录."""
    catalog = ModelCatalog()

    if not args_rest:
        s = catalog.stats()
        print(f"Model Catalog: {s['total']} models ({s['cloud']} cloud + {s['local']} local)")
        print(f"  Providers: {s['providers']}")
        print(f"  MSS models: {s['mss_models']}")
        print(f"\nTop cheap cloud models:")
        for m in s['top_cheap']:
            print(f"  {m.name}: ${m.cost_input}/1M in, ${m.cost_output}/1M out")
        return

    cmd = args_rest[0]
    query = " ".join(args_rest[1:]) if len(args_rest) > 1 else ""

    if cmd == "local":
        for m in catalog.list_local():
            strengths = ", ".join(m.strengths)
            print(f"  [{m.provider.value}] {m.name} ({strengths})")
    elif cmd == "cloud":
        for m in catalog.list_cloud()[:20]:
            print(f"  [{m.provider.value}] {m.name} ctx={m.context_length} ${m.cost_input}/1M")
    elif cmd == "search" and query:
        results = catalog.search(query)
        for m in results:
            print(f"  [{m.provider.value}] {m.name} ({m.type}) {' '.join(m.strengths)}")
    elif cmd == "provider" and query:
        for m in catalog.list_by_provider(query):
            print(f"  {m.name} ctx={m.context_length}")
    elif cmd == "mss":
        for m in catalog.list_mss():
            print(f"  {m.name} ({', '.join(m.strengths)})")
    else:
        print("mssclaw models [local|cloud|search|provider|mss]")
