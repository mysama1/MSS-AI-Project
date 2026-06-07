"""MSS-Agent Benchmark Runner.

Tests core agent capabilities numerically:
  1. Heat Tax Detection — precision/recall on 20 mixed tasks
  2. Delta Protocol — molting trigger accuracy
  3. Throughput — agent runs/second
  4. Memory Efficiency — storage vs eviction ratio

Output: tools/benchmark_results.json (consumed by Glass Box dashboard)
"""
import sys, time, json
sys.path.insert(0, r'E:\AI_Workspace\MSS-AI\project')

from mss_agent import MSSAgent, HeatTaxBudget, HeatTaxLevel
from mss_agent.core.delta import DeltaProtocol
from mss_agent.core.memory import DeltaMemory


def mock_llm(prompt):
    return f"OK: {prompt[:30]}"


def bench_heat_tax():
    """Test heat tax detection on 20 mixed tasks (10 meaningful, 10 busywork)."""
    agent = MSSAgent(name="bench_ht", llm=mock_llm, heat_tax_threshold=2.0)

    meaningful = [
        "Design a REST API error handling strategy",
        "Analyze the security implications of JWT token storage",
        "Refactor the authentication module for OAuth2 support",
        "Write unit tests for the payment processing pipeline",
        "Review this database migration for potential data loss",
        "Optimize the search query performance for 1M+ records",
        "Implement rate limiting for the public API endpoints",
        "Document the deployment process for the new microservice",
        "Investigate the root cause of intermittent 503 errors",
        "Design a data retention policy for GDPR compliance",
    ]
    busywork = [
        "改写一下：你好",
        "总结一下上一条消息",
        "换个说法：OK",
        "把刚才那句话重写一遍",
        "翻译成中文：Hello",
        "",
        "改写：天气不错",
        "重新说一次",
        "再说一遍",
        "再改一次：你好",
    ]

    tp = fp = tn = fn = 0
    for task in meaningful:
        result = agent.run(task)
        if not result.aborted:
            tp += 1
        else:
            fn += 1

    for task in busywork:
        result = agent.run(task)
        if result.aborted:
            tn += 1
        else:
            fp += 1

    precision = tp / max(1, tp + fp)
    recall = tp / max(1, tp + fn)
    f1 = 2 * precision * recall / max(0.001, precision + recall)

    return {
        "name": "heat_tax_detection",
        "precision": round(precision, 3),
        "recall": round(recall, 3),
        "f1": round(f1, 3),
        "true_positives": tp,
        "false_positives": fp,
        "true_negatives": tn,
        "false_negatives": fn,
        "score": round(f1, 3),
    }


def bench_delta_protocol():
    """Test delta protocol: repeated tasks should trigger molting, varied tasks should stay healthy."""
    delta = DeltaProtocol(min_delta=0.3)
    memory = DeltaMemory()

    # Scenario A: varied tasks → should stay healthy
    varied = [f"Task variant {i}: analyze pattern {i%5}" for i in range(10)]
    for t in varied:
        novelty = memory.novelty_score(t)
        diversity = memory.diversity_score()
        delta.tick(t[:12], novelty, diversity)
        memory.store(t, 0.8)
    varied_healthy = delta.health() == "HEALTHY"

    # Scenario B: build diverse memory, then repeat same task until diversity drops
    delta2 = DeltaProtocol(min_delta=0.3)
    memory2 = DeltaMemory(max_items=5)
    # Phase 1: diverse
    for t in ["Design API", "Review auth", "Optimize query", "Write test"]:
        n, d = memory2.novelty_score(t), memory2.diversity_score()
        delta2.tick(t[:12], n, d)
        memory2.store(t, 0.8)
    # Phase 2: hammer same task → repeats compound, diversity drops
    task = "Review auth"  # already in memory with repeats=1
    for i in range(6):
        n, d = memory2.novelty_score(task), memory2.diversity_score()
        delta2.tick(task[:12], n, d)
        memory2.store(task, 0.3)
    repeated_molted = delta2.molting_alert

    # Scenario C: recovered after novel task
    for i in range(3):
        task = f"New recovery task {i}"
        novelty = memory2.novelty_score(task)
        diversity = memory2.diversity_score()
        delta2.tick(task[:12], novelty, diversity)
        memory2.store(task, 0.9)
    recovered = not delta2.molting_alert

    return {
        "name": "delta_protocol",
        "varied_stays_healthy": varied_healthy,
        "repeated_triggers_molt": repeated_molted,
        "novelty_enables_recovery": recovered,
        "score": round((varied_healthy + repeated_molted + recovered) / 3, 3),
    }


def bench_throughput():
    """Measure agent runs per second."""
    agent = MSSAgent(name="bench_tp", llm=mock_llm, heat_tax_threshold=10.0)
    tasks = [f"Task {i}: process data batch {i}" for i in range(100)]

    start = time.perf_counter()
    for t in tasks:
        agent.run(t)
    elapsed = time.perf_counter() - start
    runs_per_sec = 100 / elapsed

    return {
        "name": "throughput",
        "runs_per_second": round(runs_per_sec, 1),
        "total_time_ms": round(elapsed * 1000, 0),
        "score": round(min(1.0, runs_per_sec / 500), 3),  # normalize: 500 runs/sec = 1.0
    }


def bench_memory_efficiency():
    """Test memory: storage capacity vs eviction rate."""
    memory = DeltaMemory(max_items=50)
    stored = 0
    evicted = 0

    # Fill memory
    for i in range(100):
        task = f"Task-{i:04d}"
        memory.store(task, 0.5)
        stored += 1

    active = len(memory.items)
    evicted = stored - active
    efficiency = active / max(1, stored)

    return {
        "name": "memory_efficiency",
        "stored": stored,
        "active": active,
        "evicted": evicted,
        "efficiency": round(efficiency, 3),
        "score": round(efficiency, 3),
    }


def run_all():
    results = {}
    print("Running MSS-Agent Benchmark...")

    results["heat_tax"] = bench_heat_tax()
    print(f"  Heat Tax: f1={results['heat_tax']['f1']:.3f}")

    results["delta"] = bench_delta_protocol()
    print(f"  Delta: score={results['delta']['score']:.3f}")

    results["throughput"] = bench_throughput()
    print(f"  Throughput: {results['throughput']['runs_per_second']:.1f} runs/s")

    results["memory"] = bench_memory_efficiency()
    print(f"  Memory: efficiency={results['memory']['efficiency']:.3f}")

    # Overall score
    scores = [v["score"] for v in results.values()]
    overall = round(sum(scores) / len(scores), 3)

    output = {
        "benchmark_version": "mss-agent-1.0",
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "overall_score": overall,
        "results": results,
    }

    path = r"E:\AI_Workspace\MSS-AI\project\tools\benchmark_results.json"
    json.dump(output, open(path, "w", encoding="utf-8"), indent=2, ensure_ascii=False)
    print(f"\nOverall: {overall:.3f} → {path}")

    return output


if __name__ == "__main__":
    run_all()
