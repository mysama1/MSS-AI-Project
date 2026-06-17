#!/usr/bin/env python3
"""
MSS Tactic — agentic system as a pure function with heat tax accounting.

Architecture inspired by LLLM's Tactic (task → result, stateless, agents as callers),
extended with A3 heat tax metering and Δ openness tracking.

Usage:
    tactic = CodeReviewTactic()
    result, report = tactic(task="review mssclaw/core/")
    print(f"Result: {result}")
    print(f"Heat tax: {report.total_heat_tax:.3f}")
    print(f"Delta: {report.delta_closing:.3f}")
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional
import time


@dataclass
class TacticStep:
    """A single step in a Tactic execution — one agent invocation."""
    agent_name: str
    action: str                    # "receive", "respond", "tool_call", "fork", "merge"
    heat_tax: float                # A3: heat tax incurred
    delta_change: float            # Δ change (+ = more open, - = closing)
    token_count: int = 0
    latency_ms: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class TacticReport:
    """Heat tax + delta report for a Tactic execution."""
    task: str
    steps: List[TacticStep] = field(default_factory=list)
    total_heat_tax: float = 0.0
    delta_start: float = 0.5
    delta_end: float = 0.5
    elapsed_ms: float = 0.0
    success: bool = True
    errors: List[str] = field(default_factory=list)

    @property
    def delta_closing(self) -> float:
        """How much Δ closed during execution (negative = opened)."""
        return self.delta_end - self.delta_start

    @property
    def l0_heat_tax(self) -> float:
        """L0: Physical heat tax (latency/power)."""
        return self.elapsed_ms / 1000.0 * 0.001  # ~0.001 per second

    @property
    def l1_heat_tax(self) -> float:
        """L1: Logical heat tax (token count/proportional to computation)."""
        total_tokens = sum(s.token_count for s in self.steps)
        return total_tokens / 100_000.0 * 0.1  # ~0.1 per 100K tokens

    @property
    def l2_heat_tax(self) -> float:
        """L2: Meaning heat tax (steps without delta gain)."""
        zero_gain_steps = [s for s in self.steps if s.delta_change <= 0]
        return len(zero_gain_steps) * 0.05  # 0.05 per wasted step

    def summary(self) -> str:
        return (
            f"Tactic: {self.task[:50]} | "
            f"Steps: {len(self.steps)} | "
            f"Heat: {self.total_heat_tax:.3f} (L0={self.l0_heat_tax:.3f} "
            f"L1={self.l1_heat_tax:.3f} L2={self.l2_heat_tax:.3f}) | "
            f"Δ: {self.delta_start:.2f}→{self.delta_end:.2f} " +
            (f"({self.delta_closing:+.2f})" if self.delta_closing != 0 else "(stable)")
        )


class MSSTactic:
    """
    Base class for MSS tactics — like LLLM's Tactic but with heat tax accounting.

    Subclass and override call().
    """

    name: str = "base_tactic"
    description: str = ""
    agents: Dict[str, Any] = {}  # agent_name → agent_instance

    def __init__(self):
        self.report: Optional[TacticReport] = None

    def record(self, agent_name: str, action: str, heat_tax: float = 0.0,
               delta_change: float = 0.0, token_count: int = 0, latency_ms: float = 0.0,
               **metadata) -> TacticStep:
        """Record a step in the tactic execution."""
        step = TacticStep(
            agent_name=agent_name, action=action,
            heat_tax=heat_tax, delta_change=delta_change,
            token_count=token_count, latency_ms=latency_ms,
            metadata=metadata,
        )
        if self.report:
            self.report.steps.append(step)
            self.report.total_heat_tax += heat_tax
        return step

    def call(self, task: str) -> tuple:
        """
        Execute the tactic. Override in subclasses.

        Returns (result, TacticReport).
        """
        t0 = time.time()
        self.report = TacticReport(task=task)

        try:
            result = self._run(task)
        except Exception as e:
            self.report.success = False
            self.report.errors.append(str(e))
            result = None

        self.report.elapsed_ms = (time.time() - t0) * 1000
        return result, self.report

    def _run(self, task: str) -> Any:
        """Override this in subclasses. Default: single-agent pass-through."""
        raise NotImplementedError("Subclass must implement _run()")


# ─── Demo ─────────────────────────────────────────────────────

@dataclass
class MockAgent:
    """Minimal agent stub for demo."""
    name: str
    respond_count: int = 0
    tools_called: int = 0

    def receive(self, text: str):
        pass

    def respond(self) -> str:
        self.respond_count += 1
        return f"[{self.name}] Analysis complete."

    def call_tool(self, tool_name: str, **kwargs):
        self.tools_called += 1
        return {"status": "ok", "tool": tool_name}


class CodeReviewTactic(MSSTactic):
    """Demo: A two-agent code review tactic."""

    name = "code_review"
    description = "Review code and synthesize findings using two agents."
    
    def __init__(self):
        super().__init__()
        self.agents = {
            "scanner": MockAgent(name="scanner"),
            "synthesizer": MockAgent(name="synthesizer"),
        }

    def _run(self, task: str) -> str:
        scanner = self.agents["scanner"]
        synth = self.agents["synthesizer"]

        # Step 1: Scanner analyzes code
        scanner.receive(f"Scan target: {task}")
        self.record("scanner", "receive", heat_tax=0.01, delta_change=0.0)
        
        scanner.respond()
        self.record("scanner", "respond", heat_tax=0.05, delta_change=+0.1,
                    token_count=200, metadata={"scan_depth": "full"})

        # Step 2: Scanner calls tool
        scanner.call_tool("ruff_check", target=task)
        self.record("scanner", "tool_call", heat_tax=0.03, delta_change=+0.05,
                    tool="ruff_check", target=str(task))

        # Step 3: Synthesizer receives scanner results
        synth.receive(f"Scanner found issues in {task}")
        self.record("synthesizer", "receive", heat_tax=0.01, delta_change=0.0)

        synth.respond()
        self.record("synthesizer", "respond", heat_tax=0.05, delta_change=+0.08,
                    token_count=150)

        # Update final delta
        self.report.delta_end = 0.73  # 0.5 + 0.1 + 0.05 + 0.08
        
        return f"Review complete for {task}: 3 issues found, severity medium."


if __name__ == "__main__":
    tactic = CodeReviewTactic()
    result, report = tactic.call(task="mssclaw/core/pipeline.py")
    
    print("=" * 60)
    print(f"  MSS Tactic Demo: {tactic.name}")
    print("=" * 60)
    print(f"  Result: {result}")
    print(f"  {report.summary()}")
    print()
    for i, step in enumerate(report.steps, 1):
        print(f"  [{i}] {step.agent_name}::{step.action} "
              f"heat={step.heat_tax:.3f} Δ={step.delta_change:+.2f} "
              f"tokens={step.token_count} lat={step.latency_ms:.1f}ms")
