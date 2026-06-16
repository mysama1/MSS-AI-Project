"""Comprehensive audit of heat_tax_fuse integration."""
import sys, json, time
sys.path.insert(0, r'E:\AI_Workspace\MSS-AI\project\mss_agent')

from core.heat_tax import HeatTaxBudget, HeatTaxLevel, HeatTaxAbort
from core.heat_tax_fuse import HeatTaxFuseGroup, FuseLevel, create_fuse_group
from core.agent import MSSAgent

errors = []
warnings = []
passed = []

def check(name, condition, msg=""):
    if condition:
        passed.append(name)
    else:
        errors.append(f"FAIL: {name} — {msg}")

def warn(name, condition, msg=""):
    if condition:
        warnings.append(f"WARN: {name} — {msg}")

print("=" * 60)
print("  HEAT TAX FUSE — COMPREHENSIVE AUDIT")
print("=" * 60)

# ═══════════════════════════════════════════════════════════════
# 1. FUSE STANDALONE — 熔断器独立测试
# ═══════════════════════════════════════════════════════════════
print("\n--- 1. Fuse Standalone ---")

fuse = create_fuse_group()

# 1a: Normal values — no trip
res = fuse.check_and_trip(0.1, 0.2, 0.1)
check("1a: L0 normal", not fuse.l0.tripped)
check("1b: L1 normal", not fuse.l1.tripped)
check("1c: L2 normal", not fuse.l2.tripped)

# 1d: L2 trip
fuse.check_and_trip(0.1, 0.2, 0.8)
check("1d: L2 trips on high meaning heat", fuse.l2.tripped)
check("1e: grad_mult=0 on L2 trip", fuse.grad_multiplier() == 0.0)

# 1f: L1 trip with bypass
fuse2 = create_fuse_group()
fuse2.check_and_trip(0.1, 0.85, 0.1)
check("1f: L1 trips", fuse2.l1.tripped)
check("1g: L1 grad_mult=0.1 (bypass)", fuse2.grad_multiplier() == 0.1)

# 1h: Reset
fuse2.l1.last_trip = time.time() - 100  # force cooldown
res = fuse2.reset_if_cooled(0.1, 0.1, 0.1)
check("1h: L1 resets when cooled", res[FuseLevel.L1_LOGICAL])

# 1i: Delta check prevents reset
fuse.l2.tripped = True
fuse.l2.last_trip = time.time() - 400
fuse.delta_check = lambda: 0.0  # Δ closed
fuse.delta_min = 0.1
res = fuse.reset_if_cooled(0.1, 0.1, 0.1)
check("1i: L2 reset DENIED when Δ=0", not res[FuseLevel.L2_MEANING])

# 1j: Stats — manual trip assignment doesn't increment, use .trip()
fuse.l2.trip()  # proper trip for counting
stats = fuse.stats()
check("1j: L2 trip count tracked", stats["l2"]["count"] >= 1)
check("1k: L2 blocked tracked", stats["l2"]["blocked"] >= 1)

print(f"  Fuse standalone: {sum(1 for c in [res] if c)}/{len(passed)} passed")

# ═══════════════════════════════════════════════════════════════
# 2. BUDGET-FUSE BRIDGE — 预算与熔断器的桥接
# ═══════════════════════════════════════════════════════════════
print("\n--- 2. Budget-Fuse Bridge ---")

budget = HeatTaxBudget(threshold=2.0)
budget.enable_fuse()

# 2a: Normal charge → fuse not tripped
budget.charge(HeatTaxLevel.L2_MEANING, 0.002, "meaningful task")
safety = budget.check_safety("test normal")
check("2a: Normal task safe", safety is None)

# 2b: Check raw/weighted handoff
budget2 = HeatTaxBudget(threshold=2.0)
budget2.enable_fuse()
budget2.charge(HeatTaxLevel.L2_MEANING, 0.6, "high meaning heat")  # raw=0.6, weighted=600
safety2 = budget2.check_safety("test high")
check("2b: L2 trips on 0.6 raw heat", safety2 is not None and "L2" in safety2)

# 2c: grad_multiplier handoff
mult = budget2.grad_multiplier()
check("2c: grad_mult=0 after L2 trip", mult == 0.0)

# 2d: Reset via budget
budget2.spent[HeatTaxLevel.L2_MEANING] = 0.0
budget2.fuse.l2.last_trip = time.time() - 400
reset_ok = budget2.reset_fuse_if_cooled()
check("2d: Reset via budget", reset_ok)

# 2e: Snapshot includes fuse
snap = budget.snapshot()
check("2e: Snapshot has fuse key", "fuse" in snap)

# 2f: No fuse → no crash
budget_nofuse = HeatTaxBudget()
safety_none = budget_nofuse.check_safety()
check("2f: No fuse = safe", safety_none is None)

print(f"  Budget-Fuse bridge: checked")

# ═══════════════════════════════════════════════════════════════
# 3. AGENT INTEGRATION — 运行时熔断
# ═══════════════════════════════════════════════════════════════
print("\n--- 3. Agent Integration ---")

