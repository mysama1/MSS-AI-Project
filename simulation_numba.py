"""
Numba-accelerated simulation components for MSS-AI
Provides JIT-compiled versions of compute-intensive operations
"""

import numpy as np
from numba import njit, prange
from typing import Tuple, Optional

# ============================================================================
# Percolation Simulation (Numba JIT)
# ============================================================================

@njit(cache=True)
def _percolation_step_numba(grid: np.ndarray, p: float, rng_state: np.ndarray) -> np.ndarray:
    """
    Numba-accelerated percolation step
    
    Args:
        grid: 2D occupancy grid (0=empty, 1=occupied)
        p: Occupation probability
        rng_state: Random state array for reproducibility
    
    Returns:
        Updated grid
    """
    size = grid.shape[0]
    new_grid = grid.copy()
    
    for i in range(size):
        for j in range(size):
            # Simple LCG random number generator (Numba-compatible)
            rng_state[0] = (rng_state[0] * 1103515245 + 12345) & 0x7fffffff
            rand_val = rng_state[0] / 0x7fffffff
            
            if rand_val < p:
                new_grid[i, j] = 1
            else:
                new_grid[i, j] = 0
    
    return new_grid

@njit(cache=True)
def _check_percolation_numba(grid: np.ndarray) -> bool:
    """
    Check if percolation exists (top-to-bottom path)
    
    Uses union-find algorithm for efficiency
    """
    size = grid.shape[0]
    
    # Quick check: any occupied cell in top and bottom rows
    top_occupied = False
    bottom_occupied = False
    
    for j in range(size):
        if grid[0, j] == 1:
            top_occupied = True
        if grid[size-1, j] == 1:
            bottom_occupied = True
    
    if not top_occupied or not bottom_occupied:
        return False
    
    # BFS from top row
    visited = np.zeros((size, size), dtype=np.int32)
    queue = np.zeros((size * size, 2), dtype=np.int32)
    queue_head = 0
    queue_tail = 0
    
    # Add all top-row occupied cells
    for j in range(size):
        if grid[0, j] == 1:
            queue[queue_tail, 0] = 0
            queue[queue_tail, 1] = j
            queue_tail += 1
            visited[0, j] = 1
    
    # BFS
    directions = np.array([[-1, 0], [1, 0], [0, -1], [0, 1]], dtype=np.int32)
    
    while queue_head < queue_tail:
        i, j = queue[queue_head, 0], queue[queue_head, 1]
        queue_head += 1
        
        # Check if reached bottom
        if i == size - 1:
            return True
        
        # Explore neighbors
        for d in range(4):
            ni = i + directions[d, 0]
            nj = j + directions[d, 1]
            
            if 0 <= ni < size and 0 <= nj < size:
                if grid[ni, nj] == 1 and visited[ni, nj] == 0:
                    visited[ni, nj] = 1
                    queue[queue_tail, 0] = ni
                    queue[queue_tail, 1] = nj
                    queue_tail += 1
    
    return False

@njit(parallel=True, cache=True)
def _run_percolation_batch_numba(
    p_values: np.ndarray,
    grid_size: int,
    n_samples: int,
    seed: int = 42
) -> np.ndarray:
    """
    Parallel batch percolation simulation
    
    Args:
        p_values: Array of occupation probabilities
        grid_size: Grid dimension
        n_samples: Samples per probability
        seed: Random seed
    
    Returns:
        Array of percolation probabilities
    """
    n_p = len(p_values)
    results = np.zeros(n_p, dtype=np.float64)
    
    for idx in prange(n_p):
        p = p_values[idx]
        count = 0
        rng_state = np.array([seed + idx], dtype=np.int64)
        
        for _ in range(n_samples):
            grid = np.zeros((grid_size, grid_size), dtype=np.int32)
            grid = _percolation_step_numba(grid, p, rng_state)
            if _check_percolation_numba(grid):
                count += 1
        
        results[idx] = count / n_samples
    
    return results


# ============================================================================
# ETA Dynamics (Numba JIT)
# ============================================================================

@njit(cache=True)
def _eta_dynamics_numba(
    T0: float,
    K: float,
    r: float,
    dt: float,
    n_steps: int,
    noise_amplitude: float,
    seed: int = 42
) -> np.ndarray:
    """
    Numba-accelerated ETA order parameter dynamics
    
    Logistic growth with noise: dT/dt = r*T*(1 - T/K) + noise
    """
    T = np.zeros(n_steps, dtype=np.float64)
    T[0] = T0
    
    rng_state = np.array([seed], dtype=np.int64)
    
    for i in range(1, n_steps):
        # LCG random for noise
        rng_state[0] = (rng_state[0] * 1103515245 + 12345) & 0x7fffffff
        noise = (rng_state[0] / 0x7fffffff - 0.5) * 2 * noise_amplitude
        
        # Logistic growth
        dT = r * T[i-1] * (1 - T[i-1] / K) * dt
        T[i] = T[i-1] + dT + noise
        
        # Clamp to [0, K]
        if T[i] < 0:
            T[i] = 0.0
        elif T[i] > K:
            T[i] = K
    
    return T


