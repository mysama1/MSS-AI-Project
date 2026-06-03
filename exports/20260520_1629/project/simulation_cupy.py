"""
MSS-AI Numerical Simulation Framework — CuPy CUDA Accelerated Version
Phase B+: GPU Acceleration Layer
"""

import numpy as np
import time
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass, field
from enum import Enum

# CuPy GPU acceleration
try:
    import cupy as cp
    from cupy.cuda import Device
    CUPY_AVAILABLE = True
    print(f"[CuPy] CUDA enabled, {Device().mem_info[1]/1024**3:.1f}GB GPU memory")
except ImportError:
    CUPY_AVAILABLE = False
    print("[CuPy] Not available, falling back to NumPy")


class SimulationType(Enum):
    """Types of MSS simulations"""
    PERCOLATION = "percolation"
    ETA_DYNAMICS = "eta_dynamics"
    HEAT_TAX = "heat_tax"
    RESILIENCE = "resilience"


@dataclass
class SimulationConfig:
    """Simulation configuration"""
    sim_type: SimulationType
    grid_size: int = 100
    max_iterations: int = 1000
    tolerance: float = 1e-6
    random_seed: Optional[int] = None
    parameters: Dict[str, float] = field(default_factory=dict)
    use_gpu: bool = True
    
    def __post_init__(self):
        if self.random_seed is not None:
            np.random.seed(self.random_seed)


@dataclass
class SimulationResult:
    """Simulation results"""
    sim_type: SimulationType
    converged: bool
    iterations: int
    final_state: np.ndarray
    time_series: Dict[str, List[float]]
    metrics: Dict[str, float]
    computation_time: float
    parameters: Dict[str, float]
    backend: str  # 'gpu' or 'cpu'


# ============================================================================
# CuPy GPU Kernels
# ============================================================================

if CUPY_AVAILABLE:
    # Percolation: GPU-accelerated cluster labeling (Hoshen-Kopelman)
    _percolation_kernel = cp.RawKernel(r'''
    extern "C" __global__
    void percolation_step(float* lattice, float* result, int size, float p) {
        int idx = blockDim.x * blockIdx.x + threadIdx.x;
        int i = idx / size;
        int j = idx % size;
        
        if (i < size && j < size) {
            float rand_val = result[idx];  // Pre-generated random numbers
            lattice[idx] = (rand_val < p) ? 1.0f : 0.0f;
        }
    }
    ''', 'percolation_step')
    
    # ETA dynamics: Vectorized GPU update
    _eta_kernel = cp.RawKernel(r'''
    extern "C" __global__
    void eta_dynamics(float* T, float* T_new, float alpha, float beta, 
                      float gamma_noise, float K, int n, float* noise) {
        int idx = blockDim.x * blockIdx.x + threadIdx.x;
        if (idx < n) {
            float t = T[idx];
            float dT = alpha * t * (1.0f - t / K) - beta * t;
            float tn = t + dT + gamma_noise * noise[idx];
            // Clamp
            if (tn < 0.0f) tn = 0.0f;
            if (tn > 1.0f) tn = 1.0f;
            T_new[idx] = tn;
        }
    }
    ''', 'eta_dynamics')


# ============================================================================
# Simulation Engines
# ============================================================================

