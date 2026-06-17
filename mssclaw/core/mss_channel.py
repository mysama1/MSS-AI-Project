#!/usr/bin/env python3
"""
MSS Channel — unified output pipeline for multi-agent systems.

Inspired by OpenClaw's channel system (18+ channels, ~60 files):
- channel-core → common interface (format, send, lifecycle)
- channel-reply-pipeline → reply formatting pipeline
- channel-policy → behavioral policy per channel
- channel-inbound → message ingestion
- channel-lifecycle → start/stop/reconnect

MSS doesn't need 18 chat apps — it needs a unified pipeline for agent output
that can format for different targets (terminal / file / Discord / API).

Usage:
    chan = MSSChannel(kind="terminal", policy={"max_lines": 50})
    chan.send("Agent A completed scan: 5 vulnerabilities found")
    chan.broadcast(["Agent B", "Agent C"], "Starting phase 2")

    # Multiple agents sharing a channel
    chan2 = MSSChannel(kind="json", file_path="output.json")
    chan2.send_dict({"agent": "A", "action": "scan", "result": 5})
"""

from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional
import json
import sys
import threading


# ─── Data models ────────────────────────────────────────────

class ChannelKind(str, Enum):
    TERMINAL = "terminal"
    JSON = "json"
    TEXT = "text"
    NULL = "null"
    CALLBACK = "callback"  # custom handler


class MessageLevel(str, Enum):
    DEBUG = "debug"
    INFO = "info"
    WARN = "warn"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class ChannelMessage:
    """A structured message through the channel."""
    text: str
    level: MessageLevel = MessageLevel.INFO
    sender: str = ""
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ChannelPolicy:
    """Behavioral policy per channel — like OpenClaw's channel-policy."""
    max_lines: int = 100
    max_chars: int = 8000
    truncate_marker: str = "... (truncated)"
    allow_levels: List[MessageLevel] = field(default_factory=lambda: list(MessageLevel))
    prefix_sender: bool = True
    timestamp: bool = True
    color: bool = True  # terminal colors
    heat_tax_threshold: float = 0.5  # block messages above this heat tax cost


# ─── Output formatters ───────────────────────────────────────

class TerminalFormatter:
    """Format messages for terminal with ANSI colors."""
    COLORS = {
        MessageLevel.DEBUG: "\033[90m",    # gray
        MessageLevel.INFO: "\033[0m",      # default
        MessageLevel.WARN: "\033[93m",     # yellow
        MessageLevel.ERROR: "\033[91m",    # red
        MessageLevel.CRITICAL: "\033[91;1m",  # bold red
    }
    RESET = "\033[0m"

    @staticmethod
    def format(msg: ChannelMessage, policy: ChannelPolicy) -> str:
        prefix = ""
        if policy.prefix_sender and msg.sender:
            prefix += f"[{msg.sender}] "
        if policy.timestamp:
            # Just show HH:MM:SS
            ts = msg.timestamp.split("T")[1].split(".")[0] if "T" in msg.timestamp else msg.timestamp
            prefix += f"{ts} "

        color = TerminalFormatter.COLORS.get(msg.level, "")
        line = f"{color}{prefix}{msg.text}{TerminalFormatter.RESET}"
        return TerminalFormatter._truncate(line, policy)

    @staticmethod
    def _truncate(text: str, policy: ChannelPolicy) -> str:
        lines = text.split("\n")
        if len(lines) > policy.max_lines:
            lines = lines[:policy.max_lines] + [policy.truncate_marker]
        result = "\n".join(lines)
        if len(result) > policy.max_chars:
            result = result[:policy.max_chars] + policy.truncate_marker
        return result


class JsonFormatter:
    """Format messages as JSON records."""
    @staticmethod
    def format(msg: ChannelMessage, policy: ChannelPolicy) -> str:
        record = {
            "text": msg.text[:policy.max_chars],
            "level": msg.level.value,
            "sender": msg.sender,
            "timestamp": msg.timestamp,
            **msg.metadata,
        }
        return json.dumps(record, ensure_ascii=False)


class TextFormatter:
    """Plain text formatter."""
    @staticmethod
    def format(msg: ChannelMessage, policy: ChannelPolicy) -> str:
        prefix = ""
        if policy.prefix_sender and msg.sender:
            prefix += f"[{msg.sender}] "
        line = f"{prefix}{msg.text}"
        if len(line) > policy.max_chars:
            line = line[:policy.max_chars] + policy.truncate_marker
        return line


# ─── Channel ─────────────────────────────────────────────────

