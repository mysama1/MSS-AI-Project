import sys; sys.path.insert(0, '.')
from mss_agent.core.budget_allocator import HeatTaxBudget, BudgetPrediction

budget = HeatTaxBudget(total_budget=10000.0)
tests = [
    ('generate 500 lines of Python code', 'code_gen'),
    ('delete all temp files', 'delete'),
    ('check todays weather', 'query'),
    ('modify main.py config', 'code_modify'),
    ('translate English to Chinese', 'translation'),
    ('restart nginx service', 'system_call'),
    ('write a README doc', 'code_gen'),
    ('hey hows it going', 'chat'),
]

print(f"{'Type':15s} {'L0':>7} {'L1':>7} {'L2':>7} {'Total':>7} {'Risk':>8} {'OK'}")
print("-" * 65)
for desc, ttype in tests:
    p = budget.predict(desc, task_type=ttype)
    flag = "PASS" if p.affordable else "FAIL"
    print(f"{ttype:15s} {p.l0_pred:7.4f} {p.l1_pred:7.3f} {p.l2_pred:7.2f} {p.total_pred:7.2f} {p.risk_level:>8} {flag}")
    budget.commit(p.task_id, p.total_pred)

print(f"\nRemaining: {budget.remaining:.2f} / {budget.total_budget:.2f}")

# Test adaptive calibration
print("\n--- Adaptive Calibration Test ---")
budget.feedback(budget.usage_log[0].task_id, actual_l2=2.0)  # code_gen predicted ~high, actual low
p2 = budget.predict("generate 500 lines of Python code", task_type="code_gen")
print(f"Before calibration: cost={p.total_pred:.2f} -> After feedback: {p2.total_pred:.2f} (L2={p2.l2_pred:.2f})")

# Edge cases
print("\n--- Edge Cases ---")
for d, t in [("", "chat"), ("a" * 5000, "code_gen")]:
    p = budget.predict(d, task_type=t)
    print(f"'{d[:30]}...' ({t}): total={p.total_pred:.4f}, risk={p.risk_level}")

print("\n--- Budget Exhaustion ---")
b2 = HeatTaxBudget(total_budget=5.0)
p = b2.predict("delete everything", task_type="delete")
print(f"tiny budget: total={p.total_pred:.2f}, affordable={p.affordable}, risk={p.risk_level}")
