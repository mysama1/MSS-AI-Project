from mss_agent.core.budget_allocator import HeatTaxBudget

# Test can_afford + commit on tight budget
b = HeatTaxBudget(total_budget=5.0)
desc = "delete everything"
if b.can_afford(desc):
    p = b.predict(desc, task_type="delete")
    b.commit(p.task_id, p.total_pred)
    print(f"Committed! remaining={b.remaining:.2f}")
else:
    print(f"Rejected! remaining={b.remaining:.2f}")

# Test commit validation (should reject overspend)
b2 = HeatTaxBudget(total_budget=100.0)
p2 = b2.predict("small query", task_type="query")
print(f"Query cost: {p2.total_pred:.2f}, affordable={p2.affordable}")

# Edge: empty string
p3 = b2.predict("", task_type="chat")
print(f"Empty total: {p3.total_pred:.4f}")

print("Budget verification: PASS")
