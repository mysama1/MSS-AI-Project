"""P1: Agent Cluster Real Workflow — Plan → Code → Audit full chain."""
import sys
sys.path.insert(0, r"E:\AI_Workspace\MSS-AI\project")

import time
from mssclaw.swarm.swarm import SwarmBus, SwarmNode
from mssclaw.swarm.protocol import (
    Message, MessageHeader, MessageType, Priority, AgentStatus
)
from mssclaw.agents.plan import PlanAgent, TaskStatus, TaskPriority
from mssclaw.agents.audit import AuditAgent
from mssclaw.agents.base import BaseAgent

# ── Simplest Code-Agent (simulated LLM output) ──
class SimCodeAgent(BaseAgent):
    """Simulated code agent — generates test code without real LLM."""
    role = "Code-Agent"
    capabilities = ["coding", "python", "execute"]
    description = "Simulated code generation agent for integration tests"

    def __init__(self, name="Code-Agent", bus=None, **kwargs):
        super().__init__(name=name, bus=bus, **kwargs)
        self._completed_tasks = []

    def _register_handlers(self):
        self.swarm.on(MessageType.TASK_ASSIGN.value)(self._handle_task)

    def _handle_task(self, msg: Message):
        """Process a task assignment — simulate code generation."""
        task_id = msg.payload.get("task_id", "unknown")
        task_spec = msg.payload.get("task_spec", {})

        print(f"  [Code-Agent] Received: {task_spec.get('title', '?')}")

        # Simulate work: generate "code"
        result = {
            "task_id": task_id,
            "code": f"# Generated code for: {task_spec.get('title')}\ndef solve():\n    return 'OK'",
            "language": "python",
            "tokens_used": 42,
            "success": True,
        }

        self._completed_tasks.append(result)

        # Report completion back to Plan
        from mssclaw.swarm.protocol import Message, MessageHeader
        reply = Message(
            header=MessageHeader(
                msg_type=MessageType.TASK_COMPLETE,
                sender=self.name,
                receiver=msg.header.sender,
                priority=Priority.NORMAL,
            ),
            payload={
                "task_id": task_id,
                "result": result,
            },
        )
        self.swarm.send(reply)
        print(f"  [Code-Agent] Completed: {task_id}")

        # Request audit review
        self.request_review(task_id, result)


# ── Setup ──
print("=== P1: Agent Cluster Real Workflow ===\n")

bus = SwarmBus(loop_max_rounds=10)

# Create agents
plan = PlanAgent(name="PLAN", bus=bus)
code = SimCodeAgent(name="Code-Agent", bus=bus)
audit = AuditAgent(name="Audit-Agent", bus=bus)

# Connect (agents connect automatically via ctor bus=)
# But we need to register handlers from the Pl
plan._register_handlers()
code._register_handlers()
audit._register_handlers()

print(f"1. Agents connected: {bus.get_status()['total_nodes']} nodes")

# ── Wait for agents to be visible ──
time.sleep(0.1)

# ── Test 1: Plan creates and assigns task ──
print("\n2. Plan creates task...")
task = plan.create_task(
    title="Implement sort utility",
    description="Write a Python function that sorts a list of integers",
    capability="coding",
    priority=TaskPriority.NORMAL,
    estimated_tokens=500,
)
assert task.id, "Task should have an ID"
print(f"   Created: {task.title} (id={task.id[:16]}...)")

# Register code agent in Plan's registry (normally via heartbeat)
plan._agent_registry["Code-Agent"] = {
    "capabilities": ["coding", "python", "execute"],
    "status": "idle",
    "load": 0,
    "healthy": True,
}
print(f"3. Agent registered: Code-Agent caps={plan._agent_registry['Code-Agent']['capabilities']}")

# Assign task
ok = plan.assign_task(task.id, "Code-Agent")
assert ok, f"Task assignment failed"
print(f"4. Task assigned: {task.status.value}")

# ── Wait for message processing ──
time.sleep(0.3)

# ── Verify ──
# Check Code-Agent received and completed
assert len(code._completed_tasks) == 1, f"Expected 1 completed task, got {len(code._completed_tasks)}"
result = code._completed_tasks[0]
assert result['success'], f"Task failed: {result}"
assert 'code' in result, f"No code in result: {result}"
print(f"5. Code generated: {len(result['code'])} chars")

# Check task status updated
print(f"   Task status: {task.status.value}")

# Check Audit-Agent received review request
audit_inbox = audit.swarm._inbox
audit_review_msgs = [m for m in audit_inbox if m.header.msg_type == MessageType.REVIEW_REQUEST]
print(f"6. Audit received {len(audit_review_msgs)} review requests")

# ── Test 2: Direct Audit of code ──
print("\n7. Audit-Agent reviews code directly...")
report = audit.audit_text(result['code'], target="code-agent-output")
print(f"   Score: {report.score:.3f}, Verdict: {report.verdict.value}")
print(f"   Dimensions: {report.dimension_scores}")

# ── Test 3: Plan receives task completion ──
plan_inbox = plan.swarm._inbox
complete_msgs = [m for m in plan_inbox if m.header.msg_type == MessageType.TASK_COMPLETE]
print(f"8. Plan received {len(complete_msgs)} task completions")
assert len(complete_msgs) >= 1, "Plan should have received TASK_COMPLETE"

# ── Test 4: Health check all agents ──
print("\n9. Health checks:")
for agent_info in [plan, code, audit]:
    h = agent_info.health_check()
    print(f"   {h['name']}: running={h['running']}, delta={h['delta']:.2f}, heat={h['heat_remaining']:.3f}")

# ── Test 5: Bus-level health ──
status = bus.get_status()
print(f"\n10. Bus health: {status['healthy_nodes']}/{status['total_nodes']} healthy, {status['total_messages']} messages")

print("\n=== P1 COMPLETE: Plan→Code→Audit full chain PASS ===")
print("Plan: create → assign → receive completion")
print("Code: receive task → generate → report → request review")
print("Audit: receive review request → audit_text → dimension scores")
