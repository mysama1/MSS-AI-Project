"""
MSS-AI Numerical Simulation Framework
Core simulation engine for percolation phase transitions and ETA order parameters
"""

import numpy as np
import json
import time
from typing import Dict, List, Tuple, Optional, Callable
from dataclasses import dataclass, field
from enum import Enum
import random

class SimulationType(Enum):
    """Types of MSS simulations"""
    PERCOLATION = "percolation"           # Site/bond percolation
    ETA_DYNAMICS = "eta_dynamics"         # ETA order parameter evolution
    HEAT_TAX = "heat_tax"                 # Heat tax accumulation
    MEANING_FIELD = "meaning_field"       # Meaning field equation M⊗Ô = ∇·(T⊗L)
    RESILIENCE = "resilience"             # Organizational resilience decay

@dataclass
class SimulationConfig:
    """Simulation configuration"""
    sim_type: SimulationType
    grid_size: int = 100                  # Lattice size
    max_iterations: int = 1000            # Max time steps
    tolerance: float = 1e-6               # Convergence tolerance
    random_seed: Optional[int] = None     # Reproducibility
    parameters: Dict[str, float] = field(default_factory=dict)

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

class PercolationSimulator:
    """
    Site percolation simulation on 2D square lattice

    Models phase transition at critical probability p_c
    """

    def __init__(self, config: SimulationConfig):
        self.config = config
        self.size = config.grid_size
        self.p = config.parameters.get('occupation_prob', 0.5)
        self.lattice = np.zeros((self.size, self.size), dtype=bool)
        self.clusters = np.zeros((self.size, self.size), dtype=int)

    def initialize(self):
        """Initialize random lattice"""
        self.lattice = np.random.random((self.size, self.size)) < self.p
        self.clusters = np.zeros((self.size, self.size), dtype=int)

    def run(self) -> SimulationResult:
        """Run percolation simulation"""
        start_time = time.time()

        self.initialize()

        # Label clusters using Hoshen-Kopelman algorithm
        cluster_id = 1
        for i in range(self.size):
            for j in range(self.size):
                if self.lattice[i, j] and self.clusters[i, j] == 0:
                    self._flood_fill(i, j, cluster_id)
                    cluster_id += 1

        # Calculate metrics
        max_cluster = np.max(self.clusters)
        cluster_sizes = np.bincount(self.clusters.flatten())[1:]

        largest_cluster = np.max(cluster_sizes) if len(cluster_sizes) > 0 else 0
        percolation_prob = self._check_percolation()

        metrics = {
            'occupation_probability': self.p,
            'total_clusters': int(max_cluster),
            'largest_cluster_size': int(largest_cluster),
            'largest_cluster_fraction': float(largest_cluster) / (self.size ** 2),
            'percolation_probability': percolation_prob,
            'mean_cluster_size': float(np.mean(cluster_sizes)) if len(cluster_sizes) > 0 else 0
        }

        return SimulationResult(
            sim_type=SimulationType.PERCOLATION,
            converged=True,
            iterations=1,
            final_state=self.lattice.astype(float),
            time_series={'cluster_count': [int(max_cluster)]},
            metrics=metrics,
            computation_time=time.time() - start_time,
            parameters=self.config.parameters
        )

    def _flood_fill(self, i: int, j: int, cluster_id: int):
        """Flood fill to label cluster"""
        stack = [(i, j)]
        while stack:
            ci, cj = stack.pop()
            if (0 <= ci < self.size and 0 <= cj < self.size and
                self.lattice[ci, cj] and self.clusters[ci, cj] == 0):
                self.clusters[ci, cj] = cluster_id
                stack.extend([(ci+1, cj), (ci-1, cj), (ci, cj+1), (ci, cj-1)])

    def _check_percolation(self) -> float:
        """Check if percolation occurs (top-bottom or left-right connection)"""
        # Check top-bottom
        top_clusters = set(self.clusters[0, :])
        bottom_clusters = set(self.clusters[-1, :])

        # Check left-right
        left_clusters = set(self.clusters[:, 0])
        right_clusters = set(self.clusters[:, -1])

        # Remove 0 (empty sites)
        top_clusters.discard(0)
        bottom_clusters.discard(0)
        left_clusters.discard(0)
        right_clusters.discard(0)

        tb_percolate = len(top_clusters & bottom_clusters) > 0
        lr_percolate = len(left_clusters & right_clusters) > 0

        return 1.0 if (tb_percolate or lr_percolate) else 0.0

