"""
MSS Data Visualization Module
Provides visualization capabilities for experimental data
"""

import json
import math
from typing import Dict, List, Optional, Tuple
from datetime import datetime
from pathlib import Path

class DataVisualizer:
    """Visualize experimental data in text format"""
    
    def __init__(self, data_dir: str = r"C:\MSS-AI-Project\data"):
        self.data_dir = Path(data_dir)
    
    def load_experiment_data(self, experiment_id: str) -> List[Dict]:
        """Load experiment data from files"""
        exp_dir = self.data_dir / experiment_id
        if not exp_dir.exists():
            return []
        
        data = []
        for data_file in sorted(exp_dir.glob("data_*.jsonl")):
            with open(data_file, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        point = json.loads(line)
                        data.append(point)
                    except json.JSONDecodeError:
                        continue
        
        return data
    
    def generate_time_series(self, experiment_id: str, 
                            measurement_type: str,
                            width: int = 80,
                            height: int = 20) -> str:
        """
        Generate ASCII time series chart
        
        Args:
            experiment_id: Experiment ID
            measurement_type: Type of measurement to plot
            width: Chart width in characters
            height: Chart height in characters
        
        Returns:
            ASCII chart string
        """
        data = self.load_experiment_data(experiment_id)
        
        # Filter by measurement type
        filtered = [d for d in data if d.get('measurement_type') == measurement_type]
        
        if not filtered:
            return f"No data found for {measurement_type} in {experiment_id}"
        
        # Extract values
        values = [d['value'] for d in filtered]
        timestamps = [d['timestamp'] for d in filtered]
        
        if not values:
            return "No values found"
        
        # Calculate statistics
        min_val = min(values)
        max_val = max(values)
        mean_val = sum(values) / len(values)
        
        # Generate chart
        chart = []
        chart.append(f"Time Series: {experiment_id} - {measurement_type}")
        chart.append(f"Data points: {len(values)} | Min: {min_val:.4f} | Max: {max_val:.4f} | Mean: {mean_val:.4f}")
        chart.append("")
        
        # Create ASCII chart
        if max_val == min_val:
            # All values are the same
            chart.append("All values are identical")
            return "\n".join(chart)
        
        # Normalize values to chart height
        normalized = [(v - min_val) / (max_val - min_val) * (height - 1) for v in values]
        
        # Create grid
        grid = [[' ' for _ in range(width)] for _ in range(height)]
        
        # Plot points
        for i, norm_val in enumerate(normalized):
            x = int(i / len(normalized) * (width - 1))
            y = height - 1 - int(norm_val)
            if 0 <= y < height and 0 <= x < width:
                grid[y][x] = '*'
        
        # Draw axes
        for y in range(height):
            grid[y][0] = '|'
        for x in range(width):
            grid[height-1][x] = '-'
        grid[height-1][0] = '+'
        
        # Add to chart
        for row in grid:
            chart.append(''.join(row))
        
        # Add labels
        chart.append("")
        chart.append(f"{timestamps[0][:19]} ... {timestamps[-1][:19]}")
        
        return "\n".join(chart)
    
    def generate_histogram(self, experiment_id: str,
                          measurement_type: str,
                          bins: int = 10,
                          width: int = 60) -> str:
        """
        Generate ASCII histogram
        
        Args:
            experiment_id: Experiment ID
            measurement_type: Type of measurement
            bins: Number of bins
            width: Chart width in characters
        
        Returns:
            ASCII histogram string
        """
        data = self.load_experiment_data(experiment_id)
        filtered = [d for d in data if d.get('measurement_type') == measurement_type]
        
        if not filtered:
            return f"No data found for {measurement_type} in {experiment_id}"
        
        values = [d['value'] for d in filtered]
        
        if not values:
            return "No values found"
        
        min_val = min(values)
        max_val = max(values)
        
        if max_val == min_val:
            return "All values are identical"
        
        # Create bins
        bin_width = (max_val - min_val) / bins
        bin_counts = [0] * bins
        
        for v in values:
            bin_idx = min(int((v - min_val) / bin_width), bins - 1)
            bin_counts[bin_idx] += 1
        
        max_count = max(bin_counts)
        
        # Generate histogram
        lines = []
        lines.append(f"Histogram: {experiment_id} - {measurement_type}")
        lines.append(f"Bins: {bins} | Total: {len(values)} | Range: [{min_val:.4f}, {max_val:.4f}]")
        lines.append("")
        
        for i in range(bins):
            bin_min = min_val + i * bin_width
            bin_max = bin_min + bin_width
            count = bin_counts[i]
            
            # Calculate bar length
            bar_length = int(count / max_count * width) if max_count > 0 else 0
            bar = '█' * bar_length
            
            lines.append(f"[{bin_min:8.4f}, {bin_max:8.4f}) | {count:4d} | {bar}")
        
        return "\n".join(lines)
    
    def generate_summary_report(self, experiment_id: str) -> str:
        """
        Generate comprehensive summary report
        
        Args:
            experiment_id: Experiment ID
        
        Returns:
            Markdown formatted report
        """
        data = self.load_experiment_data(experiment_id)
        
        if not data:
            return f"No data found for experiment {experiment_id}"
        
        # Group by measurement type
        by_type: Dict[str, List[float]] = {}
        for d in data:
            mtype = d.get('measurement_type', 'unknown')
            if mtype not in by_type:
                by_type[mtype] = []
            by_type[mtype].append(d['value'])
        
        # Generate report
        report = []
        report.append(f"# Experiment Report: {experiment_id}")
        report.append("")
        report.append(f"**Generated**: {datetime.now().isoformat()}")
        report.append(f"**Total Data Points**: {len(data)}")
        report.append(f"**Measurement Types**: {len(by_type)}")
        report.append("")
        
        # Statistics per type
        report.append("## Statistics by Measurement Type")
        report.append("")
        report.append("| Type | Count | Mean | Std Dev | Min | Max |")
        report.append("|------|-------|------|---------|-----|-----|")
        
        for mtype, values in sorted(by_type.items()):
            count = len(values)
            mean = sum(values) / count
            variance = sum((v - mean) ** 2 for v in values) / count
            std_dev = math.sqrt(variance)
            min_val = min(values)
            max_val = max(values)
            
            report.append(f"| {mtype} | {count} | {mean:.4f} | {std_dev:.4f} | {min_val:.4f} | {max_val:.4f} |")
        
        report.append("")
        report.append("## Visualizations")
        report.append("")
        
        for mtype in sorted(by_type.keys()):
            report.append(f"### {mtype}")
            report.append("")
            report.append("```")
            report.append(self.generate_time_series(experiment_id, mtype, width=60, height=15))
            report.append("```")
            report.append("")
            report.append("```")
            report.append(self.generate_histogram(experiment_id, mtype, bins=8, width=40))
            report.append("```")
            report.append("")
        
        return "\n".join(report)
    
    def export_to_csv(self, experiment_id: str, output_file: str):
        """
        Export experiment data to CSV
        
        Args:
            experiment_id: Experiment ID
            output_file: Output CSV file path
        """
        data = self.load_experiment_data(experiment_id)
        
        if not data:
            print(f"No data to export for {experiment_id}")
            return
        
        # Get all unique keys
        all_keys = set()
        for d in data:
            all_keys.update(d.keys())
        
        # Write CSV
        with open(output_file, 'w', encoding='utf-8') as f:
            # Header
            header = sorted(all_keys)
            f.write(','.join(header) + '\n')
            
            # Data rows
            for d in data:
                row = []
                for key in header:
                    value = d.get(key, '')
                    if isinstance(value, dict):
                        value = json.dumps(value, ensure_ascii=False)
                    row.append(str(value))
                f.write(','.join(row) + '\n')
        
        print(f"Exported {len(data)} records to {output_file}")

# Example usage
if __name__ == "__main__":
    visualizer = DataVisualizer()
    
    # Generate visualizations for GRAV-EXP-001
    exp_id = "GRAV-EXP-001"
    
    print(visualizer.generate_time_series(exp_id, "gravity"))
    print("\n" + "="*80 + "\n")
    print(visualizer.generate_histogram(exp_id, "gravity"))
    print("\n" + "="*80 + "\n")
    
    # Generate full report
    report = visualizer.generate_summary_report(exp_id)
    print(report)
    
    # Export to CSV
    visualizer.export_to_csv(exp_id, r"C:\MSS-AI-Project\data\GRAV-EXP-001_export.csv")
