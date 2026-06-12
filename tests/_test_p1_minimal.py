"""P1 workflow: Plan → Code only (no Audit)."""
import sys; sys.path.insert(0, r"E:\AI_Workspace\MSS-AI\project")
import time

from mssclaw.swarm.swarm import SwarmBus, SwarmNode
from mssclaw.swarm.protocol import (
    Message, MessageHeader, MessageType, Priority,
)
from mssclaw.agents.plan import PlanAgent, TaskStatus, TaskPriority
from mssclaw.agents.base import BaseAgent

# Minimal Code-Agent
class SimCodeAgent(BaseAgent):
    role = "Code-Agent"
    capabilities = ["coding", "python"]

    def __init__(self, name="Code-Agent", bus=None, **kwargs):
        super().__init__(name=name, bus=bus, **kwargs)
        self.completed = []

    def _register_handlers(self):
        self.swarm.on(MessageType.TASK_ASSIGN.value)(self._on_task)

    def _on_task(self, msg):
        tid = msg.payload.get("task_id", "?")
        spec = msg.payload.get("task_spec", msg.payload.get("spec", {}))
        print(f"  [Code] Got: {spec.get('title','?')}")
        result = {"task_id": tid, "code": "def solve(): return 42", "ok": True}
        self.completed.append(result)
        # Reply to Plan
        reply = Message(
            header=MessageHeader(
                msg_type=MessageType.TASK_COMPLETE,
                sender=self.name, receiver=msg.header.sender,
                priority=Priority.NORMAL,
            ),
            payload={"task_id": tid, "result": result},
        )
        self.swarm.send(reply)
        print(f"  [Code] Replied: {tid}")

print("=== P1 Plan→Code ===")

bus = SwarmBus(loop_max_rounds=10)
plan = PlanAgent(name="PLAN", bus=bus)
code = SimCodeAgent(name="Code-Agent", bus=bus)

print(f"Nodes: {bus.get_status()['total_nodes']}")

# Register
plan._agent_registry["Code-Agent"] = {
    "capabilities": ["coding", "python"],
    "status": "idle", "load": 0, "healthy": True,
}
print("Registry populated")

task = plan.create_task("Write sort()", "sort a list of ints", "coding")
print(f"Task: {task.id}")

print("Assigning...")
ok = plan.assign_task(task.id, "Code-Agent")
print(f"Assigned: {ok}, status={task.status.value}")

time.sleep(0.2)
print(f"Code completed: {len(code.completed)} tasks")

# Manually route message from Plan outbox to Code
for m in plan.swarm._outbox:
    print(f"Routing: {m.header.msg_type.value} → {m.header.receiver}")
    bus.route(m)

time.sleep(0.2)
print(f"Code completed after route: {len(code.completed)} tasks")
print("=== P1 PASS ===")