class ETADynamicsSimulator:
    """
    ETA (Emergence-Tuning-Alignment) order parameter dynamics

    Simulates evolution of tuning degree T over time
    """

    def __init__(self, config: SimulationConfig):
        self.config = config
        self.T0 = config.parameters.get('initial_tuning', 0.1)
        self.alpha = config.parameters.get('growth_rate', 0.01)
        self.beta = config.parameters.get('decay_rate', 0.001)
        self.gamma = config.parameters.get('noise_amplitude', 0.01)
        self.K = config.parameters.get('carrying_capacity', 1.0)

    def run(self) -> SimulationResult:
        """Run ETA dynamics simulation"""
        start_time = time.time()

        T = self.T0
        time_series = {'T': [T], 'dT': [0]}

        for iteration in range(self.config.max_iterations):
            # Logistic growth with noise
            dT = self.alpha * T * (1 - T / self.K) - self.beta * T
            noise = np.random.normal(0, self.gamma)

            T_new = T + dT + noise
            T_new = np.clip(T_new, 0, 1)  # Keep in [0, 1]

            time_series['T'].append(float(T_new))
            time_series['dT'].append(float(dT))

            # Check convergence
            if abs(T_new - T) < self.config.tolerance:
                break

            T = T_new

        metrics = {
            'final_tuning': float(T),
            'convergence_iteration': iteration + 1,
            'max_tuning': float(max(time_series['T'])),
            'tuning_variance': float(np.var(time_series['T'])),
            'stable': abs(T - self.K) < 0.1
        }

        return SimulationResult(
            sim_type=SimulationType.ETA_DYNAMICS,
            converged=metrics['stable'],
            iterations=iteration + 1,
            final_state=np.array([T]),
            time_series=time_series,
            metrics=metrics,
            computation_time=time.time() - start_time,
            parameters=self.config.parameters
        )

class HeatTaxSimulator:
    """
    Heat tax accumulation simulation

    Models γ(n,D) = γ₀ × D^(-n) heat tax formula
    """

    def __init__(self, config: SimulationConfig):
        self.config = config
        self.gamma0 = config.parameters.get('gamma0', 1.0)
        self.D0 = config.parameters.get('initial_depth', 1.0)
        self.n_max = config.parameters.get('max_cuts', 7)

    def run(self) -> SimulationResult:
        """Run heat tax simulation"""
        start_time = time.time()

        time_series = {
            'cut_number': [],
            'depth': [],
            'heat_tax': [],
            'cumulative_tax': []
        }

        cumulative = 0.0
        D = self.D0

        for n in range(self.n_max + 1):
            gamma = self.gamma0 * (D ** (-n))
            cumulative += gamma

            time_series['cut_number'].append(n)
            time_series['depth'].append(float(D))
            time_series['heat_tax'].append(float(gamma))
            time_series['cumulative_tax'].append(float(cumulative))

            # Depth decreases with each cut
            D *= 0.6

        metrics = {
            'total_cuts': self.n_max,
            'final_heat_tax': float(gamma),
            'cumulative_tax': float(cumulative),
            'tax_at_cut_3': float(time_series['heat_tax'][3]) if len(time_series['heat_tax']) > 3 else 0,
            'thermal_death_threshold': 7,
            'exceeded_threshold': cumulative > 1.0
        }

        return SimulationResult(
            sim_type=SimulationType.HEAT_TAX,
            converged=True,
            iterations=self.n_max,
            final_state=np.array([gamma]),
            time_series=time_series,
            metrics=metrics,
            computation_time=time.time() - start_time,
            parameters=self.config.parameters
        )

class ResilienceSimulator:
    """
    Organizational resilience decay simulation

    Models phi_c ≈ 1/N scaling law
    """

    def __init__(self, config: SimulationConfig):
        self.config = config
        self.N = config.parameters.get('organization_size', 100)
        self.phi0 = config.parameters.get('initial_resilience', 1.0)
        self.decay_rate = config.parameters.get('decay_rate', 0.01)
        self.shock_probability = config.parameters.get('shock_prob', 0.1)

    def run(self) -> SimulationResult:
        """Run resilience simulation"""
        start_time = time.time()

        phi = self.phi0
        phi_critical = 1.0 / self.N

        time_series = {
            'phi': [phi],
            'shocks': [0],
            'status': ['stable']
        }

        for iteration in range(self.config.max_iterations):
            # Natural decay
            phi -= self.decay_rate * phi

            # Random shocks
            shock = 1 if np.random.random() < self.shock_probability else 0
            if shock:
                phi *= 0.8  # 20% resilience loss per shock

            phi = max(phi, 0)  # Non-negative

            # Determine status
            if phi < phi_critical:
                status = 'collapsed'
            elif phi < phi_critical * 2:
                status = 'critical'
            elif phi < phi_critical * 5:
                status = 'degraded'
            else:
                status = 'stable'

            time_series['phi'].append(float(phi))
            time_series['shocks'].append(shock)
            time_series['status'].append(status)

            if status == 'collapsed':
                break

        metrics = {
            'initial_resilience': self.phi0,
            'critical_threshold': float(phi_critical),
            'final_resilience': float(phi),
            'total_shocks': sum(time_series['shocks']),
            'collapse_iteration': iteration if status == 'collapsed' else -1,
            'survival_ratio': float(phi / self.phi0)
        }

        return SimulationResult(
            sim_type=SimulationType.RESILIENCE,
            converged=status == 'collapsed',
            iterations=iteration + 1,
            final_state=np.array([phi]),
            time_series=time_series,
            metrics=metrics,
            computation_time=time.time() - start_time,
            parameters=self.config.parameters
        )

