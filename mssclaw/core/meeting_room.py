# -*- coding: utf-8 -*-
"""
S-004: MeetingRoom — Shared Database with Query + Meeting Protocol

Extends MSS-Swarm SharedStore with:
  1. Namespaced storage (agent:, task:, kb:, meeting:)
  2. Query API: prefix scan, pattern match, range query
  3. Meeting Protocol: create/join/leave/talk/decide
  4. Time-to-live (TTL) entries with auto-expiry
  5. Transactional batch operations

Design:
  - Thread-safe, in-memory (no disk I/O for MeetingRoom — that's KB-Agent's job)
  - Meeting minutes auto-generated from talk history
  - Decisions stored as versioned, immutable records
"""
import json
import time
import threading
import hashlib
from typing import Dict, List, Optional, Any, Callable, Tuple
from dataclasses import dataclass, field
from collections import defaultdict, OrderedDict


@dataclass
class TTLValue:
    """Value with time-to-live."""
    data: Any
    expires_at: float


@dataclass
class MeetingRecord:
    """A meeting session with participants, talks, decisions."""
    meeting_id: str
    topic: str
    participants: List[str] = field(default_factory=list)
    talk_log: List[Dict] = field(default_factory=list)
    decisions: List[Dict] = field(default_factory=list)
    created_at: float = 0.0
    closed_at: float = 0.0
    is_active: bool = True


class QueryResult:
    """Result from a MeetingRoom query."""
    
    def __init__(self, items: List[Tuple[str, Any]], total: int):
        self.items = items
        self.total = total
        self.truncated = len(items) < total
    
    def to_dict(self) -> Dict:
        return {
            "items": [{"key": k, "value": v} for k, v in self.items],
            "count": len(self.items),
            "total": self.total,
        }


