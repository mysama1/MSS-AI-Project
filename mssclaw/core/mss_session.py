#!/usr/bin/env python3
"""
MSS Session — persistent agent session with cost/identity/history/fork.

Inspired by OpenClaw's session system (~30 modules):
- session-store → JSON persistence + write-lock
- session-cost-usage → Token counting
- session-fork → Clone/restore sessions
- session-hooks → Lifecycle callbacks (pre/post run)
- session-identity → Who owns this session

Differences from OpenClaw:
- Heat tax tracking instead of just token counting
- Delta history instead of just transcript
- Mollting support (self-evolution vs static)
"""

from __future__ import annotations
import json
import time
import threading
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional
import os


# ─── Data models ────────────────────────────────────────────

@dataclass
class SessionStep:
    """One atomic step in a session (like a turn)."""
    turn: int
    timestamp: str
    action: str  # "call", "think", "tool", "response"
    heat_tax: float = 0.0
    delta_change: float = 0.0
    cost_tokens: int = 0
    summary: str = ""


@dataclass
class SessionIdentity:
    """Who/what owns this session."""
    session_id: str
    label: str = ""
    parent_id: Optional[str] = None  # forked from
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    agent_version: str = "0.3.11"


@dataclass
class SessionCost:
    """Cost and heat tax accounting."""
    total_tokens: int = 0
    total_heat_tax: float = 0.0
    total_steps: int = 0
    last_delta: float = 0.5
    budget_remaining: float = 0.3
    wasted_tokens: int = 0  # tokens that produced no meaning
    molting_count: int = 0  # number of times session self-improved


@dataclass
class HookRegistry:
    """Lifecycle hooks — like OpenClaw's session-hooks."""
    pre_step: List[Callable] = field(default_factory=list)
    post_step: List[Callable] = field(default_factory=list)
    on_error: List[Callable] = field(default_factory=list)
    on_lock: List[Callable] = field(default_factory=list)
    on_molt: List[Callable] = field(default_factory=list)


# ─── Session ────────────────────────────────────────────────

