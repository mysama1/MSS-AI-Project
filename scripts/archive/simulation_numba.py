"""
MSS-AI Numerical Simulation Framework — Numba JIT Accelerated Version
Phase B: Performance Optimization
"""

import numpy as np
import time
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass, field
from enum import Enum
import random

try:
    from numba import njit, prange
    NUMBA_AVAILABLE = True
except ImportError:
    NUMBA_AVAILABLE = False
    print("Warning: Numba not available, falling back to pure NumPy")

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
    use_numba: bool = True

    def __post_init__(self):
        if self.random_seed is not None:
            np.random.seed(self.random_seed)
            random.seed(self.random_seed)

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

# ============================================================================
# Numba JIT Functions
# ============================================================================

if NUMBA_AVAILABLE:
    @njit(cache=True)
    def _flood_fill_numba(lattice, clusters, i, j, cluster_id, size):
        """Numba-accelerated flood fill"""
        stack = [(i, j)]
        count = 0
        while stack:
            ci, cj = stack.pop()
            if 0 <= ci < size and 0 <= cj < size:
                if lattice[ci, cj] and clusters[ci, cj] == 0:
                    clusters[ci, cj] = cluster_id
                    count += 1
                    stack.append((ci+1, cj))
                    stack.append((ci-1, cj))
                    stack.append((ci, cj+1))
                    stack.append((ci, cj-1))
        return count

    @njit(cache=True)
    def _check_percolation_numba(clusters, size):
        """Numba-accelerated percolation check"""
        # Check top-bottom
        top_clusters = set()
        bottom_clusters = set()
        for j in range(size):
            if clusters[0, j] != 0:
                top_clusters.add(clusters[0, j])
            if clusters[-1, j] != 0:
                bottom_clusters.add(clusters[-1, j])

        if len(top_clusters & bottom_clusters) > 0:
            return 1.0

        # Check left-right
        left_clusters = set()
        right_clusters = set()
        for i in range(size):
            if clusters[i, 0] != 0:
                left_clusters.add(clusters[i, 0])
            if clusters[i, -1] != 0:
                right_clusters.add(clusters[i, -1])

        if len(left_clusters & right_clusters) > 0:
            return 1.0

        return 0.0

    @njit(cache=True)
    def _eta_dynamics_numba(T0, alpha, beta, gamma_noise, K, max_iter, tolerance):
        """Numba-accelerated ETA dynamics — optimized loop"""
        T = T0
        T_series = np.zeros(max_iter + 1)
        T_series[0] = T

        # Precompute constants
        inv_K = 1.0 / K

        for i in range(max_iter):
            dT = alpha * T * (1.0 - T * inv_K) - beta * T
            # Box-Muller transform for normal distribution
            u1 = np.random.random()
            u2 = np.random.random()
            noise = gamma_noise * np.sqrt(-2.0 * np.log(u1)) * np.cos(2.0 * np.pi * u2)

            T_new = T + dT + noise
            # Fast clamp
            if T_new < 0.0:
                T_new = 0.0
            elif T_new > 1.0:
                T_new = 1.0

            T_series[i + 1] = T_new

            diff = T_new - T
            if diff < 0:
                diff = -diff
            if diff < tolerance:
                return T_series[:i + 2], i + 1, T_new

            T = T_new

        return T_series, max_iter, T

    @njit(cache=True)
    def _heat_tax_numba(gamma0, D0, n_max):
        """Numba-accelerated heat tax calculation"""
        n = np.arange(n_max + 1)
        D = np.zeros(n_max + 1)
        gamma = np.zeros(n_max + 1)
        cumulative = np.zeros(n_max + 1)

        D[0] = D0
        gamma[0] = gamma0
        cumulative[0] = gamma0

        for i in range(1, n_max + 1):
            D[i] = D[i-1] * 0.6
            gamma[i] = gamma0 / (D[i] ** i)
            cumulative[i] = cumulative[i-1] + gamma[i]

        return n, D, gamma, cumulative

    @njit(cache=True)
    def _resilience_numba(phi0, N, decay_rate, shock_prob, max_iter):
        """Numba-accelerated resilience simulation — optimized v2"""
        phi = phi0
        phi_critical = 1.0 / N
        phi_series = np.zeros(max_iter + 1)
        shock_series = np.zeros(max_iter + 1, dtype=np.int32)
        phi_series[0] = phi

        # Precompute decay factor
        decay_factor = 1.0 - decay_rate

        for i in range(max_iter):
            phi = phi * decay_factor

            if np.random.random() < shock_prob:
                phi = phi * 0.8
                shock_series[i + 1] = 1

            if phi < 0.0:
                phi = 0.0

            phi_series[i + 1] = phi

            if phi < phi_critical:
                return phi_series[:i + 2], shock_series[:i + 2], i + 1, phi, True

        return phi_series, shock_series, max_iter, phi, False

