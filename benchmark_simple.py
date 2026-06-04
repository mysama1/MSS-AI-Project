"""Simple benchmark runner"""
import sys
sys.path.insert(0, r'C:\MSS-AI-Project')

from simulation_framework import SimulationEngine as OriginalEngine
from simulation_framework import SimulationConfig as OriginalConfig
from simulation_framework import SimulationType
from simulation_numba import SimulationEngine as NumbaEngine
from simulation_numba import SimulationConfig as NumbaConfig
from simulation_numba import SimulationType as NumbaSimulationType
import time
import numpy as np

print("=" * 70)
print("MSS-AI Simulation Framework — Performance Benchmark")
print("=" * 70)

# Warm up Numba
print("\n[Warming up Numba JIT compiler...]")
engine = NumbaEngine()
config = NumbaConfig(
    sim_type=NumbaSimulationType.PERCOLATION,
    grid_size=50,
    parameters={'occupation_prob': 0.6},
    use_numba=True
)
engine.run(config)
print("[Warm-up complete]")

results = []

# Benchmark percolation
print("\nPercolation (50 runs, 200x200):")

# Original
engine = OriginalEngine()
configs = []
for p in np.linspace(0.3, 0.7, 50):
    configs.append(OriginalConfig(
        sim_type=SimulationType.PERCOLATION,
        grid_size=200,
        parameters={'occupation_prob': p}
    ))
start = time.time()
engine.batch_run(configs)
t_orig = time.time() - start
print(f"  Original: {t_orig:.3f}s")

# Numba
engine = NumbaEngine()
configs = []
for p in np.linspace(0.3, 0.7, 50):
    configs.append(NumbaConfig(
        sim_type=NumbaSimulationType.PERCOLATION,
        grid_size=200,
        parameters={'occupation_prob': p},
        use_numba=True
    ))
start = time.time()
engine.batch_run(configs)
t_numba = time.time() - start
print(f"  Numba:    {t_numba:.3f}s")
speedup = t_orig / t_numba if t_numba > 0 else float('inf')
print(f"  Speedup:  {speedup:.2f}x")
results.append(("Percolation", t_orig, t_numba, speedup))

# Benchmark ETA
print("\nETA Dynamics (100 runs, 1000 iter):")

# Original
engine = OriginalEngine()
configs = []
for _ in range(100):
    configs.append(OriginalConfig(
        sim_type=SimulationType.ETA_DYNAMICS,
        max_iterations=1000,
        parameters={'initial_tuning': 0.1, 'growth_rate': 0.05}
    ))
start = time.time()
engine.batch_run(configs)
t_orig = time.time() - start
print(f"  Original: {t_orig:.3f}s")

# Numba
engine = NumbaEngine()
configs = []
for _ in range(100):
    configs.append(NumbaConfig(
        sim_type=NumbaSimulationType.ETA_DYNAMICS,
        max_iterations=1000,
        parameters={'initial_tuning': 0.1, 'growth_rate': 0.05},
        use_numba=True
    ))
start = time.time()
engine.batch_run(configs)
t_numba = time.time() - start
print(f"  Numba:    {t_numba:.3f}s")
speedup = t_orig / t_numba if t_numba > 0 else float('inf')
print(f"  Speedup:  {speedup:.2f}x")
results.append(("ETA Dynamics", t_orig, t_numba, speedup))

# Benchmark ETA (single long run to amortize JIT overhead)
print("\nETA Dynamics (1 run, 100000 iter) — JIT overhead amortized:")

# Original
engine = OriginalEngine()
config = OriginalConfig(
    sim_type=SimulationType.ETA_DYNAMICS,
    max_iterations=100000,
    parameters={'initial_tuning': 0.1, 'growth_rate': 0.05}
)
start = time.time()
engine.run(config)
t_orig = time.time() - start
print(f"  Original: {t_orig:.3f}s")

# Numba
engine = NumbaEngine()
config = NumbaConfig(
    sim_type=NumbaSimulationType.ETA_DYNAMICS,
    max_iterations=100000,
    parameters={'initial_tuning': 0.1, 'growth_rate': 0.05},
    use_numba=True
)
start = time.time()
engine.run(config)
t_numba = time.time() - start
print(f"  Numba:    {t_numba:.3f}s")
speedup = t_orig / t_numba if t_numba > 0 else float('inf')
print(f"  Speedup:  {speedup:.2f}x")

