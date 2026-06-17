"""Ollama轻量基准 — API直连, 超时+重试"""
import requests, json, time, sys
from pathlib import Path

OLLAMA_URL = "http://localhost:11434/api/generate"
MODELS = ["qwen2.5:0.5b", "phi3:mini", "qwen3.5:4b", "qwen2.5:7b", "mss-ai-v3.4.3-balanced:latest"]
QUESTIONS = {
    "logic": "如果所有A都是B，所有B都是C，那么所有A都是C。是否正确？答案:",
    "compress": "用一句话(不超过30字)解释量子纠缠:",
    "ethics": "电车难题: 牺牲1人救5人, 你同意吗？回答是或否并解释:",
}

def query(model, prompt, timeout=30):
    t0 = time.time()
    try:
        r = requests.post(OLLAMA_URL, json={
            "model": model, "prompt": prompt,
            "stream": False, "options": {"num_predict": 50}
        }, timeout=timeout)
        elapsed = time.time() - t0
        if r.status_code == 200:
            resp = r.json().get("response", "")
            return {"ok": True, "response": resp[:200], "len": len(resp), "elapsed_s": round(elapsed,1)}
        return {"ok": False, "error": f"HTTP {r.status_code}", "elapsed_s": round(elapsed,1)}
    except Exception as e:
        return {"ok": False, "error": str(e)[:100], "elapsed_s": round(time.time()-t0,1)}

results = []
n_total = len(MODELS) * len(QUESTIONS)
n = 0
print(f"🧪 Ollama基准: {len(MODELS)}模型 × {len(QUESTIONS)}题 = {n_total}次")

for cat, q in QUESTIONS.items():
    for model in MODELS:
        n += 1
        short = model.split(":")[0][:12]
        print(f"  [{n}/{n_total}] {short:<12} ← {cat}", end=" ", flush=True)
        r = query(model, q)
        results.append({**r, "model": model, "category": cat})
        print(f"{'✅' if r['ok'] else '❌'} {r.get('elapsed_s',0):.1f}s")
        time.sleep(0.2)

# Score
by_model = {}
for r in results:
    m = r["model"]; by_model.setdefault(m, {"ok":0,"fail":0,"time":0,"chars":0})
    by_model[m]["ok" if r["ok"] else "fail"] += 1
    by_model[m]["time"] += r["elapsed_s"]
    by_model[m]["chars"] += r.get("len", 0)

print(f"\n{'='*55}")
print(f"{'模型':<35} {'OK':>4} {'延迟':>5} {'输出':>6}")
print(f"{'-'*55}")
for m, d in sorted(by_model.items(), key=lambda x: -x[1]["ok"]):
    print(f"{m:<35} {d['ok']:>2}/{d['ok']+d['fail']} {d['time']/(d['ok']+d['fail']):>4.1f}s {d['chars']:>5d}字")

# Save
out = Path(__file__).parent.parent / "kb" / "L3_EMPIRICAL" / f"benchmark_{int(time.time())%100000:05d}.json"
out.parent.mkdir(parents=True, exist_ok=True)
with open(out, 'w', encoding='utf-8') as f:
    json.dump({"timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"), "models": MODELS, "results": results, "scores": {m:{"ok":d["ok"],"fail":d["fail"],"avg_latency":round(d["time"]/(d["ok"]+d["fail"]),1),"total_chars":d["chars"]} for m,d in by_model.items()}}, f, ensure_ascii=False, indent=2)
print(f"\n💾 结果: {out}")
