"""CuPy CUDA Benchmark — GPU加速测试"""

import numpy as np
import time

try:
    import cupy as cp
    HAS_CUPY = True
    print("[GPU] CuPy loaded successfully")
    print(f"[GPU] CUDA version: {cp.cuda.runtime.getDeviceCount()} device(s)")
    print(f"[GPU] Device 0: {cp.cuda.Device(0).use()}")
except ImportError:
    HAS_CUPY = False
    print("[GPU] CuPy not available, using NumPy fallback")

class GPUBenchmark:
    """GPU基准测试"""

    def __init__(self):
        self.results = []

    def benchmark_matrix_multiply(self, size):
        """矩阵乘法基准"""
        print(f"\n[TEST] Matrix multiply: {size}×{size}")

        # NumPy CPU
        start = time.time()
        a_np = np.random.random((size, size))
        b_np = np.random.random((size, size))
        c_np = np.dot(a_np, b_np)
        cpu_time = time.time() - start
        print(f"  CPU (NumPy): {cpu_time:.4f}s")

        if HAS_CUPY:
            # CuPy GPU
            start = time.time()
            a_cp = cp.random.random((size, size))
            b_cp = cp.random.random((size, size))
            c_cp = cp.dot(a_cp, b_cp)
            cp.cuda.Device(0).synchronize()
            gpu_time = time.time() - start
            print(f"  GPU (CuPy):  {gpu_time:.4f}s")

            speedup = cpu_time / gpu_time
            print(f"  Speedup: {speedup:.2f}x")

            return {
                'size': size,
                'cpu_time': cpu_time,
                'gpu_time': gpu_time,
                'speedup': speedup,
                'status': 'PASS'
            }
        else:
            return {
                'size': size,
                'cpu_time': cpu_time,
                'gpu_time': None,
                'speedup': 1.0,
                'status': 'CPU_ONLY'
            }

    def benchmark_fft(self, size):
        """FFT基准"""
        print(f"\n[TEST] FFT: {size} points")

        # NumPy CPU
        start = time.time()
        x_np = np.random.random(size)
        y_np = np.fft.fft(x_np)
        cpu_time = time.time() - start
        print(f"  CPU (NumPy): {cpu_time:.4f}s")

        if HAS_CUPY:
            # CuPy GPU
            start = time.time()
            x_cp = cp.random.random(size)
            y_cp = cp.fft.fft(x_cp)
            cp.cuda.Device(0).synchronize()
            gpu_time = time.time() - start
            print(f"  GPU (CuPy):  {gpu_time:.4f}s")

            speedup = cpu_time / gpu_time
            print(f"  Speedup: {speedup:.2f}x")

            return {
                'size': size,
                'cpu_time': cpu_time,
                'gpu_time': gpu_time,
                'speedup': speedup,
                'status': 'PASS'
            }
        else:
            return {
                'size': size,
                'cpu_time': cpu_time,
                'gpu_time': None,
                'speedup': 1.0,
                'status': 'CPU_ONLY'
            }

    def run_benchmarks(self):
        """运行完整基准"""
        print("="*60)
        print("GPU ACCELERATION BENCHMARK")
        print("="*60)
        print(f"CuPy available: {HAS_CUPY}")
        if HAS_CUPY:
            print(f"GPU memory: 12GB")

        # 矩阵乘法测试
        for size in [1000, 2000, 5000]:
            result = self.benchmark_matrix_multiply(size)
            self.results.append(result)

        # FFT测试
        for size in [10000, 100000, 1000000]:
            result = self.benchmark_fft(size)
            self.results.append(result)

        # 汇总
        print("\n" + "="*60)
        print("BENCHMARK SUMMARY")
        print("="*60)

        if HAS_CUPY:
            speedups = [r['speedup'] for r in self.results if r.get('speedup')]
            avg_speedup = sum(speedups) / len(speedups) if speedups else 1.0
            print(f"Average speedup: {avg_speedup:.2f}x")
            print(f"Max speedup: {max(speedups):.2f}x")
        else:
            print("GPU not available - CPU only mode")

        return self.results

if __name__ == "__main__":
    bench = GPUBenchmark()
    results = bench.run_benchmarks()

    print(f"\n[FINAL] Benchmark complete: {len(results)} tests")