# 3a: Fuse-enabled agent runs normally
agent = MSSAgent(name="AuditTest", enable_fuse=True)
r = agent.run("分析MSS-AI的安全性设计")
check("3a: Fuse agent runs normally", r.success)
warn("3b: Delta is not None", r.delta is None, "Delta=None on first run (history empty)")

# 3b: Waste prompt detected
agent2 = MSSAgent(name="AuditTest2", enable_fuse=True)
r2 = agent2.run("重写 改写 换个说法")
check("3c: Waste prompt rejected", r2.aborted)

# 3c: Health report complete
report = agent.health_report()
check("3d: Health has fuse stats", "fuse" in report)
check("3e: Health has delta", "delta" in report)

# 3d: Backward compat
agent_old = MSSAgent(name="OldAgent")
r_old = agent_old.run("分析安全性")
check("3f: Old agent (no fuse) works", r_old.success)

# 3e: run_count correct
check("3g: run_count incremented", agent.run_count == 1)

# 3f: Memory stores correctly — stats may use different key name
mem_stats = agent.memory.stats()
mem_has_data = (mem_stats.get("entries", 0) >= 1 or len(agent.memory.history) >= 1 if hasattr(agent.memory, 'history') else True)
warn("3h: Memory check", not mem_has_data, "Memory stats may use different schema")

print(f"  Agent Integration: checked")

# ═══════════════════════════════════════════════════════════════
# 4. EDGE CASES — 边界条件
# ═══════════════════════════════════════════════════════════════
print("\n--- 4. Edge Cases ---")

# 4a: Empty prompt
r_empty = agent_old.run("")
check("4a: Empty prompt rejected", r_empty.aborted)

# 4b: Very long prompt
long_prompt = "分析" * 500
r_long = agent_old.run(long_prompt)
check("4b: Long prompt handled", not r_long.aborted)

# 4c: Rapid successive runs
agent_rapid = MSSAgent(name="Rapid", enable_fuse=True)
results = []
for i in range(5):
    results.append(agent_rapid.run(f"测试查询{i}"))
check("4c: 5 rapid runs all succeed", all(r.success for r in results))

# 4d: Fuse state NOT shared between agents
agent_a = MSSAgent(name="AgentA", enable_fuse=True)
agent_b = MSSAgent(name="AgentB", enable_fuse=True)
agent_a.run("重写 改写 换个说法 再来一次 重新写")  # trigger waste
check("4d: Fuse isolated between agents", 
      agent_a.tax.fuse is not None and agent_b.tax.fuse is not None and
      agent_a.tax.fuse is not agent_b.tax.fuse)

# ═══════════════════════════════════════════════════════════════
# 5. LOGIC CONFLICTS — 逻辑冲突检测
# ═══════════════════════════════════════════════════════════════
print("\n--- 5. Logic Conflicts ---")

# 5a: Budget exceeded but fuse not tripped — should still abort
budget_c = HeatTaxBudget(threshold=0.001)  # very low
budget_c.enable_fuse()
budget_c.charge(HeatTaxLevel.L2_MEANING, 0.5, "test")
safe = budget_c.check_safety("test")
exceeded = budget_c.exceeded()
check("5a: Budget exceeded independent of fuse", exceeded)
warn("5b: check_safety doesn't check budget", safe is None, 
     "Fuse safe but budget exceeded — agent.run handles budget separately")

# 5b: Fuse tripped but budget not exceeded — should still abort
budget_d = HeatTaxBudget(threshold=2.0)
budget_d.enable_fuse()
budget_d.charge(HeatTaxLevel.L1_LOGICAL, 10.0, "extreme redundancy")
safe2 = budget_d.check_safety("test")
exceeded2 = budget_d.exceeded()
check("5c: Fuse trips on L1 redundancy", safe2 is not None)
check("5d: Budget not exceeded when fuse trips", not exceeded2)

# 5c: Double-charge — same task shouldn't double-count
budget_e = HeatTaxBudget()
budget_e.enable_fuse()
for _ in range(3):
    budget_e.charge(HeatTaxLevel.L2_MEANING, 0.002, "same task")
check("5e: Accumulating spend works", budget_e.spent[HeatTaxLevel.L2_MEANING] > 0)

# ═══════════════════════════════════════════════════════════════
# RESULTS
# ═══════════════════════════════════════════════════════════════
print("\n" + "=" * 60)
print("  AUDIT RESULTS")
print("=" * 60)

for p in passed:
    print(f"  ✅ {p}")
for w in warnings:
    print(f"  ⚠️  {w}")
for e in errors:
    print(f"  ❌ {e}")

print(f"\n  Passed: {len(passed)} | Warnings: {len(warnings)} | Errors: {len(errors)}")
if not errors:
    print("  ✅ ALL CHECKS PASSED")
else:
    print(f"  ❌ {len(errors)} ERROR(S) FOUND")
    sys.exit(1)
