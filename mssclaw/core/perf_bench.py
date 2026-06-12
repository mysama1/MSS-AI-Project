"""
DEEP-010: MSSclaw Performance Baseline

测量:
  1. 模块导入时间 (101 py files)
  2. SwarmBus 路由延迟 (1/10/100 agents)
  3. HeatTax charge 开销
  4. GuardianEngine scan 延迟
  5. Delta tick 开销
  6. AuditAgent 审计速度 (per KB)
  7. 总回归时间

输出: perf_baseline.json (版本化, 可对比)
"""
from __future__ import annotations

import json
import os
import sys
import time
import statistics

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def timeit(name: str, fn, *args, iterations: int = 100, **kwargs) -> dict:
    """Micro-benchmark a function with warmup."""
    # Warmup
    for _ in range(5):
        fn(*args, **kwargs)

    times = []
    for _ in range(iterations):
        t0 = time.perf_counter()
        fn(*args, **kwargs)
        times.append(time.perf_counter() - t0)

    return {
        "name": name,
        "iterations": iterations,
        "mean_us": round(statistics.mean(times) * 1_000_000, 1),
        "median_us": round(statistics.median(times) * 1_000_000, 1),
        "min_us": round(min(times) * 1_000_000, 1),
        "max_us": round(max(times) * 1_000_000, 1),
        "p99_us": round(sorted(times)[int(iterations * 0.99)] * 1_000_000, 1),
    }


def bench_swarmbus():
    """SwarmBus routing latency — simplified."""
    from mssclaw.swarm.swarm import SwarmBus
    from mssclaw.swarm.protocol import Message, MessageHeader, MessageType

    results = []

    for n_agents in [1, 10, 50]:
        bus = SwarmBus()

        # Bench message creation + sign
        def do_msg():
            h = MessageHeader(msg_type=MessageType.HEARTBEAT, sender="a0", receiver="a1")
            m = Message(header=h, payload={"p": "ping"})
            m.sign()

        results.append(timeit(f"Message.create+sign", do_msg))
    return results


def bench_heattax():
    """HeatTax charge + reserve + release."""
    from mssclaw.core.heat_tax import HeatTaxBudget, HeatTaxLevel

    results = []

    # Charge
    ht = HeatTaxBudget()
    results.append(timeit("HeatTax.charge(L1,25)", ht.charge, HeatTaxLevel.L1_LOGICAL, 25))

    # Reserve + release cycle
    def reserve_release():
        ht.reserve("task-1", 50)
        ht.release("task-1")

    results.append(timeit("HeatTax.reserve+release", reserve_release))

    # Snapshot
    results.append(timeit("HeatTax.snapshot()", ht.snapshot))
    return results


def bench_guardian():
    """GuardianEngine scan overhead."""
    from mssclaw.core.guardian_engine import GuardianEngine

    ge = GuardianEngine()

    # Short text scan
    def scan_short():
        ge.scan("def add(a, b): return a + b")

    results = [timeit("Guardian.scan(40B)", scan_short)]

    # Medium text scan
    medium = "def process_data(input_data, options=None, callback=None):\n" * 20
    def scan_medium():
        ge.scan(medium)

    results.append(timeit(f"Guardian.scan({len(medium)}B)", scan_medium, iterations=50))
    return results


def bench_delta():
    """Delta tick overhead."""
    from mssclaw.core.delta import DeltaProtocol

    dp = DeltaProtocol()

    def do_tick():
        dp.tick("t1", 0.5, 0.5)

    results = [timeit("Delta.tick(array)", do_tick)]

    # populate data for health
    for i in range(20):
        dp.tick(f"t{i}", 0.1, 0.1)

    # health check
    def do_health():
        dp.health()

    results.append(timeit("Delta.health(21pts)", do_health))
    return results


def bench_audit():
    """AuditAgent scan speed per KB."""
    from mssclaw.agents.audit import AuditAgent
    from mssclaw.swarm.swarm import SwarmBus

    bus = SwarmBus()
    agent = AuditAgent("audit-bench", bus)

    # Small file
    small = "def add(a, b): return a + b\n" * 50  # ~1.3KB
    def scan_small():
        agent.audit_text(small, "small.py")

    results = [timeit(f"Audit.scan({len(small)}B)", scan_small, iterations=20)]

    # Large file
    large = small * 10  # ~13KB
    def scan_large():
        agent.audit_text(large, "large.py")

    results.append(timeit(f"Audit.scan({len(large)}B)", scan_large, iterations=10))

    large2 = small * 50  # ~65KB
    def scan_large2():
        agent.audit_text(large2, "large2.py")

    results.append(timeit(f"Audit.scan({len(large2)}B)", scan_large2, iterations=5))
    return results