# ============================================================================
# Optimized Simulators
# ============================================================================

class PercolationSimulator:
    """Site percolation simulation — Numba accelerated"""

    def __init__(self, config: SimulationConfig):
        self.config = config
        self.size = config.grid_size
        self.p = config.parameters.get('occupation_prob', 0.5)
        self.use_numba = config.use_numba and NUMBA_AVAILABLE

    def run(self) -> SimulationResult:
        start_time = time.time()

        # Initialize lattice
        lattice = np.random.random((self.size, self.size)) < self.p
        clusters = np.zeros((self.size, self.size), dtype=np.int32)

        # Label clusters
        cluster_id = 1
        cluster_sizes = []

        if self.use_numba:
            for i in range(self.size):
                for j in range(self.size):
                    if lattice[i, j] and clusters[i, j] == 0:
                        size = _flood_fill_numba(lattice, clusters, i, j, cluster_id, self.size)
                        cluster_sizes.append(size)
                        cluster_id += 1
            percolation_prob = _check_percolation_numba(clusters, self.size)
        else:
            for i in range(self.size):
                for j in range(self.size):
                    if lattice[i, j] and clusters[i, j] == 0:
                        size = self._flood_fill_python(lattice, clusters, i, j, cluster_id)
                        cluster_sizes.append(size)
                        cluster_id += 1
            percolation_prob = self._check_percolation_python(clusters)

        # Calculate metrics
        largest_cluster = max(cluster_sizes) if cluster_sizes else 0
        total_sites = self.size ** 2

        metrics = {
            'occupation_probability': self.p,
            'total_clusters': cluster_id - 1,
            'largest_cluster_size': largest_cluster,
            'largest_cluster_fraction': largest_cluster / total_sites,
            'percolation_probability': percolation_prob,
            'mean_cluster_size': np.mean(cluster_sizes) if cluster_sizes else 0
        }

        return SimulationResult(
            sim_type=SimulationType.PERCOLATION,
            converged=True,
            iterations=1,
            final_state=lattice.astype(float),
            time_series={'cluster_count': [cluster_id - 1]},
            metrics=metrics,
            computation_time=time.time() - start_time,
            parameters=self.config.parameters
        )

    def _flood_fill_python(self, lattice, clusters, i, j, cluster_id):
        """Pure Python flood fill fallback"""
        stack = [(i, j)]
        count = 0
        while stack:
            ci, cj = stack.pop()
            if (0 <= ci < self.size and 0 <= cj < self.size and
                lattice[ci, cj] and clusters[ci, cj] == 0):
                clusters[ci, cj] = cluster_id
                count += 1
                stack.extend([(ci+1, cj), (ci-1, cj), (ci, cj+1), (ci, cj-1)])
        return count

    def _check_percolation_python(self, clusters):
        """Pure Python percolation check fallback"""
        top = set(clusters[0, :]) - {0}
        bottom = set(clusters[-1, :]) - {0}
        if top & bottom:
            return 1.0

        left = set(clusters[:, 0]) - {0}
        right = set(clusters[:, -1]) - {0}
        if left & right:
            return 1.0

        return 0.0

