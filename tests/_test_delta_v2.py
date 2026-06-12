# -*- coding: utf-8 -*-
"""Smoke test: DeltaProtocol v2 pattern classification"""
import sys
sys.path.insert(0, r"E:\AI_Workspace\MSS-AI\project")
from mssclaw.core.delta import DeltaProtocol

dp = DeltaProtocol(min_delta=0.3, plateau_window=4)
passed = 0
failed = 0

def assert_pattern(name: str, tasks: list, expected: str):
    global passed, failed
    dp = DeltaProtocol(min_delta=0.3, plateau_window=4)
    for novelty, diversity, task_hash in tasks:
        dp.tick(task_hash, novelty, diversity)
    actual = dp._pattern
    if actual == expected:
        print(f"  ✅ {name}: {expected}")
        passed += 1
    else:
        print(f"  ❌ {name}: expected={expected}, got={actual}, deltas={[h['delta'] for h in dp.history]}")
        failed += 1

print("=== DeltaProtocol v2 Pattern Tests ===\n")

# 1. True decline: monotonically decreasing
assert_pattern("Decline", [
    (0.8, 0.8, "t1"), (0.6, 0.7, "t2"), (0.4, 0.5, "t3"),
    (0.2, 0.3, "t4"), (0.1, 0.1, "t5"),
], "decline")

# 2. Plateau: all below threshold
assert_pattern("Plateau", [
    (0.2, 0.2, "p1"), (0.1, 0.1, "p2"), (0.2, 0.2, "p1"),
    (0.1, 0.2, "p3"),
], "plateau")

# 3. Collapse: zero diversity
assert_pattern("Collapse", [
    (0.2, 0.0, "c1"), (0.1, 0.0, "c1"), (0.1, 0.0, "c1"),
    (0.1, 0.0, "c1"), (0.1, 0.0, "c1"),
], "collapse")

# 4. Exploring: 低→高→低，有回升历史（非真下降）
assert_pattern("Exploring", [
    (0.8, 0.8, "e1"), (0.5, 0.5, "e2"), (0.2, 0.3, "e3"),
    (0.6, 0.5, "e4"), (0.2, 0.2, "e5"), (0.3, 0.3, "e6"),
    (0.2, 0.2, "e7"),
], "exploring")

# 5. Healthy: above threshold
assert_pattern("Healthy", [
    (0.8, 0.8, "h1"), (0.7, 0.7, "h2"), (0.6, 0.6, "h3"),
    (0.8, 0.7, "h4"), (0.7, 0.8, "h5"),
], "healthy")

# 6. Warming: too few samples
assert_pattern("Warming", [
    (0.8, 0.8, "w1"),
], "warming")

# 7. Uniqueness ratio
dp2 = DeltaProtocol()
for i in range(5):
    dp2.tick(f"task_{i}", 0.8, 0.8)
assert dp2.uniqueness_ratio() == 1.0, f"Expected 1.0, got {dp2.uniqueness_ratio()}"
print(f"  ✅ Uniqueness(5 unique): 1.0")
passed += 1

dp3 = DeltaProtocol()
for i in range(5):
    dp3.tick("same_task", 0.8, 0.8)
assert dp3.uniqueness_ratio() == 0.2, f"Expected 0.2, got {dp3.uniqueness_ratio()}"
print(f"  ✅ Uniqueness(1 unique): {dp3.uniqueness_ratio()}")
passed += 1

# 8. Snapshot
print(f"\n=== Snapshot ===")
snap = dp.snapshot()
for k, v in snap.items():
    print(f"  {k}: {v}")

print(f"\n{'ALL PASSED' if failed == 0 else f'{failed} FAILED, {passed} passed'}")
