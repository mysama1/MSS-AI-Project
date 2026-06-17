# D6-013: VCG成本建模 — Vickrey-Clarke-Groves Mechanism for MSS
""" 
MSS决策场景: N个Agent共享资源池R, 每个Agent i有真实估值v_i和报告估值b_i
VCG机制确保 truthful bidding 是弱占优策略:
  payoff_i = v_i(choice) - p_i
  p_i = Σ_{j≠i} v_j(alt) - Σ_{j≠i} v_j(actual)
  
  即: 你的支付 = 你给其他人造成的外部性成本
"""
import numpy as np, json, time
from pathlib import Path
from itertools import combinations

VERSION = "D6-013 v1.0"
N_AGENTS = [3, 4, 5, 6, 8]
N_SEEDS = 50
RESOURCE_CAPACITY = 100
np.random.seed(42)

results = []
for n in N_AGENTS:
    for seed in range(N_SEEDS):
        np.random.seed(seed * 1000 + n)
        
        # True valuations v_i ~ U[10, 100]
        v_true = np.random.uniform(10, 100, n)
        # Resource demands d_i ~ U[5, 30]
        demands = np.random.uniform(5, 30, n)
        # Binary preference: each agent either wants resource or not
        wants = np.random.binomial(1, 0.7, n)  # 70% want resource
        
        # --- VCG Mechanism ---
        # Sort by v/d ratio (efficiency)
        efficiency = np.where(wants > 0, v_true / demands, 0)
        order = np.argsort(-efficiency)
        
        # Greedy allocation
        allocated = np.zeros(n, dtype=bool)
        remaining = RESOURCE_CAPACITY
        for i in order:
            if wants[i] and demands[i] <= remaining:
                allocated[i] = True
                remaining -= demands[i]
        
        # VCG payments
        payments = np.zeros(n)
        for i in range(n):
            if not allocated[i]:
                continue
            # Counterfactual: re-run allocation without i
            alt_allocated = np.zeros(n, dtype=bool)
            alt_remaining = RESOURCE_CAPACITY
            # i's demand goes to next-best agents
            alt_order = [j for j in order if j != i]
            for j in alt_order:
                if wants[j] and demands[j] <= alt_remaining:
                    alt_allocated[j] = True
                    alt_remaining -= demands[j]
            # Payment = welfare loss caused by i
            alt_welfare_others = sum(v_true[j] for j in range(n) if j != i and alt_allocated[j])
            actual_welfare_others = sum(v_true[j] for j in range(n) if j != i and allocated[j])
            payments[i] = max(0, alt_welfare_others - actual_welfare_others)
        
        total_welfare = sum(v_true[i] for i in range(n) if allocated[i])
        total_payment = sum(payments)
        
        # --- Strategic Deviation Analysis ---
        # For each agent: test underreporting (b_i = 0.5 * v_i) and overreporting (b_i = 1.5 * v_i)
        def run_vcg(bids):
            eff = np.where(wants > 0, bids / demands, 0)
            ord_ = np.argsort(-eff)
            al = np.zeros(n, dtype=bool)
            rem = RESOURCE_CAPACITY
            for j in ord_:
                if wants[j] and demands[j] <= rem:
                    al[j] = True
                    rem -= demands[j]
            return al
        
        truthful_alloc = run_vcg(v_true)
        max_incentive = 0
        n_gainers = 0
        
        for i in range(n):
            truthful_utility = (v_true[i] - payments[i]) if truthful_alloc[i] else 0
            
            for bid_mult in [0.5, 0.8, 1.2, 1.5, 2.0]:
                bids_dev = v_true.copy()
                bids_dev[i] *= bid_mult
                dev_alloc = run_vcg(bids_dev)
                dev_welfare = sum(v_true[j] for j in range(n) if dev_alloc[j])
                truthful_welfare = sum(v_true[j] for j in range(n) if truthful_alloc[j])
                
                # Recompute payments for deviation scenario
                dev_payments = np.zeros(n)
                for j in range(n):
                    if not dev_alloc[j]:
                        continue
                    alt_o = [k for k in range(n) if k != j]
                    alt_al = np.zeros(n, dtype=bool)
                    alt_rem = RESOURCE_CAPACITY
                    alt_eff = np.where(wants > 0, bids_dev / demands, 0)
                    alt_order_full = np.argsort(-alt_eff)
                    for k in alt_order_full:
                        if k != j and wants[k] and demands[k] <= alt_rem:
                            alt_al[k] = True
                            alt_rem -= demands[k]
                    aw = sum(v_true[k] for k in range(n) if k != j and alt_al[k])
                    act_w = sum(v_true[k] for k in range(n) if k != j and dev_alloc[k])
                    dev_payments[j] = max(0, aw - act_w)
                
                dev_utility = (v_true[i] - dev_payments[i]) if dev_alloc[i] else 0
                gain = dev_utility - truthful_utility
                if gain > max_incentive:
                    max_incentive = gain
                if gain > 0.01:
                    n_gainers += 1
        
        # Key metrics
        budget_balance = total_payment  # VCG surplus
        n_allocated = sum(allocated)
        resource_util = 1.0 - remaining / RESOURCE_CAPACITY
        
        results.append({
            "n": n, "seed": seed,
            "welfare": total_welfare,
            "payment_total": total_payment,
            "budget_ratio": total_payment / max(1, total_welfare),
            "allocated": int(n_allocated),
            "resource_util": round(resource_util, 4),
            "max_incentive": round(max_incentive, 4),
            "n_incentive_gainers": n_gainers,
            "truthful": 1 if max_incentive <= 0.001 else 0  # ε-truthful
        })

