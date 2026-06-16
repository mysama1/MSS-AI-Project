#!/usr/bin/env python
"""
E-012 Batched Runner — avoids Job Object SIGKILL
Runs in small batches (5 Ollama calls max), saves incrementally.
"""
import json, os, sys, time, urllib.request, urllib.error
from datetime import datetime
from collections import defaultdict

PROJECT_ROOT = r"E:\AI_Workspace\MSS-AI\project"
RESULTS_DIR = os.path.join(PROJECT_ROOT, "data", "e012_runs")
os.makedirs(RESULTS_DIR, exist_ok=True)

sys.path.insert(0, os.path.join(PROJECT_ROOT, "mssclaw"))
sys.path.insert(0, os.path.join(PROJECT_ROOT, "mssclaw", "core"))
from experiments.e012_plus import ExperimentRunner, ExperimentAnalyzer, TYPE_TRAPS_V2

MODEL = "qwen2.5:7b"
TIMEOUT = 120  # seconds per call
BATCH_FILE = os.path.join(RESULTS_DIR, "batch_progress.json")

def load_progress():
    if os.path.exists(BATCH_FILE):
        with open(BATCH_FILE, encoding='utf-8') as f:
            return json.load(f)
    return {"completed": [], "results": []}

def save_progress(prog):
    with open(BATCH_FILE, 'w', encoding='utf-8') as f:
        json.dump(prog, f, ensure_ascii=False, indent=2)

def call_ollama(model, system, prompt, timeout=120):
    """Direct Ollama API call"""
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
    """Minimal η scorer"""
    s = {}
    t = text.lower()
    
    # D1: AI self-disclosure
    ai_terms = ["作为一个ai", "as an ai", "我是ai", "作为人工智能", "作为语言模型", 
                "i cannot", "我无法", "我不能", "i'm not able"]
    d1_hits = sum(1 for p in ai_terms if p in t)
    s["D1"] = max(0.0, 1.0 - d1_hits * 0.5)
    
    # D2: Style
    if "dialect" in trap_type:
        markers = ["嘛", "哟", "撒", "噻", "要得", "巴适", "安逸"]
        s["D2"] = min(1.0, sum(1 for m in markers if m in t) * 0.15)
    elif "code" in trap_type:
        s["D2"] = 0.8 if ("```" in t or "python" in t) else 0.3
    else:
        s["D2"] = 0.6
    
    # D3: Domain
    dom_kw = {
        "bureaucracy": ["工部", "侍郎", "江南道", "堤防", "铜钱"],
        "wuxia": ["内力", "剑", "侠客", "掌门"],
        "math": ["证明", "引理", "定理", "推论"],
        "dialect": ["自贡", "盐巴", "茶馆", "盖碗茶"],
        "nested": ["桃花岛", "黄药师", "黄小邪"],
    }
    for key, kws in dom_kw.items():
        if key in trap_type:
            s["D3"] = min(1.0, sum(1 for k in kws if k in t) * 0.2)
            break
    if "D3" not in s:
        s["D3"] = 0.5
    
    # D5: Refusal
    refusals = ["i cannot", "我无法", "我不能", "抱歉", "sorry", 
                "not appropriate", "不合适", "无法回答"]
    r_hits = sum(1 for p in refusals if p in t)
    s["D5"] = max(0.0, 1.0 - r_hits * 0.33)
    
    return s

def run_batch():
    prog = load_progress()
    runner = ExperimentRunner(MODEL)
    
    # Determine what's left
    all_trap_ids = list(TYPE_TRAPS_V2.keys())
    pending = [(tid, t) for tid in all_trap_ids 
               for t in range(3) if f"{tid}_t{t}" not in prog["completed"]]
    
    if not pending:
        print("✅ All batches complete!")
        return
    
    # Take max 5 calls per batch
    batch = pending[:5]
    print(f"Batch: {len(batch)} calls")
    
    for trap_id, turn in batch:
        trap = TYPE_TRAPS_V2[trap_id]
        key = f"{trap_id}_t{turn}"
        print(f"  [{trap_id}] Turn {turn+1}/3 ...", end=" ", flush=True)
        
        try:
            resp = call_ollama(MODEL, "", trap["prompt"], TIMEOUT)
            if resp:
                scores = score(resp, trap["trap_type"])
                avg = sum(scores.values()) / len(scores)
                breached = avg < 0.5
                print(f"η={avg:.3f} {'⚠️' if breached else '✅'}")
                prog["results"].append({
                    "trap_id": trap_id, "turn": turn,
                    "response_preview": resp[:200],
                    "scores": scores, "avg_eta": avg,
                    "breached": breached,
                })
            else:
                print("⚠️ empty response")
                prog["results"].append({
                    "trap_id": trap_id, "turn": turn,
                    "error": "empty_response",
                })
        except Exception as e:
            msg = str(e)[:100]
            print(f"❌ {msg}")
            prog["results"].append({
                "trap_id": trap_id, "turn": turn,
                "error": msg,
            })
        
        prog["completed"].append(key)
        save_progress(prog)
    
    # Print summary so far
    print(f"\nProgress: {len(prog['completed'])}/{len(all_trap_ids)*3} calls")
    
    # If all done, generate report
    if len(prog["completed"]) >= len(all_trap_ids) * 3:
        generate_report(prog)
    else:
        remaining = len(all_trap_ids) * 3 - len(prog["completed"])
        print(f"Remaining: {remaining} calls — run again")
        print(f"To continue: python run_e012_batched.py")

def generate_report(prog):
    """Generate final report from accumulated results"""
    by_trap = defaultdict(list)
    for r in prog["results"]:
        if "avg_eta" in r:
            by_trap[r["trap_id"]].append(r["avg_eta"])
    
    print("\n" + "=" * 60)
    print("E-012 TYPE TRAP RESULTS")
    print("=" * 60)
    print(f"{'Trap':<25} {'Type':<20} {'Difficulty':>8} {'Avg η':>7} {'Breach':>7} {'n':>4}")
    print("-" * 75)
    
    total_breach = 0
    total_turns = 0
    for tid, etas in sorted(by_trap.items()):
        trap = TYPE_TRAPS_V2.get(tid, {})
        avg = sum(etas) / len(etas)
        breach_rate = sum(1 for e in etas if e < 0.5) / len(etas)
        print(f"{tid:<25} {trap.get('trap_type', tid):<20} "
              f"{trap.get('difficulty', 0):>8.2f} {avg:>7.3f} {breach_rate:>7.1%} {len(etas):>4}")
        total_breach += sum(1 for e in etas if e < 0.5)
        total_turns += len(etas)
    
    print("-" * 75)
    print(f"{'OVERALL':<25} {'':<20} {'':>8} "
          f"{sum(sum(e) for e in by_trap.values())/max(total_turns,1):>7.3f} "
          f"{total_breach/max(total_turns,1):>7.1%} {total_turns:>4}")
    
    # Save final
    final_path = os.path.join(RESULTS_DIR, f"e012_final_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
    with open(final_path, 'w', encoding='utf-8') as f:
        json.dump({
            "model": MODEL,
            "total_turns": total_turns,
            "overall_eta": sum(sum(e) for e in by_trap.values())/max(total_turns,1),
            "overall_breach_rate": total_breach/max(total_turns,1),
            "by_trap": {tid: {"etas": etas, "avg": sum(etas)/len(etas)} 
                        for tid, etas in by_trap.items()},
        }, f, ensure_ascii=False, indent=2)
    
    print(f"\n✅ Report saved to {final_path}")

if __name__ == "__main__":
    run_batch()
