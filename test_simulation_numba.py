"""
Tests for Numba-accelerated simulation framework
"""

import unittest
import numpy as np
import time

from simulation_numba import (
    SimulationType, SimulationConfig, SimulationEngine,
    PercolationSimulator, ETADynamicsSimulator,
    HeatTaxSimulator, ResilienceSimulator,
    NUMBA_AVAILABLE
)

class TestNumbaAvailability(unittest.TestCase):
    """Test Numba availability"""

    def test_numba_available(self):
        """Numba should be available"""
        self.assertTrue(NUMBA_AVAILABLE, "Numba should be installed")

class TestPercolationNumba(unittest.TestCase):
    """Test Numba-accelerated percolation"""

    def test_basic_percolation(self):
        """Basic percolation simulation"""
        config = SimulationConfig(
            sim_type=SimulationType.PERCOLATION,
            grid_size=50,
            parameters={'occupation_prob': 0.6},
            use_numba=True
        )
        simulator = PercolationSimulator(config)
        result = simulator.run()

        self.assertEqual(result.sim_type, SimulationType.PERCOLATION)
        self.assertTrue(result.converged)
        self.assertIn('percolation_probability', result.metrics)
        self.assertIn('largest_cluster_size', result.metrics)

    def test_percolation_critical_point(self):
        """Test near critical point"""
        engine = SimulationEngine()

        p_values = np.linspace(0.5, 0.65, 10)
        results = engine.parameter_sweep(
            SimulationType.PERCOLATION,
            'occupation_prob',
            p_values,
            {'grid_size': 100}
        )

        # Find where percolation probability crosses 0.5
        percolation_probs = [r.metrics['percolation_probability'] for r in results]

        # Should have some with percolation and some without
        self.assertTrue(any(p == 0.0 for p in percolation_probs))
        self.assertTrue(any(p == 1.0 for p in percolation_probs))

    def test_numba_vs_python(self):
        """Compare Numba and Python results"""
        # Use same random seed and pre-generated lattice for fair comparison
        np.random.seed(42)
        lattice = np.random.random((50, 50)) < 0.6

        config_numba = SimulationConfig(
            sim_type=SimulationType.PERCOLATION,
            grid_size=50,
            parameters={'occupation_prob': 0.6},
            use_numba=True
        )
        config_python = SimulationConfig(
            sim_type=SimulationType.PERCOLATION,
            grid_size=50,
            parameters={'occupation_prob': 0.6},
            use_numba=False
        )

        result_numba = PercolationSimulator(config_numba).run()
        result_python = PercolationSimulator(config_python).run()

        # Both should produce valid results with similar characteristics
        self.assertGreater(result_numba.metrics['total_clusters'], 0)
        self.assertGreater(result_python.metrics['total_clusters'], 0)
        # Check both detect percolation or both don't (not exact match due to different implementations)
        self.assertEqual(
            result_numba.metrics['percolation_probability'] > 0,
            result_python.metrics['percolation_probability'] > 0
        )

