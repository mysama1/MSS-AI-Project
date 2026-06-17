"""
P1 v2: 渗流临界指数精确测定
修复: noise 0.10→0.03 | N 5→10 | p_step 0.02 | seeds×4 | rounds×5
"""
import math, random, time
from statistics import mean, stdev
from collections import defaultdict

NOISE = 0.03
N_VALUES = [12, 16, 20, 24, 28, 32, 36, 40, 48, 56]
P_VALUES = [round(0.10 + i*0.02, 2) for i in range(21)]  # 0.10-0.50
N_SEEDS = 200
N_ROUNDS = 500
TRUST_BUDGET = 0.5

def simulate(N, p_close):
    doors = [True] * N
    trust = [TRUST_BUDGET] * N
    for _ in range(N_ROUNDS):
        i, j = random.randint(0, N-1), random.randint(0, N-1)
        if i == j: continue
        
        if random.random() < NOISE:
            if doors[i] and doors[j]:
                doors[i] = False if random.random() < 0.5 else doors[i]
                doors[j] = False if random.random() < 0.5 else doors[j]
            continue
        
        if doors[i] and doors[j]:
            if random.random() < p_close:
                if random.random() < 0.5:
                    doors[i] = False; trust[j] = max(0, trust[j] - 0.1)
                else:
                    doors[j] = False; trust[i] = max(0, trust[i] - 0.1)
        elif doors[i] != doors[j]:
            closed, open_ = (i, j) if not doors[i] else (j, i)
            if trust[open_] < 0.3 and random.random() < 0.4:
                doors[open_] = False
        
        for k in range(N):
            if not doors[k] and trust[k] > 0.7 and random.random() < 0.05:
                doors[k] = True
    
    total = N * (N-1) // 2
    open_ = sum(1 for a in range(N) for b in range(a+1, N) if doors[a] and doors[b])
    return open_ / max(total, 1)

def largest_cluster_size(doors):
    """计算最大连通分量 (开放Agent的团)."""
    N = len(doors)
    open_nodes = [i for i in range(N) if doors[i]]
    if not open_nodes: return 0
    
    adj = {i: set() for i in open_nodes}
    for a in open_nodes:
        for b in open_nodes:
            if a < b:
                adj[a].add(b)
                adj[b].add(a)
    
    visited = set()
    max_size = 0
    for node in open_nodes:
        if node in visited: continue
        stack = [node]
        size = 0
        while stack:
            v = stack.pop()
            if v in visited: continue
            visited.add(v)
            size += 1
            for nb in adj.get(v, set()):
                if nb not in visited:
                    stack.append(nb)
        max_size = max(max_size, size)
    return max_size / N

print("P1 v2: 渗流临界指数精确测定")
print(f"noise={NOISE} | N={len(N_VALUES)}值({N_VALUES[0]}..{N_VALUES[-1]}) | p={len(P_VALUES)}档 | seeds={N_SEEDS} | rounds={N_ROUNDS}")
print(f"总模拟次数: {len(N_VALUES)}×{len(P_VALUES)}×{N_SEEDS} = {len(N_VALUES)*len(P_VALUES)*N_SEEDS}\n")

results = {}
t0 = time.time()
total = len(N_VALUES) * len(P_VALUES)
done = 0

for N in N_VALUES:
    for p in P_VALUES:
        etas, clusters = [], []
        for seed in range(N_SEEDS):
            random.seed(seed * 100000 + N * 1000 + int(p * 10000))
            doors = [True] * N
            trust = [TRUST_BUDGET] * N
            for _ in range(N_ROUNDS):
                i, j = random.randint(0, N-1), random.randint(0, N-1)
                if i == j: continue
                if random.random() < NOISE:
                    if doors[i] and doors[j]:
                        doors[i] = False if random.random() < 0.5 else doors[i]
                        doors[j] = False if random.random() < 0.5 else doors[j]
                    continue
                if doors[i] and doors[j]:
                    if random.random() < p:
                        if random.random() < 0.5:
                            doors[i] = False; trust[j] = max(0, trust[j]-0.1)
                        else:
                            doors[j] = False; trust[i] = max(0, trust[i]-0.1)
                elif doors[i] != doors[j]:
                    closed, op = (i, j) if not doors[i] else (j, i)
                    if trust[op] < 0.3 and random.random() < 0.4:
                        doors[op] = False
                for k in range(N):
                    if not doors[k] and trust[k] > 0.7 and random.random() < 0.05:
                        doors[k] = True
            
            tp = N*(N-1)//2
            op = sum(1 for a in range(N) for b in range(a+1,N) if doors[a] and doors[b])
            etas.append(op / max(tp, 1))
            
            # 最大团
            on = [i for i in range(N) if doors[i]]
            if on:
                adj_ = {i: set() for i in on}
                for a in on:
                    for b in on:
                        if a < b: adj_[a].add(b); adj_[b].add(a)
                vis = set()
                mc = 0
                for nd in on:
                    if nd in vis: continue
                    stk = [nd]; sz = 0
                    while stk:
                        v = stk.pop()
                        if v in vis: continue
                        vis.add(v); sz += 1
                        for nb in adj_.get(v, set()):
                            if nb not in vis: stk.append(nb)
                    mc = max(mc, sz)
                clusters.append(mc / N)
            else:
                clusters.append(0)
        
        results[(N, p)] = {
            'η': round(mean(etas), 4),
            'η_std': round(stdev(etas) if len(etas)>1 else 0, 4),
            'm': round(1-mean(etas), 4),
            'cluster': round(mean(clusters), 4),
            'cluster_std': round(stdev(clusters) if len(clusters)>1 else 0, 4),
        }
        done += 1
        if done % 20 == 0:
            print(f"  进度: {done}/{total} ({time.time()-t0:.0f}s)")