class MSSSession:
    """Persistent, resumable agent session.

    Usage:
        session = MSSSession(session_id="analysis-001", label="代码审计")
        session.start()
        ok, reason = session.can_step()
        if ok:
            session.step("tool_call", heat_tax=0.05, delta_change=+0.02)
        session.save()  # persist to disk
        # ... later ...
        session = MSSSession.load("analysis-001")
        session.step(...)
    """

    SESSIONS_DIR = Path.home() / ".mssclaw" / "sessions"

    def __init__(
        self,
        session_id: str,
        label: str = "",
        identity: Optional[SessionIdentity] = None,
        budget: float = 0.3,
        delta_min: float = 0.5,
        auto_save: bool = True,
    ):
        self.identity = identity or SessionIdentity(session_id=session_id, label=label)
        self.cost = SessionCost(budget_remaining=budget)
        self.hooks = HookRegistry()
        self._steps: List[SessionStep] = []
        self._metadata: Dict[str, Any] = {}
        self._lock = threading.Lock()
        self._active = False
        self.auto_save = auto_save
        self.delta_min = delta_min

    # ─── Lifecycle ──────────────────────────────────────

    def start(self) -> None:
        self._active = True
        self._run_hooks(self.hooks.pre_step, {"event": "session_start"})

    def end(self) -> None:
        self._active = False
        self._run_hooks(self.hooks.post_step, {"event": "session_end"})
        if self.auto_save:
            self.save()

    def can_step(self) -> tuple:
        """H648 DeferGuard check before each step."""
        if not self._active:
            return False, "Session not started"
        if self.cost.budget_remaining <= 0:
            return False, f"Heat tax budget exhausted"
        if self.cost.last_delta < self.delta_min:
            return False, (
                f"Delta {self.cost.last_delta:.2f} below minimum {self.delta_min:.2f}. "
                f"Introduce new information before continuing."
            )
        return True, "OK"

    def step(
        self,
        action: str,
        heat_tax: float = 0.02,
        delta_change: float = 0.01,
        cost_tokens: int = 0,
        summary: str = "",
    ) -> Optional[SessionStep]:
        """Record one step. Returns step or None if locked."""
        ok, reason = self.can_step()
        if not ok:
            self._run_hooks(self.hooks.on_lock, {"reason": reason})
            return None

        with self._lock:
            step = SessionStep(
                turn=self.cost.total_steps + 1,
                timestamp=datetime.now(timezone.utc).isoformat(),
                action=action,
                heat_tax=heat_tax,
                delta_change=delta_change,
                cost_tokens=cost_tokens,
                summary=summary,
            )
            self._steps.append(step)
            self.cost.total_steps += 1
            self.cost.total_heat_tax += heat_tax
            self.cost.total_tokens += cost_tokens
            self.cost.budget_remaining -= heat_tax
            self.cost.last_delta = max(0.0, min(1.0, self.cost.last_delta + delta_change))

            self._run_hooks(self.hooks.post_step, {"step": step, "cost": self.cost})

            if self.auto_save:
                self.save()
            return step

    # ─── Fork / Resume ──────────────────────────────────

    def fork(self, new_label: str) -> MSSSession:
        """Clone session into a new branch (like OpenClaw's session-fork)."""
        child = MSSSession(
            session_id=f"{self.identity.session_id}-fork-{int(time.time())}",
            label=new_label,
            identity=SessionIdentity(
                session_id=f"{self.identity.session_id}-fork-{int(time.time())}",
                label=new_label,
                parent_id=self.identity.session_id,
            ),
        )
        # Copy state
        child._steps = list(self._steps)
        child.cost = SessionCost(
            total_tokens=self.cost.total_tokens,
            total_heat_tax=self.cost.total_heat_tax,
            total_steps=self.cost.total_steps,
            last_delta=self.cost.last_delta,
            budget_remaining=self.cost.budget_remaining,
        )
        child._metadata = dict(self._metadata)
        return child

    # ─── Persistence (like session-store) ────────────────

    def save(self) -> None:
        """Persist to JSON (write-lock protected)."""
        path = self.SESSIONS_DIR / f"{self.identity.session_id}.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        data = {
            "identity": asdict(self.identity),
            "cost": asdict(self.cost),
            "steps": [asdict(s) for s in self._steps[-50:]],  # last 50 for size
            "metadata": self._metadata,
        }
        tmp = path.with_suffix(".tmp")
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        os.replace(tmp, path)  # atomic on same filesystem

    @classmethod
    def load(cls, session_id: str) -> MSSSession:
        """Resume from persisted JSON."""
        path = cls.SESSIONS_DIR / f"{session_id}.json"
        if not path.exists():
            raise FileNotFoundError(f"Session {session_id} not found at {path}")

        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)

        session = cls(session_id=session_id)
        session.identity = SessionIdentity(**data["identity"])
        session.cost = SessionCost(**data["cost"])
        session._steps = [SessionStep(**s) for s in data.get("steps", [])]
        session._metadata = data.get("metadata", {})
        session.start()
        return session

    @classmethod
    def list_sessions(cls) -> List[str]:
        """List all saved sessions."""
        if not cls.SESSIONS_DIR.exists():
            return []
        return [p.stem for p in cls.SESSIONS_DIR.glob("*.json")]

    # ─── Molting (self-evolution) ────────────────────────

    def molt(self, reason: str) -> None:
        """Record a self-improvement event (H604 molting protocol)."""
        self.cost.molting_count += 1
        self._metadata[f"molt_{self.cost.molting_count}"] = {
            "at": datetime.now(timezone.utc).isoformat(),
            "reason": reason,
            "delta_before": self.cost.last_delta,
        }
        # Openness boost from molting
        self.cost.last_delta = min(1.0, self.cost.last_delta + 0.1)
        self._run_hooks(self.hooks.on_molt, {"reason": reason})

    # ─── Reporting ───────────────────────────────────────

    def report(self) -> Dict[str, Any]:
        """Session health report."""
        steps = len(self._steps)
        if steps == 0:
            return {"status": "empty", "identity": asdict(self.identity)}

        recent_steps = self._steps[-10:]
        recent_heat = sum(s.heat_tax for s in recent_steps)
        recent_delta_avg = sum(s.delta_change for s in recent_steps) / len(recent_steps)

        return {
            "identity": asdict(self.identity),
            "cost": asdict(self.cost),
            "total_steps": steps,
            "active": self._active,
            "recent_heat": round(recent_heat, 3),
            "recent_delta_avg": round(recent_delta_avg, 3),
            "budget_pct": round(self.cost.budget_remaining / 0.3 * 100, 1),
            "molting_count": self.cost.molting_count,
        }

    # ─── Internal ────────────────────────────────────────

    def _run_hooks(self, hooks: List[Callable], ctx: Dict[str, Any]) -> None:
        for hook in hooks:
            try:
                hook(ctx)
            except Exception:
                pass  # hooks are best-effort


# ─── Demo ─────────────────────────────────────────────────────

if __name__ == "__main__":
    session = MSSSession("demo-001", "拆解OpenClaw分析")
    session.start()

    # Simulate agent steps
    session.step("analyze", heat_tax=0.05, delta_change=+0.03, summary="架构文件扫描完成")
    session.step("tool_call", heat_tax=0.08, delta_change=-0.02, summary="sandbox 调用超时")
    session.step("think", heat_tax=0.02, delta_change=+0.01, summary="Timeout 根因分析")
    session.step("response", heat_tax=0.03, delta_change=+0.05, summary="输出12大系统拆解")

    print(session.report())

    # Fork a new exploration
    child = session.fork("深入Session系统")
    child.step("explore", heat_tax=0.02, delta_change=+0.02, summary="session-store 源码分析")

    # Molting after learning
    session.molt("发现P0吸收点: Session持久化模式")

    session.save()
    print(f"\nSaved. All sessions: {MSSSession.list_sessions()}")
