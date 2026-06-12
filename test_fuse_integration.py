"""Integration test for heat_tax_fuse in MSSAgent."""
import sys, json
sys.path.insert(0, r'E:\AI_Workspace\MSS-AI\project\mss_agent')

from core.agent import MSSAgent

# Test 1: Agent without fuse (backward compat)
agent1 = MSSAgent(name='TestNoFuse')
r1 = agent1.run('分析这段代码的安全性')
print(f'[NoFuse] success={r1.success} abort={r1.aborted} delta={r1.delta:.3f}')
assert r1.success, "No-fuse agent should succeed on normal task"

# Test 2: Agent with fuse
agent2 = MSSAgent(name='TestFuse', enable_fuse=True)
r2 = agent2.run('分析这段代码的安全性')
print(f'[Fuse]   success={r2.success} abort={r2.aborted} delta={r2.delta}')
assert r2.success, "Fuse agent should succeed on normal task"

# Test 3: Trigger waste detection
r3 = agent2.run('重写 改写 换个说法')
print(f'[Waste]  success={r3.success} abort={r3.aborted} reason={r3.reason[:60]}')
assert r3.aborted, "Fuse agent should abort on waste prompt"

# Test 4: Health report
report = agent2.health_report()
print(f'[Health] runs={report["runs"]} aborts={report["aborts"]} fuse={json.dumps(report.get("fuse", {}))}')

# Test 5: Backward compat — old agent without fuse still works
agent3 = MSSAgent(name='OldStyle')
r4 = agent3.run('分析MSS-AI架构的安全性设计')
print(f'[OldStyle] success={r4.success} abort={r4.aborted}')
assert r4.success

print('\nAll integration tests passed')
