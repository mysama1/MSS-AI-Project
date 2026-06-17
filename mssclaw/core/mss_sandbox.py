#!/usr/bin/env python3
"""
MSS Sandbox — Agent-owned Python interpreter with meaning conservation.

Inspired by LLLM's AgentInterpreter (persistent namespace, timeout, stdout capture),
extended with A3 heat tax budget, Δ openness floor, and import whitelist.

Usage:
    sandbox = MSSSandbox(heat_tax_budget=0.3, delta_min=0.5)
    sandbox.inject("CALL_SKILL", skill_api_call)
    result = sandbox.run("prices = CALL_SKILL('vdp_scan', target='core.py')")
    result = sandbox.run("print(f'Found {len(prices)} vulnerabilities')")
    print(f"Heat tax: {sandbox.heat_tax_spent:.3f}, Delta: {sandbox.delta_current:.2f}")
"""
from __future__ import annotations

import contextlib
import io
import threading
import traceback
from typing import Any, Dict, List, Optional, Set


# ─── Import whitelist — MSS-meaning-field approved modules ──────
MEANING_SAFE_BUILTINS = {
    "abs", "all", "any", "ascii", "bin", "bool", "bytes", "callable",
    "chr", "complex", "dict", "dir", "divmod", "enumerate", "filter",
    "float", "format", "frozenset", "getattr", "hasattr", "hash",
    "hex", "id", "int", "isinstance", "issubclass", "iter", "len",
    "list", "map", "max", "min", "next", "object", "oct", "ord",
    "pow", "print", "range", "repr", "reversed", "round", "set",
    "slice", "sorted", "staticmethod", "str", "sum", "tuple", "type",
    "vars", "zip", "True", "False", "None", "Exception", "ValueError",
    "TypeError", "KeyError", "IndexError", "StopIteration",
}

MEANING_SAFE_IMPORTS: Set[str] = {
    "json", "re", "math", "statistics", "collections", "itertools",
    "functools", "datetime", "textwrap", "dataclasses", "typing",
    "pathlib", "copy", "enum", "pprint",
}

# Forbidden: os, sys, subprocess, shutil, socket, requests, http, urllib, etc.