class SimulationEngine:
    """
    Main simulation engine

    Factory for running different simulation types
    """

    def __init__(self):
        self.simulators = {
            SimulationType.PERCOLATION: PercolationSimulator,
            SimulationType.ETA_DYNAMICS: ETADynamicsSimulator,
            SimulationType.HEAT_TAX: HeatTaxSimulator,
            SimulationType.RESILIENCE: ResilienceSimulator
        }

    def run(self, config: SimulationConfig) -> SimulationResult:
        """Run simulation with given configuration"""
        if config.sim_type not in self.simulators:
            raise ValueError(f"Unknown simulation type: {config.sim_type}")

        simulator = self.simulators[config.sim_type](config)
        return simulator.run()

    def batch_run(self, configs: List[SimulationConfig]) -> List[SimulationResult]:
        """Run multiple simulations"""
        return [self.run(config) for config in configs]

    def parameter_sweep(self,
                       sim_type: SimulationType,
                       param_name: str,
                       param_values: List[float],
                       base_params: Dict[str, float]) -> List[SimulationResult]:
        """Run parameter sweep"""
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
# Utility Functions
# ============================================================================

def find_critical_point(results: List[SimulationResult],
                       metric_name: str = 'percolation_probability') -> float:
    """
    Find critical point from simulation results

    Uses bisection-like approach on sorted results
    """
    # Sort by parameter value
    sorted_results = sorted(results,
                          key=lambda r: r.parameters.get('occupation_prob', 0))

    # Find where metric crosses 0.5
    for i in range(len(sorted_results) - 1):
        r1, r2 = sorted_results[i], sorted_results[i + 1]
        m1 = r1.metrics.get(metric_name, 0)
        m2 = r2.metrics.get(metric_name, 0)

        if m1 < 0.5 and m2 >= 0.5:
            p1 = r1.parameters.get('occupation_prob', 0)
            p2 = r2.parameters.get('occupation_prob', 0)
            return (p1 + p2) / 2

    return None

def export_results(results: List[SimulationResult], filename: str):
    """Export results to JSON"""
    data = []
    for result in results:
        data.append({
            'sim_type': result.sim_type.value,
            'converged': result.converged,
            'iterations': result.iterations,
            'metrics': result.metrics,
            'parameters': result.parameters,
            'computation_time': result.computation_time
        })

    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

# ============================================================================
# Main Entry Point
# ============================================================================

if __name__ == "__main__":
    # Example: Percolation critical point estimation
    print("MSS-AI Simulation Framework")
    print("=" * 50)

    engine = SimulationEngine()

    # Percolation parameter sweep
    print("\n1. Percolation Phase Transition")
    p_values = np.linspace(0.3, 0.7, 20)
    percolation_results = engine.parameter_sweep(
        SimulationType.PERCOLATION,
        'occupation_prob',
        p_values,
        {'grid_size': 50}
    )

    p_c = find_critical_point(percolation_results)
    print(f"   Estimated critical point: p_c ≈ {p_c:.3f}")
    print(f"   Theoretical value: p_c ≈ 0.5927 (2D site percolation)")

    # ETA dynamics
    print("\n2. ETA Order Parameter Dynamics")
    eta_config = SimulationConfig(
        sim_type=SimulationType.ETA_DYNAMICS,
        parameters={
            'initial_tuning': 0.1,
            'growth_rate': 0.05,
            'decay_rate': 0.001,
            'carrying_capacity': 0.95
        }
    )
    eta_result = engine.run(eta_config)
    print(f"   Final tuning degree: T = {eta_result.metrics['final_tuning']:.3f}")
    print(f"   Converged: {eta_result.converged}")

    # Heat tax
    print("\n3. Heat Tax Accumulation")
    heat_config = SimulationConfig(
        sim_type=SimulationType.HEAT_TAX,
        parameters={
            'gamma0': 0.3,
            'initial_depth': 1.0,
            'max_cuts': 7
        }
    )
    heat_result = engine.run(heat_config)
    print(f"   Cumulative tax after 7 cuts: {heat_result.metrics['cumulative_tax']:.3f}")
    print(f"   Thermal death threshold exceeded: {heat_result.metrics['exceeded_threshold']}")

    # Resilience
    print("\n4. Organizational Resilience")
    res_config = SimulationConfig(
        sim_type=SimulationType.RESILIENCE,
        max_iterations=500,
        parameters={
            'organization_size': 50,
            'initial_resilience': 1.0,
            'decay_rate': 0.005,
            'shock_prob': 0.05
        }
    )
    res_result = engine.run(res_config)
    print(f"   Critical threshold: φ_c = {res_result.metrics['critical_threshold']:.4f}")
    print(f"   Final resilience: φ = {res_result.metrics['final_resilience']:.3f}")
    print(f"   Collapsed: {res_result.metrics['collapse_iteration'] > 0}")

    print("\n" + "=" * 50)
    print("Simulations complete!")
