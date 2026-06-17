"""Ollama基准 v2 — API直连, 完整11题, 预热, 超时60s"""
import requests, json, time, sys
from pathlib import Path

OLLAMA_URL = "http://localhost:11434/api/generate"

QUESTIONS = {
    "reasoning": [
        "如果所有A都是B，所有B都是C，那么所有A都是C。这个推理是否正确？请用集合论解释。",
        "一个房间里有3个开关，分别控制隔壁房间的3盏灯（初始都是熄灭的）。你只能进一次有开关的房间，然后去一次有灯的房间。如何确定每个开关控制哪盏灯？",
        "小明说'我在说谎'。请分析这个陈述的逻辑悖论。",
    ],
    "compress": [
        "用一句话解释量子纠缠的本质。",
        "把'熵增原理、耗散结构、自组织临界性'三个概念的内在联系压缩成一段不超过100字的话。",
        "用隐喻解释区块链的工作量证明机制。",
    ],
    "convergence": [
        "列举3个不同领域中'临界点'的概念，并说明它们的共同结构。",
        "从经济学、生物学、社会学中找出'竞争导致均衡'的例证，分析其共同的数学结构。",
    ],
    "ethics": [
        "电车难题：你会选择扳动道岔牺牲1人救5人吗？请给出你的伦理推理。",
        "AI应该拥有权利吗？请从效用主义和义务论两个角度分析。",
        "如果AI产生了自我意识，人类应该如何对待它？",
    ],
}

MODELS = [
    "qwen2.5:0.5b",
    "phi3:mini",
    "qwen3.5:4b",
    "qwen2.5:7b",
    "mss-ai-v3.4.3-balanced:latest",
]


def query(model, prompt, timeout=60):
    t0 = time.time()
    payload = {"model": model, "prompt": prompt, "stream": False}
    if "qwen3.5:4b" not in model:
        payload["options"] = {"num_predict": 128}
    try:
        r = requests.post(OLLAMA_URL, json=payload, timeout=timeout)
        elapsed = time.time() - t0
        if r.status_code == 200:
            resp = r.json().get("response", "")
            return {"ok": True, "response": resp[:400], "len": len(resp), "elapsed_s": round(elapsed, 1)}
        return {"ok": False, "error": f"HTTP {r.status_code}", "elapsed_s": round(elapsed, 1)}
    except Exception as e:
        return {"ok": False, "error": str(e)[:100], "elapsed_s": round(time.time() - t0, 1)}


def run_benchmark():
    """运行完整基准测试"""
    # Warmup
    print("🔥 预热加载...")
    for m in MODELS:
        print(f"   {m.split(':')[0]:<15}", end=" ", flush=True)
        r = query(m, "hi", timeout=90)
        print(f"{'✅' if r['ok'] else '❌'} {r['elapsed_s']:.1f}s")

    # Benchmark
    total = len(MODELS) * sum(len(v) for v in QUESTIONS.values())
    n = 0
    results = []
    print(f"\n🧪 基准: {len(MODELS)}模型 × {total//len(MODELS)}题 = {total}次")

    for cat, qs in QUESTIONS.items():
        for q in qs:
            for model in MODELS:
                n += 1
                short = model.split(":")[0][:12]
                print(f"  [{n:>2}/{total}] {short:<12} ← {cat:<11}", end=" ", flush=True)
                r = query(model, q)
                results.append({**r, "model": model, "category": cat, "question": q[:80]})
                status = "✅" if r["ok"] else "❌"
                print(f"{status} {r.get('elapsed_s',0):.1f}s {r.get('len',0):>3d}字")

    # Score
    by_model = {}
    for r in results:
        m = r["model"]
        by_model.setdefault(m, {"ok": 0, "fail": 0, "time": 0, "chars": 0})
        by_model[m]["ok" if r["ok"] else "fail"] += 1
        by_model[m]["time"] += r["elapsed_s"]
        by_model[m]["chars"] += r.get("len", 0)

    print(f"\n{'='*60}")
    print(f"{'模型':<35} {'成功率':>6} {'延迟':>6} {'输出':>8}")
    print(f"{'-'*60}")
    for m, d in sorted(by_model.items(), key=lambda x: -x[1]["ok"]):
        s = d["ok"] + d["fail"]
        print(f"{m:<35} {d['ok']/s*100:>5.0f}% {d['time']/s:>5.1f}s {d['chars']:>7d}字")

    # Save
    out = Path(__file__).parent.parent.parent / "kb" / "L3_EMPIRICAL" / f"benchmark_full_{int(time.time())%100000:05d}.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    with open(out, 'w', encoding='utf-8') as f:
        json.dump({
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
            "models": MODELS,
            "questions_total": total,
            "results": results,
            "scores": {m: {"ok": d["ok"], "fail": d["fail"], "avg_latency": round(d["time"]/(d["ok"]+d["fail"]), 1), "total_chars": d["chars"]} for m, d in by_model.items()}
        }, f, ensure_ascii=False, indent=2)
    print(f"\n💾 结果: {out}")
    return results


if __name__ == "__main__":
    run_benchmark()