# Aggregate
df = {}
for key in ["n"]:
    df[key] = [r[key] for r in results]
    
print("=" * 70)
print(f"D6-013: VCG成本建模 — {VERSION}")
print(f"N_configs={len(N_AGENTS)}, seeds={N_SEEDS}")
print("=" * 70)

for n in N_AGENTS:
    subset = [r for r in results if r["n"] == n]
    avg_w = np.mean([r["welfare"] for r in subset])
    avg_p = np.mean([r["payment_total"] for r in subset])
    avg_br = np.mean([r["budget_ratio"] for r in subset])
    avg_util = np.mean([r["resource_util"] for r in subset])
    avg_mi = np.mean([r["max_incentive"] for r in subset])
    tr_rate = np.mean([r["truthful"] for r in subset])
    avg_gainers = np.mean([r["n_incentive_gainers"] for r in subset])
    
    print(f"\nN={n:2d}:")
    print(f"  福利={avg_w:.1f}  支付={avg_p:.1f}  预算比={avg_br:.4f}")
    print(f"  资源利用={avg_util:.4f}  分配率={n*tr_rate:.1f}/{n}")
    print(f"  最大谎报收益={avg_mi:.4f}  ε-truthful率={tr_rate:.1%}")
    print(f"  平均获利者/轮={avg_gainers:.2f}")

# Truthful revelation check
overall_tr = np.mean([r["truthful"] for r in results])
print(f"\n{'='*70}")
print(f"全局 ε-truthful 率: {overall_tr:.1%}")
print(f"预算非平衡总量: {sum(r['payment_total'] for r in results):.1f}")

# Save
out_path = Path("E:/AI_Workspace/MSS-AI/project/kb/L3_EMPIRICAL/d6_013_vcg_results.json")
out_path.parent.mkdir(parents=True, exist_ok=True)
with open(out_path, "w") as f:
    json.dump({
        "d_id": "D6-013",
        "version": VERSION,
        "n_configs": N_AGENTS,
        "n_seeds": N_SEEDS,
        "overall_truthful_rate": overall_tr,
        "total_budget_surplus": sum(r["payment_total"] for r in results),
        "aggregates": {str(n): {"welfare": np.mean([r["welfare"] for r in results if r["n"]==n]),
                                "budget_ratio": np.mean([r["budget_ratio"] for r in results if r["n"]==n]),
                                "truthful_rate": np.mean([r["truthful"] for r in results if r["n"]==n])}
                       for n in N_AGENTS},
        "raw": results[:10]  # first 10 for inspection
    }, f, indent=2)

print(f"\nSaved: {out_path}")