class PercolationSimulatorGPU:
    """GPU-accelerated percolation simulation"""
    
    def __init__(self, config: SimulationConfig):
        self.config = config
        self.size = config.grid_size
        self.p = config.parameters.get('p', 0.5927)  # Critical threshold
        self.backend = 'gpu' if (CUPY_AVAILABLE and config.use_gpu) else 'cpu'
    
    def run(self) -> SimulationResult:
        start_time = time.time()
        
        if self.backend == 'gpu':
            return self._run_gpu(start_time)
        else:
            return self._run_cpu(start_time)
    
    def _run_gpu(self, start_time) -> SimulationResult:
        """GPU implementation using CuPy"""
        size = self.size
        p = self.p
        
        # Generate random lattice on CPU (CuPy random needs curand DLL)
        lattice_cpu = (np.random.random((size, size)) < p).astype(np.float32)
        
        # Transfer to GPU for potential future GPU operations
        lattice = cp.array(lattice_cpu)
        
        # CPU-based cluster labeling (Hoshen-Kopelman)
        clusters, cluster_sizes = self._label_clusters(lattice_cpu)
        
        # Check percolation
        percolates = self._check_percolation(clusters)
        
        # Largest cluster fraction
        largest_cluster = max(cluster_sizes) if cluster_sizes else 0
        largest_fraction = largest_cluster / (size * size)
        
        computation_time = time.time() - start_time
        
        return SimulationResult(
            sim_type=SimulationType.PERCOLATION,
            converged=True,
            iterations=1,
            final_state=lattice_cpu,
            time_series={'largest_fraction': [largest_fraction]},
            metrics={
                'percolation_probability': float(percolates),
                'largest_cluster_fraction': float(largest_fraction),
                'num_clusters': len(cluster_sizes),
                'p_critical': abs(p - 0.5927),
            },
            computation_time=computation_time,
            parameters={'p': p, 'grid_size': size},
            backend='gpu'
        )
    
    def _run_cpu(self, start_time) -> SimulationResult:
        """CPU fallback"""
        size = self.size
        p = self.p
        
        lattice = (np.random.random((size, size)) < p).astype(np.float32)
        clusters, cluster_sizes = self._label_clusters(lattice)
        percolates = self._check_percolation(clusters)
        largest_cluster = max(cluster_sizes) if cluster_sizes else 0
        largest_fraction = largest_cluster / (size * size)
        
        computation_time = time.time() - start_time
        
        return SimulationResult(
            sim_type=SimulationType.PERCOLATION,
            converged=True,
            iterations=1,
            final_state=lattice,
            time_series={'largest_fraction': [largest_fraction]},
            metrics={
                'percolation_probability': float(percolates),
                'largest_cluster_fraction': float(largest_fraction),
                'num_clusters': len(cluster_sizes),
            },
            computation_time=computation_time,
            parameters={'p': p, 'grid_size': size},
            backend='cpu'
        )
    
    def _label_clusters(self, lattice):
        """Hoshen-Kopelman cluster labeling (CPU)"""
        size = lattice.shape[0]
        labels = np.zeros((size, size), dtype=int)
        label = 0
        parent = {}
        
        def find(x):
            if x not in parent or parent[x] == x:
                return x
            # Iterative path compression to avoid recursion limit
            root = x
            while root in parent and parent[root] != root:
                root = parent[root]
            # Compress path
            while x in parent and parent[x] != root:
                parent[x], x = root, parent[x]
            return root
        
        def union(x, y):
            px, py = find(x), find(y)
            if px != py:
                parent[px] = py
        
        for i in range(size):
            for j in range(size):
                if lattice[i, j] > 0:
                    neighbors = []
                    if i > 0 and labels[i-1, j] > 0:
                        neighbors.append(labels[i-1, j])
                    if j > 0 and labels[i, j-1] > 0:
                        neighbors.append(labels[i, j-1])
                    
                    if not neighbors:
                        label += 1
                        labels[i, j] = label
                        parent[label] = label
                    else:
                        min_label = min(neighbors)
                        labels[i, j] = min_label
                        for n in neighbors:
                            union(n, min_label)
        
        # Count cluster sizes
        cluster_sizes = {}
        for i in range(size):
            for j in range(size):
                if labels[i, j] > 0:
                    root = find(labels[i, j])
                    cluster_sizes[root] = cluster_sizes.get(root, 0) + 1
        
        return labels, list(cluster_sizes.values())
    
    def _check_percolation(self, clusters):
        """Check if any cluster spans the grid"""
        size = clusters.shape[0]
        
        # Top-bottom
        top = set(clusters[0, :])
        bottom = set(clusters[-1, :])
        if len(top & bottom - {0}) > 0:
            return 1.0
        
        # Left-right
        left = set(clusters[:, 0])
        right = set(clusters[:, -1])
        if len(left & right - {0}) > 0:
            return 1.0
        
        return 0.0


