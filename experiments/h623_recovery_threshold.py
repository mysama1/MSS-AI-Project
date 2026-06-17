"""
H623因果验证: 恢复阈值敏感度实验
假设: 降低恢复阈值→恢复变强→p_c_eff开始随N漂移→趋近标准渗流
"""
import random, time, math
from statistics import mean

NOISE = 0.03
N_VALUES = [12, 20, 32, 48]
P_VALUES = [round(0.08 + i*0.02, 2) for i in range(16)]  # 0.08-0.38
N_SEEDS = 100
N_ROUNDS = 500
TRUST_BUDGET = 0.5
RECOVERY_THRESHOLDS = [0.3, 0.4, 0.5, 0.6, 0.7]

def simulate(N, p_close, rec_thresh):
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
            closed, op = (i, j) if not doors[i] else (j, i)
            if trust[op] < 0.3 and random.random() < 0.4:
                doors[op] = False
        for k in range(N):
            if not doors[k] and trust[k] > rec_thresh and random.random() < 0.05:
                doors[k] = True
    tp = N*(N-1)//2
    op = sum(1 for a in range(N) for b in range(a+1,N) if doors[a] and doors[b])
    return op / max(tp, 1)

print("H623 恢复阈值敏感度实验")
print(f"阈值: {RECOVERY_THRESHOLDS} | N: {N_VALUES} | p: {len(P_VALUES)}档 | {N_SEEDS}seeds×{N_ROUNDS}rds")
t0 = time.time()

results = {}
total = len(RECOVERY_THRESHOLDS) * sum(1 for N in N_VALUES for p in P_VALUES)
done = 0

for rt in RECOVERY_THRESHOLDS:
    for N in N_VALUES:
        for p in P_VALUES:
            etas = []
            for seed in range(N_SEEDS):
                random.seed(seed*100000 + N*1000 + int(p*10000) + int(rt*1000000))
                etas.append(simulate(N, p, rt))
            results[(rt, N, p)] = round(mean(etas), 4)
            done += 1

print(f"完成: {time.time()-t0:.1f}s\n")

# 对每个恢复阈值找 p_c_eff 漂移
print("── p_c_eff(N) 按恢复阈值分组 ──")
print(f"{'阈值':>6s} {'N=12':>8s} {'N=20':>8s} {'N=32':>8s} {'N=48':>8s} {'漂移':>8s} {'判定':>12s}")
for rt in RECOVERY_THRESHOLDS:
    pcs = []
    for N in N_VALUES:
        pts = sorted([(p, results[(rt,N,p)]) for p in P_VALUES], key=lambda x: x[0])
        slopes = []
        for i in range(1, len(pts)):
            dp = pts[i][0] - pts[i-1][0]
            dm = (1-pts[i][1]) - (1-pts[i-1][1])
            if dp > 0: slopes.append((pts[i][0], abs(dm)/dp))
        if slopes:
            best = max(slopes, key=lambda x: x[1])
            pcs.append(best[0])
    
    if len(pcs) >= 2:
        drift = max(pcs) - min(pcs)
        stable = "✅ 固定" if drift < 0.02 else ("⚠️ 微漂" if drift < 0.06 else "❌ 显著漂移")
        print(f"  {rt:.1f}   {pcs[0]:8.4f} {pcs[1]:8.4f} {pcs[2]:8.4f} {pcs[3]:8.4f} {drift:8.3f} {stable}")

# 关键比较
print(f"\n── 关键结论 ──")
print(f"v1 (noise=0.10, rt=0.7): p_c fixed at 0.12 — 信任介导坍缩 (新动力学)")
print(f"v2 (noise=0.03, rt=0.7): p_c fixed at 0.12 — 确认, 非噪声假象")
print(f"v3 敏感度: 降低恢复阈值看p_c是否恢复标准FSS漂移")

best = min(RECOVERY_THRESHOLDS, key=lambda rt: max(
    results.get((rt, N, p), 1) for N in N_VALUES for p in P_VALUES if abs(p-0.12)<0.03
))
print(f"\n建议下一步: 恢复阈值{best}时η值最高, 进一步细化p_c附近采样")
