"""Is it a hang or just SIGKILL?"""
import sys; sys.path.insert(0, r"E:\AI_Workspace\MSS-AI\project")

from mssclaw.swarm.swarm import SwarmBus, SwarmNode
from mssclaw.swarm.protocol import make_task_assign, MessageType

bus = SwarmBus()
plan_node = SwarmNode(name='PLAN', role='planner', capabilities=['planning'])
plan_node.connect(bus)
plan_node.on(MessageType.TASK_ASSIGN.value)(lambda m: print('handler', flush=True))

msg = make_task_assign('PLAN', 'Code-Agent', 'task-1',
    {'title':'test','description':'x','priority':2,'estimated_tokens':1000})

print('1 send start', flush=True)
plan_node.send(msg)
print('2 send done', flush=True)
print('3 route start', flush=True)
bus.route(msg)
print('4 route done', flush=True)
