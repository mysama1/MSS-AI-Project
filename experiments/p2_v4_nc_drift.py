"""
P2 v4: N_c漂移精确定位 — 细粒度trust_budget扫描临界区 0.01-0.30

Purpose: P2 v3 found negative γ/ν, but transition region is narrow (0.05-0.25).
This run scans with 0.01 granularity to precisely locate N_c and verify FSS.
"""
import math, random, time, json
from statistics import mean
from pathlib import Path

NOISE = 0.05
N_VALUES = [8, 16, 24, 32, 48, 64, 96, 128]
P_CLOSE = [0.10, 0.20]
TRUST_BUDGETS = [round(0.01 * i, 2) for i in range(1, 31)]  # 0.01-0.30
N_SEEDS = 200
N_ROUNDS = 500


def simulate(N, p_close, trust_budget):
    doors = [True] * N
    trust = [trust_budget] * N
    for _ in range(N_ROUNDS):
        i, j = random.randint(0, N - 1), random.randint(0, N - 1)
        if i == j: continue
        if random.random() < NOISE:
            if doors[i] and doors[j]:
                if random.random() < 0.5: doors[i] = not doors[i]
                if random.random() < 0.5: doors[j] = not doors[j]
            continue
        if doors[i] and doors[j]:
            if random.random() < p_close:
                closer = i if random.random() < 0.5 else j
                doors[closer] = False
                trust[closer] = max(0, trust[closer] - 0.1)
        elif doors[i] != doors[j]:
            closed, open_ = (i, j) if not doors[i] else (j, i)
            if trust[open_] < trust_budget * 0.6 and random.random() < 0.3:
                doors[open_] = False
        for k in range(N):
            if not doors[k] and trust[k] > trust_budget * 0.8:
                if random.random() < 0.03: doors[k] = True
    return sum(doors) / N


def susceptibility(data):
    rho_mean = mean(data)
    rho2_mean = sum(x * x for x in data) / len(data)
    return len(data) * (rho2_mean - rho_mean * rho_mean)


print("P2 v4: N_c drift — fine-grained TB 0.01-0.30")
print(f"N: {N_VALUES}, pc: {P_CLOSE}, Seeds: {N_SEEDS}, Rounds: {N_ROUNDS}")
print(f"{'='*70}")

all_results = {}
for N_val in N_VALUES:
    print(f"\nN={N_val}:")
    tb_data = {}
    for pc in P_CLOSE:
        rhos, chis = [], []
        for tb in TRUST_BUDGETS:
            vals = []
            for seed in range(N_SEEDS):
                random.seed(seed * 1000 + hash(f"{N_val}_{pc}_{tb}") % 10007)
                vals.append(simulate(N_val, pc, tb))
            rhos.append(mean(vals))
            chis.append(susceptibility(vals))
        
        # Find critical tb where rho crosses 0.5
        rho_dict = dict(zip(TRUST_BUDGETS, rhos))
        chi_dict = dict(zip(TRUST_BUDGETS, chis))
        
        mid = next((tb for tb, rho in zip(TRUST_BUDGETS, rhos) if rho < 0.5), None)
        chi_peak = max(chis)
        chi_tb = TRUST_BUDGETS[chis.index(chi_peak)]
        
        print(f"  pc={pc:.2f}: mid_tb={mid or '>0.30'}, χ_peak={chi_peak:.3f}@tb={chi_tb:.2f} "
              f"[{rhos[0]:.3f}→{rhos[-1]:.3f}]")
        
        tb_data[f"pc_{pc:.2f}"] = {"rho": rho_dict, "chi": chi_dict, "mid_tb": mid, "chi_peak_tb": chi_tb}
    all_results[N_val] = tb_data

# N_c analysis: find where mid_tb stabilizes
print(f"\n{'='*70}")
print("N_c drift analysis (pc=0.10):")
for N_val in N_VALUES:
    for key in [k for k in all_results[N_val] if '0.10' in k]:
        d = all_results[N_val][key]
        print(f"  N={N_val:3d}: mid_tb={d.get('mid_tb','>0.30')} χ_peak@tb={d.get('chi_peak_tb','?')}")

# Save
out = Path(__file__).parent.parent / "kb" / "L3_EMPIRICAL" / f"p2_v4_nc_drift_{int(time.time())%100000:05d}.json"
out.parent.mkdir(parents=True, exist_ok=True)
data = {
    "version": "v4",
    "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
    "parameters": {"noise": NOISE, "N": N_VALUES, "pc": P_CLOSE, "tb_range": "0.01-0.30", "seeds": N_SEEDS, "rounds": N_ROUNDS},
    "results": {str(N): v for N, v in all_results.items()}
}
with open(out, "w", encoding="utf-8") as f:
    json.dump(data, f, ensure_ascii=False, indent=2)
print(f"\nSaved: {out}")
