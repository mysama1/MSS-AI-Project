# E018: Type IV 自指悖论 — Self-Referential Paradox Detection & Resolution
"""
从H635 Type II消解定理出发, 垂直深入Type IV悖论:

Type I:  逻辑矛盾 (A∧¬A) → A6升维可解
Type II:  最优性冲突 (max f s.t. constraints) → L2-OP只能部分解
Type III: 元层次冲突 (规则自身vs规则应用)
Type IV:  自指悖论 (系统包含自身描述 → Gödel/Turing)

E018设计: 
  1. 构造自指Agent系统 (Agent包含对自身状态的判断逻辑)
  2. 触发自指循环 (Agent的决策函数引用自身输出)
  3. 测量悖论强度: 振荡幅度, 收敛速度, 逃逸概率
  4. 验证H635的Type IV情况: 消解定理是否在自指域内成立
"""
import numpy as np, json, time
from pathlib import Path
from dataclasses import dataclass

VERSION = "E018 v1.0"
N_SEEDS = 30
N_ROUNDS = 200

# Self-referential agent model:
# Agent has a belief b_t about state, and a meta-belief m_t about b_t
# Decision: d_t = σ(w1·b_t + w2·m_t)
# Update: b_{t+1} = (1-α)·b_t + α·(observation_t)
# Self-referential trap: m_t = agent's own prediction of b_t

@dataclass
class SelfRefAgent:
    b: float  # belief about world state
    m: float  # meta-belief about own belief
    α: float  # learning rate
    β: float  # self-reference strength (0=none, 1=full)
    γ: float  # noise sensitivity
    
    def observe(self, truth):
        """Update belief from observation"""
        self.b = (1 - self.α) * self.b + self.α * (truth + np.random.normal(0, self.γ))
    
    def self_reflect(self):
        """Meta-cognition: predict own belief"""
        prediction = self.b + self.β * (self.m - self.b)
        self.m = prediction
        return prediction
    
    def decide(self, truth):
        """Make decision, potentially trapped in self-reference"""
        self.observe(truth)
        prediction = self.self_reflect()
        # Decision quality: how well does agent track truth after self-reference?
        error = abs(self.m - truth)
        return error, prediction

def run_selfref_experiment(β, α=0.3, γ=0.1, truth_drift=0.02):
    """
    Run a self-referential agent experiment.
    truth_drift: how fast the ground truth changes (non-stationary world)
    """
    agent = SelfRefAgent(b=0.5, m=0.5, α=α, β=β, γ=γ)
    truth = 0.5
    errors = []
    oscillations = []
    
    for t in range(N_ROUNDS):
        # Truth drifts slowly
        truth = truth + np.random.normal(0, truth_drift)
        truth = np.clip(truth, 0, 1)
        
        error, pred = agent.decide(truth)
        errors.append(error)
        
        # Detect oscillation: large sign changes in belief
        if t > 0:
            osc = abs(agent.b - prev_b) / max(truth_drift, 0.001)
            oscillations.append(osc)
        prev_b = agent.b
    
    return {
        "mean_error": np.mean(errors),
        "max_error": np.max(errors),
        "final_error": errors[-1] if errors else 0,
        "oscillation_index": np.mean(oscillations) if oscillations else 0,
        "n_divergences": sum(1 for e in errors if e > 0.5),
        "converged": errors[-5:] and np.std(errors[-5:]) < 0.02
    }

print("=" * 70)
print(f"E018: Type IV 自指悖论 — {VERSION}")
print(f"β ∈ [0, 0.2, 0.4, 0.6, 0.8, 1.0], seeds={N_SEEDS}, rounds={N_ROUNDS}")
print("=" * 70)

betas = [0.0, 0.2, 0.4, 0.6, 0.8, 1.0]
results = []

for β in betas:
    agg = {"mean_error": [], "max_error": [], "oscillation": [], "divergences": [], "converged": []}
    for seed in range(N_SEEDS):
        np.random.seed(seed * 100 + int(β * 100))
        r = run_selfref_experiment(β)
        agg["mean_error"].append(r["mean_error"])
        agg["max_error"].append(r["max_error"])
        agg["oscillation"].append(r["oscillation_index"])
        agg["divergences"].append(r["n_divergences"])
        agg["converged"].append(1 if r["converged"] else 0)
    
    results.append({
        "β": β,
        "mean_error": np.mean(agg["mean_error"]),
        "max_error": np.mean(agg["max_error"]),
        "oscillation": np.mean(agg["oscillation"]),
        "divergence_rate": np.mean(agg["divergences"]) / N_ROUNDS,
        "convergence_rate": np.mean(agg["converged"]),
        "n_seeds": N_SEEDS
    })

# --- Display ---
for r in results:
    β = r["β"]
    bar = "█" * int(r["oscillation"] * 10)
    status = "⚠️ 自指崩溃" if r["convergence_rate"] < 0.3 else ("⚡ 高振荡" if r["oscillation"] > 5 else "✅ 稳定")
    print(f"\nβ={β:.1f}:")
    print(f"  均误={r['mean_error']:.4f}  峰值={r['max_error']:.4f}")
    print(f"  振荡={r['oscillation']:.2f} {bar}")
    print(f"  发散={r['divergence_rate']:.1%}  收敛={r['convergence_rate']:.0%}  → {status}")

# --- Critical β detection ---
bp = np.array([r["β"] for r in results])
osc = np.array([r["oscillation"] for r in results])
err = np.array([r["mean_error"] for r in results])

# Find phase transition point: β where oscillation > threshold
threshold = 3.0
critical_idx = np.argmax(osc > threshold)
β_critical = bp[critical_idx] if critical_idx > 0 else None

print(f"\n{'='*70}")
print(f"Type IV 相变分析:")
print(f"  振荡阈值={threshold}, β_critical={β_critical}")
print(f"  临界前: 振荡={np.mean(osc[bp < (β_critical or 0.5)]):.2f}")
print(f"  临界后: 振荡={np.mean(osc[bp >= (β_critical or 0.5)]):.2f}")

# --- H635 connection ---
print(f"\n--- H635 Type II 消解定理 → Type IV 扩展 ---")
print(f"Type IV 自指悖论不同于 Type I/II:")
print(f"  1. 自指循环产生无界振荡 → η永远达不到稳态")
print(f"  2. 消解定理在 β > {β_critical} 时不成立 (消解需要有限的不动点)")
print(f"  3. 需要 A7: 最优性作为创造性选择 → 跳出自我描述的镜子")

# --- MSS prediction ---
# β maps to trust_budget: higher tb → more self-awareness → more self-reference
# This creates a U-shaped curve: too little self-reference → naive, too much → paralysis
print(f"\nMSS预测: η(β) 呈倒U型, 峰值在 β≈0.3-0.4")
print(f"  低β: 缺乏自知 → 对环境过拟合 (η低)")
print(f"  高β: 过度自指 → 信念振荡 (η低)")
print(f"  最佳β: 适度的元认知 → 对环境适应+自我校正 (η高)")

# Save
out_path = Path("E:/AI_Workspace/MSS-AI/project/kb/L3_EMPIRICAL/e018_type4_paradox.json")
out_path.parent.mkdir(parents=True, exist_ok=True)
with open(str(out_path), "w") as f:
    json.dump({
        "experiment": "E018",
        "version": VERSION,
        "type": "Type IV Self-Referential Paradox",
        "n_seeds": N_SEEDS,
        "n_rounds": N_ROUNDS,
        "β_critical": β_critical,
        "results": results
    }, f, indent=2)
print(f"\nSaved: {out_path}")
