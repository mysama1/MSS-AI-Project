"""
Agent Memory Persistence — 会话状态持久化

保存/恢复: 对话历史, Delta历史, 热税状态, 桥状态, 认知状态.

用法:
    agent.save("session_001.json")
    agent.load("session_001.json")
"""
from __future__ import annotations
import json
import time
from pathlib import Path
from typing import Optional


class SessionPersistence:
    """Agent 会话持久化."""

    @staticmethod
    def save(agent, path: str) -> str:
        """保存 Agent 完整状态."""
        data = {
            "version": "1.0",
            "saved_at": time.time(),
            "agent": {
                "name": agent.name,
                "run_count": agent.run_count,
                "abort_count": agent.abort_count,
            },
            "tax": agent.tax.snapshot(),
            "delta": agent.delta.snapshot(),
            "bridge": {
                "level": agent.l2bridge.level.name,
                "history": agent.l2bridge.history[-50:],
            },
            "memory": agent.memory.stats(),
            "cognition": agent.cognition.stats(),
        }

        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        return str(p)

    @staticmethod
    def load(agent, path: str) -> bool:
        """恢复 Agent 状态 (部分 — 统计信息)."""
        p = Path(path)
        if not p.exists():
            return False

        data = json.loads(p.read_text(encoding="utf-8"))

        # Restore run counts
        agent_data = data.get("agent", {})
        agent.run_count = agent_data.get("run_count", 0)
        agent.abort_count = agent_data.get("abort_count", 0)

        # Tax state is not fully restorable (encrypted), but we log it
        tax_data = data.get("tax", {})
        if tax_data:
            pass  # tax snapshot is read-only

        # Delta history restoration
        delta_data = data.get("delta", {})
        if delta_data and "history" in delta_data:
            agent.delta.history = delta_data.get("history", [])[-100:]

        # Bridge
        bridge_data = data.get("bridge", {})
        if bridge_data and "history" in bridge_data:
            agent.l2bridge.history = bridge_data["history"][-50:]

        return True

    @staticmethod
    def list_sessions(directory: str = None) -> list:
        """列出保存的会话."""
        d = Path(directory or Path.home() / ".mssclaw" / "sessions")
        if not d.exists():
            return []
        sessions = []
        for f in sorted(d.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True):
            try:
                data = json.loads(f.read_text(encoding="utf-8"))
                sessions.append({
                    "file": f.name,
                    "saved_at": data.get("saved_at", 0),
                    "runs": data.get("agent", {}).get("run_count", 0),
                    "delta": data.get("delta", {}).get("current_delta", "N/A"),
                })
            except Exception:
                sessions.append({"file": f.name, "saved_at": 0, "runs": 0, "delta": "error"})
        return sessions

    @staticmethod
    def auto_save(agent, base_dir: str = None):
        """自动保存 (基于时间戳命名)."""
        d = Path(base_dir or Path.home() / ".mssclaw" / "sessions")
        ts = time.strftime("%Y%m%d_%H%M%S")
        name = f"session_{agent.name}_{ts}.json"
        return SessionPersistence.save(agent, str(d / name))
