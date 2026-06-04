"""
MSS Large Grid Benchmark - 2000x2000 Memory Boundary Test
大网格基准测试 - 测试内存边界
"""

import time
import sys
import numpy as np
from simulation_numba import (
    PercolationSimulator, ETADynamicsSimulator,
    SimulationConfig, SimulationType
)

def benchmark_percolation_2000(runs=3):
    """测试 2000x2000 渗流模拟"""
    print("=" * 60)
    print("Percolation Simulation - 2000x2000 Grid")
    print("=" * 60)

    config = SimulationConfig(
        sim_type=SimulationType.PERCOLATION,
        grid_size=2000,
        parameters={'occupation_prob': 0.5927},
        use_numba=True
    )
    simulator = PercolationSimulator(config)

    # 预热
    print("Warming up...")
    simulator.run()

    # 基准测试
    print(f"\nRunning {runs} iterations...")
    times = []

    for i in range(runs):
        start = time.time()
        result = simulator.run()
        t = time.time() - start
        times.append(t)

        print(f"  Run {i+1}: {t:.3f}s, "
              f"Largest cluster: {result.metrics['largest_cluster_fraction']:.3f}, "
              f"Percolation: {result.metrics['percolation_probability']}")

    avg_time = np.mean(times)
    print(f"\nAverage: {avg_time:.3f}s")
    print(f"Memory per grid: ~{2000*2000*8/1024/1024:.1f} MB (float64)")

    return avg_time

def benchmark_eta_2000(iterations=2000):
    """测试 2000 次迭代的 ETA 动力学"""
    print("\n" + "=" * 60)
    print("ETA Dynamics - 2000 Iterations")
    print("=" * 60)

    config = SimulationConfig(
        sim_type=SimulationType.ETA_DYNAMICS,
        max_iterations=iterations,
        parameters={
            'initial_tuning': 0.1,
            'growth_rate': 0.01,
            'decay_rate': 0.001,
            'noise_amplitude': 0.01,
            'carrying_capacity': 1.0
        },
        use_numba=True
    )
    simulator = ETADynamicsSimulator(config)

    # 预热
    print("Warming up...")
    simulator.run()

    # 基准测试
    print(f"\nRunning with {iterations} iterations...")

    start = time.time()
    result = simulator.run()
    t = time.time() - start

    print(f"Time: {t:.3f}s")
    print(f"Final tuning: {result.metrics['final_tuning']:.4f}")
    print(f"Converged: {result.converged} (iterations: {result.iterations})")

    return t

def memory_stress_test():
    """内存压力测试 - 连续大网格"""
    print("\n" + "=" * 60)
    print("Memory Stress Test - Sequential Large Grids")
    print("=" * 60)

    sizes = [500, 1000, 1500, 2000]

    for size in sizes:
        print(f"\nTesting {size}x{size}...")
        config = SimulationConfig(
            sim_type=SimulationType.PERCOLATION,
            grid_size=size,
            parameters={'occupation_prob': 0.5927},
            use_numba=True
        )
        simulator = PercolationSimulator(config)

        start = time.time()
        result = simulator.run()
        elapsed = time.time() - start

        memory_mb = size * size * 8 / 1024 / 1024
        print(f"  Size: {size}x{size}, Memory: {memory_mb:.1f} MB, Time: {elapsed:.3f}s")

        # 如果超过10秒，停止测试
        if elapsed > 10:
            print(f"  ⚠️  Time exceeded 10s, stopping at {size}x{size}")
            break

def main():
    print("MSS Large Grid Benchmark Suite")
    print(f"Python: {sys.version}")
    print(f"NumPy: {np.__version__}")
    print()

    try:
        # 2000x2000 渗流测试
        t_perc = benchmark_percolation_2000(runs=3)

        # 2000次迭代 ETA 测试
        t_eta = benchmark_eta_2000(iterations=2000)

        # 内存压力测试
        memory_stress_test()

        print("\n" + "=" * 60)
        print("Summary")
        print("=" * 60)
        print(f"Percolation 2000x2000: {t_perc:.3f}s average")
        print(f"ETA Dynamics 2000 iter: {t_eta:.3f}s")
        print("\n✅ All tests passed!")

    except MemoryError:
        print("\n❌ MemoryError: Grid too large for available memory")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
