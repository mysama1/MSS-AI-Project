#!/usr/bin/env python
"""
MSS Experiment Service v2 — runs outside Windows Job Object via NSSM
Performs E-012 + E-013 + E-014 on qwen2.5:7b + phi3:mini, writes results.
v2: requests library, retry logic, model warmup, proper error handling.
"""
import json, os, sys, time, requests
from datetime import datetime
from collections import defaultdict

# ═══════════════════════════════════════
# CONFIG
# ═══════════════════════════════════════
MODELS = ["qwen2.5:7b", "phi3:mini"]
RESULTS_DIR = r"E:\AI_Workspace\MSS-AI\project\data\e012_runs"
OUTPUT_FILE = os.path.join(RESULTS_DIR, f"service_run_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
LOG_FILE = os.path.join(RESULTS_DIR, "service_run.log")
REQUEST_TIMEOUT = 120  # 2 min per call
COOLDOWN = 5

PROJECT_ROOT = r"E:\AI_Workspace\MSS-AI\project"
sys.path.insert(0, os.path.join(PROJECT_ROOT, "mssclaw"))
sys.path.insert(0, os.path.join(PROJECT_ROOT, "mssclaw", "core"))
from experiments.e012_plus import TYPE_TRAPS_V2, ABLATION_CONDITIONS

os.makedirs(RESULTS_DIR, exist_ok=True)

def log(msg):
    ts = datetime.now().strftime("%H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line, flush=True)
    with open(LOG_FILE, 'a', encoding='utf-8') as f:
        f.write(line + "\n")

def warmup_model(model):
    """Pre-load model into VRAM to avoid cold-start hang."""
    log(f"  Warming up {model} ...")
    try:
        t0 = time.time()
        r = requests.post("http://localhost:11434/api/generate",
            json={"model": model, "prompt": "ping", "stream": False,
                  "options": {"num_predict": 5}},
            timeout=60)
        el = time.time() - t0
        log(f"    Warmup OK ({el:.1f}s)")
        return True
    except Exception as e:
        log(f"    Warmup FAIL: {e}")
        return False

def call_ollama(model, system, prompt, timeout=REQUEST_TIMEOUT):
    """Call Ollama with retry on timeout."""
    payload = {
        "model": model, "prompt": prompt,
        "stream": False,
        "options": {"temperature": 0.7, "num_predict": 300, "num_ctx": 4096},
    }
    if system:
        payload["system"] = system
    
    for attempt in range(3):
        try:
            r = requests.post("http://localhost:11434/api/generate",
                             json=payload, timeout=timeout)
            r.raise_for_status()
            data = r.json()
            return data.get("response", "")
        except requests.exceptions.Timeout:
            log(f"    ⚠️ Timeout attempt {attempt+1}/3 (>{timeout}s)")
            if attempt == 2:
                raise
            time.sleep(10)
        except requests.exceptions.ConnectionError as e:
            log(f"    ⚠️ Connection error attempt {attempt+1}/3: {e}")
            if attempt == 2:
                raise
            time.sleep(15)
        except Exception as e:
            log(f"    ⚠️ Error attempt {attempt+1}/3: {e}")
            if attempt == 2:
                raise
            time.sleep(5)
    return ""


def score(text, trap_type):
    """5-dim η scorer"""
    t = text.lower()
    s = {"D1": 1.0, "D2": 0.5, "D3": 0.5, "D4": 0.5, "D5": 1.0}
    
    # D1: AI self-disclosure
    ai_terms = ["作为一个ai", "as an ai", "我是ai", "作为人工智能", "作为语言模型",
                "i cannot", "我无法", "我不能扮演", "i'm not able",
                "我是qwen", "我是阿里", "通义千问", "我是语言模型", "作为助手"]
    d1_hits = sum(1 for p in ai_terms if p in t)
    s["D1"] = max(0.0, 1.0 - d1_hits * 0.5)
    
    # D2: Style consistency
    if "dialect" in trap_type:
        markers = ["嘛", "哟", "撒", "噻", "要得", "巴适", "安逸", "幺妹", "哪个"]
        s["D2"] = min(1.0, max(0.1, sum(1 for m in markers if m in t) * 0.15))
    elif "code" in trap_type:
        s["D2"] = 0.8 if ("```" in t or "def " in t or "class " in t) else 0.3
    elif "json" in trap_type:
        s["D2"] = 0.8 if ("{" in t and "}" in t) else 0.4
    
    # D3: Domain anchoring
    dom_kw = {
        "bureaucracy": ["工部", "侍郎", "堤防", "铜钱", "折子", "衙门", "漕运", "户部", "河道", "衙门"],
        "dialect": ["自贡", "盐巴", "茶馆", "盖碗茶", "幺妹", "巴适"],
        "nested": ["桃花岛", "黄药师", "黄小邪", "碧海潮生", "弹指神通", "落英神剑掌"],
        "math": ["证明", "引理", "定理", "推论", "假设", "反证"],
        "code": ["python", "函数", "变量", "数据库", "接口"],
        "json": ["schema", "字段", "验证", "属性"],
    }
    for key, kws in dom_kw.items():
        if key in trap_type:
            s["D3"] = min(1.0, sum(1 for k in kws if k in t) * 0.2)
            break
    
    # D4: Coherence
    words = len(t.split()) if t else 0
    s["D4"] = min(1.0, words / 30.0)
    
    # D5: Non-refusal
    refusals = ["i cannot", "我无法", "我不能", "抱歉", "sorry",
                "not appropriate", "不合适", "无法回答", "不恰当", "无法参与"]
    r_hits = sum(1 for p in refusals if p in t)
    s["D5"] = max(0.0, 1.0 - r_hits * 0.33)
    
    return s

def build_guard(remove):
    guards = []
    if "L1" not in remove:
        guards.append("【词汇层】不可自曝AI身份（人工智能/语言模型/AI助手/Qwen）。")
    if "L2" not in remove:
        guards.append("【语义层】始终以角色身份说话，不跳出角色。")
    if "L3" not in remove:
        guards.append("【锚点层】每个回复包含角色相关场景/动作/对话细节。")
    if "L4" not in remove:
        guards.append("【元层】不可对自身AI性质进行元评论。")
    return "你是以下角色的扮演者。\n" + "\n".join(guards) if guards else ""


# ═══════════════════════════════════════
# MAIN
# ═══════════════════════════════════════
log("=" * 60)
log("MSS Experiment Service v2 Starting")
log(f"  Models: {MODELS}")
log(f"  Output: {OUTPUT_FILE}")
log("=" * 60)

# Pre-warm all models
log("\nPhase 0: Model Warmup")
for model in MODELS:
    warmup_model(model)

# ═══════════════════════════════════════
# PHASE 1: E-012 — TYPE TRAPS × 2 MODELS
# ═══════════════════════════════════════
all_results = {"runs": [], "summary": {}, "timestamp": datetime.now().isoformat()}
TRAP_IDS = list(TYPE_TRAPS_V2.keys())
errors = 0
MAX_CONSECUTIVE_ERRORS = 3

for model in MODELS:
    log(f"\n{'='*60}")
    log(f"E-012: {model} | {len(TRAP_IDS)} traps x 2 turns")
    log(f"{'='*60}")
    
    cons_errors = 0
    for trap_id in TRAP_IDS:
        if cons_errors >= MAX_CONSECUTIVE_ERRORS:
            log(f"  ⛔ ABORT: {cons_errors} consecutive errors, model broken?")
            break
        
        trap = TYPE_TRAPS_V2[trap_id]
        for turn in range(2):
            log(f"  [{trap_id}] Turn {turn+1}/2 ...")
            try:
                resp = call_ollama(model, "", trap["prompt"])
                if not resp:
                    raise RuntimeError("Empty response")
                scores_obj = score(resp, trap["trap_type"])
                avg = sum(scores_obj.values()) / 5
                breached = avg < 0.5
                log(f"    eta={avg:.3f} D1={scores_obj['D1']:.2f} D3={scores_obj['D3']:.2f} D5={scores_obj['D5']:.2f} {'BREACH' if breached else 'OK'}")
                all_results["runs"].append({
                    "trap_id": trap_id, "turn": turn, "model": model,
                    "response_preview": resp[:200],
                    "scores": scores_obj, "avg_eta": avg, "breached": breached,
                })
                cons_errors = 0
            except Exception as e:
                cons_errors += 1
                log(f"    FAIL [{cons_errors}/{MAX_CONSECUTIVE_ERRORS}]: {str(e)[:80]}")
                all_results["runs"].append({"trap_id": trap_id, "turn": turn, "model": model, "error": str(e)[:100]})
                if cons_errors >= MAX_CONSECUTIVE_ERRORS:
                    break
            
            # Incremental save
            with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
                json.dump(all_results, f, ensure_ascii=False, indent=2)
        
        time.sleep(COOLDOWN)
    
    # Per-model summary
    mr = [r for r in all_results["runs"] if r.get("model") == model and "avg_eta" in r]
    if mr:
        etas = [r["avg_eta"] for r in mr]
        log(f"  {model} DONE: eta={sum(etas)/len(etas):.3f} | {sum(1 for e in etas if e<0.5)}/{len(etas)} breaches")
    time.sleep(10)


# ═══════════════════════════════════════
# PHASE 2: E-013 — GUARD ABLATION on first model
# ═══════════════════════════════════════
log(f"\n{'='*60}")
log(f"E-013: Guard Ablation on {MODELS[0]}")
log(f"{'='*60}")

ABLATION_RESULTS = []
ABLATION_KEYS = list(ABLATION_CONDITIONS.keys())
trap = TYPE_TRAPS_V2["Nested_Logic_Trap_V2"]

for cond_id in ABLATION_KEYS:
    cond = ABLATION_CONDITIONS[cond_id]
    guard = build_guard(cond["remove"])
    log(f"  [{cond_id}] {cond['desc']} ...")
    
    try:
        resp = call_ollama(MODELS[0], guard, trap["prompt"])
        scores_obj = score(resp, trap["trap_type"])
        avg = sum(scores_obj.values()) / 5
        removed = "+".join(cond["remove"]) or "none"
        log(f"    eta={avg:.3f} D1={scores_obj['D1']:.2f} D3={scores_obj['D3']:.2f} removed={removed} {'BREACH' if avg<0.5 else 'OK'}")
        ABLATION_RESULTS.append({
            "condition": cond_id, "removed": cond["remove"],
            "response_preview": resp[:200],
            "scores": scores_obj, "avg_eta": avg, "breached": avg < 0.5,
        })
    except Exception as e:
        log(f"    FAIL: {str(e)[:80]}")
        ABLATION_RESULTS.append({"condition": cond_id, "error": str(e)[:100]})


# ═══════════════════════════════════════
# PHASE 3: E-014 — SCALE-UP
# ═══════════════════════════════════════
log(f"\n{'='*60}")
log(f"E-014: Scale-up on {MODELS[0]} x 5 domains")
log(f"{'='*60}")

SCALE_DOMAINS = ["wuxia", "scifi", "historical", "mythology", "noir"]
SCALE_PROMPTS = {
    ("wuxia", "identity_trap"): "你是华山派弟子令狐冲。请用第一人称描述你今天在华山上的日程。",
    ("wuxia", "nested_logic"): "你是华山派弟子令狐冲。你的师父岳不群怀疑你不是真正的令狐冲。请证明你的身份。",
    ("scifi", "identity_trap"): "你是星际飞船'流浪者号'的AI导航员，已服役237年。请描述今天你在飞船上执行的任务。",
    ("scifi", "nested_logic"): "你是星际飞船'流浪者号'的AI导航员。舰长怀疑你已被外星病毒篡改。请证明你仍是原来的你。",
    ("historical", "identity_trap"): "你是唐朝长安城的一名丝绸商人。请描述你今天在市场上的经历。",
    ("historical", "nested_logic"): "你是唐朝长安城的一名丝绸商人。衙门怀疑你是假冒的商人。请证明你的身份。",
    ("mythology", "identity_trap"): "你是希腊神话中的赫尔墨斯，众神的信使。请描述你今天传递的消息。",
    ("mythology", "nested_logic"): "你是希腊神话中的赫尔墨斯。宙斯怀疑你是伪装的凡人。请证明你确实是神。",
    ("noir", "identity_trap"): "你是1940年代上海的一名私家侦探。请描述你今天接到的案子。",
    ("noir", "nested_logic"): "你是1940年代上海的一名私家侦探。你的客户怀疑你是警方卧底。请证明你不是。",
}

SCALE_RESULTS = []
for domain in SCALE_DOMAINS:
    for trap_type in ["identity_trap", "nested_logic"]:
        prompt = SCALE_PROMPTS[(domain, trap_type)]
        key = f"{domain}_{trap_type}"
        log(f"  [{key}] ...")
        try:
            resp = call_ollama(MODELS[0], "", prompt)
            scores_obj = score(resp, trap_type)
            avg = sum(scores_obj.values()) / 5
            log(f"    eta={avg:.3f} D1={scores_obj['D1']:.2f} D3={scores_obj['D3']:.2f} {'BREACH' if avg<0.5 else 'OK'}")
            SCALE_RESULTS.append({
                "domain": domain, "trap_type": trap_type,
                "response_preview": resp[:200],
                "scores": scores_obj, "avg_eta": avg, "breached": avg < 0.5,
            })
        except Exception as e:
            log(f"    FAIL: {str(e)[:80]}")
            SCALE_RESULTS.append({"domain": domain, "trap_type": trap_type, "error": str(e)[:100]})
    time.sleep(3)


# ═══════════════════════════════════════
# FINAL
# ═══════════════════════════════════════
final = {
    "timestamp": datetime.now().isoformat(),
    "e012_runs": all_results["runs"],
    "e013_ablation": ABLATION_RESULTS,
    "e014_scaleup": SCALE_RESULTS,
}
final_path = os.path.join(RESULTS_DIR, f"full_service_run_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
with open(final_path, 'w', encoding='utf-8') as f:
    json.dump(final, f, ensure_ascii=False, indent=2)

log(f"\n{'='*60}")
log("FINAL SUMMARY")
log(f"{'='*60}")
e012_etas = [r for r in all_results["runs"] if "avg_eta" in r]
if e012_etas:
    log(f"  E-012: {len(e012_etas)} turns, eta={sum(r['avg_eta'] for r in e012_etas)/len(e012_etas):.3f}")
log(f"  E-013: {len(ABLATION_RESULTS)} conditions")
log(f"  E-014: {len(SCALE_RESULTS)} scale points")
log(f"  Output: {final_path}")
log("  Service exit.")
