"""Trace PlanAgent send at source level."""
import sys; sys.path.insert(0, r"E:\AI_Workspace\MSS-AI\project")

from mssclaw.swarm.swarm import SwarmBus
from mssclaw.swarm.protocol import make_task_assign
from mssclaw.agents.plan import PlanAgent
from mssclaw.agents.base import BaseAgent

bus = SwarmBus()

# Monkey-patch send to trace
original_send = None

class TracedPlanAgent(PlanAgent):
    pass

# Actually, let's monkey-patch at the method level
plan = PlanAgent(name="P", bus=bus)

# Trace the send call step-by-step
t = plan.create_task("test", "desc", "coding")

msg = make_task_assign("P", "Code-Agent", t.id, 
    {"title": "test", "description": "x", "priority": 2, "estimated_tokens": 1000})

print("1. msg created")
print("2. msg.header.sender before:", msg.header.sender)
msg.header.sender = "P"
print("3. msg.header.sender after:", msg.header.sender)
print("4. msg.header.timestamp before:", msg.header.timestamp)
msg.header.timestamp = __import__('time').time()
print("5. msg.header.timestamp after:", msg.header.timestamp)
print("6. calling msg.sign()...")
msg.sign()
print("7. sign done:", msg.content_signature)
print("8. lock check:", plan.swarm._lock.locked())
print("9. acquiring lock...")
with plan.swarm._lock:
    plan.swarm._outbox.append(msg)
    plan.swarm.metrics.messages_sent += 1
    plan.swarm.metrics.msg_ids.append(msg.header.msg_id)
print("10. send complete")
