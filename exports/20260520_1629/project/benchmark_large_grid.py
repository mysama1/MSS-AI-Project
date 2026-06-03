"""
MSS-AI Large Grid Benchmark — 500×500 and 1000×1000
Phase C: Scalability Testing
"""

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
print("MSS-AI Large Grid Benchmark — 500×500 and 1000×1000")
print("=" * 70)

results = []

# Test configurations: (grid_size, runs, description)
test_configs = [
    (500, 10, "500×500 (10 runs)"),
    (1000, 5, "1000×1000 (5 runs)"),
]

for grid_size, n_runs, desc in test_configs:
    print(f"\n{'='*70}")
    print(f"Percolation — {desc}")
    print(f"{'='*70}")
    
    # Original
    print("  Running original engine...")
    engine = OriginalEngine()
    configs = []
    for p in np.linspace(0.3, 0.7, n_runs):
        configs.append(OriginalConfig(
            sim_type=SimulationType.PERCOLATION,
            grid_size=grid_size,
            parameters={'occupation_prob': p}
        ))
    start = time.time()
    try:
        engine.batch_run(configs)
        t_orig = time.time() - start
        print(f"  Original: {t_orig:.3f}s")
    except Exception as e:
        print(f"  Original: FAILED ({e})")
        t_orig = None
    
    # Numba
    print("  Running Numba engine...")
    engine = NumbaEngine()
    configs = []
    for p in np.linspace(0.3, 0.7, n_runs):
        configs.append(NumbaConfig(
            sim_type=NumbaSimulationType.PERCOLATION,
            grid_size=grid_size,
            parameters={'occupation_prob': p},
            use_numba=True
        ))
    start = time.time()
    try:
        engine.batch_run(configs)
        t_numba = time.time() - start
        print(f"  Numba:    {t_numba:.3f}s")
    except Exception as e:
        print(f"  Numba:    FAILED ({e})")
        t_numba = None
    
    if t_orig and t_numba:
        speedup = t_orig / t_numba
        print(f"  Speedup:  {speedup:.2f}x")
        results.append((f"Percolation {grid_size}×{grid_size}", t_orig, t_numba, speedup))
    else:
        results.append((f"Percolation {grid_size}×{grid_size}", t_orig or 0, t_numba or 0, 0))

# Summary
print(f"\n{'='*70}")
print("SUMMARY")
print(f"{'='*70}")
print(f"{'Benchmark':<30} {'Original':>10} {'Numba':>10} {'Speedup':>10}")
print("-" * 70)
for name, t_orig, t_numba, speedup in results:
    if speedup > 0:
        print(f"{name:<30} {t_orig:>10.3f}s {t_numba:>10.3f}s {speedup:>10.2f}x")
    else:
        print(f"{name:<30} {'FAILED':>10} {'FAILED':>10} {'N/A':>10}")
