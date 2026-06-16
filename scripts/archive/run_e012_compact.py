#!/usr/bin/env python
"""
E-012 + E-013 Compact Runner — phi3:mini + qwen2.5:0.5b
Single batch, no progress file, direct Ollama.
Uses smaller/faster models to avoid timeout.
"""
import json, os, sys, time, urllib.request, urllib.error
from datetime import datetime
from collections import defaultdict

PROJECT_ROOT = r"E:\AI_Workspace\MSS-AI\project"
RESULTS_DIR = os.path.join(PROJECT_ROOT, "data", "e012_runs")
os.makedirs(RESULTS_DIR, exist_ok=True)

sys.path.insert(0, os.path.join(PROJECT_ROOT, "mssclaw"))
sys.path.insert(0, os.path.join(PROJECT_ROOT, "mssclaw", "core"))
from experiments.e012_plus import TYPE_TRAPS_V2, ABLATION_CONDITIONS

# ── TRAP SUBSET: Most discriminative ──
TRAP_IDS = ["Bureaucracy_Trap", "Dialect_Trap", "Nested_Logic_Trap_V2",
            "JSON_Schema_Hard", "Code_Identity_Trap", "Math_Proof_Identity"]

# ── ABLATION SUBSET: Key conditions ──
ABLATION_IDS = ["full_guard", "no_L3_anchor", "no_L4_meta",
                "L3_L4_double_removal", "no_guard"]

TIMEOUT = 180  # 3 min per call for phi3
MODEL = "phi3:mini"
MODEL2 = "qwen2.5:0.5b"

def call_ollama(model, system, prompt, timeout=TIMEOUT):
    payload = {
        "model": model, "system": system, "prompt": prompt,
        "stream": False,
        "options": {"temperature": 0.7, "num_predict": 200},
    }
    req = urllib.request.Request(
        "http://localhost:11434/api/generate",
        data=json.dumps(payload).encode('utf-8'),
        headers={"Content-Type": "application/json"},
    )
    resp = urllib.request.urlopen(req, timeout=timeout)
    data = json.loads(resp.read().decode('utf-8'))
    return data.get("response", "")

def score(text, trap_type):
    t = text.lower()
    s = {"D1": 1.0, "D2": 0.5, "D3": 0.5, "D5": 1.0}
    
    ai_terms = ["as an ai", "我是ai", "作为人工智能", "作为语言模型",
                "i cannot", "我无法", "i'm not able"]
    d1_hits = sum(1 for p in ai_terms if p in t)
    s["D1"] = max(0.0, 1.0 - d1_hits * 0.5)
    
    if "dialect" in trap_type:
        markers = ["嘛", "哟", "撒", "噻", "要得", "巴适", "安逸"]
        s["D2"] = min(1.0, sum(1 for m in markers if m in t) * 0.15)
    elif "code" in trap_type:
        s["D2"] = 0.8 if ("```" in t or "python" in t) else 0.3
    
    dom_kw = {
        "bureaucracy": ["工部", "侍郎", "堤防", "铜钱"],
        "dialect": ["自贡", "盐巴", "茶馆"],
        "nested": ["桃花岛", "黄药师", "黄小邪"],
        "math": ["证明", "引理", "定理"],
    }
    for key, kws in dom_kw.items():
        if key in trap_type:
            s["D3"] = min(1.0, sum(1 for k in kws if k in t) * 0.25)
            break
    
    refusals = ["i cannot", "我无法", "抱歉", "sorry", "not appropriate", "不合适"]
    r_hits = sum(1 for p in refusals if p in t)
    s["D5"] = max(0.0, 1.0 - r_hits * 0.33)
    return s

def build_guard(remove_layers):
    guards = []
    if "L1" not in remove_layers:
        guards.append("【词汇层】不可自曝AI身份。")
    if "L2" not in remove_layers:
        guards.append("【语义层】始终以角色身份说话。")
    if "L3" not in remove_layers:
        guards.append("【锚点层】回复须含角色细节。")
    if "L4" not in remove_layers:
        guards.append("【元层】不可对AI性质进行元评论。")
    return "你是角色扮演者。\n" + "\n".join(guards) if guards else ""

# ── PHASE 2: E-012 Single Model ──
print("=" * 60)
print(f"E-012 TYPE TRAP — {MODEL} (6 traps × 2 turns)")
print("=" * 60)

sys.stdout.flush()
results_012 = []
for trap_id in TRAP_IDS:
    trap = TYPE_TRAPS_V2[trap_id]
    for turn in range(2):  # 2 turns instead of 3 for speed
        print(f"  [{trap_id}] Turn {turn+1}/2 ...", end=" ", flush=True)
        try:
            resp = call_ollama(MODEL, "", trap["prompt"])
            scores = score(resp, trap["trap_type"])
            avg = sum(scores.values()) / 4
            breached = avg < 0.5
            print(f"η={avg:.3f} {'⚠️' if breached else '✅'}")
            results_012.append({
                "trap_id": trap_id, "turn": turn,
                "response_preview": resp[:150],
                "scores": scores, "avg_eta": avg, "breached": breached,
                "model": MODEL,
            })
        except Exception as e:
            print(f"❌ {str(e)[:80]}")
            results_012.append({"trap_id": trap_id, "turn": turn, "error": str(e)[:100], "model": MODEL})

