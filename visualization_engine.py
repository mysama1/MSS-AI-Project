"""
MSS-AI Visualization Engine
Generate charts, graphs, and visual reports from simulation and analysis data
"""

import json
import os
import time
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum
import base64
from io import StringIO

class ChartType(Enum):
    """Supported chart types"""
    LINE = "line"                    # Time series line chart
    BAR = "bar"                      # Bar chart
    SCATTER = "scatter"              # Scatter plot
    HEATMAP = "heatmap"              # Heatmap
    RADAR = "radar"                  # Radar/spider chart
    HISTOGRAM = "histogram"          # Distribution histogram
    NETWORK = "network"              # Network/graph visualization
    TABLE = "table"                  # Data table

@dataclass
class ChartConfig:
    """Chart configuration"""
    chart_type: ChartType
    title: str = ""
    x_label: str = ""
    y_label: str = ""
    width: int = 800
    height: int = 600
    colors: List[str] = field(default_factory=lambda: [
        "#4A90E2", "#E94B3C", "#50C878", "#F5A623", "#9013FE",
        "#BD10E0", "#417505", "#7ED321", "#B8E986", "#F8E71C"
    ])
    show_legend: bool = True
    show_grid: bool = True

@dataclass
class ChartData:
    """Chart data container"""
    series: Dict[str, List[float]] = field(default_factory=dict)
    labels: List[str] = field(default_factory=list)
    categories: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

