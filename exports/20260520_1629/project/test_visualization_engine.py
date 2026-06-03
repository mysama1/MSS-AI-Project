"""
Tests for MSS-AI Visualization Engine
"""

import unittest
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from visualization_engine import (
    ChartType, ChartConfig, ChartData,
    ASCIIChartRenderer, VisualizationEngine,
    create_dashboard
)


class TestChartConfig(unittest.TestCase):
    """Test chart configuration"""
    
    def test_default_config(self):
        """Test default configuration"""
        config = ChartConfig(chart_type=ChartType.LINE)
        self.assertEqual(config.width, 800)
        self.assertEqual(config.height, 600)
        self.assertTrue(config.show_legend)
        self.assertTrue(config.show_grid)
    
    def test_custom_config(self):
        """Test custom configuration"""
        config = ChartConfig(
            chart_type=ChartType.BAR,
            title="Test Chart",
            width=400,
            height=300,
            show_legend=False
        )
        self.assertEqual(config.title, "Test Chart")
        self.assertEqual(config.width, 400)
        self.assertFalse(config.show_legend)


class TestASCIIChartRenderer(unittest.TestCase):
    """Test ASCII chart renderer"""
    
    def test_line_chart_basic(self):
        """Test basic line chart rendering"""
        data = ChartData(
            series={'Test': [0, 0.5, 1.0]},
            labels=['A', 'B', 'C']
        )
        config = ChartConfig(
            chart_type=ChartType.LINE,
            title="Test Line Chart"
        )
        
        renderer = ASCIIChartRenderer()
        result = renderer.render_line_chart(data, config)
        
        self.assertIn("Test Line Chart", result)
        self.assertIn("Legend:", result)
    
    def test_line_chart_empty(self):
        """Test line chart with empty data"""
        data = ChartData()
        config = ChartConfig(chart_type=ChartType.LINE)
        
        renderer = ASCIIChartRenderer()
        result = renderer.render_line_chart(data, config)
        
        self.assertIn("[No data]", result)
    
    def test_bar_chart(self):
        """Test bar chart rendering"""
        data = ChartData(
            series={'Values': [10, 20, 30]},
            labels=['A', 'B', 'C']
        )
        config = ChartConfig(
            chart_type=ChartType.BAR,
            title="Test Bar Chart"
        )
        
        renderer = ASCIIChartRenderer()
        result = renderer.render_bar_chart(data, config)
        
        self.assertIn("Test Bar Chart", result)
        self.assertIn("10.000", result)
        self.assertIn("30.000", result)
    
    def test_radar_chart(self):
        """Test radar chart rendering"""
        data = ChartData(
            series={'Score': [0.8, 0.6, 0.9, 0.7]},
            labels=['A', 'B', 'C', 'D']
        )
        config = ChartConfig(
            chart_type=ChartType.RADAR,
            title="Test Radar"
        )
        
        renderer = ASCIIChartRenderer()
        result = renderer.render_radar_chart(data, config)
        
        self.assertIn("Test Radar", result)
        self.assertIn("Average:", result)
    
    def test_heatmap(self):
        """Test heatmap rendering"""
        data = ChartData(
            series={
                'Row1': [0.1, 0.5, 0.9],
                'Row2': [0.3, 0.7, 0.2]
            },
            labels=['Row1', 'Row2'],
            categories=['Row1', 'Row2']
        )
        config = ChartConfig(
            chart_type=ChartType.HEATMAP,
            title="Test Heatmap"
        )
        
        renderer = ASCIIChartRenderer()
        result = renderer.render_heatmap(data, config)
        
        self.assertIn("Test Heatmap", result)
        self.assertIn("Scale:", result)
    
    def test_table(self):
        """Test table rendering"""
        data = ChartData(
            series={
                'Col1': [1.0, 2.0, 3.0],
                'Col2': [4.0, 5.0, 6.0]
            }
        )
        config = ChartConfig(
            chart_type=ChartType.TABLE,
            title="Test Table"
        )
        
        renderer = ASCIIChartRenderer()
        result = renderer.render_table(data, config)
        
        self.assertIn("Test Table", result)
        self.assertIn("Col1", result)
        self.assertIn("Col2", result)


class TestVisualizationEngine(unittest.TestCase):
    """Test visualization engine"""
    
    def setUp(self):
        self.engine = VisualizationEngine()
    
    def test_render_line(self):
        """Test render line chart"""
        data = ChartData(series={'Test': [0, 1, 2]})
        config = ChartConfig(chart_type=ChartType.LINE)
        
        result = self.engine.render(data, config)
        self.assertIn("Legend:", result)
    
    def test_render_simulation_result(self):
        """Test render simulation result"""
        sim_result = {
            'sim_type': 'eta_dynamics',
            'time_series': {'T': [0.1, 0.5, 0.9]},
            'converged': True,
            'iterations': 100
        }
        
        result = self.engine.render_simulation_result(sim_result)
        self.assertIn("eta_dynamics", result)
    
    def test_render_resilience_scan(self):
        """Test render resilience scan"""
        scan_result = {
            'organization': 'TestOrg',
            'departments': [
                {'name': 'R&D', 'phi': 0.85},
                {'name': 'Marketing', 'phi': 0.72}
            ]
        }
        
        result = self.engine.render_resilience_scan(scan_result)
        self.assertIn("TestOrg", result)
        self.assertIn("R&D", result)
    
    def test_render_kb_summary(self):
        """Test render KB summary"""
        kb_data = {
            'layer_distribution': {
                'L1': 22,
                'L2': 27,
                'L3': 17
            }
        }
        
        result = self.engine.render_knowledge_base_summary(kb_data)
        self.assertIn("Knowledge Base", result)
        self.assertIn("L1", result)
    
    def test_render_compliance_report(self):
        """Test render compliance report"""
        analysis = {
            'confidence': 0.85,
            'rsca_compliance': 0.92,
            'layer': 'L2'
        }
        
        result = self.engine.render_compliance_report(analysis)
        self.assertIn("Compliance", result)


class TestDashboard(unittest.TestCase):
    """Test dashboard creation"""
    
    def test_create_dashboard(self):
        """Test dashboard generation"""
        status = {
            'status': 'operational',
            'uptime': 3600,
            'health_score': 0.92,
            'knowledge_base_entries': 312,
            'tests_passed': 294,
            'tests_total': 294
        }
        
        result = create_dashboard(status)
        
        self.assertIn("MSS-AI SYSTEM DASHBOARD", result)
        self.assertIn("operational", result)
        self.assertIn("312", result)
        self.assertIn("294/294", result)


if __name__ == "__main__":
    unittest.main(verbosity=2)
