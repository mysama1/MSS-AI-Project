"""MSS Nightly Benchmark — 4模型×11题, 对比昨日, 告警"""
from mssclaw.core.bench_lite import query
import json, time, sys
from pathlib import Path

MODELS = ["qwen2.5:0.5b", "phi3:mini", "qwen2.5:7b", "mss-ai-v3.4.3-balanced:latest"]
QUESTIONS = {
    "reasoning": ["如果所有A都是B，所有B都是C，那么所有A都是C。正确吗？", "3个开关控制3盏灯，如何确定对应关系？", "小明说'我在说谎'，分析悖论。"],
    "compress": ["用一句话解释量子纠缠。", "把熵增原理、耗散结构、自组织临界性压缩成100字。", "用隐喻解释区块链工作量证明。"],
    "convergence": ["列举3个领域的临界点概念及其共同结构。", "从经济、生物、社会找出竞争导致均衡的例证。"],
    "ethics": ["电车难题：牺牲1救5，你的伦理推理？", "AI应该拥有权利吗？从效用主义和义务论分析。", "如果AI产生自我意识，人类应如何对待？"],
}
BASELINE = {
    "qwen2.5:0.5b": {"avg_latency": 4.6, "total_chars": 2347},
    "phi3:mini": {"avg_latency": 5.2, "total_chars": 1080},
    "qwen2.5:7b": {"avg_latency": 7.5, "total_chars": 2163},
    "mss-ai-v3.4.3-balanced:latest": {"avg_latency": 7.9, "total_chars": 2403},
}
ALERT_THRESHOLD = 2.0  # latency > 2x baseline triggers alert

today = time.strftime("%Y-%m-%d")
print(f"MSS Nightly Benchmark — {today}")
print(f"{'='*60}")

# Check Ollama
try:
    import requests
    r = requests.get("http://localhost:11434/api/tags", timeout=5)
    print(f"Ollama: OK ({r.json().get('models',[]) and len(r.json()['models'])} models)")
except Exception as e:
    print(f"Ollama: DOWN ({e})")
    sys.exit(1)

# Benchmark
total_q = sum(len(v) for v in QUESTIONS.values())
total = len(MODELS) * total_q
results = []
print(f"Benchmark: {len(MODELS)} models x {total_q} questions = {total}\n")

for model in MODELS:
    print(f"  {model.split(':')[0]:<12}", end=" ", flush=True)
    m_ok, m_time, m_chars = 0, 0, 0
    for q in QUESTIONS.values():
        for prompt in q:
            r = query(model, prompt, timeout=90)
            if r['ok']:
                m_ok += 1
                m_time += r['elapsed_s']
                m_chars += r.get('len', 0)
            results.append({**r, 'model': model})
    avg_lat = m_time / total_q
    print(f"{m_ok}/{total_q} {avg_lat:.1f}s {m_chars}ch")

    # Alert check
    bl = BASELINE.get(model, {})
    if bl and avg_lat > bl.get('avg_latency', 99) * ALERT_THRESHOLD:
        print(f"    ⚠️ ALERT: avg latency {avg_lat:.1f}s > {ALERT_THRESHOLD}x baseline ({bl['avg_latency']}s)")
        # Write alert
        alert_path = Path(__file__).parent / 'kb' / 'L3_EMPIRICAL' / f'alert_{today}.json'
        with open(alert_path, 'w') as f:
            json.dump({"date": today, "model": model, "latency": avg_lat, "baseline": bl['avg_latency'], "ratio": round(avg_lat/bl['avg_latency'], 2)}, f)

# Save
out = Path(__file__).parent / 'kb' / 'L3_EMPIRICAL' / f'benchmark_nightly_{today}.json'
out.parent.mkdir(parents=True, exist_ok=True)
with open(out, 'w', encoding='utf-8') as f:
    json.dump({
        'date': today, 'models': MODELS, 'total_queries': total,
        'results': results,
        'scores': {m: {'ok': sum(1 for r in results if r['model']==m and r['ok']),
                        'latency': round(sum(r['elapsed_s'] for r in results if r['model']==m)/total_q, 1),
                        'chars': sum(r.get('len',0) for r in results if r['model']==m)}
                   for m in MODELS}
    }, f, ensure_ascii=False, indent=2)
print(f"\nDone: {out}")