class ETADynamicsSimulator:
    """ETA dynamics simulation — Numba accelerated"""

    def __init__(self, config: SimulationConfig):
        self.config = config
        self.T0 = config.parameters.get('initial_tuning', 0.1)
        self.alpha = config.parameters.get('growth_rate', 0.01)
        self.beta = config.parameters.get('decay_rate', 0.001)
        self.gamma = config.parameters.get('noise_amplitude', 0.01)
        self.K = config.parameters.get('carrying_capacity', 1.0)
        self.use_numba = config.use_numba and NUMBA_AVAILABLE

    def run(self) -> SimulationResult:
        start_time = time.time()

        if self.use_numba:
            T_series, iterations, T_final = _eta_dynamics_numba(
                self.T0, self.alpha, self.beta, self.gamma, self.K,
                self.config.max_iterations, self.config.tolerance
            )
            T_list = T_series.tolist()
        else:
            T = self.T0
            T_list = [T]
            iterations = self.config.max_iterations

            for i in range(self.config.max_iterations):
                dT = self.alpha * T * (1 - T / self.K) - self.beta * T
                noise = np.random.normal(0, self.gamma)
                T_new = T + dT + noise
                T_new = np.clip(T_new, 0, 1)
                T_list.append(float(T_new))

                if abs(T_new - T) < self.config.tolerance:
                    iterations = i + 1
                    break
                T = T_new

            T_final = T

        metrics = {
            'final_tuning': float(T_final),
            'convergence_iteration': iterations,
            'max_tuning': float(max(T_list)),
            'tuning_variance': float(np.var(T_list)),
            'stable': abs(T_final - self.K) < 0.1
        }

        return SimulationResult(
            sim_type=SimulationType.ETA_DYNAMICS,
            converged=metrics['stable'],
            iterations=iterations,
            final_state=np.array([T_final]),
            time_series={'T': T_list, 'dT': [0] * len(T_list)},
            metrics=metrics,
            computation_time=time.time() - start_time,
            parameters=self.config.parameters
        )

class HeatTaxSimulator:
    """Heat tax simulation — vectorized NumPy (Numba disabled: vectorized NumPy is already optimal)"""

    def __init__(self, config: SimulationConfig):
        self.config = config
        self.gamma0 = config.parameters.get('gamma0', 1.0)
        self.D0 = config.parameters.get('initial_depth', 1.0)
        self.n_max = config.parameters.get('max_cuts', 7)
        # NOTE: Numba disabled for Heat Tax — vectorized NumPy is already optimal
        # Numba JIT adds overhead for small arrays (n_max=7) with no performance benefit
        self.use_numba = False

    def run(self) -> SimulationResult:
        start_time = time.time()

        # Pre-allocated arrays for cache-friendly computation
        n = np.arange(self.n_max + 1, dtype=np.float64)
        D = np.empty(self.n_max + 1, dtype=np.float64)
        gamma = np.empty(self.n_max + 1, dtype=np.float64)
        cumulative = np.empty(self.n_max + 1, dtype=np.float64)

        # Compute with in-place operations to minimize allocations
        np.power(0.6, n, out=D)
        np.multiply(self.D0, D, out=D)
        np.power(D, -n, out=gamma)
        np.multiply(self.gamma0, gamma, out=gamma)
        np.cumsum(gamma, out=cumulative)

        time_series = {
            'cut_number': n.tolist(),
            'depth': D.tolist(),
            'heat_tax': gamma.tolist(),
            'cumulative_tax': cumulative.tolist()
        }

        metrics = {
            'total_cuts': self.n_max,
            'final_heat_tax': float(gamma[-1]),
            'cumulative_tax': float(cumulative[-1]),
            'tax_at_cut_3': float(gamma[3]) if len(gamma) > 3 else 0,
            'thermal_death_threshold': 7,
            'exceeded_threshold': cumulative[-1] > 1.0
        }

        return SimulationResult(
            sim_type=SimulationType.HEAT_TAX,
            converged=True,
            iterations=self.n_max,
            final_state=np.array([gamma[-1]]),
            time_series=time_series,
            metrics=metrics,
            computation_time=time.time() - start_time,
            parameters=self.config.parameters
        )