def bench_imports():
    """Full module import time."""
    modules = [
        "mssclaw.core.heat_tax",
        "mssclaw.core.delta",
        "mssclaw.core.guardian_engine",
        "mssclaw.core.meaning_temperature",
        "mssclaw.core.tsp_bridge",
        "mssclaw.swarm.swarm",
        "mssclaw.swarm.protocol",
        "mssclaw.agents.audit",
        "mssclaw.agents.code",
        "mssclaw.agents.plan",
        "mssclaw.llm.ollama",
        "mssclaw.llm.providers",
    ]
    import importlib
    results = []
    for mod in modules:
        t0 = time.perf_counter()
        importlib.import_module(mod)
        elapsed = (time.perf_counter() - t0) * 1_000_000
        results.append({"module": mod, "import_us": round(elapsed, 1)})

    # Total
    t0 = time.perf_counter()
    for mod in modules:
        importlib.import_module(mod)
    total_ms = (time.perf_counter() - t0) * 1000

    return results, total_ms


def main():
    print("=== MSSclaw Performance Baseline ===\n")
    all_results = {}

    # 1. Imports
    print("[1/5] Module imports...")
    import_results, total_import = bench_imports()
    all_results["imports"] = import_results
    all_results["import_total_ms"] = round(total_import, 1)
    print(f"      12 modules in {total_import:.0f}ms")

    # 2. SwarmBus
    print("[2/5] SwarmBus routing...")
    swarm_results = bench_swarmbus()
    all_results["swarmbus"] = swarm_results
    for r in swarm_results:
        print(f"      {r['name']}: {r['mean_us']:.0f}us")

    # 3. HeatTax
    print("[3/5] HeatTax operations...")
    ht_results = bench_heattax()
    all_results["heattax"] = ht_results
    for r in ht_results:
        print(f"      {r['name']}: {r['mean_us']:.0f}us")

    # 4. Guardian + Delta
    print("[4/5] Guardian + Delta...")
    ge_results = bench_guardian()
    dp_results = bench_delta()
    all_results["guardian"] = ge_results
    all_results["delta"] = dp_results
    for r in ge_results + dp_results:
        print(f"      {r['name']}: {r['mean_us']:.0f}us")

    # 5. AuditAgent
    print("[5/5] AuditAgent scanning...")
    audit_results = bench_audit()
    all_results["audit"] = audit_results
    for r in audit_results:
        kb = int(r['name'].split('(')[1].replace('B)',''))
        throughput = kb / (r['mean_us'] / 1_000_000)  # KB/s
        print(f"      {r['name']}: {r['mean_us']:.0f}us ({throughput/1000:.0f}KB/s)")

    # Summary
    print(f"\n=== BASELINE SUMMARY ===")
    print(f"  Import (x12):  {total_import:.0f}ms")
    print(f"  SwarmBus(50A): {swarm_results[-1]['mean_us']:.0f}us")
    print(f"  HeatTax avg:   {statistics.mean([r['mean_us'] for r in ht_results]):.0f}us")
    print(f"  Guardian(min): {ge_results[0]['mean_us']:.0f}us")
    print(f"  Delta(tick):   {dp_results[0]['mean_us']:.0f}us")
    print(f"  Audit(1.3KB):  {audit_results[0]['mean_us']:.0f}us")

    # Write baseline
    outpath = os.path.join(os.path.dirname(__file__), "..", "data", "perf_baseline.json")
    os.makedirs(os.path.dirname(outpath), exist_ok=True)
    all_results["timestamp"] = time.strftime("%Y-%m-%dT%H:%M:%S")
    all_results["version"] = "v1.0"
    with open(outpath, "w") as f:
        json.dump(all_results, f, indent=2)
    print(f"\n  Baseline saved: {outpath}")


if __name__ == "__main__":
    main()
