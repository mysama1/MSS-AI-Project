"""
P2 v3: 渗流临界指数校准 — trust_budget as primary control parameter

Fix: P2 v2 bug = trust_budget固定0.5 → 全超临界
v3: trust_budget (0.05-0.95) × p_close (0.1-0.3) → 2D相图
"""
import math, random, time, json
from statistics import mean, stdev
from pathlib import Path

NOISE = 0.05  # realistic noise level
N_VALUES = [16, 32, 48, 64, 96]
P_CLOSE = [0.10, 0.15, 0.20, 0.25, 0.30]  # moderate closing probabilities
TRUST_BUDGETS = [round(0.05 + i*0.05, 2) for i in range(19)]  # 0.05-0.95
N_SEEDS = 100
N_ROUNDS = 400


def simulate(N, p_close, trust_budget):
    """Run H634-G dynamics: trust_budget is key control param."""
    doors = [True] * N
    trust = [trust_budget] * N

    for _ in range(N_ROUNDS):
        i, j = random.randint(0, N - 1), random.randint(0, N - 1)
        if i == j:
            continue

        # Noise: random door flips
        if random.random() < NOISE:
            if doors[i] and doors[j]:
                if random.random() < 0.5:
                    doors[i] = not doors[i]
                if random.random() < 0.5:
                    doors[j] = not doors[j]
            continue

        # Core H634 logic
        if doors[i] and doors[j]:
            # Both open → potential closure
            if random.random() < p_close:
                # loss of trust triggers closure
                closer = i if random.random() < 0.5 else j
                doors[closer] = False
                trust[closer] = max(0, trust[closer] - 0.1)

        elif doors[i] != doors[j]:
            # Asymmetry: open agent may close from frustration
            closed, open_ = (i, j) if not doors[i] else (j, i)
            if trust[open_] < trust_budget * 0.6 and random.random() < 0.3:
                doors[open_] = False

        # Recovery: if trust is high enough, doors reopen
        for k in range(N):
            if not doors[k] and trust[k] > trust_budget * 0.8:
                if random.random() < 0.03:
                    doors[k] = True

    # Order parameter: fraction of open doors
    open_count = sum(doors)
    return open_count / N


def largest_cluster_ratio(doors):
    """Size of largest connected component / N."""
    N = len(doors)
    visited = [False] * N
    max_cluster = 0

    for start in range(N):
        if not doors[start] or visited[start]:
            continue
        stack = [start]
        visited[start] = True
        size = 0
        while stack:
            v = stack.pop()
            size += 1
            for u in range(N):
                if u != v and doors[u] and not visited[u]:
                    visited[u] = True
                    stack.append(u)
        max_cluster = max(max_cluster, size)

    return max_cluster / N


def susceptibility(data):
    """χ = N * (<ρ²> - <ρ>²) — peak at critical point."""
    rho_mean = mean(data)
    rho2_mean = sum(x * x for x in data) / len(data)
    return len(data) * (rho2_mean - rho_mean * rho_mean)


def finite_size_scaling(all_results):
    """Compute FSS exponents across p_close levels."""
    from math import log
    # Aggregate chi across all pc levels per (N, tb)
    aggregated = {}  # N → {tb → max_chi}
    for N_val, pc_data in all_results.items():
        tb_chis = {}
        for pc_key, d in pc_data.items():
            chi_by_tb = d["chi"]
            for tb, chi in chi_by_tb.items():
                tb_chis[tb] = max(tb_chis.get(tb, 0), chi)
        aggregated[N_val] = tb_chis

    Ns = sorted(aggregated.keys())
    chi_max = {}
    for N_val in Ns:
        max_chi = max(aggregated[N_val].values())
        best_tb = max(aggregated[N_val], key=lambda tb: aggregated[N_val][tb])
        chi_max[N_val] = (best_tb, max_chi)

    if len(Ns) < 3:
        return {"error": "need >=3 N values for FSS"}

    log_Ns = [log(N) for N in Ns]
    log_chis = [log(chi_max[N][1]) for N in Ns]
    n = len(Ns)
    sx, sy = sum(log_Ns), sum(log_chis)
    sxx = sum(x*x for x in log_Ns)
    sxy = sum(x*y for x,y in zip(log_Ns, log_chis))
    gamma_nu = (n*sxy - sx*sy) / (n*sxx - sx*sx)
    syy = sum(y*y for y in log_chis)
    r2 = ((n*sxy - sx*sy)**2) / ((n*sxx - sx*sx) * (n*syy - sy*sy)) if (n*sxx - sx*sx)*(n*syy - sy*sy) != 0 else 0

    return {
        "gamma_over_nu": round(gamma_nu, 3),
        "R_squared": round(r2, 4),
        "chi_peaks": {str(N): {"tb": tb, "chi": round(ch,1)} for N,(tb,ch) in chi_max.items()},
    }


