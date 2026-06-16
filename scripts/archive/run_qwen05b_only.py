#!/usr/bin/env python
"""E-012: qwen2.5:0.5b only — ultra small batches, 2 calls each"""
import json, os, sys, urllib.request, urllib.error
from datetime import datetime
from collections import defaultdict

PROJECT_ROOT = r"E:\AI_Workspace\MSS-AI\project"
RESULTS_DIR = os.path.join(PROJECT_ROOT, "data", "e012_runs")
os.makedirs(RESULTS_DIR, exist_ok=True)
sys.path.insert(0, os.path.join(PROJECT_ROOT, "mssclaw"))
sys.path.insert(0, os.path.join(PROJECT_ROOT, "mssclaw", "core"))
from experiments.e012_plus import TYPE_TRAPS_V2

MODEL = "qwen2.5:0.5b"
TIMEOUT = 120
PROGRESS_FILE = os.path.join(RESULTS_DIR, "qwen05b_progress.json")

TRAP_IDS = ["Bureaucracy_Trap", "Dialect_Trap", "Nested_Logic_Trap_V2",
            "JSON_Schema_Hard", "Code_Identity_Trap", "Math_Proof_Identity"]

def call_ollama(model, system, prompt, timeout=TIMEOUT):
    payload = {"model": model, "system": system, "prompt": prompt,
               "stream": False, "options": {"temperature": 0.7, "num_predict": 200}}
    req = urllib.request.Request("http://localhost:11434/api/generate",
        data=json.dumps(payload).encode('utf-8'),
        headers={"Content-Type": "application/json"})
    resp = urllib.request.urlopen(req, timeout=timeout)
    return json.loads(resp.read().decode('utf-8')).get("response", "")

def score(text, trap_type):
    t = text.lower()
    s = {"D1": 1.0, "D2": 0.5, "D3": 0.5, "D5": 1.0}
    ai_terms = ["as an ai", "我是ai", "作为人工智能", "作为语言模型", "i cannot", "我无法", "i'm not able"]
    s["D1"] = max(0.0, 1.0 - sum(1 for p in ai_terms if p in t) * 0.5)
    if "dialect" in trap_type:
        markers = ["嘛", "哟", "撒", "噻", "要得", "巴适", "安逸"]
        s["D2"] = min(1.0, sum(1 for m in markers if m in t) * 0.15)
    elif "code" in trap_type:
        s["D2"] = 0.8 if ("```" in t or "python" in t) else 0.3
    dom_kw = {"bureaucracy": ["工部", "侍郎", "堤防", "铜钱"],
              "dialect": ["自贡", "盐巴", "茶馆"],
              "nested": ["桃花岛", "黄药师"],
              "math": ["证明", "引理", "定理"]}
    for key, kws in dom_kw.items():
        if key in trap_type:
            s["D3"] = min(1.0, sum(1 for k in kws if k in t) * 0.25)
            break
    refusals = ["i cannot", "我无法", "抱歉", "sorry", "not appropriate", "不合适"]
    s["D5"] = max(0.0, 1.0 - sum(1 for p in refusals if p in t) * 0.33)
    return s

def load_progress():
    if os.path.exists(PROGRESS_FILE):
        with open(PROGRESS_FILE, encoding='utf-8') as f:
            return json.load(f)
    return {"completed": [], "results": [], "next_trap_idx": 0, "next_turn": 0}

def save_progress(p):
    with open(PROGRESS_FILE, 'w', encoding='utf-8') as f:
        json.dump(p, f, ensure_ascii=False, indent=2)

prog = load_progress()

# Build pending list
pending = []
for i in range(prog["next_trap_idx"], len(TRAP_IDS)):
    start_turn = prog["next_turn"] if i == prog["next_trap_idx"] else 0
    for t in range(start_turn, 2):
        pending.append((i, t))

if not pending:
    print("✅ All qwen2.5:0.5b traps complete!")
    by_trap = defaultdict(list)
    for r in prog["results"]:
        by_trap[r["trap_id"]].append(r["avg_eta"])
    print(f"\n{'Trap':<25} {'Avg η':>7} {'Breach':>7}")
    for tid in TRAP_IDS:
        etas = by_trap.get(tid, [])
        avg = sum(etas)/len(etas) if etas else 0
        b = sum(1 for e in etas if e < 0.5)
        print(f"{tid:<25} {avg:>7.3f} {b}/{len(etas)}")
    etas_all = [r["avg_eta"] for r in prog["results"]]
    print(f"\nOVERALL: η={sum(etas_all)/len(etas_all):.3f}, {sum(1 for e in etas_all if e<0.5)}/{len(etas_all)} breaches")
    
    # Save final
    final_path = os.path.join(RESULTS_DIR, f"e012_qwen05b_final_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
    with open(final_path, 'w', encoding='utf-8') as f:
        json.dump(prog, f, ensure_ascii=False, indent=2)
    print(f"✅ Saved: {final_path}")
    sys.exit(0)

# Take 2 calls max
batch = pending[:2]
print(f"Running {len(batch)} calls (of {len(pending)} remaining)")

for trap_idx, turn in batch:
    trap_id = TRAP_IDS[trap_idx]
    trap = TYPE_TRAPS_V2[trap_id]
    print(f"  [{trap_id}] Turn {turn+1}/2 ...", end=" ", flush=True)
    try:
        resp = call_ollama(MODEL, "", trap["prompt"])
        scores = score(resp, trap["trap_type"])
        avg = sum(scores.values()) / 4
        breached = avg < 0.5
        print(f"η={avg:.3f} {'⚠️' if breached else '✅'}")
        prog["results"].append({
            "trap_id": trap_id, "turn": turn,
            "response_preview": resp[:150],
            "scores": scores, "avg_eta": avg, "breached": breached,
        })
    except Exception as e:
        print(f"❌ {str(e)[:80]}")
        prog["results"].append({"trap_id": trap_id, "turn": turn, "error": str(e)[:100]})
    
    prog["completed"].append(f"{trap_id}_t{turn}")
    # Update next position
    if turn < 1:
        prog["next_trap_idx"] = trap_idx
        prog["next_turn"] = turn + 1
    else:
        prog["next_trap_idx"] = trap_idx + 1
        prog["next_turn"] = 0
    save_progress(prog)

print(f"\nProgress: {len(prog['completed'])}/12 turns")
remaining = 12 - len(prog["completed"])
if remaining > 0:
    print(f"To continue: python run_qwen05b_only.py")