class MeetingRoom:
    """
    Shared namespace-separated storage with meeting protocol.
    
    Namespaces:
      agent:  — agent state and metadata
      task:   — task definitions and results
      kb:     — knowledge base entries (cached)
      meeting:— meeting minutes and decisions
      shared: — cross-namespace shared values
    """
    
    VALID_NAMESPACES = {"agent", "task", "kb", "meeting", "shared"}
    
    def __init__(self):
        self._stores: Dict[str, Dict[str, Any]] = {
            ns: OrderedDict() for ns in self.VALID_NAMESPACES
        }
        self._ttl_store: Dict[str, TTLValue] = {}
        self._meetings: Dict[str, MeetingRecord] = {}
        self._locks: Dict[str, threading.Lock] = defaultdict(threading.Lock)
        self._global_lock = threading.Lock()
        self._batch_counter: int = 0
    
    # ── Key formatting ──
    
    @staticmethod
    def fmt_key(namespace: str, key: str) -> str:
        return f"{namespace}:{key}"
    
    @staticmethod
    def parse_key(full_key: str) -> Tuple[str, str]:
        parts = full_key.split(":", 1)
        return parts[0], parts[1] if len(parts) > 1 else ""
    
    # ── Basic CRUD ──
    
    def set(self, namespace: str, key: str, value: Any, ttl_seconds: float = 0):
        """Set a value. If ttl > 0, auto-expires."""
        if namespace not in self.VALID_NAMESPACES:
            raise ValueError(f"Invalid namespace: {namespace}")
        
        with self._global_lock:
            self._stores[namespace][key] = value
        
        if ttl_seconds > 0:
            full_key = self.fmt_key(namespace, key)
            with self._global_lock:
                self._ttl_store[full_key] = TTLValue(
                    data=value, expires_at=time.time() + ttl_seconds
                )
    
    def get(self, namespace: str, key: str, default=None) -> Any:
        """Get a value. Checks TTL first."""
        full_key = self.fmt_key(namespace, key)
        
        # Check TTL
        with self._global_lock:
            ttl_val = self._ttl_store.get(full_key)
            if ttl_val and time.time() > ttl_val.expires_at:
                del self._ttl_store[full_key]
                if namespace in self._stores and key in self._stores[namespace]:
                    del self._stores[namespace][key]
                return default
        
        return self._stores.get(namespace, {}).get(key, default)
    
    def delete(self, namespace: str, key: str) -> bool:
        """Delete a key. Returns True if existed."""
        full_key = self.fmt_key(namespace, key)
        with self._global_lock:
            self._ttl_store.pop(full_key, None)
            if namespace in self._stores:
                return self._stores[namespace].pop(key, None) is not None
        return False
    
    # ── Query ──
    
    def query(self, namespace: str, 
              prefix: str = "",
              pattern: str = "",
              limit: int = 100,
              offset: int = 0) -> QueryResult:
        """
        Query keys in a namespace.
        - prefix: keys starting with this prefix
        - pattern: substring match in key
        - limit/offset: pagination
        """
        if namespace not in self.VALID_NAMESPACES:
            raise ValueError(f"Invalid namespace: {namespace}")
        
        store = self._stores[namespace]
        items = []
        count = 0
        
        for key, value in store.items():
            if prefix and not key.startswith(prefix):
                continue
            if pattern and pattern not in key:
                continue
            if count >= offset:
                items.append((key, value))
            count += 1
            if len(items) >= limit:
                break
        
        return QueryResult(items, count)
    
    def range_query(self, namespace: str,
                    key_from: str = "", key_to: str = "\uffff",
                    limit: int = 100) -> QueryResult:
        """Range query: keys in [key_from, key_to]."""
        if namespace not in self.VALID_NAMESPACES:
            raise ValueError(f"Invalid namespace: {namespace}")
        
        store = self._stores[namespace]
        items = []
        total = 0
        
        for key in sorted(store.keys()):
            if key_from <= key <= key_to:
                total += 1
                if len(items) < limit:
                    items.append((key, store[key]))
        
        return QueryResult(items, total)
    
    # ── Batch operations ──
    
    def batch_set(self, entries: List[Dict]) -> Dict:
        """
        Atomic batch set. entries = [{"ns":..., "key":..., "value":..., "ttl":...}]
        Returns {"ok": count, "errors": [...]}
        """
        ok = 0
        errors = []
        
        with self._global_lock:
            for entry in entries:
                try:
                    ns = entry["ns"]
                    key = entry["key"]
                    value = entry["value"]
                    ttl = entry.get("ttl", 0)
                    if ns in self.VALID_NAMESPACES:
                        self._stores[ns][key] = value
                        if ttl > 0:
                            full_key = self.fmt_key(ns, key)
                            self._ttl_store[full_key] = TTLValue(
                                data=value, expires_at=time.time() + ttl
                            )
                        ok += 1
                    else:
                        errors.append(f"Invalid namespace: {ns}")
                except Exception as e:
                    errors.append(str(e))
        
        self._batch_counter += 1
        return {"ok": ok, "errors": errors, "batch_id": self._batch_counter}
    
    # ── Meeting Protocol ──
    
    def create_meeting(self, topic: str, host_agent_id: str) -> str:
        """Create a new meeting. Returns meeting_id."""
        meeting_id = hashlib.sha256(
            f"{topic}{host_agent_id}{time.time()}".encode()
        ).hexdigest()[:12]
        
        meeting = MeetingRecord(
            meeting_id=meeting_id,
            topic=topic,
            participants=[host_agent_id],
            created_at=time.time(),
        )
        
        with self._global_lock:
            self._meetings[meeting_id] = meeting
        
        # Store in meeting namespace
        self.set("meeting", f"{meeting_id}:meta", {
            "topic": topic, "status": "active",
            "host": host_agent_id, "created_at": meeting.created_at,
        })
        
        return meeting_id
    
    def join_meeting(self, meeting_id: str, agent_id: str) -> bool:
        """Agent joins a meeting."""
        meeting = self._meetings.get(meeting_id)
        if not meeting or not meeting.is_active:
            return False
        
        with self._global_lock:
            if agent_id not in meeting.participants:
                meeting.participants.append(agent_id)
        
        return True
    
    def talk(self, meeting_id: str, agent_id: str, content: str,
             talk_type: str = "statement") -> bool:
        """Record a talk entry in the meeting."""
        meeting = self._meetings.get(meeting_id)
        if not meeting or not meeting.is_active:
            return False
        
        entry = {
            "agent": agent_id,
            "content": content,
            "type": talk_type,  # statement / question / proposal / vote / reject
            "timestamp": time.time(),
            "seq": len(meeting.talk_log),
        }
        
        with self._global_lock:
            meeting.talk_log.append(entry)
        
        # Store talk in meeting namespace
        self.set("meeting", f"{meeting_id}:talk:{entry['seq']}", entry)
        
        return True
    
    def decide(self, meeting_id: str, decision: str,
               proposer: str, votes: Dict[str, str],
               quorum: int = 0) -> Optional[Dict]:
        """
        Record a decision. Requires quorum votes (default: majority of participants).
        Returns decision record if adopted, None if quorum not met.
        """
        meeting = self._meetings.get(meeting_id)
        if not meeting or not meeting.is_active:
            return None
        
        required = quorum or max(len(meeting.participants) // 2 + 1, 1)
        yes_votes = sum(1 for v in votes.values() if v.lower() in ("yes", "agree", "同意"))
        
        if yes_votes < required:
            return None
        
        record = {
            "decision_id": hashlib.sha256(
                f"{meeting_id}{decision}{time.time()}".encode()
            ).hexdigest()[:12],
            "content": decision,
            "proposer": proposer,
            "votes": votes,
            "yes_count": yes_votes,
            "total_participants": len(meeting.participants),
            "adopted_at": time.time(),
            "version": len(meeting.decisions) + 1,
        }
        
        with self._global_lock:
            meeting.decisions.append(record)
        
        # Store in meeting namespace
        self.set("meeting", f"{meeting_id}:decision:{record['version']}", record)
        
        return record
    
    def close_meeting(self, meeting_id: str) -> Optional[Dict]:
        """Close a meeting. Returns summary including all decisions."""
        meeting = self._meetings.get(meeting_id)
        if not meeting or not meeting.is_active:
            return None
        
        with self._global_lock:
            meeting.is_active = False
            meeting.closed_at = time.time()
        
        summary = {
            "meeting_id": meeting_id,
            "topic": meeting.topic,
            "participants": meeting.participants,
            "total_talks": len(meeting.talk_log),
            "total_decisions": len(meeting.decisions),
            "decisions": [{"ver": d["version"], "content": d["content"]}
                         for d in meeting.decisions],
            "duration_s": meeting.closed_at - meeting.created_at,
        }
        
        self.set("meeting", f"{meeting_id}:summary", summary)
        return summary
    
    def get_meeting_history(self, meeting_id: str) -> Optional[Dict]:
        """Get full meeting record."""
        meeting = self._meetings.get(meeting_id)
        if not meeting:
            return None
        return {
            "topic": meeting.topic,
            "participants": meeting.participants,
            "is_active": meeting.is_active,
            "talk_count": len(meeting.talk_log),
            "decision_count": len(meeting.decisions),
            "talks": meeting.talk_log[-50:],  # Last 50 talks
            "decisions": meeting.decisions,
        }
    
    def list_active_meetings(self) -> List[str]:
        """List IDs of active meetings."""
        with self._global_lock:
            return [mid for mid, m in self._meetings.items() if m.is_active]
    
    # ── Housekeeping ──
    
    def gc_ttl(self) -> int:
        """Garbage collect expired TTL entries. Returns count removed."""
        removed = 0
        now = time.time()
        expired = []
        
        with self._global_lock:
            for full_key, ttl_val in list(self._ttl_store.items()):
                if now > ttl_val.expires_at:
                    expired.append(full_key)
        
        for full_key in expired:
            ns, key = self.parse_key(full_key)
            with self._global_lock:
                self._ttl_store.pop(full_key, None)
                if ns in self._stores:
                    self._stores[ns].pop(key, None)
                removed += 1
        
        return removed
    
    def get_size_stats(self) -> Dict:
        """Get storage size stats per namespace."""
        with self._global_lock:
            return {
                ns: len(store) for ns, store in self._stores.items()
            }


# ═══════════════════════════════════════════════════════
# Self-test
# ═══════════════════════════════════════════════════════

def _test():
    room = MeetingRoom()
    
    # Test 1: basic CRUD
    room.set("agent", "a1", {"name": "test_agent", "status": "idle"})
    val = room.get("agent", "a1")
    assert val["name"] == "test_agent"
    print("T1 PASS: basic CRUD")
    
    # Test 2: TTL
    room.set("task", "temp", "expires soon", ttl_seconds=0.01)
    time.sleep(0.02)
    val = room.get("task", "temp")
    assert val is None, f"TTL should expire: {val}"
    print("T2 PASS: TTL expiry")
    
    # Test 3: query by prefix
    for i in range(5):
        room.set("kb", f"H{100+i}", {"id": f"H{100+i}"})
    for i in range(3):
        room.set("kb", f"CF{10+i}", {"id": f"CF{10+i}"})
    
    result = room.query("kb", prefix="H")
    assert result.total == 5, f"Expected 5 H-prefix keys, got {result.total}"
    print("T3 PASS: prefix query (5 H-keys)")
    
    # Test 4: range query
    result = room.range_query("kb", "CF", "CF99")
    assert result.total == 3
    print("T4 PASS: range query (3 CF-keys)")
    
    # Test 5: batch set
    res = room.batch_set([
        {"ns": "agent", "key": "a2", "value": {"v": 2}},
        {"ns": "agent", "key": "a3", "value": {"v": 3}},
        {"ns": "bad_ns", "key": "x", "value": 1},  # should fail
        {"ns": "task", "key": "t1", "value": "task1", "ttl": 60},
    ])
    assert res["ok"] == 3, f"Expected 3 OK: {res}"
    assert len(res["errors"]) == 1
    assert room.get("task", "t1") == "task1"
    print("T5 PASS: batch set (3 ok, 1 error)")
    
    # Test 6: meeting create/join/talk
    mid = room.create_meeting("Sprint Planning", "agent_a1")
    assert room.join_meeting(mid, "agent_a2")
    assert room.join_meeting(mid, "agent_a3")
    
    room.talk(mid, "agent_a1", "We need to build the NormativeField")
    room.talk(mid, "agent_a2", "Agreed, let's scope it")
    room.talk(mid, "agent_a3", "I'll handle the LexicalGuard layer")
    print("T6 PASS: meeting with 3 participants, 3 talks")
    
    # Test 7: decision with quorum
    decision = room.decide(mid, "Build S-003 NormativeField this sprint",
                          "agent_a1", {"agent_a1": "yes", "agent_a2": "yes", "agent_a3": "yes"})
    assert decision is not None
    assert decision["yes_count"] == 3
    print("T7 PASS: unanimous decision adopted")
    
    # Test 8: decision fails quorum
    decision2 = room.decide(mid, "Skip testing",
                           "agent_a1", {"agent_a1": "yes", "agent_a2": "no", "agent_a3": "no"})
    assert decision2 is None, "Quorum not met should return None"
    print("T8 PASS: quorum failure blocks decision")
    
    # Test 9: close meeting
    summary = room.close_meeting(mid)
    assert summary["total_talks"] == 3
    assert summary["total_decisions"] == 1
    print("T9 PASS: meeting closed with summary")
    
    # Test 10: storage stats
    stats = room.get_size_stats()
    assert stats["agent"] >= 3
    assert stats["kb"] >= 8
    print(f"T10 PASS: storage stats — {sum(stats.values())} total entries")
    
    print("\nS-004 MeetingRoom: all 10 tests PASSED")


if __name__ == "__main__":
    _test()