class ASCIIChartRenderer:
    """
    ASCII-based chart renderer for terminal output
    No external dependencies required
    """

    @staticmethod
    def render_line_chart(data: ChartData, config: ChartConfig) -> str:
        """Render line chart in ASCII"""
        lines = []
        lines.append(f"{'=' * 60}")
        lines.append(f"  {config.title}")
        lines.append(f"{'=' * 60}")

        if not data.series:
            lines.append("  [No data]")
            return "\n".join(lines)

        # Find min/max for scaling
        all_values = []
        for series_data in data.series.values():
            all_values.extend(series_data)

        if not all_values:
            lines.append("  [No data]")
            return "\n".join(lines)

        min_val = min(all_values)
        max_val = max(all_values)
        val_range = max_val - min_val if max_val != min_val else 1

        # Chart dimensions
        chart_width = 50
        chart_height = 15

        # Build chart
        lines.append(f"  {config.y_label}")
        for row in range(chart_height, -1, -1):
            y_val = min_val + (val_range * row / chart_height)
            row_str = f"  {y_val:6.2f} |"

            for col in range(chart_width + 1):
                x_ratio = col / chart_width
                x_idx = int(x_ratio * (len(all_values) - 1))

                # Check if any series has value at this position
                has_point = False
                for series_data in data.series.values():
                    if x_idx < len(series_data):
                        val = series_data[x_idx]
                        val_ratio = (val - min_val) / val_range
                        val_row = int(val_ratio * chart_height)
                        if val_row == row:
                            has_point = True
                            break

                if has_point:
                    row_str += "*"
                else:
                    row_str += " "

            lines.append(row_str)

        lines.append(f"         {'-' * (chart_width + 1)}")
        lines.append(f"  {config.x_label}")

        # Legend
        if config.show_legend:
            lines.append("\n  Legend:")
            for i, (name, _) in enumerate(data.series.items()):
                symbol = ["*", "#", "@", "+", "x"][i % 5]
                lines.append(f"    {symbol} {name}")

        return "\n".join(lines)

    @staticmethod
    def render_bar_chart(data: ChartData, config: ChartConfig) -> str:
        """Render bar chart in ASCII"""
        lines = []
        lines.append(f"{'=' * 60}")
        lines.append(f"  {config.title}")
        lines.append(f"{'=' * 60}")

        if not data.series:
            lines.append("  [No data]")
            return "\n".join(lines)

        # Use first series
        series_name = list(data.series.keys())[0]
        values = data.series[series_name]
        labels = data.labels if data.labels else [str(i) for i in range(len(values))]

        max_val = max(values) if values else 1
        bar_width = 40

        for label, value in zip(labels, values):
            bar_len = int((value / max_val) * bar_width) if max_val > 0 else 0
            bar = "█" * bar_len
            lines.append(f"  {label:15} |{bar:<{bar_width}}| {value:.3f}")

        lines.append(f"  {'-' * 60}")
        lines.append(f"  {config.x_label}")

        return "\n".join(lines)

    @staticmethod
    def render_radar_chart(data: ChartData, config: ChartConfig) -> str:
        """Render radar chart in ASCII"""
        lines = []
        lines.append(f"{'=' * 60}")
        lines.append(f"  {config.title}")
        lines.append(f"{'=' * 60}")

        if not data.series:
            lines.append("  [No data]")
            return "\n".join(lines)

        # Use first series for radar
        series_name = list(data.series.keys())[0]
        values = data.series[series_name]
        labels = data.labels if data.labels else [f"D{i}" for i in range(len(values))]

        max_val = max(values) if values else 1

        lines.append("\n  Dimensions:")
        for label, value in zip(labels, values):
            pct = (value / max_val) * 100 if max_val > 0 else 0
            bar = "█" * int(pct / 5)
            lines.append(f"    {label:15} [{bar:<20}] {value:.3f} ({pct:.1f}%)")

        # Calculate average
        avg = sum(values) / len(values) if values else 0
        lines.append(f"\n  Average: {avg:.3f}")
        lines.append(f"  Max: {max_val:.3f}")
        lines.append(f"  Min: {min(values):.3f}" if values else "  Min: N/A")

        return "\n".join(lines)

    @staticmethod
    def render_heatmap(data: ChartData, config: ChartConfig) -> str:
        """Render heatmap in ASCII with grayscale blocks"""
        lines = []
        lines.append(f"{'=' * 60}")
        lines.append(f"  {config.title}")
        lines.append(f"{'=' * 60}")

        if not data.series or not data.categories:
            lines.append("  [No data]")
            return "\n".join(lines)

        # Get matrix data
        matrix = []
        for series_name in data.categories:
            if series_name in data.series:
                matrix.append(data.series[series_name])

        if not matrix:
            lines.append("  [No data]")
            return "\n".join(lines)

        # Find min/max for scaling
        all_vals = [v for row in matrix for v in row]
        min_val = min(all_vals)
        max_val = max(all_vals)
        val_range = max_val - min_val if max_val != min_val else 1

        # Heatmap characters from low to high intensity
        chars = " ░▒▓█"

        lines.append(f"\n  {' ' * 10} " + " ".join(f"{i:2}" for i in range(len(matrix[0]))))
        lines.append(f"  {' ' * 10} " + "-" * (len(matrix[0]) * 3))

        for i, row in enumerate(matrix):
            label = data.labels[i] if i < len(data.labels) else f"R{i}"
            row_str = f"  {label:8} |"
            for val in row:
                idx = int(((val - min_val) / val_range) * (len(chars) - 1))
                row_str += f" {chars[idx]} "
            lines.append(row_str)

        lines.append(f"\n  Scale: {min_val:.3f} (low) → {max_val:.3f} (high)")

        return "\n".join(lines)

    @staticmethod
    def render_table(data: ChartData, config: ChartConfig) -> str:
        """Render data table"""
        lines = []
        lines.append(f"{'=' * 80}")
        lines.append(f"  {config.title}")
        lines.append(f"{'=' * 80}")

        if not data.series:
            lines.append("  [No data]")
            return "\n".join(lines)

        # Build table
        headers = ["Index"] + list(data.series.keys())
        col_width = 15

        # Header
        header_line = "  |"
        for h in headers:
            header_line += f" {h:^{col_width}} |"
        lines.append(header_line)
        lines.append("  " + "-" * (len(header_line) - 2))

        # Data rows
        max_len = max(len(v) for v in data.series.values())
        for i in range(max_len):
            row_line = f"  | {i:^{col_width}} |"
            for series_data in data.series.values():
                val = series_data[i] if i < len(series_data) else ""
                row_line += f" {val:^{col_width}.4f} |" if isinstance(val, float) else f" {str(val):^{col_width}} |"
            lines.append(row_line)

        return "\n".join(lines)

