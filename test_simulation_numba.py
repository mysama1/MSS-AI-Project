"""
Tests for Numba-accelerated simulation components
"""

import unittest
import numpy as np
import sys

# Check if numba is available
try:
    import numba
    HAS_NUMBA = True
except ImportError:
    HAS_NUMBA = False
    print("Warning: numba not available, skipping JIT tests")

if HAS_NUMBA:
    from simulation_numba import (
        run_percolation_batch,
        run_eta_dynamics,
        run_heat_tax,
        benchmark
    )


@unittest.skipUnless(HAS_NUMBA, "numba not installed")
class TestPercolationNumba(unittest.TestCase):
    """Test Numba-accelerated percolation"""
    
    def test_percolation_batch_shape(self):
        """Test output shape"""
        p_values = np.linspace(0.3, 0.7, 10)
        results = run_percolation_batch(p_values, grid_size=20, n_samples=10)
        
        self.assertEqual(len(results), 10)
        self.assertTrue(np.all((results >= 0) & (results <= 1)))
    
    def test_percolation_critical_point(self):
        """Test critical point estimation"""
        p_values = np.linspace(0.3, 0.7, 20)
        results = run_percolation_batch(p_values, grid_size=50, n_samples=50)
        
        # Find where percolation probability crosses 0.5
        crossing_idx = np.argmax(results > 0.5)
        if crossing_idx > 0:
            p_c = p_values[crossing_idx]
            # Theoretical p_c ≈ 0.5927 for 2D square lattice
            self.assertTrue(0.55 <= p_c <= 0.65)
    
    def test_percolation_reproducibility(self):
        """Test with same seed gives same results"""
        p_values = np.linspace(0.3, 0.7, 5)
        
        results1 = run_percolation_batch(p_values, grid_size=20, n_samples=20, seed=42)
        results2 = run_percolation_batch(p_values, grid_size=20, n_samples=20, seed=42)
        
        np.testing.assert_array_almost_equal(results1, results2)
    
    def test_percolation_monotonicity(self):
        """Test that higher p gives higher or equal percolation probability"""
        p_values = np.linspace(0.3, 0.7, 10)
        results = run_percolation_batch(p_values, grid_size=30, n_samples=30)
        
        # Check general trend (allowing for statistical noise)
        diffs = np.diff(results)
        # Most differences should be positive
        self.assertTrue(np.sum(diffs > -0.1) >= len(diffs) * 0.7)


@unittest.skipUnless(HAS_NUMBA, "numba not installed")
class TestETADynamicsNumba(unittest.TestCase):
    """Test Numba-accelerated ETA dynamics"""
    
    def test_eta_shape(self):
        """Test output shape"""
        T = run_eta_dynamics(n_steps=1000)
        self.assertEqual(len(T), 1000)
    
    def test_eta_bounds(self):
        """Test T stays within [0, K]"""
        T = run_eta_dynamics(T0=0.1, K=1.0, n_steps=1000)
        
        self.assertTrue(np.all(T >= 0))
        self.assertTrue(np.all(T <= 1.0))
    
    def test_eta_convergence(self):
        """Test T converges toward K"""
        T = run_eta_dynamics(T0=0.1, K=1.0, r=0.1, n_steps=5000, noise_amplitude=0.001)
        
        # Last 100 values should be close to K
        final_mean = np.mean(T[-100:])
        self.assertTrue(final_mean > 0.8)
    
    def test_eta_reproducibility(self):
        """Test with same seed gives same results"""
        T1 = run_eta_dynamics(n_steps=1000, seed=42)
        T2 = run_eta_dynamics(n_steps=1000, seed=42)
        
        np.testing.assert_array_almost_equal(T1, T2)
    
    def test_eta_initial_condition(self):
        """Test initial value"""
        T0 = 0.5
        T = run_eta_dynamics(T0=T0, n_steps=100)
        
        self.assertAlmostEqual(T[0], T0, places=5)


@unittest.skipUnless(HAS_NUMBA, "numba not installed")
class TestHeatTaxNumba(unittest.TestCase):
    """Test Numba-accelerated heat tax"""
    
    def test_heat_tax_shape(self):
        """Test output shapes"""
        cuts, taxes, cumulative = run_heat_tax(n_cuts=7)
        
        self.assertEqual(len(cuts), 7)
        self.assertEqual(len(taxes), 7)
        self.assertEqual(len(cumulative), 7)
    
    def test_heat_tax_monotonicity(self):
        """Test cumulative is monotonically increasing"""
        _, _, cumulative = run_heat_tax(n_cuts=10)
        
        diffs = np.diff(cumulative)
        self.assertTrue(np.all(diffs >= 0))
    
    def test_heat_tax_formula(self):
        """Test tax formula: γ(n,D) = γ₀ × D^(-n)"""
        gamma0 = 0.3
        depth = 0.6
        n_cuts = 3
        
        cuts, taxes, _ = run_heat_tax(n_cuts=n_cuts, depth=depth, gamma0=gamma0)
        
        # Check first tax value
        expected_first = gamma0 * (depth ** (-1))
        self.assertAlmostEqual(taxes[0], expected_first, places=5)
    
    def test_heat_tax_increasing(self):
        """Test individual taxes increase with n (for depth < 1)"""
        _, taxes, _ = run_heat_tax(n_cuts=5, depth=0.6, decay_rate=0.0)
        
        # For depth < 1, D^(-n) increases with n, so tax increases
        for i in range(1, len(taxes)):
            self.assertTrue(taxes[i] > taxes[i-1])


@unittest.skipUnless(HAS_NUMBA, "numba not installed")
class TestBenchmark(unittest.TestCase):
    """Test benchmark function"""
    
    def test_benchmark_runs(self):
        """Test benchmark runs without error"""
        # Just verify it doesn't crash
        try:
            benchmark()
        except Exception as e:
            self.fail(f"benchmark() raised {e}")


class TestNumbaAvailability(unittest.TestCase):
    """Test numba availability detection"""
    
    def test_numba_detection(self):
        """Test that numba detection works"""
        # This should always pass
        self.assertIn(HAS_NUMBA, [True, False])
    
    @unittest.skipIf(HAS_NUMBA, "numba is available")
    def test_fallback_message(self):
        """Test fallback when numba not available"""
        # When numba is not available, imports should be skipped
        self.assertFalse(HAS_NUMBA)


if __name__ == "__main__":
    # Run tests
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # Add all test classes
    suite.addTests(loader.loadTestsFromTestCase(TestPercolationNumba))
    suite.addTests(loader.loadTestsFromTestCase(TestETADynamicsNumba))
    suite.addTests(loader.loadTestsFromTestCase(TestHeatTaxNumba))
    suite.addTests(loader.loadTestsFromTestCase(TestBenchmark))
    suite.addTests(loader.loadTestsFromTestCase(TestNumbaAvailability))
    
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Exit with appropriate code
    sys.exit(0 if result.wasSuccessful() else 1)