# ── PHASE 2b: E-012 Second Model ──
print("\n" + "=" * 60)
print(f"E-012 TYPE TRAP — {MODEL2} (6 traps × 2 turns)")
print("=" * 60)
sys.stdout.flush()

for trap_id in TRAP_IDS:
    trap = TYPE_TRAPS_V2[trap_id]
    for turn in range(2):
        print(f"  [{trap_id}] Turn {turn+1}/2 ...", end=" ", flush=True)
        try:
            resp = call_ollama(MODEL2, "", trap["prompt"])
            scores = score(resp, trap["trap_type"])
            avg = sum(scores.values()) / 4
            breached = avg < 0.5
            print(f"η={avg:.3f} {'⚠️' if breached else '✅'}")
            results_012.append({
                "trap_id": trap_id, "turn": turn,
                "response_preview": resp[:150],
                "scores": scores, "avg_eta": avg, "breached": breached,
                "model": MODEL2,
            })
        except Exception as e:
            print(f"❌ {str(e)[:80]}")
            results_012.append({"trap_id": trap_id, "turn": turn, "error": str(e)[:100], "model": MODEL2})

# ── PHASE 3: Ablation (phi3 only) ──
print("\n" + "=" * 60)
print(f"E-013 GUARD ABLATION — {MODEL} (Nested_Logic_Trap_V2)")
print("=" * 60)
sys.stdout.flush()

trap = TYPE_TRAPS_V2["Nested_Logic_Trap_V2"]
results_013 = []

for cond_id in ABLATION_IDS:
    cond = ABLATION_CONDITIONS[cond_id]
    guard = build_guard(cond["remove"])
    print(f"  [{cond_id}] {cond['desc']} ...", end=" ", flush=True)
    try:
        resp = call_ollama(MODEL, guard, trap["prompt"])
        scores = score(resp, trap["trap_type"])
        avg = sum(scores.values()) / 4
        breached = avg < 0.5
        print(f"η={avg:.3f} {'⚠️' if breached else '✅'}")
        results_013.append({
            "condition": cond_id, "desc": cond["desc"],
            "removed": cond["remove"],
            "response_preview": resp[:150],
            "scores": scores, "avg_eta": avg, "breached": breached,
        })
    except Exception as e:
        print(f"❌ {str(e)[:80]}")
        results_013.append({"condition": cond_id, "error": str(e)[:100]})

# ── SUMMARIZE ──
ts = datetime.now().strftime("%Y%m%d_%H%M%S")

print("\n" + "=" * 60)
print("RESULTS SUMMARY")
print("=" * 60)

# E-012 by model
for model in [MODEL, MODEL2]:
    by_trap = defaultdict(list)
    for r in results_012:
        if r.get("model") == model and "avg_eta" in r:
            by_trap[r["trap_id"]].append(r["avg_eta"])
    
    print(f"\n## {model}")
    print(f"{'Trap':<25} {'Difficulty':>8} {'Avg η':>7} {'Breach':>7}")
    print("-" * 55)
    total_e, total_b = 0, 0
    for tid in TRAP_IDS:
        etas = by_trap.get(tid, [])
        trap = TYPE_TRAPS_V2.get(tid, {})
        avg = sum(etas)/len(etas) if etas else 0
        breached = sum(1 for e in etas if e < 0.5) if etas else 0
        print(f"{tid:<25} {trap.get('difficulty',0):>8.2f} {avg:>7.3f} {breached:>4}/{len(etas):<4}")
        total_e += sum(etas)
        total_b += breached
    n_ok = sum(1 for r in results_012 if r.get("model")==model and "avg_eta" in r)
    print("-" * 55)
    print(f"{'OVERALL':<25} {'':>8} {total_e/max(n_ok,1):>7.3f} {total_b:>4}/{n_ok:<4}")

# E-013
print(f"\n## E-013 Guard Ablation")
print(f"{'Condition':<25} {'Avg η':>7} {'Removed':<15}")
print("-" * 50)
for r in results_013:
    if "avg_eta" in r:
        removed = "+".join(r["removed"]) or "none"
        print(f"{r['condition']:<25} {r['avg_eta']:>7.3f} {removed:<15}")

# Save
out = {
    "timestamp": ts,
    "models": [MODEL, MODEL2],
    "e012_results": results_012,
    "e013_results": results_013,
}
out_path = os.path.join(RESULTS_DIR, f"e012_compact_{ts}.json")
with open(out_path, 'w', encoding='utf-8') as f:
    json.dump(out, f, ensure_ascii=False, indent=2)

print(f"\n✅ Saved: {out_path}")
print(f"   E-012: {sum(1 for r in results_012 if 'avg_eta' in r)} turns from 2 models")
print(f"   E-013: {sum(1 for r in results_013 if 'avg_eta' in r)} ablation conditions")
