#!/usr/bin/env python3
"""
MSS GroupChat — AutoGen-inspired multi-agent conversation roundtable.

Inspired by AutoGen's GroupChat + GroupChatManager:
- Multiple agents share one conversation
- Turn-taking with speaker selection
- Nested chat (sub-conversations spawned by agents)
- Human-in-the-loop at critical junctures

MSS differences:
- Every message carries heat_tax metadata
- Delta tracking per agent through the conversation
- A6 elevation detection (when conversation hits contradiction)
- Trust budget decay (agents that waste tokens lose speaking privileges)
- Quorum detection (when enough agents converge, conversation stops)
"""

from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, Tuple
import time


# ─── Data models ────────────────────────────────────────────

class ChatRole(str, Enum):
    MODERATOR = "moderator"
    PARTICIPANT = "participant"
    OBSERVER = "observer"  # reads but doesn't speak
    HUMAN = "human"


class SpeakerStrategy(str, Enum):
    ROUND_ROBIN = "round_robin"
    BY_PRIORITY = "by_priority"  # highest delta agent speaks
    BY_RELEVANCE = "by_relevance"  # most relevant to last topic
    VOLUNTEER = "volunteer"  # agents volunteer via callback


@dataclass
class ChatMessage:
    """A single message in the group chat."""
    sender_id: str
    sender_role: ChatRole
    text: str
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    heat_tax_cost: float = 0.005  # default per-message heat tax
    delta_estimate: float = 0.0  # agent's own estimate of delta contribution
    reply_to: Optional[str] = None  # id of message being replied to
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ChatAgent:
    """An agent participating in the group chat."""
    agent_id: str
    role: ChatRole = ChatRole.PARTICIPANT
    priority: float = 0.5  # speaking priority (0-1)
    trust_budget: float = 0.7  # starts trusting
    total_heat_tax: float = 0.0
    delta_history: List[float] = field(default_factory=list)
    message_count: int = 0
    silenced_until: float = 0.0  # unix timestamp, 0 = not silenced
    metadata: Dict[str, Any] = field(default_factory=dict)

    def speak_priority(self) -> float:
        """How much this agent wants to speak now."""
        if time.time() < self.silenced_until:
            return -1.0  # silenced
        # Blend trust and recent delta
        recent_delta = (sum(self.delta_history[-3:]) / max(len(self.delta_history[-3:]), 1)) if self.delta_history else 0.5
        return self.trust_budget * 0.6 + recent_delta * 0.4


# ─── GroupChat ──────────────────────────────────────────────

