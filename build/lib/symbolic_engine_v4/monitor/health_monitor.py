"""
MSS Symbolic Engine v4.0 - Health Monitor
System health monitoring and alerting
"""

import time
import threading
from typing import Dict, List, Optional, Callable
from datetime import datetime
from collections import deque

class HealthMonitor:
    """
    System health monitor with automatic alerting

    Monitors:
    - Graph memory usage
    - Query performance
    - API response times
    - Error rates
    """

    def __init__(self, max_history: int = 1000):
        self.max_history = max_history
        self.metrics_history = {
            "query_time": deque(maxlen=max_history),
            "memory_usage": deque(maxlen=max_history),
            "error_rate": deque(maxlen=max_history),
            "api_latency": deque(maxlen=max_history)
        }

        self.alerts: List[Dict] = []
        self.alert_callbacks: List[Callable] = []
        self.thresholds = {
            "query_time_ms": 1000,  # Alert if query > 1s
            "memory_mb": 512,       # Alert if memory > 512MB
            "error_rate": 0.05,     # Alert if error rate > 5%
            "api_latency_ms": 500   # Alert if API latency > 500ms
        }

        self._running = False
        self._monitor_thread = None

    def start_monitoring(self, interval_seconds: int = 30):
        """Start background monitoring"""
        if self._running:
            return

        self._running = True
        self._monitor_thread = threading.Thread(target=self._monitor_loop, args=(interval_seconds,))
        self._monitor_thread.daemon = True
        self._monitor_thread.start()
        print(f"Health monitoring started (interval: {interval_seconds}s)")

    def stop_monitoring(self):
        """Stop background monitoring"""
        self._running = False
        if self._monitor_thread:
            self._monitor_thread.join(timeout=5)

    def _monitor_loop(self, interval: int):
        """Background monitoring loop"""
        while self._running:
            self._check_health()
            time.sleep(interval)

    def _check_health(self):
        """Check system health and trigger alerts"""
        # Check query time
        if self.metrics_history["query_time"]:
            avg_query_time = sum(self.metrics_history["query_time"]) / len(self.metrics_history["query_time"])
            if avg_query_time > self.thresholds["query_time_ms"]:
                self._trigger_alert(
                    "query_time",
                    f"Average query time {avg_query_time:.1f}ms exceeds threshold {self.thresholds['query_time_ms']}ms"
                )

        # Check error rate
        if self.metrics_history["error_rate"]:
            avg_error_rate = sum(self.metrics_history["error_rate"]) / len(self.metrics_history["error_rate"])
            if avg_error_rate > self.thresholds["error_rate"]:
                self._trigger_alert(
                    "error_rate",
                    f"Error rate {avg_error_rate:.2%} exceeds threshold {self.thresholds['error_rate']:.2%}"
                )

    def record_metric(self, metric_type: str, value: float):
        """Record a metric value"""
        if metric_type in self.metrics_history:
            self.metrics_history[metric_type].append(value)

    def record_query(self, execution_time_ms: float, success: bool = True):
        """Record query metrics"""
        self.record_metric("query_time", execution_time_ms)
        if not success:
            self.record_metric("error_rate", 1.0)
        else:
            self.record_metric("error_rate", 0.0)

    def record_api_call(self, latency_ms: float):
        """Record API call latency"""
        self.record_metric("api_latency", latency_ms)

    def _trigger_alert(self, alert_type: str, message: str):
        """Trigger an alert"""
        alert = {
            "type": alert_type,
            "message": message,
            "timestamp": datetime.now().isoformat(),
            "severity": "warning"
        }

        self.alerts.append(alert)

        # Call registered callbacks
        for callback in self.alert_callbacks:
            try:
                callback(alert)
            except Exception as e:
                print(f"Alert callback error: {e}")

    def register_alert_callback(self, callback: Callable):
        """Register an alert callback"""
        self.alert_callbacks.append(callback)

    def get_health_status(self) -> Dict:
        """Get current health status"""
        status = {
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "metrics": {},
            "alerts": len(self.alerts)
        }

        # Calculate averages
        for metric_type, history in self.metrics_history.items():
            if history:
                avg = sum(history) / len(history)
                status["metrics"][metric_type] = {
                    "current": history[-1] if history else 0,
                    "average": round(avg, 2),
                    "count": len(history)
                }

        # Determine overall status
        if self.alerts:
            recent_alerts = [a for a in self.alerts
                           if (datetime.now() - datetime.fromisoformat(a["timestamp"])).total_seconds() < 3600]
            if len(recent_alerts) > 5:
                status["status"] = "critical"
            elif len(recent_alerts) > 0:
                status["status"] = "warning"

        return status

    def get_alerts(self, limit: int = 10) -> List[Dict]:
        """Get recent alerts"""
        return self.alerts[-limit:]

    def clear_alerts(self):
        """Clear all alerts"""
        self.alerts.clear()

    def set_threshold(self, metric: str, value: float):
        """Set alert threshold"""
        if metric in self.thresholds:
            self.thresholds[metric] = value

class PerformanceProfiler:
    """Simple performance profiler"""

    def __init__(self):
        self.profiles: Dict[str, List[float]] = {}

    def profile(self, name: str):
        """Context manager for profiling"""
        return ProfileContext(self, name)

    def record(self, name: str, duration_ms: float):
        """Record a profiled duration"""
        if name not in self.profiles:
            self.profiles[name] = []
        self.profiles[name].append(duration_ms)

    def get_stats(self, name: str) -> Optional[Dict]:
        """Get statistics for a profiled function"""
        if name not in self.profiles or not self.profiles[name]:
            return None

        times = self.profiles[name]
        return {
            "count": len(times),
            "total_ms": round(sum(times), 2),
            "avg_ms": round(sum(times) / len(times), 2),
            "min_ms": round(min(times), 2),
            "max_ms": round(max(times), 2)
        }

    def get_all_stats(self) -> Dict[str, Dict]:
        """Get statistics for all profiled functions"""
        return {name: self.get_stats(name) for name in self.profiles.keys()}

class ProfileContext:
    """Context manager for profiling"""

    def __init__(self, profiler: PerformanceProfiler, name: str):
        self.profiler = profiler
        self.name = name
        self.start_time = None

    def __enter__(self):
        self.start_time = time.time()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.start_time:
            duration_ms = (time.time() - self.start_time) * 1000
            self.profiler.record(self.name, duration_ms)