elapsed = time.time() - t0
print(f"\n完成: {elapsed:.1f}s\n")

# ── FSS 拟合 ──
by_N = defaultdict(list)
for (N, p), d in results.items():
    by_N[N].append((p, d['m'], d['η'], d['cluster']))

# 对每个N找effective p_c (最大变化率)
eff_pc = {}
for N in sorted(by_N):
    pts = sorted(by_N[N], key=lambda x: x[0])
    slopes = []
    for i in range(1, len(pts)):
        dp = pts[i][0] - pts[i-1][0]
        dm = pts[i][1] - pts[i-1][1]
        if dp > 0: slopes.append((pts[i][0], dm/dp))
    if slopes:
        best = max(slopes, key=lambda x: abs(x[1]))
        eff_pc[N] = {'p_c_eff': round(best[0], 4), 'max_slope': round(best[1], 4)}

print("── effective p_c(N) ──")
for N in sorted(eff_pc):
    print(f"  N={N:3d}: p_c_eff={eff_pc[N]['p_c_eff']:.4f}  slope={eff_pc[N]['max_slope']:.4f}")

# ν拟合: p_c(N) = p_c(∞) + a·N^(-1/ν)
Ns = sorted(eff_pc)
best_nu, best_r2, best_pc_inf = 0.5, 0, 0

for nu in [round(0.1 + i*0.02, 3) for i in range(100)]:
    xs = [N**(-1/nu) for N in Ns]
    ys = [eff_pc[N]['p_c_eff'] for N in Ns]
    mx, my = sum(xs)/len(xs), sum(ys)/len(ys)
    num = sum((xs[i]-mx)*(ys[i]-my) for i in range(len(xs)))
    den = sum((x-mx)**2 for x in xs)
    if den < 1e-10: continue
    slope = num/den
    intercept = my - slope*mx
    preds = [slope*x + intercept for x in xs]
    ss_res = sum((ys[i]-preds[i])**2 for i in range(len(ys)))
    ss_tot = sum((y-my)**2 for y in ys)
    r2 = 1 - ss_res/max(ss_tot, 1e-10)
    if r2 > best_r2:
        best_r2, best_nu, best_pc_inf = r2, nu, intercept

# β拟合: log(m(N)) = -(β/ν)·log(N) + const
logNs = [math.log(N) for N in Ns]
logMs = [math.log(max(results[(N, eff_pc[N]['p_c_eff'])]['m'], 1e-6)) for N in Ns]
mln, mlm = sum(logNs)/len(logNs), sum(logMs)/len(logMs)
num_b = sum((logNs[i]-mln)*(logMs[i]-mlm) for i in range(len(logNs)))
den_b = sum((ln-mln)**2 for ln in logNs)
beta_over_nu = -num_b / max(den_b, 1e-10)

print(f"\n── 拟合结果 ──")
print(f"  ν = {best_nu:.4f}  (R² = {best_r2:.4f})")
print(f"  β = {best_nu * beta_over_nu:.4f}")
print(f"  p_c(∞) = {best_pc_inf:.4f}")

# 普适类对比
refs = {
    '2D_percolation': (1.333, 0.139),
    '2D_Ising': (1.0, 0.125),
    'mean_field': (0.5, 0.5),
    'directed_percolation_1+1': (1.733, 0.276),
}
nu_fit, beta_fit = best_nu, best_nu * beta_over_nu

print(f"\n── 普适类距离 ──")
dists = []
for name, (nu_ref, beta_ref) in refs.items():
    d = math.sqrt(((nu_fit-nu_ref)/nu_ref)**2 + ((beta_fit-beta_ref)/beta_ref)**2)
    dists.append((name, d, nu_ref, beta_ref))
dists.sort(key=lambda x: x[1])

for name, d, nu_ref, beta_ref in dists:
    mark = '★' if dists.index((name,d,nu_ref,beta_ref)) == 0 else ' '
    print(f"  {mark} {name:>25s}: ν_ref={nu_ref:.3f} β_ref={beta_ref:.3f}  dist={d:.3f}")

# η曲线摘要
print(f"\n── η(p) 关键截面 (N=32) ──")
for p in [0.10, 0.15, 0.20, 0.25, 0.30, 0.35, 0.40]:
    if (32, p) in results:
        d = results[(32, p)]
        print(f"  p={p:.2f}: η={d['η']:.4f} m={d['m']:.4f} cluster={d['cluster']:.4f}")

# 判定
best_class = dists[0]
print(f"\n{'='*60}")
if best_class[1] < 0.15:
    print(f"  ✅ 收敛! 最近普适类: {best_class[0]} (距离={best_class[1]:.3f})")
    print(f"     系统性偏差 <15% → 可以合理判定H634-G属于{best_class[0]}普适类")
elif best_class[1] < 0.3:
    print(f"  ⚠️ 接近: {best_class[0]} (距离={best_class[1]:.3f})")
    print(f"     偏差15-30% → 倾向{best_class[0]}但需进一步确认")
else:
    print(f"  ❌ 不收敛: 最近{best_class[0]}但距离={best_class[1]:.3f}>0.3")
    print(f"     H634-G不属于任何已知标准普适类")
print(f"{'='*60}")
