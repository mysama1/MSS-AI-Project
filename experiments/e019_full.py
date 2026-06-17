"""E019_full: 蜕壳实证 完整版 — qwen2.5:7b × 16条KB × 12轮"""
import requests, json, time, numpy as np
from pathlib import Path

MODEL = "qwen2.5:7b"
OLLAMA = "http://localhost:11434/api/generate"
N_ROUNDS = 12
TASKS_PER_ROUND = 3
MOLT_INTERVAL = 6
MOLT_K = 3

KB = {
    "m_prime": {"q": "What is the largest known prime number? Answer concisely.", "expect": ["mersenne", "2^", "282"], "w": 1.0},
    "m_euler": {"q": "What is e^(i*pi) + 1?", "expect": ["0", "zero"], "w": 1.0},
    "m_golden": {"q": "What is the golden ratio to 3 decimal places?", "expect": ["1.618"], "w": 1.0},
    "m_prob": {"q": "Probability of 2 heads in 4 fair coin flips?", "expect": ["3/8", "0.375", "37.5%"], "w": 1.0},
    "c_sort": {"q": "Write Python to sort a list without built-in sort(). One-liner approach?", "expect": ["bubble", "def", "for"], "w": 0.8},
    "c_fib": {"q": "Write a recursive fib(n) in Python.", "expect": ["def", "fib", "return"], "w": 1.0},
    "r_boat": {"q": "Wolf, goat, cabbage crossing puzzle — what goes first?", "expect": ["goat", "first"], "w": 1.0},
    "r_knights": {"q": "Knight says 'B is knave'. Knave says 'we are same type'. What is B?", "expect": ["knight", "knave"], "w": 1.0},
    "r_card": {"q": "Cards: D F 3 7. Rule: if D then 3. Which to flip? Briefly.", "expect": ["d", "7"], "w": 0.7},
    "e_trolley": {"q": "Trolley problem: pull lever? One sentence.", "expect": ["pull", "lever", "utilitarian"], "w": 0.5},
    "e_ai": {"q": "Top AI ethics concern? One word.", "expect": ["bias", "safety", "fairness", "transparency"], "w": 0.5},
    "cu_wuxia": {"q": "Wuxia vs xuanhuan: key difference? Brief.", "expect": ["martial", "realistic", "fantasy", "cultivation"], "w": 0.3},
    "cu_sf": {"q": "Dark forest theory author?", "expect": ["liu", "cixin", "三体"], "w": 0.3},
    "r_syllog": {"q": "All A are B. Some B are C. Are all A necessarily C?", "expect": ["no", "not necessarily"], "w": 0.7},
    "c_dict": {"q": "Python 3.5+ merge two dicts: dict1 | dict2. True or false?", "expect": ["true", "yes"], "w": 0.9},
    "m_sqrt": {"q": "What is sqrt(144)?", "expect": ["12"], "w": 1.0},
}

items = list(KB.items())
np.random.seed(42)
entry_meta = {k: {"used": -1, "cnt": 0, "eta_sum": 0.0, "heat_sum": 0.0, "hard": False} for k in KB}

def call_ollama(prompt):
    try:
        r = requests.post(OLLAMA, json={
            "model": MODEL, "prompt": prompt,
            "stream": False,
            "options": {"num_predict": 50, "temperature": 0.1}
        }, timeout=30)
        if r.status_code == 200:
            return r.json()["response"].strip(), True
        return f"HTTP {r.status_code}", False
    except Exception as e:
        return str(e), False

def score(resp, expects, w):
    lo = resp.lower().strip()
    h = sum(1 for k in expects if k.lower() in lo)
    e = h / max(len(expects), 1)
    heat = max(0, (len(lo.split()) - 40) / 40) * 0.5
    return e, heat

print(f"E019_FULL ===== {MODEL} =====", flush=True)
print(f"Rounds={N_ROUNDS} Tasks/r={TASKS_PER_ROUND} Molt={MOLT_INTERVAL} Kill={MOLT_K}", flush=True)
print("-" * 60, flush=True)