class MSSGroupChat:
    """Multi-agent roundtable conversation.

    Usage:
        chat = MSSGroupChat("Architecture Review", strategy=SpeakerStrategy.BY_PRIORITY)
        chat.add_agent("planner", priority=0.8, trust_budget=0.9)
        chat.add_agent("skeptic", priority=0.6, trust_budget=0.5)
        chat.add_agent("human", role=ChatRole.HUMAN)

        chat.start_topic("Should we use async or sync for pipeline?")
        while chat.should_continue():
            speaker = chat.select_speaker()
            response = get_agent_response(speaker)  # your LLM call here
            chat.speak(speaker, response)
        print(chat.summary())
    """

    def __init__(
        self,
        topic: str = "",
        strategy: SpeakerStrategy = SpeakerStrategy.ROUND_ROBIN,
        max_rounds: int = 20,
        quorum_threshold: float = 0.85,  # convergence score to auto-stop
        heat_tax_budget: float = 0.5,
        delta_min: float = 0.3,
    ):
        self.topic = topic
        self.strategy = strategy
        self.max_rounds = max_rounds
        self.quorum_threshold = quorum_threshold
        self.heat_tax_budget = heat_tax_budget
        self.delta_min = delta_min

        self._agents: Dict[str, ChatAgent] = {}
        self._messages: List[ChatMessage] = []
        self._round: int = 0
        self._last_speaker: Optional[str] = None
        self._a6_events: List[Dict[str, Any]] = []  # contradiction → elevation events
        self._concluded: bool = False
        self._conclusion_reason: str = ""
        self._hooks: Dict[str, List[Callable]] = {
            "on_message": [],
            "on_a6": [],
            "on_quorum": [],
            "on_silence": [],  # agent silenced for waste
        }

    # ─── Agent management ──────────────────────────────────

    def add_agent(
        self,
        agent_id: str,
        role: ChatRole = ChatRole.PARTICIPANT,
        priority: float = 0.5,
        trust_budget: float = 0.7,
        **metadata,
    ) -> ChatAgent:
        agent = ChatAgent(
            agent_id=agent_id,
            role=role,
            priority=priority,
            trust_budget=trust_budget,
            metadata=metadata,
        )
        self._agents[agent_id] = agent
        return agent

    def remove_agent(self, agent_id: str) -> bool:
        return self._agents.pop(agent_id, None) is not None

    # ─── Conversation ──────────────────────────────────────

    def start_topic(self, topic: str) -> ChatMessage:
        """Open a new topic. Returns the opening message."""
        self.topic = topic
        msg = ChatMessage(
            sender_id="system",
            sender_role=ChatRole.MODERATOR,
            text=topic,
            metadata={"event": "topic_start"},
        )
        self._messages.append(msg)
        self._round = 0
        return msg

    def select_speaker(self) -> Optional[str]:
        """Select the next speaker based on strategy."""
        eligible = {
            aid: a for aid, a in self._agents.items()
            if a.role in (ChatRole.PARTICIPANT, ChatRole.MODERATOR)
            and a.speak_priority() >= 0
            and aid != self._last_speaker  # don't let same agent speak twice
        }
        if not eligible:
            return None

        if self.strategy == SpeakerStrategy.ROUND_ROBIN:
            # Simple cycling through agents
            ids = sorted(eligible.keys())
            if self._last_speaker and self._last_speaker in ids:
                idx = ids.index(self._last_speaker)
                return ids[(idx + 1) % len(ids)]
            return ids[0]

        elif self.strategy == SpeakerStrategy.BY_PRIORITY:
            # Highest speak_priority wins
            return max(eligible.keys(), key=lambda aid: eligible[aid].speak_priority())

        elif self.strategy == SpeakerStrategy.BY_RELEVANCE:
            # Default to priority (relevance needs external scoring)
            return max(eligible.keys(), key=lambda aid: eligible[aid].priority)

        elif self.strategy == SpeakerStrategy.VOLUNTEER:
            # Return all eligible — caller decides
            return list(eligible.keys())[0]  # first available

    def speak(self, agent_id: str, text: str, **msg_kwargs) -> ChatMessage:
        """Record an agent's speech."""
        if agent_id not in self._agents:
            raise KeyError(f"Agent {agent_id} not in chat")

        agent = self._agents[agent_id]
        msg = ChatMessage(sender_id=agent_id, sender_role=agent.role, text=text, **msg_kwargs)
        self._messages.append(msg)

        # Update agent stats
        agent.message_count += 1
        agent.total_heat_tax += msg.heat_tax_cost
        agent.delta_history.append(msg.delta_estimate)

        # Trust budget decay for high-heat agents
        if agent.total_heat_tax > self.heat_tax_budget * agent.message_count:
            agent.trust_budget = max(0.1, agent.trust_budget - 0.05)

        # A6 detection: check if recent messages show contradiction
        self._check_a6()

        self._round += 1
        self._last_speaker = agent_id

        # Fire hooks
        for hook in self._hooks["on_message"]:
            try:
                hook(msg, agent)
            except Exception:
                pass

        return msg

    def human_input(self, text: str) -> ChatMessage:
        """Record human input into the conversation."""
        msg = ChatMessage(sender_id="human", sender_role=ChatRole.HUMAN, text=text)
        self._messages.append(msg)
        self._round += 1
        return msg

    # ─── Detection ─────────────────────────────────────────

    def should_continue(self) -> Tuple[bool, str]:
        """Check if conversation should keep going."""
        if self._concluded:
            return False, self._conclusion_reason
        if self._round >= self.max_rounds:
            self._concluded = True
            self._conclusion_reason = f"Max rounds ({self.max_rounds}) reached"
            return False, self._conclusion_reason
        if self._check_quorum():
            self._concluded = True
            self._conclusion_reason = f"Quorum reached (≥{self.quorum_threshold})"
            return False, self._conclusion_reason
        return True, ""

    def _check_quorum(self) -> bool:
        """Check if agents have converged."""
        active = [a for a in self._agents.values() if a.message_count > 0]
        if len(active) < 2:
            return False

        # Convergence = average delta over last round
        recent_deltas = []
        for a in active:
            if a.delta_history:
                recent_deltas.append(a.delta_history[-1])
        if not recent_deltas:
            return False

        avg_delta = sum(recent_deltas) / len(recent_deltas)
        if avg_delta >= self.quorum_threshold:
            self._run_hooks("on_quorum", {"avg_delta": avg_delta})
            return True
        return False

    def _check_a6(self) -> None:
        """Detect contradiction patterns that warrant A6 elevation."""
        if len(self._messages) < 4:
            return

        # Simple heuristic: last 4 messages from different agents with diverging claims
        recent = self._messages[-4:]
        speakers = {m.sender_id for m in recent}
        if len(speakers) >= 3:
            # Check for contradictory keywords
            contradictory_pairs = [
                ("should", "shouldn't"), ("yes", "no"), ("agree", "disagree"),
                ("sync", "async"), ("option a", "option b"),
            ]
            texts = " ".join(m.text.lower() for m in recent)
            hits = sum(1 for a, b in contradictory_pairs if a in texts and b in texts)
            if hits >= 2:
                event = {
                    "round": self._round,
                    "agents": list(speakers),
                    "contradiction_count": hits,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                }
                self._a6_events.append(event)
                self._run_hooks("on_a6", event)

    # ─── Summary ───────────────────────────────────────────

    def summary(self) -> Dict[str, Any]:
        """Conversation summary with heat tax/delta report."""
        agent_stats = {}
        total_heat = 0.0
        for aid, agent in self._agents.items():
            avg_delta = sum(agent.delta_history) / max(len(agent.delta_history), 1)
            agent_stats[aid] = {
                "messages": agent.message_count,
                "total_heat_tax": round(agent.total_heat_tax, 3),
                "avg_delta": round(avg_delta, 3),
                "trust_budget": round(agent.trust_budget, 2),
                "silenced": time.time() < agent.silenced_until,
            }
            total_heat += agent.total_heat_tax

        return {
            "topic": self.topic,
            "rounds": self._round,
            "messages": len(self._messages),
            "total_heat_tax": round(total_heat, 3),
            "a6_events": len(self._a6_events),
            "concluded": self._concluded,
            "conclusion_reason": self._conclusion_reason,
            "agents": agent_stats,
        }

    def export_transcript(self) -> List[Dict[str, Any]]:
        """Export full transcript."""
        return [
            {
                "round": i,
                "sender": m.sender_id,
                "role": m.sender_role.value,
                "text": m.text,
                "heat_tax": m.heat_tax_cost,
                "timestamp": m.timestamp,
            }
            for i, m in enumerate(self._messages)
        ]

    # ─── Hooks ─────────────────────────────────────────────

    def on(self, event: str, handler: Callable) -> None:
        """Register hook: 'on_message', 'on_a6', 'on_quorum', 'on_silence'."""
        if event in self._hooks:
            self._hooks[event].append(handler)

    def _run_hooks(self, event: str, data: Dict[str, Any]) -> None:
        for hook in self._hooks.get(event, []):
            try:
                hook(data)
            except Exception:
                pass

    # ─── Silence mechanism ─────────────────────────────────

    def silence_agent(self, agent_id: str, duration_seconds: float, reason: str = "") -> None:
        """Silence an agent for wasting tokens / violating rules."""
        if agent_id in self._agents:
            self._agents[agent_id].silenced_until = time.time() + duration_seconds
            self._run_hooks("on_silence", {"agent": agent_id, "duration": duration_seconds, "reason": reason})


