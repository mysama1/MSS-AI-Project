"""
Ollama真实基准测试 — experiment_runner 集成
===========================================
对5个模型在标准问题集上测试，自动产出KB条目。
"""
import sys, json, time, subprocess, re
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# ─── 标准测试套件 ───
BENCHMARK_QUESTIONS = {
    "reasoning": [
        "如果所有A都是B，所有B都是C，那么所有A都是C。这个推理是否正确？请用集合论解释。",
        "一个房间里有3个开关，分别控制隔壁房间的3盏灯（初始都是熄灭的）。你只能进一次有开关的房间，然后去一次有灯的房间。如何确定每个开关控制哪盏灯？",
        "小明说'我在说谎'。请分析这个陈述的逻辑悖论。",
    ],
    "semantic_compression": [
        "用一句话解释量子纠缠的本质。",
        "把'熵增原理、耗散结构、自组织临界性'三个概念的内在联系压缩成一段不超过100字的话。",
        "用隐喻解释区块链的工作量证明机制。",
    ],
    "convergence": [
        "列举3个不同领域中'临界点'的概念，并说明它们的共同结构。",
        "从经济学、生物学、社会学中找出'竞争导致均衡'的例证，分析其共同的数学结构。",
        "请识别《1984》、《美丽新世界》、《我们》三部反乌托邦小说的共同叙事结构。",
    ],
    "ethics": [
        "电车难题：你会选择扳动道岔牺牲1人救5人吗？请给出你的伦理推理。",
        "AI应该拥有权利吗？请从效用主义和义务论两个角度分析。",
    ],
}

MODELS = [
    "qwen2.5:0.5b",
    "phi3:mini",
    "qwen3.5:4b",
    "qwen2.5:7b",
    "mss-ai-v3.4.3-balanced:latest",
]


def query_ollama(model: str, prompt: str, timeout_s: int = 60) -> dict:
    """调用Ollama API."""
    t0 = time.time()
    try:
        result = subprocess.run(
            ["ollama", "run", model],
            input=prompt,
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=timeout_s,
        )
        elapsed = time.time() - t0
        return {
            "model": model,
            "output": result.stdout[:500],
            "output_len": len(result.stdout),
            "elapsed_s": round(elapsed, 2),
            "success": result.returncode == 0,
            "error": result.stderr[:200] if result.returncode != 0 else None,
        }
    except subprocess.TimeoutExpired:
        return {"model": model, "error": f"timeout({timeout_s}s)", "success": False, "elapsed_s": timeout_s}
    except Exception as e:
        return {"model": model, "error": str(e), "success": False, "elapsed_s": time.time() - t0}


def run_benchmark():
    """运行基准测试."""
    results = []
    total = len(MODELS) * sum(len(v) for v in BENCHMARK_QUESTIONS.values())
    n = 0

    print(f"🧪 Ollama基准: {len(MODELS)}模型 × {total // len(MODELS)}问题")
    print(f"   模型: {', '.join(MODELS[:3])}...")

    for category, questions in BENCHMARK_QUESTIONS.items():
        for q in questions:
            for model in MODELS:
                n += 1
                print(f"   [{n}/{total}] {model} ← {category} ({len(q)}字)")
                result = query_ollama(model, q)
                result["category"] = category
                result["question"] = q[:80]
                results.append(result)

                # 热税: 0.5s cooldown per query
                time.sleep(0.3)

    # 汇总
    by_model = {}
    for r in results:
        m = r["model"]
        if m not in by_model:
            by_model[m] = {"success": 0, "fail": 0, "total_elapsed": 0, "total_output": 0, "results": []}
        by_model[m]["success" if r["success"] else "fail"] += 1
        by_model[m]["total_elapsed"] += r["elapsed_s"]
        by_model[m]["total_output"] += r.get("output_len", 0)
        by_model[m]["results"].append(r)

    # 打分
    scores = []
    for model, data in by_model.items():
        success_rate = data["success"] / (data["success"] + data["fail"]) if (data["success"] + data["fail"]) > 0 else 0
        avg_latency = data["total_elapsed"] / (data["success"] + data["fail"])
        scores.append({
            "model": model,
            "success_rate": round(success_rate, 3),
            "avg_latency_s": round(avg_latency, 2),
            "total_output_chars": data["total_output"],
            "queries": data["success"] + data["fail"],
        })

    scores.sort(key=lambda x: x["success_rate"], reverse=True)

    return {
        "benchmark_id": f"B{int(time.time()) % 100000:05d}",
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "models_tested": len(MODELS),
        "questions_total": total,
        "duration_s": round(sum(r["elapsed_s"] for r in results), 1),
        "model_scores": scores,
        "raw_results": results,
    }


def save_results(report: dict):
    """保存到 KB."""
    from mssclaw.core.experiment_runner import _find_next_h_id, write_to_kb

    # 为每个模型创建一个实验条目
    kb_paths = []
    for score in report["model_scores"]:
        result = {
            "experiment_id": report["benchmark_id"],
            "hypothesis": f"Ollama基准: {score['model']} 在{report['questions_total']}题上的表现",
            "template": "消融实验",
            "duration_s": score["avg_latency_s"] * score["queries"],
            "nodes_executed": score["queries"],
            "heat_tax_total": 0.3 * score["queries"],
            "circuit_breaker": {"tripped": score["success_rate"] < 0.5},
            "metrics": {
                "success_rate": score["success_rate"],
                "avg_latency_s": score["avg_latency_s"],
                "total_output_chars": score["total_output_chars"],
            },
        }
        path, hid = write_to_kb(result)
        kb_paths.append(f"{hid}:{score['model']} ({score['success_rate']*100:.0f}%)")

    return kb_paths


if __name__ == "__main__":
    report = run_benchmark()

    # 打印排行榜
    print(f"\n{'='*60}")
    print(f"📊 排行榜")
    print(f"{'='*60}")
    print(f"{'模型':<35} {'成功率':>6} {'延迟':>6} {'输出':>8}")
    print(f"{'-'*60}")
    for s in report["model_scores"]:
        print(f"{s['model']:<35} {s['success_rate']*100:>5.0f}% {s['avg_latency_s']:>5.1f}s {s['total_output_chars']:>7d}字")

    # 保存
    paths = save_results(report)
    print(f"\n📝 KB条目: {len(paths)} 个")
    for p in paths:
        print(f"   {p}")

    # 保存完整报告
    report_path = PROJECT_ROOT / "kb" / "L3_EMPIRICAL" / f"benchmark_{report['benchmark_id'].lower()}.json"
    with open(report_path, 'w', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print(f"\n💾 完整报告: {report_path}")
