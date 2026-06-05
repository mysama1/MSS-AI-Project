"""
Tests for MSS-AI Simulation Framework
"""

import unittest
import sys
import os
import numpy as np

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from simulation_framework import (
    SimulationConfig, SimulationType, SimulationResult,
    PercolationSimulator, ETADynamicsSimulator, HeatTaxSimulator,
    ResilienceSimulator, SimulationEngine,
    find_critical_point, export_results
)


class TestSimulationConfig(unittest.TestCase):
    """Test simulation configuration"""
    
    def test_default_config(self):
        """Test default configuration"""
        config = SimulationConfig(sim_type=SimulationType.PERCOLATION)
        self.assertEqual(config.grid_size, 100)
        self.assertEqual(config.max_iterations, 1000)
        self.assertEqual(config.tolerance, 1e-6)
    
    def test_custom_config(self):
        """Test custom configuration"""
        config = SimulationConfig(
            sim_type=SimulationType.ETA_DYNAMICS,
            grid_size=50,
            max_iterations=500,
            parameters={'growth_rate': 0.05}
        )
        self.assertEqual(config.grid_size, 50)
        self.assertEqual(config.parameters['growth_rate'], 0.05)


class TestPercolationSimulator(unittest.TestCase):
    """Test percolation simulation"""
    
    def test_low_probability(self):
        """Test percolation at low probability"""
        config = SimulationConfig(
            sim_type=SimulationType.PERCOLATION,
            grid_size=20,
            parameters={'occupation_prob': 0.1}
        )
        sim = PercolationSimulator(config)
        result = sim.run()
        
        self.assertEqual(result.sim_type, SimulationType.PERCOLATION)
        self.assertTrue(result.converged)
        self.assertLess(result.metrics['percolation_probability'], 0.5)
    
    def test_high_probability(self):
        """Test percolation at high probability"""
        config = SimulationConfig(
            sim_type=SimulationType.PERCOLATION,
            grid_size=20,
            parameters={'occupation_prob': 0.9}
        )
        sim = PercolationSimulator(config)
        result = sim.run()
        
        self.assertGreater(result.metrics['percolation_probability'], 0.5)
        self.assertGreater(result.metrics['largest_cluster_fraction'], 0.5)
    
    def test_cluster_labeling(self):
        """Test cluster labeling correctness"""
        config = SimulationConfig(
            sim_type=SimulationType.PERCOLATION,
            grid_size=10,
            parameters={'occupation_prob': 0.5}
        )
        sim = PercolationSimulator(config)
        result = sim.run()
        
        self.assertGreaterEqual(result.metrics['total_clusters'], 0)
        self.assertLessEqual(result.metrics['total_clusters'], 100)


class TestETADynamics(unittest.TestCase):
    """Test ETA dynamics simulation"""
    
    def test_convergence(self):
        """Test ETA convergence to carrying capacity"""
        config = SimulationConfig(
            sim_type=SimulationType.ETA_DYNAMICS,
            max_iterations=1000,
            parameters={
                'initial_tuning': 0.1,
                'growth_rate': 0.1,
                'decay_rate': 0.001,
                'carrying_capacity': 0.8
            }
        )
        sim = ETADynamicsSimulator(config)
        result = sim.run()
        
        self.assertTrue(result.converged)
        self.assertGreater(result.metrics['final_tuning'], 0.7)
        self.assertLessEqual(result.metrics['final_tuning'], 1.0)
    
    def test_time_series(self):
        """Test time series generation"""
        config = SimulationConfig(
            sim_type=SimulationType.ETA_DYNAMICS,
            parameters={'initial_tuning': 0.5}
        )
        sim = ETADynamicsSimulator(config)
        result = sim.run()
        
        self.assertIn('T', result.time_series)
        self.assertIn('dT', result.time_series)
        self.assertGreater(len(result.time_series['T']), 1)