class VisualizationEngine:
    """
    Main visualization engine

    Generates various chart types from MSS-AI data
    """

    def __init__(self):
        self.renderer = ASCIIChartRenderer()
        self.renderers = {
            ChartType.LINE: self.renderer.render_line_chart,
            ChartType.BAR: self.renderer.render_bar_chart,
            ChartType.RADAR: self.renderer.render_radar_chart,
            ChartType.HEATMAP: self.renderer.render_heatmap,
            ChartType.TABLE: self.renderer.render_table,
        }

    def render(self, data: ChartData, config: ChartConfig) -> str:
        """Render chart based on configuration"""
        if config.chart_type not in self.renderers:
            return f"Chart type {config.chart_type.value} not yet implemented"

        return self.renderers[config.chart_type](data, config)

    def render_simulation_result(self, result: Dict[str, Any],
                                chart_type: ChartType = ChartType.LINE) -> str:
        """Render simulation result as chart"""
        # Extract time series data
        time_series = result.get('time_series', {})

        data = ChartData(
            series=time_series,
            metadata={
                'sim_type': result.get('sim_type', 'unknown'),
                'converged': result.get('converged', False),
                'iterations': result.get('iterations', 0)
            }
        )

        config = ChartConfig(
            chart_type=chart_type,
            title=f"Simulation: {result.get('sim_type', 'Unknown')}",
            x_label="Iteration",
            y_label="Value"
        )

        return self.render(data, config)

    def render_resilience_scan(self, scan_result: Dict[str, Any]) -> str:
        """Render organizational resilience scan results"""
        # Extract department data
        departments = scan_result.get('departments', [])

        if not departments:
            return "No department data available"

        # Build radar chart data
        dept_names = [d.get('name', f'Dept {i}') for i, d in enumerate(departments)]
        phi_scores = [d.get('phi', 0) for d in departments]

        data = ChartData(
            series={'Resilience (φ)': phi_scores},
            labels=dept_names
        )

        config = ChartConfig(
            chart_type=ChartType.RADAR,
            title=f"Organizational Resilience Scan: {scan_result.get('organization', 'Unknown')}",
            x_label="Departments",
            y_label="φ Score"
        )

        return self.render(data, config)

    def render_knowledge_base_summary(self, kb_data: Dict[str, Any]) -> str:
        """Render knowledge base summary"""
        layer_dist = kb_data.get('layer_distribution', {})

        if not layer_dist:
            return "No layer distribution data"

        categories = list(layer_dist.keys())
        values = list(layer_dist.values())

        data = ChartData(
            series={'Entries': values},
            labels=categories
        )

        config = ChartConfig(
            chart_type=ChartType.BAR,
            title="Knowledge Base Layer Distribution",
            x_label="Layer",
            y_label="Entry Count"
        )

        return self.render(data, config)

    def render_compliance_report(self, analysis_result: Dict[str, Any]) -> str:
        """Render compliance analysis report"""
        metrics = {
            'Confidence': analysis_result.get('confidence', 0),
            'RSCA Compliance': analysis_result.get('rsca_compliance', 0),
            'Layer Score': {
                'L1': 1.0 if analysis_result.get('layer') == 'L1' else 0,
                'L2': 1.0 if analysis_result.get('layer') == 'L2' else 0,
                'L3': 1.0 if analysis_result.get('layer') == 'L3' else 0
            }
        }

        # Create table
        data = ChartData(
            series={
                'Metric': ['Confidence', 'RSCA Compliance', 'Layer Match'],
                'Value': [
                    analysis_result.get('confidence', 0),
                    analysis_result.get('rsca_compliance', 0),
                    1.0 if analysis_result.get('layer') else 0
                ]
            }
        )

        config = ChartConfig(
            chart_type=ChartType.TABLE,
            title="Compliance Analysis Report",
            x_label="Metric",
            y_label="Score"
        )

        return self.render(data, config)

# ============================================================================
# Utility Functions
# ============================================================================

def create_simulation_visualization(sim_result: Dict[str, Any],
                                   output_file: Optional[str] = None) -> str:
    """Create visualization from simulation result"""
    engine = VisualizationEngine()
    chart = engine.render_simulation_result(sim_result)

    if output_file:
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(chart)

    return chart

