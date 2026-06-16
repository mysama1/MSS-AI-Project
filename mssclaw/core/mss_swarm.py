# -*- coding: utf-8 -*-
"""
S-002: MSS-Swarm — Agent 注册/发现/通信基类

蜂巢架构的原子层。每个 Agent 作为一个 Node 注册到 Swarm，
通过 pub/sub 消息总线通信，支持四种交互模式：
  - DIRECT: 点对点消息
  - BROADCAST: 全局广播
  - TASK_ASSIGN: 任务派发（自动路由到能力匹配的 Agent）
  - QUERY: 查询-响应模式

设计原则：
  - 零外部依赖（stdlib only）
  - Agent 无状态（所有状态存储在 Swarm 的共享存储中）
  - 每个 Agent 声明 capabilities 和 capacity
  - 自动心跳 + 死亡检测
"""
import json
import time
import threading
import uuid
from dataclasses import dataclass, field
from typing import Dict, List, Callable, Optional, Set, Any
from collections import defaultdict


@dataclass
class AgentInfo:
    """Agent registration metadata."""
    agent_id: str
    agent_type: str          # "kb", "code", "video", "translate", "product", "guardian"
    capabilities: List[str]  # e.g. ["code_gen", "audit", "refactor"]
    capacity: int = 1        # Max concurrent tasks
    status: str = "idle"     # idle / busy / dead
    registered_at: float = 0.0
    last_heartbeat: float = 0.0
    metadata: Dict = field(default_factory=dict)


@dataclass
class Message:
    """Swarm message envelope."""
    msg_id: str
    msg_type: str            # DIRECT / BROADCAST / TASK_ASSIGN / QUERY / RESPONSE
    sender_id: str
    receiver_id: str = ""    # Empty for BROADCAST
    task_id: str = ""        # For task tracking
    payload: Any = None
    timestamp: float = 0.0


class MessageBus:
    """In-memory pub/sub message bus with topic routing."""

    def __init__(self):
        self.subscriptions: Dict[str, List[Callable]] = defaultdict(list)
        self.message_log: List[Message] = []
        self.max_log = 1000
        self._lock = threading.Lock()

    def subscribe(self, agent_id: str, handler: Callable[[Message], Any]):
        with self._lock:
            self.subscriptions[agent_id].append(handler)

    def unsubscribe(self, agent_id: str):
        with self._lock:
            self.subscriptions.pop(agent_id, None)

    def publish(self, msg: Message) -> List[Any]:
        """Publish message. Returns list of handler responses."""
        with self._lock:
            self.message_log.append(msg)
            if len(self.message_log) > self.max_log:
                self.message_log = self.message_log[-self.max_log:]

        results = []
        if msg.msg_type == "BROADCAST":
            with self._lock:
                handlers = []
                for handlers_list in self.subscriptions.values():
                    handlers.extend(handlers_list)
        else:
            with self._lock:
                handlers = self.subscriptions.get(msg.receiver_id, [])

        for handler in handlers:
            try:
                result = handler(msg)
                if result is not None:
                    results.append(result)
            except Exception as e:
                results.append({"error": str(e)})
        return results


class SharedStore:
    """Key-value store shared across all agents in the swarm."""

    def __init__(self):
        self._store: Dict[str, Any] = {}
        self._locks: Dict[str, threading.Lock] = {}
        self._global_lock = threading.Lock()

    def get(self, key: str, default=None):
        return self._store.get(key, default)

    def set(self, key: str, value: Any):
        with self._global_lock:
            self._store[key] = value

    def get_or_create_lock(self, key: str) -> threading.Lock:
        with self._global_lock:
            if key not in self._locks:
                self._locks[key] = threading.Lock()
            return self._locks[key]

    def snapshot(self, prefix: str = "") -> Dict[str, Any]:
        with self._global_lock:
            if prefix:
                return {k: v for k, v in self._store.items() if k.startswith(prefix)}
            return dict(self._store)


class SwarmNode:
    """Base class for all swarm agents."""

    def __init__(self, agent_type: str, capabilities: List[str],
                 bus: MessageBus, store: SharedStore,
                 capacity: int = 1, metadata: Dict = None):
        self.info = AgentInfo(
            agent_id=str(uuid.uuid4())[:8],
            agent_type=agent_type,
            capabilities=capabilities,
            capacity=capacity,
            metadata=metadata or {},
        )
        self.bus = bus
        self.store = store
        self._running = False
        self._heartbeat_thread = None
        self._handlers: Dict[str, Callable] = {}

        # Register message handler
        self.bus.subscribe(self.info.agent_id, self._on_message)

    def _on_message(self, msg: Message) -> Any:
        """Route incoming message to appropriate handler."""
        handler = self._handlers.get(msg.msg_type)
        if handler:
            return handler(msg)
        return None

    def register_handler(self, msg_type: str, handler: Callable):
        """Register a handler for a specific message type."""
        self._handlers[msg_type] = handler

    def send(self, receiver_id: str, payload: Any, msg_type: str = "DIRECT",
             task_id: str = "") -> List[Any]:
        """Send a message to another agent."""
        msg = Message(
            msg_id=str(uuid.uuid4())[:8],
            msg_type=msg_type,
            sender_id=self.info.agent_id,
            receiver_id=receiver_id,
            task_id=task_id,
            payload=payload,
            timestamp=time.time(),
        )
        return self.bus.publish(msg)

    def broadcast(self, payload: Any) -> List[Any]:
        """Broadcast to all agents."""
        return self.send("", payload, "BROADCAST")

    def query(self, receiver_id: str, payload: Any) -> List[Any]:
        """Send a query and collect responses."""
        return self.send(receiver_id, payload, "QUERY")

    def start(self, heartbeat_interval: float = 5.0):
        """Start the agent (background heartbeat)."""
        self._running = True
        self.info.status = "idle"
        self.info.registered_at = time.time()
        self.info.last_heartbeat = time.time()

        def heartbeat_loop():
            while self._running:
                time.sleep(heartbeat_interval)
                if self._running:
                    self.info.last_heartbeat = time.time()

        self._heartbeat_thread = threading.Thread(target=heartbeat_loop, daemon=True)
        self._heartbeat_thread.start()

    def stop(self):
        """Stop the agent."""
        self._running = False
        self.info.status = "dead"
        self.bus.unsubscribe(self.info.agent_id)

    # Subclass hooks
    def on_task_assignment(self, task: Dict) -> Dict:
        """Override: handle a task assigned to this agent."""
        raise NotImplementedError

    def on_query(self, query: Dict) -> Any:
        """Override: handle a query."""
        raise NotImplementedError


