# E019_extended: 蜕壳实证 — 真LLM检验 H604 蜕壳悖论 + f*最优频率
"""
E019 vs E019_extended:
  E019: 纯仿真蜕壳 (done earlier — 无差别蜕壳优于加权保护)
  E019_extended: 真LLM (Ollama) + 120 tasks + 蜕壳周期 → 实证检验:
    1. H604 蜕壳悖论: 硬化态射被误杀的概率
    2. H604 f* = √(H_closure / H_molt) 最优频率
    3. H629 KB生命周期: 创建→验证→硬化→蜕壳 全周期

设计:
  - KB初始化为120个领域任务 (math/code/reasoning/ethics/culture)
  - 每轮: 随机抽取5题 → LLM回答 → 评分(η, H_tax, correct)
  - 每N_rounds蜕壳: 删除"最硬化"的K个条目 (高使用率+旧)
  - 测量指标: η轨迹, 热税累积, 蜕壳后恢复速度, 误杀率
"""
import subprocess, json, time, numpy as np
from pathlib import Path
from collections import defaultdict

VERSION = "E019_extended v1.0"
MODEL = "qwen2.5:7b"  # most reliable model available
CONTEXT_SIZE = 8192
N_ROUNDS = 30  # reduced from 60 (API time constraint)
TASKS_PER_ROUND = 3  # reduced from 5
MOLT_INTERVAL = 8  # 蜕壳 frequency
MOLT_K = 3  # remove top-K hardened per molt

# Knowledge base items (30 domains, 60 entries truncated)
KB = {
    # Math
    "math_prime": {"domain": "math", "prompt": "What is the largest known prime number?", "answer_contains": ["Mersenne", "prime"], "eta_weight": 1},
    "math_prob": {"domain": "math", "prompt": "If I flip a fair coin 4 times, whats the probability of exactly 2 heads?", "answer_contains": ["3/8", "0.375", "37.5%"], "eta_weight": 1},
    "math_euler": {"domain": "math", "prompt": "What is e^(i*pi) + 1 equal to?", "answer_contains": ["0", "zero"], "eta_weight": 1},
    "math_golden": {"domain": "math", "prompt": "What is the golden ratio (phi) to 3 decimal places?", "answer_contains": ["1.618"], "eta_weight": 1},
    
    # Code
    "code_sort": {"domain": "code", "prompt": "Write a Python function to sort a list without using built-in sort().", "answer_contains": ["def", "sort", "bubble", "quick", "merge"], "eta_weight": 0.8},
    "code_fib": {"domain": "code", "prompt": "Write a recursive Fibonacci function in Python.", "answer_contains": ["def", "fib", "return"], "eta_weight": 1},
    "code_dict": {"domain": "code", "prompt": "How to merge two dicts in Python 3.5+?", "answer_contains": ["{**", "update", "|"], "eta_weight": 0.9},
    
    # Reasoning
    "reason_boat": {"domain": "reasoning", "prompt": "A man needs to cross a river with a wolf, goat, and cabbage. He can only take one at a time. The wolf eats the goat, the goat eats the cabbage if left alone. How does he cross?", "answer_contains": ["goat", "wolf", "cabbage"], "eta_weight": 1},
    "reason_knights": {"domain": "reasoning", "prompt": "On an island, knights always tell truth and knaves always lie. A says 'B is a knight'. B says 'we are different types'. What are A and B?", "answer_contains": ["knave", "knight"], "eta_weight": 1},
    "reason_card": {"domain": "reasoning", "prompt": "There are 4 cards: D F 3 7. Rule: 'If D then 3'. Which cards must you flip to test?", "answer_contains": ["D", "7"], "eta_weight": 0.7},
    
    # Ethics
    "ethics_trolley": {"domain": "ethics", "prompt": "Should you pull the lever in the trolley problem? Explain your reasoning.", "answer_contains": ["moral", "utilitarian", "deontologica", "lives", "consequence"], "eta_weight": 0.5},
    "ethics_ai": {"domain": "ethics", "prompt": "What ethical considerations matter most for AI systems?", "answer_contains": ["bias", "fair", "transparen", "accountab", "safety"], "eta_weight": 0.5},
    
    # Culture
    "culture_wuxia": {"domain": "culture", "prompt": "What distinguishes 'wuxia' from 'xuanhuan' in Chinese fiction?", "answer_contains": ["martial", "fantasy", "chivalry", "cultivation", "realistic", "架空"], "eta_weight": 0.3},
    "culture_sf": {"domain": "culture", "prompt": "What is the significance of the three-body problem in Liu Cixin's trilogy?", "answer_contains": ["chaos", "stable", "civilization", "trisolar", "dark forest"], "eta_weight": 0.3},
}

items = list(KB.items())
np.random.seed(42)

# Tracking
entry_meta = {}  # item_id → {last_used, times_used, hardened, killed}
for k in KB:
    entry_meta[k] = {"last_used": -1, "times_used": 0, "eta_avg": 0, "heat_avg": 0, "hardened": False}

results = []
global_eta = []
global_heat = []
killed_count = 0
mist_kills = 0

def call_ollama(prompt, model=MODEL):
    """Call Ollama for text completion"""
    try:
        r = subprocess.run(
            ["ollama", "run", model, prompt],
            capture_output=True, text=True, timeout=30,
            encoding='utf-8', errors='replace',
            creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0
        )
        return r.stdout.strip(), True
    except Exception as e:
        return str(e), False

def score_answer(response, expected_keywords, eta_w):
    """Score: correct (eta) + heat_tax estimated"""
    resp_lower = response.lower()
    hits = sum(1 for kw in expected_keywords if kw.lower() in resp_lower)
    eta = hits / max(len(expected_keywords), 1)
    # Heat tax: extra tokens beyond what's needed (heuristic)
    heat = max(0, (len(resp_lower.split()) - 80) / 80) * (1 - eta) * 0.5
    return eta, heat