class MSSChannel:
    """Unified output pipeline for agent communication.

    Usage:
        chan = MSSChannel(kind="terminal", policy=ChannelPolicy(max_lines=50))
        chan.info("Agent A", "Starting phase 1")
        chan.warn("Agent A", "High heat tax detected")
        chan.error("Agent A", "Sandbox timeout")
    """

    FORMATTERS = {
        ChannelKind.TERMINAL: TerminalFormatter,
        ChannelKind.JSON: JsonFormatter,
        ChannelKind.TEXT: TextFormatter,
    }

    def __init__(
        self,
        kind: ChannelKind = ChannelKind.TERMINAL,
        policy: Optional[ChannelPolicy] = None,
        file_path: Optional[Path] = None,
        callback: Optional[Callable] = None,
    ):
        self.kind = kind if isinstance(kind, ChannelKind) else ChannelKind(kind)
        self.policy = policy or ChannelPolicy()
        self.file_path = file_path
        self.callback = callback
        self._formatter = self.FORMATTERS.get(kind, TextFormatter)
        self._lock = threading.Lock()
        self._message_count: int = 0
        self._total_heat_tax: float = 0.0

    def send(
        self,
        text: str,
        sender: str = "",
        level: MessageLevel = MessageLevel.INFO,
        metadata: Optional[Dict[str, Any]] = None,
        heat_tax_cost: float = 0.0,
    ) -> Optional[str]:
        """Send a message through the channel. Returns formatted text or None."""
        if level not in self.policy.allow_levels:
            return None
        if heat_tax_cost > self.policy.heat_tax_threshold:
            return None  # too expensive

        msg = ChannelMessage(text=text, level=level, sender=sender, metadata=metadata or {})
        formatted = self._formatter.format(msg, self.policy)

        with self._lock:
            self._message_count += 1
            self._total_heat_tax += heat_tax_cost

            if self.kind == ChannelKind.TERMINAL:
                print(formatted, file=sys.stdout)
            elif self.kind == ChannelKind.JSON and self.file_path:
                with open(self.file_path, "a", encoding="utf-8") as f:
                    f.write(formatted + "\n")
            elif self.kind == ChannelKind.TEXT and self.file_path:
                with open(self.file_path, "a", encoding="utf-8") as f:
                    f.write(formatted + "\n")
            elif self.kind == ChannelKind.CALLBACK and self.callback:
                self.callback(msg, formatted)
            elif self.kind == ChannelKind.NULL:
                pass

        return formatted

    # ─── Convenience methods ──────────────────────────────

    def debug(self, sender: str, text: str, **kwargs) -> Optional[str]:
        return self.send(text, sender, MessageLevel.DEBUG, **kwargs)

    def info(self, sender: str, text: str, **kwargs) -> Optional[str]:
        return self.send(text, sender, MessageLevel.INFO, **kwargs)

    def warn(self, sender: str, text: str, **kwargs) -> Optional[str]:
        return self.send(text, sender, MessageLevel.WARN, **kwargs)

    def error(self, sender: str, text: str, **kwargs) -> Optional[str]:
        return self.send(text, sender, MessageLevel.ERROR, **kwargs)

    def critical(self, sender: str, text: str, **kwargs) -> Optional[str]:
        return self.send(text, sender, MessageLevel.CRITICAL, **kwargs)

    def broadcast(self, senders: List[str], text: str, level: MessageLevel = MessageLevel.INFO) -> List[Optional[str]]:
        """Send same message as multiple senders (like a multi-agent announcement)."""
        return [self.send(text, s, level) for s in senders]

    def send_dict(self, data: Dict[str, Any], sender: str = "") -> Optional[str]:
        """Send structured data (auto-formats based on channel kind)."""
        if self.kind == ChannelKind.JSON:
            return self.send(json.dumps(data, ensure_ascii=False), sender)
        else:
            # Pretty print for human-readable channels
            pretty = json.dumps(data, indent=2, ensure_ascii=False)
            return self.send(pretty, sender)

    def report(self) -> Dict[str, Any]:
        """Channel health report."""
        return {
            "kind": self.kind.value,
            "message_count": self._message_count,
            "total_heat_tax": round(self._total_heat_tax, 3),
            "file": str(self.file_path) if self.file_path else None,
        }

    def close(self) -> None:
        """Close channel (flush if needed)."""
        if self.file_path and self.kind == ChannelKind.JSON:
            # Ensure final newline
            with open(self.file_path, "a", encoding="utf-8") as f:
                f.write("\n")


# ─── Demo ─────────────────────────────────────────────────────

if __name__ == "__main__":
    # Terminal channel
    term = MSSChannel(kind="terminal", policy=ChannelPolicy(max_lines=10))
    term.info("Agent-Analyzer", "Starting architecture scan...")
    term.warn("Agent-Analyzer", "Found 3 potential issues")
    term.debug("Agent-Analyzer", "Cache hit on module 0x7F")  # this won't show (DEBUG filtered)
    term.error("Agent-Scanner", "Timeout on core.py:53")

    # Broadcast (multi-agent announcement)
    term.broadcast(
        ["Agent-A", "Agent-B", "Agent-C"],
        "Phase 1 complete — proceeding to phase 2",
        MessageLevel.INFO,
    )

    # JSON channel (for machine consumption)
    json_chan = MSSChannel(kind="json", file_path=Path("/tmp/mss_output.json"))
    json_chan.send_dict({"phase": 1, "agents": 3, "vulnerabilities": 5}, sender="Orchestrator")

    print(f"\nChannel report: {term.report()}")