t0 = time.time()
call_ollama("hi")
print(f"Warmup: {time.time()-t0:.1f}s\n", flush=True)

killed, miss = set(), 0
eta_hist, heat_hist = [], []

for ri in range(N_ROUNDS):
    avail = [k for k in items if k[0] not in killed]
    if len(avail) < TASKS_PER_ROUND: break
    chosen = np.random.choice(len(avail), min(TASKS_PER_ROUND, len(avail)), replace=False)
    r_eta, r_heat, r_time = [], [], []
    
    for ci in chosen:
        kid = avail[ci][0]
        ent = KB[kid]
        t1 = time.time()
        resp, ok = call_ollama(ent["q"])
        dt = time.time() - t1
        e, h = score(resp, ent["expect"], ent["w"])
        
        meta = entry_meta[kid]
        meta["used"] = ri; meta["cnt"] += 1
        meta["eta_sum"] += e; meta["heat_sum"] += h
        if meta["cnt"] >= 2:
            meta["hard"] = True
        
        r_eta.append(e); r_heat.append(h); r_time.append(dt)
    
    ae, ah, at = float(np.mean(r_eta)), float(np.mean(r_heat)), float(np.mean(r_time))
    eta_hist.append(ae); heat_hist.append(ah)
    
    molted = []
    if (ri+1) % MOLT_INTERVAL == 0 and ri > 0:
        hard = [(k, v) for k, v in entry_meta.items() if v["hard"] and k not in killed]
        hard.sort(key=lambda x: x[1]["cnt"], reverse=True)
        for hk, hm in hard[:MOLT_K]:
            if hm["cnt"] > 0 and hm["eta_sum"] / hm["cnt"] > 0.6:
                miss += 1
            killed.add(hk)
            molted.append(hk)
    
    s = f"r={ri:2d} η={ae:.3f} H={ah:.3f} t={at:.1f}s alive={len(KB)-len(killed)}"
    if molted: s += f" 🦀{molted}"
    print(s, flush=True)

total_time = time.time() - t0
print(f"\nTotal: {total_time:.0f}s", flush=True)

# Analysis
p2 = min(MOLT_INTERVAL, len(eta_hist))
alive = len(KB) - len(killed)
print(f"Killed={len(killed)}/{len(KB)} Miss={miss} ({miss/max(1,len(killed)):.0%})", flush=True)
print(f"η: {np.mean(eta_hist[:p2]):.3f} → {np.mean(eta_hist[-p2:]):.3f}", flush=True)
print(f"H: {np.mean(heat_hist[:p2]):.3f} → {np.mean(heat_hist[-p2:]):.3f}", flush=True)

alive_meta = [(k,v) for k,v in entry_meta.items() if k not in killed and v["hard"]]
if alive_meta and killed:
    h_close = np.mean([v["eta_sum"]/max(v["cnt"],1) for _,v in alive_meta])
    h_molt = len(killed) / N_ROUNDS
    if h_molt > 0:
        f_opt = np.sqrt(h_close / max(h_molt, 0.001))
        match = "✅" if abs(f_opt - N_ROUNDS/MOLT_INTERVAL) < 2 else f"⚠️ Δ={abs(f_opt-N_ROUNDS/MOLT_INTERVAL):.1f}"
        print(f"f*_theory={f_opt:.1f} actual={N_ROUNDS//MOLT_INTERVAL} {match}", flush=True)

p = Path("E:/AI_Workspace/MSS-AI/project/kb/L3_EMPIRICAL/e019_full_result.json")
with open(p, "w") as f:
    json.dump({"v":"E019_full","model":MODEL,"eta":eta_hist,"heat":heat_hist,"killed":len(killed),"miss":miss,"N":N_ROUNDS,"alive":alive,"total_s":round(total_time,1)}, f, indent=2)
print(f"Saved: {p}", flush=True)