# ============================================================================
# Heat Tax Accumulation (Numba JIT)
# ============================================================================

@njit(cache=True)
def _heat_tax_accumulation_numba(
    n_cuts: int,
    depth: float,
    gamma0: float,
    decay_rate: float
) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """
    Numba-accelerated heat tax accumulation
    
    Returns:
        cuts: Array of cut numbers
        taxes: Array of tax values per cut
        cumulative: Cumulative tax
    """
    cuts = np.arange(1, n_cuts + 1, dtype=np.int32)
    taxes = np.zeros(n_cuts, dtype=np.float64)
    cumulative = np.zeros(n_cuts, dtype=np.float64)
    
    for i in range(n_cuts):
        n = cuts[i]
        # Formula: γ(n,D) = γ₀ × D^(-n)
        # For depth < 1, D^(-n) increases with n, so tax increases
        # This is correct behavior: deeper cuts have higher tax
        tax = gamma0 * (depth ** (-n))
        
        # Apply decay (optional, for modeling recovery)
        if decay_rate > 0 and i > 0:
            tax *= np.exp(-decay_rate * i)
        
        taxes[i] = tax
        
        if i == 0:
            cumulative[i] = tax
        else:
            cumulative[i] = cumulative[i-1] + tax
    
    return cuts, taxes, cumulative


# ============================================================================
# High-Level API
# ============================================================================

def run_percolation_batch(
    p_values: np.ndarray,
    grid_size: int = 50,
    n_samples: int = 100,
    seed: int = 42
) -> np.ndarray:
    """
    Run parallel batch percolation simulation
    
    Example:
        >>> p_values = np.linspace(0.3, 0.7, 20)
        >>> results = run_percolation_batch(p_values, grid_size=50, n_samples=100)
        >>> print(f"Critical point: {p_values[np.argmax(results > 0.5)]}")
    """
    return _run_percolation_batch_numba(p_values, grid_size, n_samples, seed)

def run_eta_dynamics(
    T0: float = 0.1,
    K: float = 1.0,
    r: float = 0.05,
    dt: float = 0.01,
    n_steps: int = 1000,
    noise_amplitude: float = 0.01,
    seed: int = 42
) -> np.ndarray:
    """
    Run ETA dynamics simulation
    
    Returns:
        Array of T values over time
    """
    return _eta_dynamics_numba(T0, K, r, dt, n_steps, noise_amplitude, seed)

def run_heat_tax(
    n_cuts: int = 7,
    depth: float = 0.6,
    gamma0: float = 0.3,
    decay_rate: float = 0.1
) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """
    Run heat tax accumulation simulation
    
    Returns:
        (cuts, taxes, cumulative)
    """
    return _heat_tax_accumulation_numba(n_cuts, depth, gamma0, decay_rate)


# ============================================================================
# Benchmark
# ============================================================================

def benchmark():
    """Run performance benchmark"""
    import time
    
    print("=" * 60)
    print("MSS-AI Numba Benchmark")
    print("=" * 60)
    
    # Percolation benchmark
    print("\n1. Percolation Simulation")
    p_values = np.linspace(0.3, 0.7, 20)
    
    start = time.time()
    results = run_percolation_batch(p_values, grid_size=50, n_samples=50)
    elapsed = time.time() - start
    
    print(f"   Grid: 50×50, Samples: 50, Points: 20")
    print(f"   Time: {elapsed:.3f}s")
    print(f"   Throughput: {20 * 50 / elapsed:.1f} sims/s")
    print(f"   Critical p ≈ {p_values[np.argmax(results > 0.5)]:.3f}")
    
    # ETA benchmark
    print("\n2. ETA Dynamics")
    start = time.time()
    T = run_eta_dynamics(n_steps=10000)
    elapsed = time.time() - start
    
    print(f"   Steps: 10000")
    print(f"   Time: {elapsed:.3f}s")
    print(f"   Final T: {T[-1]:.4f}")
    
    # Heat tax benchmark
    print("\n3. Heat Tax Accumulation")
    start = time.time()
    cuts, taxes, cumulative = run_heat_tax(n_cuts=100)
    elapsed = time.time() - start
    
    print(f"   Cuts: 100")
    print(f"   Time: {elapsed:.3f}s")
    print(f"   Total tax: {cumulative[-1]:.4f}")
    
    print("\n" + "=" * 60)
    print("Benchmark complete")
    print("=" * 60)


if __name__ == "__main__":
    benchmark()