class TestHeatTax(unittest.TestCase):
    """Test heat tax simulation"""
    
    def test_cumulative_tax(self):
        """Test cumulative tax increases"""
        config = SimulationConfig(
            sim_type=SimulationType.HEAT_TAX,
            parameters={
                'gamma0': 0.3,
                'max_cuts': 5
            }
        )
        sim = HeatTaxSimulator(config)
        result = sim.run()
        
        self.assertEqual(result.iterations, 5)
        self.assertGreater(result.metrics['cumulative_tax'], 0)
        self.assertEqual(len(result.time_series['heat_tax']), 6)  # 0 to 5
    
    def test_thermal_death(self):
        """Test thermal death threshold"""
        config = SimulationConfig(
            sim_type=SimulationType.HEAT_TAX,
            parameters={
                'gamma0': 1.0,
                'max_cuts': 7
            }
        )
        sim = HeatTaxSimulator(config)
        result = sim.run()
        
        self.assertEqual(result.metrics['thermal_death_threshold'], 7)


class TestResilience(unittest.TestCase):
    """Test resilience simulation"""
    
    def test_critical_scaling(self):
        """Test critical threshold scaling"""
        config = SimulationConfig(
            sim_type=SimulationType.RESILIENCE,
            parameters={
                'organization_size': 100,
                'initial_resilience': 1.0,
                'decay_rate': 0.0,
                'shock_prob': 0.0
            }
        )
        sim = ResilienceSimulator(config)
        result = sim.run()
        
        self.assertAlmostEqual(result.metrics['critical_threshold'], 0.01, places=5)
        self.assertAlmostEqual(result.metrics['final_resilience'], 1.0, places=5)
    
    def test_decay(self):
        """Test natural decay"""
        config = SimulationConfig(
            sim_type=SimulationType.RESILIENCE,
            max_iterations=100,
            parameters={
                'organization_size': 1000,
                'initial_resilience': 1.0,
                'decay_rate': 0.01,
                'shock_prob': 0.0
            }
        )
        sim = ResilienceSimulator(config)
        result = sim.run()
        
        self.assertLess(result.metrics['final_resilience'], 1.0)


class TestSimulationEngine(unittest.TestCase):
    """Test simulation engine"""
    
    def setUp(self):
        self.engine = SimulationEngine()
    
    def test_run_percolation(self):
        """Test engine runs percolation"""
        config = SimulationConfig(
            sim_type=SimulationType.PERCOLATION,
            parameters={'occupation_prob': 0.5}
        )
        result = self.engine.run(config)
        
        self.assertEqual(result.sim_type, SimulationType.PERCOLATION)
    
    def test_batch_run(self):
        """Test batch execution"""
        configs = [
            SimulationConfig(
                sim_type=SimulationType.HEAT_TAX,
                parameters={'gamma0': 0.1}
            ),
            SimulationConfig(
                sim_type=SimulationType.HEAT_TAX,
                parameters={'gamma0': 0.5}
            )
        ]
        results = self.engine.batch_run(configs)
        
        self.assertEqual(len(results), 2)
        self.assertLess(
            results[0].metrics['cumulative_tax'],
            results[1].metrics['cumulative_tax']
        )
    
    def test_parameter_sweep(self):
        """Test parameter sweep"""
        results = self.engine.parameter_sweep(
            SimulationType.PERCOLATION,
            'occupation_prob',
            [0.3, 0.5, 0.7],
            {'grid_size': 20}
        )
        
        self.assertEqual(len(results), 3)
        
        # Check increasing percolation probability
        probs = [r.metrics['percolation_probability'] for r in results]
        self.assertLessEqual(probs[0], probs[1])
        self.assertLessEqual(probs[1], probs[2])


class TestCriticalPoint(unittest.TestCase):
    """Test critical point finding"""
    
    def test_find_critical_point(self):
        """Test critical point estimation"""
        # Create mock results
        results = []
        for p in [0.3, 0.4, 0.5, 0.6, 0.7]:
            result = SimulationResult(
                sim_type=SimulationType.PERCOLATION,
                converged=True,
                iterations=1,
                final_state=np.array([0]),
                time_series={},
                metrics={'percolation_probability': 1.0 if p > 0.55 else 0.0},
                computation_time=0,
                parameters={'occupation_prob': p}
            )
            results.append(result)
        
        p_c = find_critical_point(results)
        self.assertIsNotNone(p_c)
        self.assertGreaterEqual(p_c, 0.5)
        self.assertLessEqual(p_c, 0.6)


if __name__ == "__main__":
    unittest.main(verbosity=2)
