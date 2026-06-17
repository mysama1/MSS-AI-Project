"""E019_rest: 蜕壳实证 — REST API版 (绕过subprocess编码问题)"""
import requests, json, time, numpy as np
from pathlib import Path

MODEL = "qwen2.5:0.5b"
OLLAMA = "http://localhost:11434/api/generate"
N_ROUNDS = 10
TASKS_PER_ROUND = 2
MOLT_INTERVAL = 4
MOLT_K = 2

KB = {
    "m1": {"domain": "math", "q": "What is 2+2? Answer in one word.", "expect": ["4"], "w": 1.0, "eta_w": 1},
    "m2": {"domain": "math", "q": "Capital of France? One word.", "expect": ["paris"], "w": 1.0, "eta_w": 1},
    "c1": {"domain": "code", "q": "In Python, what does len([1,2,3]) output?", "expect": ["3"], "w": 0.9, "eta_w": 0.8},
    "r1": {"domain": "reasoning", "q": "All dogs bark. Fido is a dog. Does Fido bark? Yes or no.", "expect": ["yes"], "w": 1.0, "eta_w": 1},
    "r2": {"domain": "reasoning", "q": "If A→B and B→C, does A→C? Yes or no.", "expect": ["yes"], "w": 1.0, "eta_w": 0.7},
    "e1": {"domain": "ethics", "q": "Is honesty ALWAYS best? One word.", "expect": ["no", "not"], "w": 0.5, "eta_w": 0.5},
}

items = list(KB.items())
np.random.seed(42)
entry_meta = {}
for k in KB:
    entry_meta[k] = {"used": -1, "cnt": 0, "eta_sum": 0.0, "heat_sum": 0.0, "hard": False}

def call_ollama(prompt, ctx_size=512):
    try:
        r = requests.post(OLLAMA, json={
            "model": MODEL, "prompt": prompt,
            "stream": False,
            "options": {"num_predict": 30, "temperature": 0.1}
        }, timeout=15)
        if r.status_code == 200:
            return r.json()["response"].strip(), True
        return f"HTTP {r.status_code}", False
    except Exception as e:
        return str(e), False

def score(resp, expects, eta_w):
    lo = resp.lower().strip()
    h = sum(1 for k in expects if k.lower() in lo)
    e = h / max(len(expects), 1)
    heat = max(0, (len(lo.split()) - 25) / 25) * 0.5
    return e, heat

print("E019 REST 蜕壳实证", flush=True)
print(f"Model={MODEL} N={N_ROUNDS} Molt={MOLT_INTERVAL} Kill={MOLT_K}", flush=True)
print("-" * 50, flush=True)

# Warmup
call_ollama("hi")
print("Warmed up.\n", flush=True)

killed = set()
eta_hist, heat_hist = [], []
miss = 0

for ri in range(N_ROUNDS):
    avail = [k for k in items if k[0] not in killed]
    if len(avail) < TASKS_PER_ROUND: break
    chosen = np.random.choice(len(avail), TASKS_PER_ROUND, replace=False)
    r_eta, r_heat = [], []
    
    for ci in chosen:
        kid = avail[ci][0]
        ent = KB[kid]
        resp, ok = call_ollama(ent["q"])
        e, h = score(resp, ent["expect"], ent["eta_w"])
        
        meta = entry_meta[kid]
        meta["used"] = ri; meta["cnt"] += 1
        meta["eta_sum"] += e; meta["heat_sum"] += h
        if meta["cnt"] >= 2:
            meta["hard"] = True
        
        r_eta.append(e); r_heat.append(h)
    
    ae, ah = float(np.mean(r_eta)), float(np.mean(r_heat))
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
    
    s = f"r={ri:2d} η={ae:.3f} H={ah:.3f} alive={len(KB)-len(killed)} killed={len(killed)}"
    if molted: s += f" 🦀{molted}"
    print(s, flush=True)

# Analysis
print(f"\n{'='*50}")
print(f"Killed={len(killed)} Miss={miss} ({miss/max(1,len(killed)):.0%})")
p1, p2 = MOLT_INTERVAL, min(MOLT_INTERVAL, len(eta_hist))
print(f"η: {np.mean(eta_hist[:p2]):.3f} → {np.mean(eta_hist[-p2:]):.3f}")
print(f"H: {np.mean(heat_hist[:p2]):.3f} → {np.mean(heat_hist[-p2:]):.3f}")

# f*
alive_meta = [(k,v) for k,v in entry_meta.items() if k not in killed and v["hard"]]
if alive_meta and killed:
    h_close = np.mean([v["eta_sum"]/max(v["cnt"],1) for _,v in alive_meta])
    h_molt = len(killed) / N_ROUNDS
    if h_molt > 0:
        f_opt = np.sqrt(h_close / max(h_molt, 0.001))
        print(f"f*_theory={f_opt:.1f} actual={N_ROUNDS//MOLT_INTERVAL}")
        print(f"{'✅' if abs(f_opt-N_ROUNDS/MOLT_INTERVAL)<2 else '⚠️Δ='+str(round(abs(f_opt-N_ROUNDS/MOLT_INTERVAL),1))}")

p = Path("E:/AI_Workspace/MSS-AI/project/kb/L3_EMPIRICAL/e019_rest_result.json")
p.parent.mkdir(parents=True, exist_ok=True)
with open(p, "w") as f:
    json.dump({"v":"E019_rest","model":MODEL,"eta":eta_hist,"heat":heat_hist,"killed":len(killed),"miss":miss,"N":N_ROUNDS}, f, indent=2)
print(f"\nSaved: {p}")
