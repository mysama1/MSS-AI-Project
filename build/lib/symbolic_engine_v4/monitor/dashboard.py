"""
MSS Symbolic Engine v4.0 - Monitoring Dashboard
Simple text-based dashboard for system monitoring
"""

import time
import json
from datetime import datetime
from typing import Dict, List
from .health_monitor import HealthMonitor

class MonitoringDashboard:
    """Text-based monitoring dashboard"""
    
    def __init__(self, health_monitor: HealthMonitor):
        self.health_monitor = health_monitor
        self.start_time = datetime.now()
    
    def generate_dashboard(self) -> str:
        """Generate dashboard text"""
        health = self.health_monitor.get_health_status()
        alerts = self.health_monitor.get_alerts(5)
        
        # Calculate uptime
        uptime = datetime.now() - self.start_time
        uptime_str = str(uptime).split('.')[0]  # Remove microseconds
        
        dashboard = f"""
╔══════════════════════════════════════════════════════════════════╗
║           MSS Symbolic Engine v4.0 - Monitoring Dashboard        ║
╠══════════════════════════════════════════════════════════════════╣
║  Status: {health['status'].upper():^10}  |  Uptime: {uptime_str:^20}  ║
╠══════════════════════════════════════════════════════════════════╣
║  System Metrics                                                    ║
╠══════════════════════════════════════════════════════════════════╣
"""
        
        # Add metrics
        for metric_name, metric_data in health['metrics'].items():
            dashboard += f"║  {metric_name:20} | Current: {metric_data['current']:8.2f} | Avg: {metric_data['average']:8.2f}  ║\n"
        
        dashboard += """╠══════════════════════════════════════════════════════════════════╣
║  Recent Alerts ({alerts_count})                                               ║
╠══════════════════════════════════════════════════════════════════╣
""".format(alerts_count=len(alerts))
        
        # Add alerts
        if alerts:
            for alert in alerts:
                dashboard += f"║  [{alert['severity']:8}] {alert['type']:15} | {alert['message'][:40]:40} ║\n"
        else:
            dashboard += "║  No alerts - System healthy                                      ║\n"
        
        dashboard += """╠══════════════════════════════════════════════════════════════════╣
║  Last Updated: {timestamp:50} ║
╚══════════════════════════════════════════════════════════════════╝
""".format(timestamp=datetime.now().isoformat())
        
        return dashboard
    
    def generate_json_report(self) -> Dict:
        """Generate JSON monitoring report"""
        return {
            "timestamp": datetime.now().isoformat(),
            "uptime_seconds": (datetime.now() - self.start_time).total_seconds(),
            "health_status": self.health_monitor.get_health_status(),
            "recent_alerts": self.health_monitor.get_alerts(10),
            "thresholds": self.health_monitor.thresholds
        }
    
    def save_report(self, filepath: str):
        """Save monitoring report to file"""
        report = self.generate_json_report()
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
    
    def print_dashboard(self):
        """Print dashboard to console"""
        print(self.generate_dashboard())

# Simple CLI dashboard
if __name__ == "__main__":
    monitor = HealthMonitor()
    dashboard = MonitoringDashboard(monitor)
    
    # Simulate some metrics
    monitor.record_metric("query_time", 150)
    monitor.record_metric("query_time", 200)
    monitor.record_metric("query_time", 180)
    monitor.record_metric("memory_usage", 128)
    monitor.record_metric("error_rate", 0.02)
    
    # Print dashboard
    dashboard.print_dashboard()