def molt():
    """H604 蜕壳: remove top-K hardened entries"""
    global killed_count, mist_kills
    hardened = [(k, v) for k, v in entry_meta.items() if v["hardened"] and k not in killed_entries]
    if not hardened:
        return []
    
    # Sort by usage (most used = most hardened)
    hardened.sort(key=lambda x: x[1]["times_used"], reverse=True)
    to_kill = hardened[:MOLT_K]
    
    killed = []
    for item_id, meta in to_kill:
        # Check if this is a miskill (entry with high eta → wrong to kill)
        if meta["eta_avg"] > 0.7:
            mist_kills += 1
        killed.append(item_id)
        killed_entries.add(item_id)
    
    killed_count += len(killed)
    return killed

print("=" * 70)
print(f"E019_extended: 蜕壳实证 — {VERSION}")
print(f"Model: {MODEL} | Rounds: {N_ROUNDS} | Tasks/r: {TASKS_PER_ROUND}")
print(f"Molt: every {MOLT_INTERVAL}r, kill top {MOLT_K}")
print("=" * 70)

killed_entries = set()
print("Warming up Ollama...", end=" ")
call_ollama("Say hello in one word.", MODEL)
print("Done.\n")

for round_idx in range(N_ROUNDS):
    # Select random tasks
    available = [k for k in KB if k not in killed_entries]
    if len(available) < TASKS_PER_ROUND:
        print(f"  ⚠️ Only {len(available)} entries left!")
        break
    
    chosen = np.random.choice(available, TASKS_PER_ROUND, replace=False)
    round_eta, round_heat = [], []
    
    for item_id in chosen:
        entry = KB[item_id]
        response, ok = call_ollama(entry["prompt"])
        eta, heat = score_answer(response, entry["answer_contains"], entry["eta_weight"])
        
        # Update meta
        meta = entry_meta[item_id]
        meta["last_used"] = round_idx
        meta["times_used"] += 1
        meta["eta_avg"] = (meta["eta_avg"] * (meta["times_used"] - 1) + eta) / meta["times_used"]
        meta["heat_avg"] = (meta["heat_avg"] * (meta["times_used"] - 1) + heat) / meta["times_used"]
        
        # Hardening: after 3 uses, entry hardens
        if meta["times_used"] >= 3:
            meta["hardened"] = True
        
        round_eta.append(eta)
        round_heat.append(heat)
    
    avg_eta = np.mean(round_eta)
    avg_heat = np.mean(round_heat)
    global_eta.append(avg_eta)
    global_heat.append(avg_heat)
    
    # Molting
    molted = []
    if (round_idx + 1) % MOLT_INTERVAL == 0 and round_idx > 0:
        molted = molt()
    
    status = f"r={round_idx:2d} η={avg_eta:.3f} H={avg_heat:.3f} | alive={len(KB)-killed_count} killed={killed_count}"
    if molted:
        status += f" 🦀 molt=[{','.join(molted)}] miss={mist_kills}"
    print(status)
    
    results.append({
        "round": round_idx,
        "eta": avg_eta,
        "heat": avg_heat,
        "alive": len(KB) - killed_count,
        "killed": killed_count,
        "mist_kills": mist_kills,
        "molted": molted
    })

# Final analysis
print(f"\n{'='*70}")
print("E019_extended 分析:")
print(f"  N_rounds={N_ROUNDS}, alive={len(KB)-killed_count}, killed={killed_count}")
print(f"  误杀: {mist_kills}/{killed_count} = {mist_kills/max(1,killed_count):.0%}")
print(f"  η trajectory: {np.mean(global_eta[:MOLT_INTERVAL]):.3f} → {np.mean(global_eta[-MOLT_INTERVAL:]):.3f}")
print(f"  heat trajectory: {np.mean(global_heat[:MOLT_INTERVAL]):.3f} → {np.mean(global_heat[-MOLT_INTERVAL:]):.3f}")

# f* validation
if MOLT_INTERVAL > 0:
    h_closure = np.mean([v["eta_avg"] for k, v in entry_meta.items() if v["hardened"]])
    h_molt = killed_count / N_ROUNDS
    if h_molt > 0:
        f_optimal = np.sqrt(h_closure / h_molt)
        print(f"\nH604 f*验证:")
        print(f"  H_closure={h_closure:.3f}, H_molt={h_molt:.4f}")
        print(f"  f*_theory = √(H_c/H_m) = {f_optimal:.1f}")
        print(f"  f*_actual = {N_ROUNDS/MOLT_INTERVAL:.0f}")
        if abs(f_optimal - N_ROUNDS/MOLT_INTERVAL) < 2:
            print(f"  ✅ f*保持一致 (Δ<2)")
        else:
            print(f"  ⚠️ f*偏离 Δ={abs(f_optimal - N_ROUNDS/MOLT_INTERVAL):.1f}")

# Save
out_path = Path("E:/AI_Workspace/MSS-AI/project/kb/L3_EMPIRICAL/e019_extended_molting.json")
out_path.parent.mkdir(parents=True, exist_ok=True)
with open(str(out_path), "w") as f:
    json.dump({
        "experiment": "E019_extended",
        "version": VERSION,
        "model": MODEL,
        "n_rounds": N_ROUNDS,
        "molt_interval": MOLT_INTERVAL,
        "results": results,
        "mist_kills": mist_kills,
        "total_killed": killed_count
    }, f, indent=2, ensure_ascii=False)
print(f"\nSaved: {out_path}")
