"""
MSS Tool Provider — Dify/外部工具箱吸收桥接层

吸收策略: 不重写工具, 包装一层热税/Δ/信任预算的门面。
Dify内置工具 (~50+): Google/Bing/Wikipedia/Code/Slack/Email/PDF/Scraper...
全部通过 HTTP API 可调用 → MSS 零代码复用。

Auth: Provider autodiscovery from Dify's tool catalog.
"""

from __future__ import annotations
import time
import json
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Callable
from enum import Enum


# ─── Tool Heat Tax Tracking ──────────────────────────────

class ToolHeatTaxTracker:
    """Track per-tool heat tax (L0 time + L1 args size + L2 meaning waste)."""

    def __init__(self):
        self._records: List[Dict[str, Any]] = []
        self._budget: Dict[str, float] = {}

    def record(self, tool_name: str, elapsed: float, result: Any = None):
        """Record a tool invocation for heat tax accounting."""
        l0 = min(1.0, elapsed / 10.0)  # L0: physical time (10s = 100%)
        l2 = 0.0  # L2: meaning waste (placeholder, need LLM judge)
        composite = l0 * 0.4 + l2 * 0.6

        self._records.append({
            "tool": tool_name,
            "elapsed": round(elapsed, 3),
            "l0": round(l0, 3),
            "l2": round(l2, 3),
            "composite": round(composite, 3),
            "time": time.time(),
        })
        self._budget[tool_name] = self._budget.get(tool_name, 0) + composite

    def get_budget(self, tool_name: str) -> float:
        """Get accumulated heat tax for a tool."""
        return self._budget.get(tool_name, 0)

    def get_recent(self, limit: int = 10) -> List[Dict]:
        return self._records[-limit:]

    def summary(self) -> Dict[str, Any]:
        return {
            "total_invocations": len(self._records),
            "total_heat_tax": round(sum(r["composite"] for r in self._records), 3),
            "by_tool": dict(sorted(self._budget.items(), key=lambda x: x[1], reverse=True)),
        }


# ─── Dify Tool Bridge ─────────────────────────────────────

class DifyToolProvider:
    """Bridge to Dify's builtin tool ecosystem.

    Dify exposes tools as HTTP endpoints (Plugin daemon pattern):
        POST /v1/tools/{provider}/{tool}/invoke

    This provider wraps those calls with MSS heat tax + trust budget tracking.
    """

    def __init__(
        self,
        dify_api_url: str = "http://localhost:5001",
        api_key: Optional[str] = None,
    ):
        self.api_url = dify_api_url
        self.api_key = api_key
        self.heat_tax = ToolHeatTaxTracker()
        self._catalog: Optional[Dict[str, List[Dict]]] = None

    def _call(self, provider: str, tool: str, params: Dict) -> Dict:
        """Raw API call to Dify tool."""
        import requests
        url = f"{self.api_url}/v1/tools/{provider}/{tool}/invoke"
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        resp = requests.post(url, json=params, headers=headers, timeout=30)
        resp.raise_for_status()
        return resp.json()

    def invoke(
        self,
        provider: str,
        tool: str,
        params: Dict[str, Any],
        trust_budget: float = 1.0,
    ) -> Dict[str, Any]:
        """Invoke Dify tool with MSS tracking overlay.

        Returns enriched result: {result, mss: {heat_tax, delta, ...}}
        """
        if trust_budget < 0.3:
            return {
                "error": "trust_budget_insufficient",
                "required": 0.3,
                "available": trust_budget,
            }

        start = time.time()
        try:
            raw = self._call(provider, tool, params)
            elapsed = time.time() - start
            self.heat_tax.record(f"{provider}/{tool}", elapsed, raw)

            return {
                "result": raw,
                "mss_overlay": {
                    "elapsed_ms": round(elapsed * 1000),
                    "heat_tax_l0": round(min(1.0, elapsed / 10.0), 3),
                    "trust_budget_consumed": round(0.02 * (1 + len(json.dumps(params)) / 1000), 4),
                }
            }
        except Exception as e:
            elapsed = time.time() - start
            self.heat_tax.record(f"{provider}/{tool}", elapsed)
            return {"error": str(e), "elapsed_ms": round(elapsed * 1000)}

    def catalog(self) -> Dict[str, Any]:
        """Discover available Dify tools (from plugin daemon)."""
        if self._catalog:
            return self._catalog

        import requests
        try:
            resp = requests.get(f"{self.api_url}/v1/tools", timeout=5)
            self._catalog = resp.json()
        except Exception:
            self._catalog = {
                "builtin": [
                    {"provider": "google", "tools": ["search"]},
                    {"provider": "wikipedia", "tools": ["search"]},
                    {"provider": "code", "tools": ["execute"]},
                    {"provider": "time", "tools": ["current_time"]},
                    {"provider": "webscraper", "tools": ["scrape"]},
                ]
            }
        return self._catalog

    # ─── Convenience methods ───

    def search_web(self, query: str, provider: str = "google") -> Dict:
        return self.invoke(provider, "search", {"query": query})

    def fetch_page(self, url: str) -> Dict:
        return self.invoke("webscraper", "scrape", {"url": url})

    def execute_code(self, code: str, language: str = "python") -> Dict:
        return self.invoke("code", "execute", {"code": code, "language": language})

    def current_time(self) -> Dict:
        return self.invoke("time", "current_time", {})


