"""Debug: find where assign_task hangs."""
import sys
sys.path.insert(0, r"E:\AI_Workspace\MSS-AI\project")

from mssclaw.swarm.swarm import SwarmBus
from mssclaw.agents.plan import PlanAgent, TaskPriority

bus = SwarmBus(loop_max_rounds=10)
plan = PlanAgent(name="PLAN", bus=bus)
plan._agent_registry["Code-Agent"] = {
    "capabilities": ["coding"], "status": "idle", "load": 0, "healthy": True
}

task = plan.create_task("test", "test desc", "coding")
print(f"task: {task.id}")

# Step-by-step
print("step: check task exists")
t = plan._tasks.get(task.id)
print(f"  task found: {t is not None}")

print("step: agent info")
info = plan._agent_registry.get("Code-Agent", {})
caps = info.get("capabilities", [])
print(f"  caps: {caps}")

print("step: make_task_assign")
from mssclaw.swarm.protocol import make_task_assign
msg = make_task_assign("PLAN", "Code-Agent", task.id, {
    "title": "test", "description": "x", "priority": 2, "estimated_tokens": 1000,
})
print(f"  msg created, id={msg.header.msg_id}")

print("step: swarm.send")
result = plan.swarm.send(msg)
print(f"  sent, id={result}")

print("step: update task")
task.assigned_to = "Code-Agent"
task.status = TaskStatus.ASSIGNED
print(f"  done")

print("assign_task OK")