class MSSSandbox:
    """
    Stateful Python interpreter for MSS agents.

    Key differences from LLLM's AgentInterpreter:
    1. Heat tax budget — execution stops when limit exceeded
    2. Delta tracking — each run() affects openness score
    3. Import whitelist — only meaning-safe modules allowed
    4. Tool signature — inject named tools with type hints

    Attributes:
        heat_tax_budget: Max cumulative heat tax allowed
        delta_min: Minimum openness threshold to allow execution
        delta_current: Current openness score
        heat_tax_spent: Cumulative heat tax consumed
        call_count: Number of run() calls (for H601 degradation detection)
    """

    def __init__(
        self,
        heat_tax_budget: float = 0.3,
        delta_min: float = 0.5,
        max_output_chars: int = 8000,
        timeout: float = 30.0,
        import_whitelist: Optional[Set[str]] = None,
    ):
        self.heat_tax_budget = heat_tax_budget
        self.delta_min = delta_min
        self.max_output_chars = max_output_chars
        self.timeout = timeout
        self.import_whitelist = import_whitelist or MEANING_SAFE_IMPORTS

        # ─── Runtime state ─────────────────────────────────────
        self.heat_tax_spent: float = 0.0
        self.delta_current: float = 0.5  # starts at neutral
        self.call_count: int = 0
        self._tools: Dict[str, Any] = {}
        self._namespace: Dict[str, Any] = self._build_base_namespace()
        self._errors: List[str] = []
        self._locked: bool = False  # locked when budget exhausted

    # ═══════════════════════════════════════════════════════════
    # Public API
    # ═══════════════════════════════════════════════════════════

    def inject(self, name: str, callable_obj: Any, delta_cost: float = 0.01):
        """Inject a named tool into the sandbox namespace.

        Args:
            name: Variable name in the sandbox (e.g. 'CALL_SKILL')
            callable_obj: The actual function
            delta_cost: Heat tax per invocation of this tool
        """
        self._tools[name] = callable_obj
        self._namespace[name] = callable_obj
        # Store delta cost on the wrapper for tracking
        self._namespace[f"_{name}_delta_cost"] = delta_cost

    def can_execute(self) -> tuple:
        """Check if sandbox can accept more code. (H648 Defer Guard pattern)"""
        if self._locked:
            return False, "Sandbox locked: heat tax budget exhausted"
        if self.delta_current < self.delta_min:
            return False, (
                f"Delta {self.delta_current:.2f} below minimum {self.delta_min:.2f}. "
                f"Suggestion: introduce new information before continuing."
            )
        if self.heat_tax_spent >= self.heat_tax_budget:
            return False, (
                f"Heat tax {self.heat_tax_spent:.3f} >= budget {self.heat_tax_budget:.3f}. "
                f"Budget exhausted."
            )
        return True, "OK"

    def run(self, code: str, base_delta_cost: float = 0.02) -> str:
        """Execute code in the persistent namespace.

        Returns captured stdout or a formatted traceback.

        Raises RuntimeError if heat tax budget exhausted.

        Args:
            code: Python source to execute
            base_delta_cost: Heat tax cost for this execution (before tool calls)
        """
        ok, reason = self.can_execute()
        if not ok:
            raise RuntimeError(reason)

        self.call_count += 1
        self.heat_tax_spent += base_delta_cost

        captured = io.StringIO()
        exc_holder: list = []

        def _do_run() -> None:
            try:
                with contextlib.redirect_stdout(captured):
                    exec(code, self._namespace)
            except Exception as exc:
                exc_holder.append(exc)

        thread = threading.Thread(target=_do_run, daemon=True)
        thread.start()
        thread.join(self.timeout)

        if thread.is_alive():
            self.heat_tax_spent += 0.05  # timeout penalty
            raise TimeoutError(
                f"Sandbox execution timed out after {self.timeout:.0f}s. "
                f"Heat tax penalty +0.05 applied."
            )

        if exc_holder:
            exc = exc_holder[0]
            output = "".join(
                traceback.format_exception(type(exc), exc, exc.__traceback__)
            )
            self.delta_current -= 0.02  # error reduces openness
            self._errors.append(f"run#{self.call_count}: {type(exc).__name__}: {exc}")
        else:
            output = captured.getvalue()
            # Successful execution increases delta slightly
            self.delta_current = min(1.0, self.delta_current + 0.01)

        # Check budget after execution
        if self.heat_tax_spent >= self.heat_tax_budget:
            self._locked = True

        return self._maybe_truncate(output)

    def reset(self) -> None:
        """Reset sandbox for a new agent session."""
        self.heat_tax_spent = 0.0
        self.delta_current = 0.5
        self.call_count = 0
        self._locked = False
        self._errors.clear()
        self._namespace = self._build_base_namespace()
        # Re-inject tools
        for name, obj in self._tools.items():
            self._namespace[name] = obj

    def status(self) -> Dict[str, Any]:
        """Return sandbox status for observability."""
        degradation_risk = 1.0 - (1 - 0.01) ** (self.call_count // 3) if self.call_count >= 3 else 0.0
        return {
            "heat_tax_spent": round(self.heat_tax_spent, 3),
            "heat_tax_budget": self.heat_tax_budget,
            "delta_current": round(self.delta_current, 2),
            "delta_min": self.delta_min,
            "call_count": self.call_count,
            "locked": self._locked,
            "degradation_risk": round(degradation_risk, 3),
            "errors": self._errors[-3:],  # last 3 errors
        }

    # ═══════════════════════════════════════════════════════════
    # Internal
    # ═══════════════════════════════════════════════════════════

    def _build_base_namespace(self) -> Dict[str, Any]:
        import builtins as _bt
        safe_builtins = {
            k: getattr(_bt, k) for k in MEANING_SAFE_BUILTINS
            if hasattr(_bt, k)
        }
        # Gate all `import` statements through the whitelist
        safe_builtins["__import__"] = self._import_gate
        return {
            "__builtins__": safe_builtins,
        }

    def _import_gate(self, name: str, globals=None, locals=None, fromlist=(), level: int = 0):
        """Import whitelist gatekeeper. Python's __import__ signature."""
        # Extract base module name (before first dot)
        base = name.split(".")[0]
        if base not in self.import_whitelist:
            raise ImportError(
                f"Module '{base}' is not in the MSS meaning-safe import list. "
                f"Allowed: {sorted(self.import_whitelist)}"
            )
        return __import__(name, globals, locals, fromlist, level)

    def _maybe_truncate(self, text: str) -> str:
        if self.max_output_chars and len(text) > self.max_output_chars:
            return text[:self.max_output_chars] + f"\n... (truncated at {self.max_output_chars} chars)"
        return text


# ─── Demo ─────────────────────────────────────────────────────

if __name__ == "__main__":
    print("=" * 60)
    print("  MSS Sandbox — Agent-owned Python with meaning constraints")
    print("=" * 60)

    sb = MSSSandbox(heat_tax_budget=0.3, delta_min=0.5)

    # Inject a mock skill API
    def mock_skill(endpoint: str, **kwargs):
        if endpoint == "vdp_scan":
            return [{"file": "core.py", "rule": "B602", "severity": "HIGH"}]
        return {"error": "unknown endpoint"}

    sb.inject("CALL_SKILL", mock_skill, delta_cost=0.02)

    # Session simulation
    print("\n[1] First call — scan for vulnerabilities:")
    r = sb.run(
        "vulns = CALL_SKILL('vdp_scan', target='core.py')\n"
        "print(f'Found {len(vulns)} vulnerabilities')"
    )
    print(f"  {r.strip()}")
    print(f"  Status: {sb.status()}")

    print("\n[2] Data processing (separate session):")
    sb2 = MSSSandbox(heat_tax_budget=0.3, delta_min=0.5)
    sb2.inject("CALL_SKILL", mock_skill, delta_cost=0.02)
    sb2.run("vulns = CALL_SKILL('vdp_scan', target='core.py')")
    r = sb2.run(
        "import json\n"
        "data = json.dumps(vulns, indent=2) if 'vulns' in dir() else '[]'\n"
        "print(data)"
    )
    print(f"  {r.strip()}")
    print(f"  Status: {sb2.status()}")

    print("\n[3] Error handling — division by zero (delta should drop):")
    sb3 = MSSSandbox(heat_tax_budget=0.3, delta_min=0.4)
    r = sb3.run("result = 1/0  # deliberate error")
    print(f"  {r.strip()[:100]}...")
    print(f"  Delta: {sb3.delta_current:.2f} (dropped from 0.50)")

    print("\n[4] Import gate — os is blocked:")
    sb4 = MSSSandbox(heat_tax_budget=0.3, delta_min=0.5)
    r = sb4.run("import os; print(os.name)")
    print(f"  → {r.strip()[:80]}...")

    print("\n[5] Import gate — json is allowed:")
    sb5 = MSSSandbox(heat_tax_budget=0.3, delta_min=0.5)
    r = sb5.run("import json; print(json.dumps({'key': 'val'}))")
    print(f"  {r.strip()}")

    print("\n[6] Heat tax approaching budget:")
    sb6 = MSSSandbox(heat_tax_budget=0.3, delta_min=0.5)
    for i in range(20):
        try:
            sb6.run("x = 1 + 1")
        except RuntimeError:
            break
    print(f"  Locked: {sb6._locked}, Heat tax: {sb6.heat_tax_spent:.3f}/{sb6.heat_tax_budget:.3f}")
    print(f"  Calls before lock: {sb6.call_count}")