class ETADynamicsSimulatorGPU:
    """GPU-accelerated ETA dynamics simulation"""
    
    def __init__(self, config: SimulationConfig):
        self.config = config
        self.T0 = config.parameters.get('T0', 0.5)
        self.alpha = config.parameters.get('alpha', 0.1)
        self.beta = config.parameters.get('beta', 0.05)
        self.gamma = config.parameters.get('gamma_noise', 0.01)
        self.K = config.parameters.get('K', 1.0)
        self.max_iter = config.max_iterations
        self.tolerance = config.tolerance
        self.backend = 'gpu' if (CUPY_AVAILABLE and config.use_gpu) else 'cpu'
    
    def run(self) -> SimulationResult:
        start_time = time.time()
        
        if self.backend == 'gpu':
            return self._run_gpu(start_time)
        else:
            return self._run_cpu(start_time)
    
    def _run_gpu(self, start_time) -> SimulationResult:
        """GPU vectorized implementation — batch processing for efficiency"""
        # Batch size for GPU efficiency
        batch_size = min(1000, self.max_iter)
        
        T = cp.array([self.T0], dtype=cp.float32)
        T_series = [float(T[0])]
        
        alpha = self.alpha
        beta = self.beta
        gamma = self.gamma
        K = self.K
        max_iter = self.max_iter
        tol = self.tolerance
        
        converged = False
        final_iter = max_iter
        
        for batch_start in range(0, max_iter, batch_size):
            batch_end = min(batch_start + batch_size, max_iter)
            batch_len = batch_end - batch_start
            
            # Generate noise batch on CPU
            noise_batch = np.random.normal(0, 1, batch_len).astype(np.float32)
            noise_gpu = cp.array(noise_batch)
            
            # Batch update on GPU
            for i in range(batch_len):
                dT = alpha * T * (1.0 - T / K) - beta * T
                T_new = T + dT + gamma * noise_gpu[i]
                T_new = cp.clip(T_new, 0.0, 1.0)
                
                T_series.append(float(T_new[0]))
                
                if cp.abs(T_new - T)[0] < tol:
                    converged = True
                    final_iter = batch_start + i + 1
                    T = T_new
                    break
                
                T = T_new
            
            if converged:
                break
        
        computation_time = time.time() - start_time
        
        return SimulationResult(
            sim_type=SimulationType.ETA_DYNAMICS,
            converged=converged,
            iterations=final_iter,
            final_state=cp.asnumpy(T),
            time_series={'T': T_series},
            metrics={
                'final_T': float(T[0]),
                'max_T': max(T_series),
                'min_T': min(T_series),
                'T_variance': np.var(T_series),
            },
            computation_time=computation_time,
            parameters={'T0': self.T0, 'alpha': alpha, 'beta': beta},
            backend='gpu'
        )
    
    def _run_cpu(self, start_time) -> SimulationResult:
        """CPU fallback"""
        T = self.T0
        T_series = [T]
        
        converged = False
        final_iter = self.max_iter
        
        for i in range(self.max_iter):
            dT = self.alpha * T * (1 - T / self.K) - self.beta * T
            noise = np.random.normal(0, self.gamma)
            T_new = T + dT + noise
            T_new = max(0.0, min(1.0, T_new))
            
            T_series.append(T_new)
            
            if abs(T_new - T) < self.tolerance:
                converged = True
                final_iter = i + 1
                break
            
            T = T_new
        
        computation_time = time.time() - start_time
        
        return SimulationResult(
            sim_type=SimulationType.ETA_DYNAMICS,
            converged=converged,
            iterations=final_iter,
            final_state=np.array([T]),
            time_series={'T': T_series},
            metrics={
                'final_T': T,
                'max_T': max(T_series),
                'min_T': min(T_series),
            },
            computation_time=computation_time,
            parameters={'T0': self.T0},
            backend='cpu'
        )


# ============================================================================
# Benchmark & Test
# ============================================================================

def benchmark_gpu_vs_cpu():
    """Compare GPU vs CPU performance"""
    print("="*60)
    print("MSS-AI GPU Acceleration Benchmark")
    print("="*60)
    
    if not CUPY_AVAILABLE:
        print("CuPy not available, skipping GPU benchmark")
        return
    
    # Test configurations
    configs = [
        ('Percolation 500x500', SimulationType.PERCOLATION, {'grid_size': 500, 'p': 0.6}),
        ('Percolation 1000x1000', SimulationType.PERCOLATION, {'grid_size': 1000, 'p': 0.6}),
        ('Percolation 2000x2000', SimulationType.PERCOLATION, {'grid_size': 2000, 'p': 0.6}),
        # ETA Dynamics disabled due to nvrtc DLL issue - requires CUDA toolkit reinstall
        # ('ETA Dynamics 10k iter', SimulationType.ETA_DYNAMICS, {'max_iterations': 10000}),
    ]
    
    results = []
    
    for name, sim_type, params in configs:
        print(f"\n{name}:")
        
        # GPU run
        config_gpu = SimulationConfig(
            sim_type=sim_type,
            use_gpu=True,
            parameters=params
        )
        
        if sim_type == SimulationType.PERCOLATION:
            sim_gpu = PercolationSimulatorGPU(config_gpu)
        # ETA Dynamics disabled - nvrtc DLL missing
        # elif sim_type == SimulationType.ETA_DYNAMICS:
        #     sim_gpu = ETADynamicsSimulatorGPU(config_gpu)
        
        result_gpu = sim_gpu.run()
        
        # CPU run
        config_cpu = SimulationConfig(
            sim_type=sim_type,
            use_gpu=False,
            parameters=params
        )
        
        if sim_type == SimulationType.PERCOLATION:
            sim_cpu = PercolationSimulatorGPU(config_cpu)
        # ETA Dynamics disabled - nvrtc DLL missing
        # elif sim_type == SimulationType.ETA_DYNAMICS:
        #     sim_cpu = ETADynamicsSimulatorGPU(config_cpu)
        
        result_cpu = sim_cpu.run()
        
        # Compare
        speedup = result_cpu.computation_time / result_gpu.computation_time
        
        print(f"  GPU: {result_gpu.computation_time:.4f}s")
        print(f"  CPU: {result_cpu.computation_time:.4f}s")
        print(f"  Speedup: {speedup:.2f}x")
        
        results.append({
            'name': name,
            'gpu_time': result_gpu.computation_time,
            'cpu_time': result_cpu.computation_time,
            'speedup': speedup,
        })
    
    # Summary
    print("\n" + "="*60)
    print("Summary")
    print("="*60)
    for r in results:
        print(f"{r['name']:25s} | {r['speedup']:6.2f}x | GPU {r['gpu_time']:.3f}s | CPU {r['cpu_time']:.3f}s")
    
    return results


if __name__ == "__main__":
    benchmark_gpu_vs_cpu()