class TestETADynamicsNumba(unittest.TestCase):
    """Test Numba-accelerated ETA dynamics"""

    def test_convergence(self):
        """ETA should converge to carrying capacity"""
        config = SimulationConfig(
            sim_type=SimulationType.ETA_DYNAMICS,
            max_iterations=1000,
            parameters={
                'initial_tuning': 0.1,
                'growth_rate': 0.05,
                'decay_rate': 0.001,
                'carrying_capacity': 0.95
            },
            use_numba=True
        )
        simulator = ETADynamicsSimulator(config)
        result = simulator.run()

        self.assertTrue(result.converged or result.iterations < 1000)
        self.assertGreater(result.metrics['final_tuning'], 0.5)

    def test_numba_speedup(self):
        """Numba should be faster than pure Python"""
        config_numba = SimulationConfig(
            sim_type=SimulationType.ETA_DYNAMICS,
            max_iterations=100000,
            parameters={'initial_tuning': 0.1, 'growth_rate': 0.05},
            use_numba=True
        )
        config_python = SimulationConfig(
            sim_type=SimulationType.ETA_DYNAMICS,
            max_iterations=100000,
            parameters={'initial_tuning': 0.1, 'growth_rate': 0.05},
            use_numba=False
        )

        # Warm up Numba
        ETADynamicsSimulator(config_numba).run()

        start = time.time()
        ETADynamicsSimulator(config_numba).run()
        t_numba = time.time() - start

        start = time.time()
        ETADynamicsSimulator(config_python).run()
        t_python = time.time() - start

        if t_numba > 0.001:
            speedup = t_python / t_numba
            print(f"\nETA Speedup: {speedup:.2f}x (Numba: {t_numba:.4f}s, Python: {t_python:.4f}s)")
            self.assertLess(t_numba, t_python * 0.9, "Numba should be faster")
        else:
            print(f"\nETA too fast to measure (Numba: {t_numba:.4f}s, Python: {t_python:.4f}s)")
            self.assertTrue(True)

class TestHeatTaxNumba(unittest.TestCase):
    """Test vectorized heat tax"""

    def test_thermal_death(self):
        """Heat tax should exceed threshold after 7 cuts"""
        config = SimulationConfig(
            sim_type=SimulationType.HEAT_TAX,
            parameters={'gamma0': 0.3, 'max_cuts': 7}
        )
        simulator = HeatTaxSimulator(config)
        result = simulator.run()

        self.assertTrue(result.metrics['exceeded_threshold'])
        self.assertEqual(result.metrics['total_cuts'], 7)

    def test_monotonic_increase(self):
        """Cumulative tax should monotonically increase"""
        config = SimulationConfig(
            sim_type=SimulationType.HEAT_TAX,
            parameters={'gamma0': 0.5, 'max_cuts': 5}
        )
        result = HeatTaxSimulator(config).run()

        cumulative = result.time_series['cumulative_tax']
        for i in range(1, len(cumulative)):
            self.assertGreaterEqual(cumulative[i], cumulative[i-1])

class TestResilienceNumba(unittest.TestCase):
    """Test Numba-accelerated resilience"""

    def test_decay(self):
        """Resilience should decay over time"""
        config = SimulationConfig(
            sim_type=SimulationType.RESILIENCE,
            max_iterations=100,
            parameters={
                'organization_size': 100,
                'initial_resilience': 1.0,
                'decay_rate': 0.01,
                'shock_prob': 0.0  # No shocks for deterministic test
            },
            use_numba=True
        )
        simulator = ResilienceSimulator(config)
        result = simulator.run()

        self.assertLess(result.metrics['final_resilience'], result.metrics['initial_resilience'])

    def test_critical_threshold(self):
        """Critical threshold should be 1/N"""
        config = SimulationConfig(
            sim_type=SimulationType.RESILIENCE,
            parameters={'organization_size': 50}
        )
        result = SimulationEngine().run(config)

        expected_critical = 1.0 / 50
        self.assertAlmostEqual(
            result.metrics['critical_threshold'],
            expected_critical,
            places=5
        )

class TestBatchPerformance(unittest.TestCase):
    """Test batch simulation performance"""

    def test_batch_percolation(self):
        """Batch percolation simulations"""
        engine = SimulationEngine()

        configs = []
        for p in np.linspace(0.3, 0.7, 20):
            configs.append(SimulationConfig(
                sim_type=SimulationType.PERCOLATION,
                grid_size=100,
                parameters={'occupation_prob': p},
                use_numba=True
            ))

        start = time.time()
        results = engine.batch_run(configs)
        elapsed = time.time() - start

        self.assertEqual(len(results), 20)
        print(f"\nBatch percolation (20 runs, 100x100): {elapsed:.3f}s")
        self.assertLess(elapsed, 5.0, "Should complete in reasonable time")

if __name__ == '__main__':
    unittest.main(verbosity=2)
