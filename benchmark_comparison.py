"""
MSS-AI Simulation Framework — Performance Benchmark
Compares original vs Numba-accelerated versions
"""

import time
import numpy as np
from simulation_framework import SimulationEngine as OriginalEngine
from simulation_framework import SimulationConfig as OriginalConfig
from simulation_framework import SimulationType
from simulation_numba import SimulationEngine as NumbaEngine
from simulation_numba import SimulationConfig as NumbaConfig

def benchmark_percolation(engine_class, config_class, use_numba=True):
    """Benchmark percolation simulation"""
    engine = engine_class()
    configs = []
    for p in np.linspace(0.3, 0.7, 50):
        kwargs = {
            'sim_type': SimulationType.PERCOLATION,
            'grid_size': 200,
            'parameters': {'occupation_prob': p}
        }
        if hasattr(config_class, '__dataclass_fields__') and 'use_numba' in config_class.__dataclass_fields__:
            kwargs['use_numba'] = use_numba
        configs.append(config_class(**kwargs))
    start = time.time()
    results = engine.batch_run(configs)
    return time.time() - start

def benchmark_eta(engine_class, config_class, use_numba=True):
    """Benchmark ETA dynamics"""
    engine = engine_class()
    configs = []
    for _ in range(100):
        kwargs = {
            'sim_type': SimulationType.ETA_DYNAMICS,
            'max_iterations': 1000,
            'parameters': {'initial_tuning': 0.1, 'growth_rate': 0.05}
        }
        if hasattr(config_class, '__dataclass_fields__') and 'use_numba' in config_class.__dataclass_fields__:
            kwargs['use_numba'] = use_numba
        configs.append(config_class(**kwargs))
    start = time.time()
    results = engine.batch_run(configs)
    return time.time() - start

def benchmark_heat_tax(engine_class, config_class, use_numba=True):
    """Benchmark heat tax"""
    engine = engine_class()
    configs = []
    for _ in range(1000):
        kwargs = {
            'sim_type': SimulationType.HEAT_TAX,
            'parameters': {'gamma0': 0.3, 'max_cuts': 7}
        }
        if hasattr(config_class, '__dataclass_fields__') and 'use_numba' in config_class.__dataclass_fields__:
            kwargs['use_numba'] = use_numba
        configs.append(config_class(**kwargs))
    start = time.time()
    results = engine.batch_run(configs)
    return time.time() - start

def benchmark_resilience(engine_class, config_class, use_numba=True):
    """Benchmark resilience"""
    engine = engine_class()
    configs = []
    for _ in range(100):
        kwargs = {
            'sim_type': SimulationType.RESILIENCE,
            'max_iterations': 1000,
            'parameters': {'organization_size': 100, 'shock_prob': 0.1}
        }
        if hasattr(config_class, '__dataclass_fields__') and 'use_numba' in config_class.__dataclass_fields__:
            kwargs['use_numba'] = use_numba
        configs.append(config_class(**kwargs))
    start = time.time()
    results = engine.batch_run(configs)
    return time.time() - start

if __name__ == "__main__":
    print("=" * 70)
    print("MSS-AI Simulation Framework — Performance Benchmark")
    print("=" * 70)

    # Warm up Numba JIT compiler
    print("\n[Warming up Numba JIT compiler...]")
    from simulation_numba import SimulationType as NumbaSimulationType
    engine = NumbaEngine()
    config = NumbaConfig(
        sim_type=NumbaSimulationType.PERCOLATION,
        grid_size=50,
        parameters={'occupation_prob': 0.6},
        use_numba=True
    )
    engine.run(config)
    print("[Warm-up complete]")

    # Run benchmarks
    benchmarks = [
        ("Percolation (50 runs, 200x200)", benchmark_percolation),
        ("ETA Dynamics (100 runs, 1000 iter)", benchmark_eta),
        ("Heat Tax (1000 runs)", benchmark_heat_tax),
        ("Resilience (100 runs, 1000 iter)", benchmark_resilience),
    ]

    results = []
    for name, func in benchmarks:
        print(f"\n{name}:")

        # Original
        t_orig = func(OriginalEngine, OriginalConfig, use_numba=False)
        print(f"  Original: {t_orig:.3f}s")

        # Numba
        t_numba = func(NumbaEngine, NumbaConfig, use_numba=True)
        print(f"  Numba:    {t_numba:.3f}s")

        speedup = t_orig / t_numba if t_numba > 0 else float('inf')
        print(f"  Speedup:  {speedup:.2f}x")

        results.append((name, t_orig, t_numba, speedup))

    # Summary
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print(f"{'Benchmark':<40} {'Original':>10} {'Numba':>10} {'Speedup':>10}")
    print("-" * 70)
    for name, t_orig, t_numba, speedup in results:
        print(f"{name:<40} {t_orig:>10.3f}s {t_numba:>10.3f}s {speedup:>10.2f}x")

    total_orig = sum(r[1] for r in results)
    total_numba = sum(r[2] for r in results)
    total_speedup = total_orig / total_numba if total_numba > 0 else float('inf')
    print("-" * 70)
    print(f"{'TOTAL':<40} {total_orig:>10.3f}s {total_numba:>10.3f}s {total_speedup:>10.2f}x")