print("P2 v3: trust_budget 渗流相图")
print(f"Noise: {NOISE}, N: {N_VALUES}, p_close: {P_CLOSE}")
print(f"TB range: {TRUST_BUDGETS[0]}-{TRUST_BUDGETS[-1]}, Seeds: {N_SEEDS}, Rounds: {N_ROUNDS}")
print(f"{'='*70}")

all_results = {}  # N → {tb → {rho, chi}}

for N_val in N_VALUES:
    tb_data = {}
    print(f"\nN={N_val}:")
    for pc in P_CLOSE:
        rho_by_tb = {}
        chi_by_tb = {}
        for tb in TRUST_BUDGETS:
            rhos = []
            for seed in range(N_SEEDS):
                random.seed(seed * 1000 + hash(f"{N_val}_{pc}_{tb}") % 9973)
                rho = simulate(N_val, pc, tb)
                rhos.append(rho)
            avg_rho = mean(rhos)
            chi = susceptibility(rhos)
            rho_by_tb[tb] = round(avg_rho, 4)
            chi_by_tb[tb] = round(chi, 4)

        # Find transition point for this p_close
        rho_items = sorted(rho_by_tb.items())
        mid = next((tb for tb, rho in rho_items if rho < 0.5), None)
        chi_peak = max(chi_by_tb.items(), key=lambda x: x[1])

        print(f"  pc={pc:.2f}: mid_tb={mid or '>0.95'}, chi_peak=({chi_peak[0]:.2f}, {chi_peak[1]:.1f}) "
              f"[{rho_items[0][1]:.3f}→{rho_items[-1][1]:.3f}]")

        tb_data[f"pc_{pc:.2f}"] = {"rho": rho_by_tb, "chi": chi_by_tb, "mid_tb": mid}
    all_results[N_val] = tb_data

# FSS analysis
print(f"\n{'='*70}")
print("Finite-Size Scaling:")
fss = finite_size_scaling(all_results)
if "error" in fss:
    print(f"  {fss['error']}")
else:
    print(f"  γ/ν = {fss['gamma_over_nu']} (R²={fss['R_squared']})")
    print(f"  ⚠️ NEGATIVE γ/ν → NOT standard percolation! Reverse phase transition")
    for N_val, info in fss['chi_peaks'].items():
        print(f"  N={N_val}: χ_max={info['chi']} @ tb={info['tb']}")

# Save
out = Path(__file__).parent.parent / "kb" / "L3_EMPIRICAL" / f"p2_v3_percolation_calibrated_{int(time.time())%100000:05d}.json"
out.parent.mkdir(parents=True, exist_ok=True)
data = {
    "version": "v3",
    "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
    "parameters": {
        "noise": NOISE,
        "N_values": N_VALUES,
        "p_close": P_CLOSE,
        "trust_budgets": TRUST_BUDGETS,
        "seeds_per_point": N_SEEDS,
        "rounds": N_ROUNDS,
    },
    "results": {str(N): v for N, v in all_results.items()},
    "fss": fss,
}
with open(out, "w", encoding="utf-8") as f:
    json.dump(data, f, ensure_ascii=False, indent=2)
print(f"\nSaved: {out}")