class ResilienceSimulator:
    """Resilience simulation — Numba accelerated"""

    def __init__(self, config: SimulationConfig):
        self.config = config
        self.N = config.parameters.get('organization_size', 100)
        self.phi0 = config.parameters.get('initial_resilience', 1.0)
        self.decay_rate = config.parameters.get('decay_rate', 0.01)
        self.shock_probability = config.parameters.get('shock_prob', 0.1)
        self.use_numba = config.use_numba and NUMBA_AVAILABLE

    def run(self) -> SimulationResult:
        start_time = time.time()

        # Pre-allocate arrays to avoid repeated list.append overhead
        max_iter = self.config.max_iterations
        phi_arr = np.empty(max_iter + 1, dtype=np.float64)
        shock_arr = np.empty(max_iter + 1, dtype=np.int32)
        phi_arr[0] = self.phi0
        shock_arr[0] = 0

        if self.use_numba:
            phi_series, shock_series, iterations, phi_final, collapsed = _resilience_numba(
                self.phi0, self.N, self.decay_rate, self.shock_probability,
                max_iter
            )
            phi_list = phi_series.tolist()
            shock_list = shock_series.tolist()
        else:
            phi = self.phi0
            phi_critical = 1.0 / self.N
            collapsed = False

            for i in range(max_iter):
                phi -= self.decay_rate * phi
                shock = 1 if np.random.random() < self.shock_probability else 0
                if shock:
                    phi *= 0.8
                if phi < 0:
                    phi = 0.0

                phi_arr[i + 1] = phi
                shock_arr[i + 1] = shock

                if phi < phi_critical:
                    collapsed = True
                    iterations = i + 1
                    break
            else:
                iterations = max_iter

            phi_final = phi
            phi_list = phi_arr[:iterations + 1].tolist()
            shock_list = shock_arr[:iterations + 1].tolist()

        phi_critical = 1.0 / self.N

        metrics = {
            'initial_resilience': self.phi0,
            'critical_threshold': float(phi_critical),
            'final_resilience': float(phi_final),
            'total_shocks': sum(shock_list),
            'collapse_iteration': iterations if collapsed else -1,
            'survival_ratio': float(phi_final / self.phi0)
        }

        return SimulationResult(
            sim_type=SimulationType.RESILIENCE,
            converged=collapsed,
            iterations=iterations,
            final_state=np.array([phi_final]),
            time_series={'phi': phi_list, 'shocks': shock_list},
            metrics=metrics,
            computation_time=time.time() - start_time,
            parameters=self.config.parameters
        )

# ============================================================================
# Simulation Engine
# ============================================================================

class SimulationEngine:
    """Main simulation engine"""

    def __init__(self):
        self.simulators = {
            SimulationType.PERCOLATION: PercolationSimulator,
            SimulationType.ETA_DYNAMICS: ETADynamicsSimulator,
            SimulationType.HEAT_TAX: HeatTaxSimulator,
            SimulationType.RESILIENCE: ResilienceSimulator
        }

    def run(self, config: SimulationConfig) -> SimulationResult:
        if config.sim_type not in self.simulators:
            raise ValueError(f"Unknown simulation type: {config.sim_type}")

        simulator = self.simulators[config.sim_type](config)
        return simulator.run()

    def batch_run(self, configs: List[SimulationConfig]) -> List[SimulationResult]:
        return [self.run(config) for config in configs]

    def parameter_sweep(self,
                       sim_type: SimulationType,
                       param_name: str,
                       param_values: List[float],
                       base_params: Dict[str, float]) -> List[SimulationResult]:
        configs = []
        for value in param_values:
            params = base_params.copy()
            params[param_name] = value
            configs.append(SimulationConfig(
                sim_type=sim_type,
                parameters=params
            ))

        return self.batch_run(configs)

# ============================================================================
# Benchmark
# ============================================================================

if __name__ == "__main__":
    print("MSS-AI Simulation Framework — Numba JIT Accelerated")
    print("=" * 60)
    print(f"Numba available: {NUMBA_AVAILABLE}")
    print()

    engine = SimulationEngine()

    # Benchmark percolation
    print("1. Percolation Benchmark")
    for size in [100, 200, 400]:
        config = SimulationConfig(
            sim_type=SimulationType.PERCOLATION,
            grid_size=size,
            parameters={'occupation_prob': 0.6},
            use_numba=True
        )
        result = engine.run(config)
        print(f"   {size}x{size}: {result.computation_time:.4f}s")

    # Benchmark ETA
    print("\n2. ETA Dynamics Benchmark")
    config = SimulationConfig(
        sim_type=SimulationType.ETA_DYNAMICS,
        max_iterations=10000,
        parameters={'initial_tuning': 0.1, 'growth_rate': 0.05},
        use_numba=True
    )
    result = engine.run(config)
    print(f"   10000 iterations: {result.computation_time:.4f}s")

    # Benchmark resilience
    print("\n3. Resilience Benchmark")
    config = SimulationConfig(
        sim_type=SimulationType.RESILIENCE,
        max_iterations=10000,
        parameters={'organization_size': 100, 'shock_prob': 0.1},
        use_numba=True
    )
    result = engine.run(config)
    print(f"   10000 iterations: {result.computation_time:.4f}s")