# ─── Tool Registry (MSS-native) ───────────────────────────

@dataclass
class MSSTool:
    """MSS-native tool definition with heat tax metadata."""
    name: str
    description: str
    provider: str  # "builtin" | "dify" | "ollama" | "custom"
    heat_tax_cost: float = 0.01  # estimated heat tax per invocation
    trust_budget_required: float = 0.1
    fn: Optional[Callable] = None
    params_schema: Dict[str, Any] = field(default_factory=dict)


class MSSToolRegistry:
    """Unified tool registry — MSS native + Dify bridge + custom."""

    def __init__(self, dify_provider: Optional[DifyToolProvider] = None):
        self.tools: Dict[str, MSSTool] = {}
        self.dify = dify_provider
        self._register_builtins()

    def _register_builtins(self):
        """Register MSS-native tools."""
        self.register(MSSTool(
            name="web_search",
            description="Search the web",
            provider="builtin",
            heat_tax_cost=0.05,
        ))
        self.register(MSSTool(
            name="code_execute",
            description="Execute Python code",
            provider="builtin",
            heat_tax_cost=0.02,
        ))
        self.register(MSSTool(
            name="kb_lookup",
            description="Look up MSS knowledge base entry",
            provider="builtin",
            heat_tax_cost=0.005,
            trust_budget_required=0.05,
        ))
        self.register(MSSTool(
            name="delta_check",
            description="Check Δ openness of a concept",
            provider="builtin",
            heat_tax_cost=0.01,
        ))

    def register(self, tool: MSSTool):
        self.tools[tool.name] = tool

    def get(self, name: str) -> Optional[MSSTool]:
        return self.tools.get(name)

    def list_by_provider(self, provider: str) -> List[MSSTool]:
        return [t for t in self.tools.values() if t.provider == provider]

    def get_heat_tax_estimate(self, tool_names: List[str]) -> float:
        """Estimate total heat tax for a tool chain."""
        total = 0.0
        for name in tool_names:
            tool = self.tools.get(name)
            if tool:
                total += tool.heat_tax_cost
        return round(total, 4)


# ─── Demo ─────────────────────────────────────────────────

if __name__ == "__main__":
    # MSS tool registry
    registry = MSSToolRegistry()
    print("=== MSS Tool Registry ===")
    for name, tool in registry.tools.items():
        print(f"  {name:15s} | heat: {tool.heat_tax_cost:0.3f} | trust: {tool.trust_budget_required:0.2f}")

    # Dify bridge (offline demo)
    dify = DifyToolProvider()
    catalog = dify.catalog()
    print(f"\n=== Dify Tool Catalog (offline) ===")
    for provider in catalog.get("builtin", []):
        print(f"  {provider['provider']:12s} → {', '.join(provider['tools'])}")

    # Heat tax demo
    tracker = ToolHeatTaxTracker()
    tracker.record("google/search", 0.8)
    tracker.record("code/execute", 1.2)
    tracker.record("google/search", 0.3)
    print(f"\n=== Heat Tax Summary ===")
    print(json.dumps(tracker.summary(), indent=2))
