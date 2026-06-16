"""Narrow down lock issue."""
import sys
sys.path.insert(0, r"E:\AI_Workspace\MSS-AI\project")
import time

from mssclaw.swarm.swarm import SwarmBus
from mssclaw.agents.plan import PlanAgent
from mssclaw.swarm.protocol import make_task_assign

bus = SwarmBus(loop_max_rounds=10)
plan = PlanAgent(name="PLAN", bus=bus)
plan._agent_registry["Code-Agent"] = {
    "capabilities": ["coding"], "status": "idle", "load": 0, "healthy": True
}

task = plan.create_task("test", "test desc", "coding")

print("Before make_task_assign")
msg = make_task_assign("PLAN", "Code-Agent", task.id, {
    "title": "test", "description": "x", "priority": 2, "estimated_tokens": 1000,
})
print(f"After make_task_assign: msg_id={msg.header.msg_id}")

print("Checking locks...")
print(f"  swarms._lock locked: {plan.swarm._lock.locked()}")
print(f"  bus._lock locked: {bus._lock.locked()}")
print(f"  plan._lock locked: {plan._lock.locked()}")

print("Before swarm.send")
# Direct outbox append test - bypass send()
plan.swarm._outbox.append(msg)
print("After outbox append")

print("Before msg.sign")
msg.sign()
print("After msg.sign")

print("Before send")
result = plan.swarm.send(msg)
print(f"After send: {result}")

task.assigned_to = "Code-Agent"
print("assign OK")