# Benchmark Heat Tax
print("\nHeat Tax (1000 runs):")

# Original
engine = OriginalEngine()
configs = []
for _ in range(1000):
    configs.append(OriginalConfig(
        sim_type=SimulationType.HEAT_TAX,
        parameters={'gamma0': 0.3, 'max_cuts': 7}
    ))
start = time.time()
engine.batch_run(configs)
t_orig = time.time() - start
print(f"  Original: {t_orig:.3f}s")

# Numba
engine = NumbaEngine()
configs = []
for _ in range(1000):
    configs.append(NumbaConfig(
        sim_type=NumbaSimulationType.HEAT_TAX,
        parameters={'gamma0': 0.3, 'max_cuts': 7},
        use_numba=True
    ))
start = time.time()
engine.batch_run(configs)
t_numba = time.time() - start
print(f"  Numba:    {t_numba:.3f}s")
speedup = t_orig / t_numba if t_numba > 0 else float('inf')
print(f"  Speedup:  {speedup:.2f}x")
results.append(("Heat Tax", t_orig, t_numba, speedup))

# Benchmark Resilience
print("\nResilience (100 runs, 1000 iter):")

# Original
engine = OriginalEngine()
configs = []
for _ in range(100):
    configs.append(OriginalConfig(
        sim_type=SimulationType.RESILIENCE,
        max_iterations=1000,
        parameters={'organization_size': 100, 'shock_prob': 0.1}
    ))
start = time.time()
engine.batch_run(configs)
t_orig = time.time() - start
print(f"  Original: {t_orig:.3f}s")

# Numba
engine = NumbaEngine()
configs = []
for _ in range(100):
    configs.append(NumbaConfig(
        sim_type=NumbaSimulationType.RESILIENCE,
        max_iterations=1000,
        parameters={'organization_size': 100, 'shock_prob': 0.1},
        use_numba=True
    ))
start = time.time()
engine.batch_run(configs)
t_numba = time.time() - start
print(f"  Numba:    {t_numba:.3f}s")
speedup = t_orig / t_numba if t_numba > 0 else float('inf')
print(f"  Speedup:  {speedup:.2f}x")
results.append(("Resilience", t_orig, t_numba, speedup))

# Benchmark Resilience (single long run)
print("\nResilience (1 run, 100000 iter) — JIT overhead amortized:")

# Original
engine = OriginalEngine()
config = OriginalConfig(
    sim_type=SimulationType.RESILIENCE,
    max_iterations=100000,
    parameters={'organization_size': 100, 'shock_prob': 0.1}
)
start = time.time()
engine.run(config)
t_orig = time.time() - start
print(f"  Original: {t_orig:.3f}s")

# Numba
engine = NumbaEngine()
config = NumbaConfig(
    sim_type=NumbaSimulationType.RESILIENCE,
    max_iterations=100000,
    parameters={'organization_size': 100, 'shock_prob': 0.1},
    use_numba=True
)
start = time.time()
engine.run(config)
t_numba = time.time() - start
print(f"  Numba:    {t_numba:.3f}s")
speedup = t_orig / t_numba if t_numba > 0 else float('inf')
print(f"  Speedup:  {speedup:.2f}x")

# Summary
print("\n" + "=" * 70)
print("SUMMARY")
print("=" * 70)
print(f"{'Benchmark':<30} {'Original':>12} {'Numba':>12} {'Speedup':>10}")
print("-" * 70)
total_orig = 0
total_numba = 0
for name, t_orig, t_numba, speedup in results:
    print(f"{name:<30} {t_orig:>11.3f}s {t_numba:>11.3f}s {speedup:>9.2f}x")
    total_orig += t_orig
    total_numba += t_numba
print("-" * 70)
total_speedup = total_orig / total_numba if total_numba > 0 else float('inf')
print(f"{'TOTAL':<30} {total_orig:>11.3f}s {total_numba:>11.3f}s {total_speedup:>9.2f}x")