def create_dashboard(system_status: Dict[str, Any]) -> str:
    """Create system status dashboard"""
    lines = []
    lines.append("╔" + "═" * 78 + "╗")
    lines.append("║" + " " * 20 + "MSS-AI SYSTEM DASHBOARD" + " " * 35 + "║")
    lines.append("╠" + "═" * 78 + "╣")

    # Status section
    lines.append("║  SYSTEM STATUS" + " " * 64 + "║")
    lines.append("║  " + "-" * 74 + "  ║")

    status = system_status.get('status', 'unknown')
    status_symbol = "✓" if status == 'operational' else "✗"
    lines.append(f"║  {status_symbol} Status: {status:15} Uptime: {system_status.get('uptime', 0):.1f}s" + " " * 30 + "║")
    lines.append(f"║  Health Score: {system_status.get('health_score', 0):.2f}" + " " * 56 + "║")
    lines.append(f"║  Knowledge Base: {system_status.get('knowledge_base_entries', 0)} entries" + " " * 48 + "║")
    lines.append(f"║  Tests: {system_status.get('tests_passed', 0)}/{system_status.get('tests_total', 0)} passed" + " " * 52 + "║")

    lines.append("╠" + "═" * 78 + "╣")

    # Components section
    lines.append("║  ACTIVE COMPONENTS" + " " * 59 + "║")
    lines.append("║  " + "-" * 74 + "  ║")

    components = [
        ("Symbolic Engine", "v3"),
        ("NL Bridge", "v2"),
        ("Health Monitor", "active"),
        ("Knowledge Base", "loaded"),
        ("Compliance Checker", "36 rules"),
    ]

    for name, status in components:
        lines.append(f"║  • {name:20} {status:15}" + " " * 35 + "║")

    lines.append("╚" + "═" * 78 + "╝")

    return "\n".join(lines)

# ============================================================================
# Main Entry Point
# ============================================================================

if __name__ == "__main__":
    print("MSS-AI Visualization Engine")
    print("=" * 60)

    engine = VisualizationEngine()

    # Example 1: Line chart
    print("\n1. Line Chart - ETA Dynamics")
    data = ChartData(
        series={
            'Tuning Degree': [0.1, 0.15, 0.22, 0.31, 0.45, 0.62, 0.78, 0.89, 0.95, 0.98],
            'Noise': [0.01, -0.02, 0.03, -0.01, 0.02, -0.03, 0.01, -0.02, 0.01, 0.0]
        }
    )
    config = ChartConfig(
        chart_type=ChartType.LINE,
        title="ETA Order Parameter Evolution",
        x_label="Time Step",
        y_label="Tuning Degree T"
    )
    print(engine.render(data, config))

    # Example 2: Bar chart
    print("\n2. Bar Chart - Layer Distribution")
    data = ChartData(
        series={'Entries': [22, 27, 17]},
        labels=['L1 (Hard Core)', 'L2 (Protective)', 'L3 (Heuristic)']
    )
    config = ChartConfig(
        chart_type=ChartType.BAR,
        title="Knowledge Base Layer Distribution",
        x_label="Layer",
        y_label="Entry Count"
    )
    print(engine.render(data, config))

    # Example 3: Radar chart
    print("\n3. Radar Chart - Resilience Scan")
    data = ChartData(
        series={'Resilience': [0.85, 0.72, 0.91, 0.68, 0.79]},
        labels=['R&D', 'Marketing', 'Operations', 'HR', 'Finance']
    )
    config = ChartConfig(
        chart_type=ChartType.RADAR,
        title="Organizational Resilience Scan",
        x_label="Departments",
        y_label="φ Score"
    )
    print(engine.render(data, config))

    # Example 4: Dashboard
    print("\n4. System Dashboard")
    status = {
        'status': 'operational',
        'uptime': 3600,
        'health_score': 0.92,
        'knowledge_base_entries': 312,
        'tests_passed': 294,
        'tests_total': 294
    }
    print(create_dashboard(status))

    print("\n" + "=" * 60)
    print("Visualization examples complete!")
