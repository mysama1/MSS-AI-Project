"""P2: CrossDomainRouter + Gateway connectivity verification."""
import sys
sys.path.insert(0, r"E:\AI_Workspace\MSS-AI\project")

from mssclaw.swarm.swarm import SwarmBus, SwarmNode
from mssclaw.core.cross_domain import CrossDomainRouter, CrossDomainChannel
from mssclaw.swarm.protocol import Message, MessageHeader, MessageType, Priority

# Setup buses and nodes
plan_node = SwarmNode(name='Plan-Agent', role='planner', capabilities=['plan', 'decompose'])
code_node = SwarmNode(name='Code-Agent', role='executor', capabilities=['code', 'execute'])
life_node = SwarmNode(name='Life', role='personal', capabilities=['reminder'])

work_bus = SwarmBus(loop_max_rounds=3)
personal_bus = SwarmBus(loop_max_rounds=3)
plan_node.connect(work_bus)
code_node.connect(work_bus)
life_node.connect(personal_bus)

ws = work_bus.get_status()
ps = personal_bus.get_status()
print(f"Work bus: {ws['total_nodes']} nodes, healthy={ws['healthy_nodes']}")
print(f"Personal bus: {ps['total_nodes']} nodes, healthy={ps['healthy_nodes']}")

# Create router
router = CrossDomainRouter(work_bus=work_bus, personal_bus=personal_bus)
router.start()

# Test 1: Work→Personal LIFE_NOTIFY (dry_run)
r1 = router.send(CrossDomainChannel.LIFE_NOTIFY,
                 sender='Plan-Agent', receiver='Life',
                 payload={'text': 'dinner time', 'time': '18:00'},
                 dry_run=True)
assert r1['allowed'], f"LIFE_NOTIFY should be allowed: {r1}"
print(f"1. LIFE_NOTIFY W→P (dry): PASS (allowed={r1['allowed']})")

# Test 2: Personal→Work WORK_PAUSE (dry_run)
r2 = router.send(CrossDomainChannel.WORK_PAUSE,
                 sender='Concierge', receiver='PLAN',
                 payload={'reason': 'dinner'},
                 dry_run=True)
assert r2['allowed'], f"WORK_PAUSE should be allowed: {r2}"
print(f"2. WORK_PAUSE P→W (dry): PASS (allowed={r2['allowed']})")

# Test 3: Block reverse direction (LIFE_NOTIFY from Personal → Work should fail)
r3 = router.send(CrossDomainChannel.LIFE_NOTIFY,
                 sender='Concierge', receiver='PLAN',
                 payload={'text': 'leak'},
                 dry_run=True)
assert not r3['allowed'], f"Reverse LIFE_NOTIFY should be blocked: {r3}"
print(f"3. Blocked reverse (dry): PASS (allowed={r3['allowed']})")

# Test 4: Work bus internal route (non-cross-domain)
msg = Message(
    header=MessageHeader(
        sender='Plan-Agent', receiver='Code-Agent',
        msg_type=MessageType.TASK_ASSIGN, priority=Priority.NORMAL
    ),
    payload={'task': 'verify_p2'}
)
ok = work_bus.route(msg)
assert ok, "Work bus route failed"
print(f"4. Work bus route internal: PASS (sent={ok})")

# Test 5: Verify Code-Agent received the message
node = work_bus._nodes.get('Code-Agent')
assert node and len(node._inbox) > 0, "Code-Agent should have received message"
delivered = node._inbox[-1]
assert delivered.payload['task'] == 'verify_p2', f"Wrong payload: {delivered.payload}"
print(f"5. Message delivered: PASS (Code-Agent inbox={len(node._inbox)})")

# Stats
stats = router.get_stats()
print(f"\nStats: total={stats['total']}, w2p={stats['work_to_personal']}, p2w={stats['personal_to_work']}, blocked={stats['blocked']}")

# Test 6: Gateway health check
from mssclaw.channels.openclaw import OpenClawChannel
ch = OpenClawChannel(timeout=10)
health = ch.health()
print(f"\n6. Gateway health: {health}")
assert health['available'], f"Gateway not available: {health}"

print("\n=== P2 COMPLETE: 6/6 PASS ===")
print("Gateway: RUNNING (port 50942)")
print("CrossDomainRouter: cross-domain + internal routing verified")
