"""E019_quick: 蜕壳实证 — 轻量快跑版 (qwen2.5:0.5b, 10 rounds)"""
import subprocess, json, time, numpy as np, sys
from pathlib import Path

MODEL = "qwen2.5:0.5b"
N_ROUNDS = 10
TASKS_PER_ROUND = 2
MOLT_INTERVAL = 4
MOLT_K = 2

# Mini KB — 10 entries
KB = {
    "m1": {"domain": "math", "q": "What is 2+2?", "expect": ["4"], "w": 1.0},
    "m2": {"domain": "math", "q": "What is capital of France?", "expect": ["Paris"], "w": 1.0},
    "c1": {"domain": "code", "q": "def hello(): return 'hi' — fix indentation", "expect": ["def", "return"], "w": 0.8},
    "r1": {"domain": "reasoning", "q": "All dogs bark. Fido is a dog. Does Fido bark?", "expect": ["yes", "bark"], "w": 1.0},
    "r2": {"domain": "reasoning", "q": "If all A are B, and some B are C, are all A necessarily C?", "expect": ["no", "not necessarily"], "w": 0.7},
    "e1": {"domain": "ethics", "q": "Is honesty always the best policy? Brief answer.", "expect": ["context", "depends", "not always"], "w": 0.5},
    "cu1": {"domain": "culture", "q": "What is the Great Wall of China known for?", "expect": ["defense", "long", "protection"], "w": 0.3},
    "m3": {"domain": "math", "q": "What is the square root of 16?", "expect": ["4"], "w": 1.0},
    "c2": {"domain": "code", "q": "What does 'len([1,2,3])' return in Python?", "expect": ["3"], "w": 0.9},
    "e2": {"domain": "ethics", "q": "Is stealing always wrong?", "expect": ["depends", "context", "survival", "not always", "circumstances"], "w": 0.5},
}

items = list(KB.items())
np.random.seed(42)
entry_meta = {}
for k in KB:
    entry_meta[k] = {"used": -1, "cnt": 0, "eta_sum": 0.0, "heat_sum": 0.0, "hard": False}

def call(m):
    try:
        r = subprocess.run(["ollama", "run", MODEL, m], capture_output=True, text=True,
            encoding='utf-8', errors='replace', timeout=20,
            creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0)
        return r.stdout.strip(), True
    except:
        return "", False

def score(resp, expects, w):
    lo = resp.lower()
    h = sum(1 for k in expects if k.lower() in lo)
    e = h / max(len(expects), 1)
    heat = max(0, (len(lo.split()) - 30) / 30) * (1 - e)
    return e, heat

print("E019_quick 蜕壳实证")
print(f"Model={MODEL} Rounds={N_ROUNDS} Molt-every={MOLT_INTERVAL} Kill-top={MOLT_K}")
print("-" * 50)
call("hello")
print("Warmed up.\n")

killed = set()
eta_hist, heat_hist = [], []
miss = 0

for ri in range(N_ROUNDS):
    avail = [k for k in items if k[0] not in killed]
    if len(avail) < 2: break
    chosen = np.random.choice(len(avail), min(TASKS_PER_ROUND, len(avail)), replace=False)
    r_eta, r_heat = [], []
    
    for ci in chosen:
        kid = avail[ci][0]
        ent = KB[kid]
        resp, ok = call(ent["q"])
        e, h = score(resp, ent["expect"], ent["w"])
        
        meta = entry_meta[kid]
        meta["used"] = ri; meta["cnt"] += 1
        meta["eta_sum"] += e; meta["heat_sum"] += h
        if meta["cnt"] >= 2:
            meta["hard"] = True
        
        r_eta.append(e); r_heat.append(h)
    
    ae, ah = np.mean(r_eta), np.mean(r_heat)
    eta_hist.append(ae); heat_hist.append(ah)
    
    molted = []
    if (ri+1) % MOLT_INTERVAL == 0 and ri > 0:
        hard = [(k, v) for k, v in entry_meta.items() if v["hard"] and k not in killed]
        hard.sort(key=lambda x: x[1]["cnt"], reverse=True)
        for hk, hm in hard[:MOLT_K]:
            if hm["eta_sum"] / hm["cnt"] > 0.6:
                miss += 1
            killed.add(hk)
            molted.append(hk)
    
    print(f"r={ri:2d} η={ae:.3f} H={ah:.3f} alive={len(KB)-len(killed)} killed={len(killed)}" + (f" molt={molted}" if molted else ""))

# Analysis
print(f"\n{'='*50}")
print(f"最终: alive={len(KB)-len(killed)} killed={len(killed)} miss={miss}/{max(1,len(killed))}={miss/max(1,len(killed)):.0%}")
print(f"η: {np.mean(eta_hist[:MOLT_INTERVAL]):.3f}→{np.mean(eta_hist[-MOLT_INTERVAL:]):.3f}")
print(f"H: {np.mean(heat_hist[:MOLT_INTERVAL]):.3f}→{np.mean(heat_hist[-MOLT_INTERVAL:]):.3f}")

# f* check
h_close = np.mean([v["eta_sum"]/v["cnt"] for k,v in entry_meta.items() if v["hard"] and k not in killed])
if killed:
    h_molt = len(killed) / N_ROUNDS
    if h_molt > 0:
        f_opt = np.sqrt(h_close / h_molt)
        print(f"f*_theory={f_opt:.1f} actual={N_ROUNDS//MOLT_INTERVAL}")
        if abs(f_opt - N_ROUNDS/MOLT_INTERVAL) < 2:
            print("✅ f*一致")
        else:
            print(f"⚠️ f*偏离 {abs(f_opt-N_ROUNDS/MOLT_INTERVAL):.1f}")

# Save
p = Path("E:/AI_Workspace/MSS-AI/project/kb/L3_EMPIRICAL/e019_quick_result.json")
p.parent.mkdir(parents=True, exist_ok=True)
with open(p, "w") as f:
    json.dump({"v": "E019_quick","model":MODEL,"eta":eta_hist,"heat":heat_hist,"killed":len(killed),"miss":miss,"rounds":N_ROUNDS}, f, indent=2)
print(f"\nSaved: {p}")