# ─── Demo ─────────────────────────────────────────────────────

if __name__ == "__main__":
    chat = MSSGroupChat(strategy=SpeakerStrategy.BY_PRIORITY, max_rounds=10)

    chat.add_agent("architect", priority=0.9, trust_budget=0.95, role=ChatRole.PARTICIPANT)
    chat.add_agent("skeptic", priority=0.7, trust_budget=0.6, role=ChatRole.PARTICIPANT)
    chat.add_agent("implementer", priority=0.6, trust_budget=0.8, role=ChatRole.PARTICIPANT)
    chat.add_agent("human", role=ChatRole.HUMAN)

    chat.start_topic("Should we use async or sync for the data pipeline?")

    # Simulate conversation
    turns = [
        ("architect", "Async is clearly better — non-blocking I/O gives us 10x throughput", 0.005, 0.1),
        ("skeptic", "Async adds complexity. Our current sync pipeline works. What's the real bottleneck?", 0.005, 0.2),
        ("implementer", "I've benchmarked both. Sync is simpler but caps at ~50 req/s. We need 200+.", 0.005, 0.3),
        ("architect", "See? The implementer confirms my point — async is the only way.", 0.005, 0.05),
        ("skeptic", "Fine, but I want an explicit error budget. If async causes >2 incidents/month, we roll back.", 0.005, 0.4),
    ]

    for agent_id, text, heat, delta in turns:
        if not chat.should_continue()[0]:
            break
        chat.speak(agent_id, text, heat_tax_cost=heat, delta_estimate=delta)

    # Human input
    chat.human_input("Go async, but with the skeptic's error budget condition.")

    print(chat.summary())
    print(f"\nTranscript ({len(chat.export_transcript())} messages):")
    for t in chat.export_transcript():
        print(f"  [{t['role']}] {t['sender']}: {t['text'][:60]}...")
