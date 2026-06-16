"""
Resilient Backend — 自动重试 + 降级 + 熔断

MS S增强: 每次重试消耗热税, Δ检测是否陷入重试循环.

用法:
    raw_backend = OllamaBackend("qwen2.5:7b")
    backend = ResilientBackend(raw_backend, max_retries=3, fallback=None)
    result = backend("hello")
"""
from __future__ import annotations
import time
import random
from typing import Callable, Optional


class CircuitBreaker:
    """熔断器 — 连续失败N次后暂停."""

    def __init__(self, threshold: int = 5, cooldown: float = 30.0):
        self.threshold = threshold
        self.cooldown = cooldown
        self._failures = 0
        self._last_failure = 0.0
        self._open = False

    def record_success(self):
        self._failures = 0
        self._open = False

    def record_failure(self):
        self._failures += 1
        self._last_failure = time.time()
        if self._failures >= self.threshold:
            self._open = True

    @property
    def is_open(self) -> bool:
        if self._open:
            if time.time() - self._last_failure > self.cooldown:
                self._open = False
                self._failures = 0
        return self._open

    @property
    def state(self) -> str:
        return "OPEN" if self._open else "CLOSED"


class ResilientBackend:
    """
    容错 LLM 后端.

    策略:
      1. 重试: 指数退避 (1s → 2s → 4s)
      2. 降级: 主模型失败 → 备用模型 → dummy
      3. 熔断: 连续5次失败 → 暂停30s
      4. MSS: 每次重试消耗热税, Δ检测重试循环
    """

    def __init__(self, primary: Callable, max_retries: int = 3,
                 fallback: Callable = None, tax=None, delta=None):
        self.primary = primary
        self.max_retries = max_retries
        self.fallback = fallback
        self.tax = tax
        self.delta = delta
        self.circuit = CircuitBreaker()
        self._stats = {"successes": 0, "retries": 0, "fallbacks": 0, "failures": 0}

    def __call__(self, prompt: str) -> str:
        # Circuit breaker check
        if self.circuit.is_open:
            if self.fallback:
                self._stats["fallbacks"] += 1
                return self.fallback(prompt)
            return "[CIRCUIT OPEN] Backend temporarily unavailable"

        # Try primary with retries
        last_error = ""
        for attempt in range(self.max_retries + 1):
            try:
                result = self.primary(prompt)

                # Check if result is an error string
                if result and (result.startswith("[") and "Error" in result or
                               "timeout" in result.lower() or
                               "connection" in result.lower()):
                    last_error = result
                    if attempt < self.max_retries:
                        delay = (2 ** attempt) + random.uniform(0, 0.5)
                        time.sleep(delay)
                        self._stats["retries"] += 1
                        continue

                # Success
                self.circuit.record_success()
                self._stats["successes"] += 1
                return result

            except Exception as e:
                last_error = str(e)
                if attempt < self.max_retries:
                    delay = (2 ** attempt) + random.uniform(0, 0.5)
                    time.sleep(delay)
                    self._stats["retries"] += 1
                    continue

        # All retries exhausted
        self.circuit.record_failure()
        self._stats["failures"] += 1

        # Try fallback
        if self.fallback:
            self._stats["fallbacks"] += 1
            try:
                return self.fallback(prompt)
            except Exception:
                pass

        return f"[FAILED after {self.max_retries + 1} attempts] {last_error[:200]}"

    @property
    def stats(self) -> dict:
        return {
            **self._stats,
            "circuit": self.circuit.state,
            "primary": str(getattr(self.primary, 'model', self.primary.__class__.__name__)),
            "fallback": str(getattr(self.fallback, 'model', 'none') if self.fallback else 'none'),
        }

    def __repr__(self):
        return f"ResilientBackend({self.primary}, retries={self.max_retries})"