class SwarmOrchestrator:
    """Central orchestrator: agent registry, task routing, health monitoring."""

    def __init__(self, bus: MessageBus = None, store: SharedStore = None):
        self.bus = bus or MessageBus()
        self.store = store or SharedStore()
        self.registry: Dict[str, AgentInfo] = {}
        self.task_queue: List[Dict] = []
        self._lock = threading.Lock()

    def register(self, node: SwarmNode) -> str:
        """Register an agent node."""
        with self._lock:
            self.registry[node.info.agent_id] = node.info
        node.start()
        return node.info.agent_id

    def find_agent(self, capability: str) -> Optional[str]:
        """Find an idle agent with the given capability."""
        with self._lock:
            for aid, info in self.registry.items():
                if capability in info.capabilities and info.status == "idle":
                    return aid
        return None

    def find_all(self, capability: str) -> List[str]:
        """Find all agents (idle or busy) with the given capability."""
        with self._lock:
            return [aid for aid, info in self.registry.items()
                    if capability in info.capabilities]

    def assign_task(self, task: Dict, required_capability: str) -> Optional[str]:
        """Assign a task to the best matching agent."""
        agent_id = self.find_agent(required_capability)
        if agent_id:
            with self._lock:
                self.registry[agent_id].status = "busy"
            task["assigned_to"] = agent_id
            task["assigned_at"] = time.time()
            self.store.set(f"task:{task.get('task_id','')}", task)
            return agent_id
        else:
            self.task_queue.append(task)
            return None

    def list_agents(self) -> List[Dict]:
        """List all registered agents with status."""
        with self._lock:
            return [
                {"id": aid, "type": info.agent_type, "status": info.status,
                 "capabilities": info.capabilities,
                 "last_heartbeat": info.last_heartbeat}
                for aid, info in self.registry.items()
            ]

    def get_health(self) -> Dict:
        """Get swarm health overview."""
        now = time.time()
        with self._lock:
            total = len(self.registry)
            alive = sum(1 for info in self.registry.values()
                       if now - info.last_heartbeat < 30)
            idle = sum(1 for info in self.registry.values()
                      if info.status == "idle")
            busy = sum(1 for info in self.registry.values()
                      if info.status == "busy")
        return {
            "total_agents": total, "alive": alive, "idle": idle, "busy": busy,
            "pending_tasks": len(self.task_queue),
        }


# ═══════════════════════════════════════════════════════
# Self-test
# ═══════════════════════════════════════════════════════

def _test():
    bus = MessageBus()
    store = SharedStore()
    orch = SwarmOrchestrator(bus, store)

    # Test 1: register agent
    agent = SwarmNode("test", ["echo"], bus, store)
    aid = orch.register(agent)
    assert len(orch.list_agents()) == 1

    # Test 2: find agent
    assert orch.find_agent("echo") == aid
    assert orch.find_agent("nonexistent") is None

    # Test 3: direct messaging
    received = []
    agent.register_handler("DIRECT", lambda msg: received.append(msg.payload))

    resp = agent.send(aid, {"test": "hello"})
    time.sleep(0.1)
    assert len(received) == 1, f"Expected 1, got {len(received)}: {received}"
    assert received[0]["test"] == "hello"

    # Test 4: broadcast
    received2 = []
    agent.register_handler("BROADCAST", lambda msg: received2.append(msg.payload))
    agent.broadcast({"all": "hello"})
    time.sleep(0.1)
    assert len(received2) == 1

    # Test 5: task assignment
    agent2 = SwarmNode("worker", ["build"], bus, store)
    aid2 = orch.register(agent2)
    assigned = orch.assign_task({"task_id": "t1", "action": "build"}, "build")
    assert assigned == aid2

    # Test 6: health
    health = orch.get_health()
    assert health["total_agents"] == 2
    assert health["alive"] == 2
    assert health["busy"] == 1

    # Test 7: shared store
    store.set("swarm:key", "value")
    assert store.get("swarm:key") == "value"

    # Cleanup
    agent.stop()
    agent2.stop()

    print("S-002 MSS-Swarm: all 7 tests PASSED")


if __name__ == "__main__":
    _test()
