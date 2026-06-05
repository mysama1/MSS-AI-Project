"""
MSS System Stability Monitor & Adaptive Task Scheduler
根据系统稳定性动态调整任务优先级和执行策略
"""

import time
import os
import json
import threading
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional, Callable, Any, Tuple
from datetime import datetime
from enum import Enum, auto
from collections import deque

from mss_exceptions import SystemException, ErrorCode, ErrorLogger

class StabilityLevel(Enum):
    """系统稳定性等级"""
    CRITICAL = auto()      # 严重不稳定，只执行保存操作
    DEGRADED = auto()      # 降级模式，执行轻量任务
    NORMAL = auto()        # 正常模式，标准任务
    OPTIMAL = auto()       # 最优模式，可执行重负载任务

class TaskPriority(Enum):
    """任务优先级"""
    CRITICAL = 4    # 必须执行（如保存、检查点）
    HIGH = 3        # 重要任务
    NORMAL = 2      # 标准任务
    LOW = 1         # 可延迟任务
    BACKGROUND = 0  # 后台任务，不稳定时跳过

@dataclass
class SystemMetrics:
    """系统指标快照"""
    timestamp: float
    cpu_percent: float = 0.0
    memory_percent: float = 0.0
    memory_available_mb: float = 0.0
    disk_free_gb: float = 0.0
    tool_success_rate: float = 1.0
    avg_response_time_ms: float = 0.0
    error_count: int = 0

    @property
    def is_healthy(self) -> bool:
        return (
            self.memory_percent < 85 and
            self.tool_success_rate > 0.7 and
            self.avg_response_time_ms < 5000
        )

@dataclass
class StabilityReport:
    """稳定性报告"""
    level: StabilityLevel
    score: float  # 0.0 - 1.0
    metrics: SystemMetrics
    recommendation: str
    allowed_task_types: List[str]
    timestamp: float

    def to_dict(self) -> Dict:
        return {
            "level": self.level.name,
            "score": round(self.score, 3),
            "metrics": asdict(self.metrics),
            "recommendation": self.recommendation,
            "allowed_tasks": self.allowed_task_types,
            "timestamp": datetime.fromtimestamp(self.timestamp).isoformat(),
        }

class SystemHealthMonitor:
    """
    系统健康监控器

    持续监控系统状态，记录历史，检测趋势
    """

    def __init__(
        self,
        history_size: int = 20,
        check_interval_sec: int = 30,
        enabled: bool = True
    ):
        self.history_size = history_size
        self.check_interval_sec = check_interval_sec
        self.enabled = enabled

        self.metrics_history: deque = deque(maxlen=history_size)
        self.error_log: deque = deque(maxlen=50)
        self.tool_calls: deque = deque(maxlen=100)

        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self.error_logger = ErrorLogger("stability")

        # Performance tracking
        self._call_times: deque = deque(maxlen=20)
        self._success_count = 0
        self._fail_count = 0

    def record_tool_call(self, success: bool, duration_ms: float):
        """记录工具调用结果"""
        self.tool_calls.append({
            "success": success,
            "duration_ms": duration_ms,
            "timestamp": time.time(),
        })

        if success:
            self._success_count += 1
        else:
            self._fail_count += 1
            self.error_log.append({
                "type": "tool_failure",
                "timestamp": time.time(),
            })

        self._call_times.append(duration_ms)

    def get_current_metrics(self) -> SystemMetrics:
        """获取当前系统指标"""
        metrics = SystemMetrics(timestamp=time.time())

        # Memory (Windows)
        try:
            import psutil
            mem = psutil.virtual_memory()
            metrics.memory_percent = mem.percent
            metrics.memory_available_mb = mem.available / (1024 * 1024)
            metrics.cpu_percent = psutil.cpu_percent(interval=0.1)

            disk = psutil.disk_usage('/')
            metrics.disk_free_gb = disk.free / (1024**3)
        except ImportError:
            # Fallback without psutil
            pass

        # Tool success rate (last 20 calls)
        recent_calls = list(self.tool_calls)[-20:]
        if recent_calls:
            success_count = sum(1 for c in recent_calls if c["success"])
            metrics.tool_success_rate = success_count / len(recent_calls)

        # Average response time
        if self._call_times:
            metrics.avg_response_time_ms = sum(self._call_times) / len(self._call_times)

        metrics.error_count = self._fail_count

        return metrics

    def calculate_stability(self) -> StabilityReport:
        """计算当前稳定性等级"""
        metrics = self.get_current_metrics()
        self.metrics_history.append(metrics)

        # Calculate score (0.0 - 1.0)
        score = 1.0

        # Memory penalty
        if metrics.memory_percent > 90:
            score -= 0.4
        elif metrics.memory_percent > 80:
            score -= 0.2
        elif metrics.memory_percent > 70:
            score -= 0.1

        # Tool success rate penalty
        if metrics.tool_success_rate < 0.5:
            score -= 0.4
        elif metrics.tool_success_rate < 0.7:
            score -= 0.2
        elif metrics.tool_success_rate < 0.9:
            score -= 0.1

        # Response time penalty
        if metrics.avg_response_time_ms > 10000:
            score -= 0.3
        elif metrics.avg_response_time_ms > 5000:
            score -= 0.15

        # Trend penalty (deteriorating)
        if len(self.metrics_history) >= 3:
            recent = list(self.metrics_history)[-3:]
            if all(r.memory_percent > 80 for r in recent):
                score -= 0.1

        score = max(0.0, min(1.0, score))

        # Determine level
        if score < 0.3:
            level = StabilityLevel.CRITICAL
            recommendation = "系统严重不稳定。只执行保存/检查点操作，立即减少负载。"
            allowed = ["checkpoint", "save", "status_check"]
        elif score < 0.6:
            level = StabilityLevel.DEGRADED
            recommendation = "系统降级运行。执行轻量任务，避免复杂操作。"
            allowed = ["checkpoint", "save", "query", "simple_analysis", "test"]
        elif score < 0.85:
            level = StabilityLevel.NORMAL
            recommendation = "系统运行正常。标准任务可执行。"
            allowed = ["checkpoint", "save", "query", "analysis", "generation", "test"]
        else:
            level = StabilityLevel.OPTIMAL
            recommendation = "系统状态良好。可执行全量任务包括重负载操作。"
            allowed = ["all"]

        return StabilityReport(
            level=level,
            score=score,
            metrics=metrics,
            recommendation=recommendation,
            allowed_task_types=allowed,
            timestamp=time.time(),
        )

    def start_monitoring(self):
        """启动后台监控线程"""
        if not self.enabled or self._thread is not None:
            return

        self._stop_event.clear()
        self._thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self._thread.start()

    def stop_monitoring(self):
        """停止监控线程"""
        if self._thread is None:
            return
        self._stop_event.set()
        self._thread.join(timeout=5)
        self._thread = None

    def _monitor_loop(self):
        """后台监控循环"""
        while not self._stop_event.is_set():
            self._stop_event.wait(self.check_interval_sec)
            if not self._stop_event.is_set():
                try:
                    report = self.calculate_stability()
                    if report.level in (StabilityLevel.CRITICAL, StabilityLevel.DEGRADED):
                        self.error_logger.log(
                            SystemException(
                                f"Stability degraded: {report.level.name} (score={report.score:.2f})"
                            )
                        )
                except Exception:
                    pass

class AdaptiveTaskScheduler:
    """
    自适应任务调度器

    根据系统稳定性动态调整任务执行
    """

    def __init__(self, monitor: SystemHealthMonitor):
        self.monitor = monitor
        self.task_queue: List[Dict] = []
        self.completed_tasks: List[Dict] = []
        self.skipped_tasks: List[Dict] = []
        self.error_logger = ErrorLogger("scheduler")

    def register_task(
        self,
        name: str,
        priority: TaskPriority,
        task_type: str,
        func: Callable,
        *args,
        **kwargs
    ) -> str:
        """
        注册任务到队列

        Args:
            name: 任务名称
            priority: 优先级
            task_type: 任务类型（用于稳定性过滤）
            func: 执行函数
            *args, **kwargs: 函数参数
        """
        task_id = f"task_{int(time.time() * 1000)}_{len(self.task_queue)}"
        task = {
            "id": task_id,
            "name": name,
            "priority": priority,
            "type": task_type,
            "func": func,
            "args": args,
            "kwargs": kwargs,
            "registered_at": time.time(),
            "status": "pending",
        }
        self.task_queue.append(task)

        # Sort by priority (highest first)
        self.task_queue.sort(key=lambda t: t["priority"].value, reverse=True)

        return task_id

    def can_execute(self, task_type: str) -> Tuple[bool, str]:
        """
        检查任务是否可以执行

        Returns:
            (can_execute, reason)
        """
        report = self.monitor.calculate_stability()

        if "all" in report.allowed_task_types:
            return True, "All tasks allowed"

        if task_type in report.allowed_task_types:
            return True, f"Task type '{task_type}' allowed"

        return False, f"Task type '{task_type}' not allowed in {report.level.name} mode"

    def execute_next(self) -> Optional[Dict]:
        """
        执行队列中下一个允许的任务

        Returns:
            执行结果，如果无任务可执行则返回 None
        """
        if not self.task_queue:
            return None

        # Find highest priority task that can execute
        for i, task in enumerate(self.task_queue):
            can_exec, reason = self.can_execute(task["type"])

            if can_exec:
                # Execute task
                task["status"] = "running"
                start_time = time.time()

                try:
                    result = task["func"](*task["args"], **task["kwargs"])
                    task["status"] = "completed"
                    task["result"] = result
                    task["duration_sec"] = time.time() - start_time
                    self.completed_tasks.append(task)
                except Exception as e:
                    task["status"] = "failed"
                    task["error"] = str(e)
                    task["duration_sec"] = time.time() - start_time
                    self.error_logger.log(SystemException(f"Task {task['name']} failed: {e}"))

                # Remove from queue
                self.task_queue.pop(i)
                return task
            else:
                # Task cannot execute in current stability level
                if task["priority"] == TaskPriority.CRITICAL:
                    # Critical tasks always try once more
                    continue

                task["status"] = "skipped"
                task["skip_reason"] = reason
                self.skipped_tasks.append(task)
                self.task_queue.pop(i)
                return task

        return None

    def execute_all_possible(self) -> Dict:
        """执行所有当前允许的任务"""
        results = {
            "executed": 0,
            "skipped": 0,
            "failed": 0,
            "tasks": [],
        }

        while True:
            task = self.execute_next()
            if task is None:
                break

            results["tasks"].append({
                "name": task["name"],
                "status": task["status"],
                "duration": task.get("duration_sec", 0),
            })

            if task["status"] == "completed":
                results["executed"] += 1
            elif task["status"] == "skipped":
                results["skipped"] += 1
            elif task["status"] == "failed":
                results["failed"] += 1

        return results

    def get_status(self) -> Dict:
        """获取调度器状态"""
        report = self.monitor.calculate_stability()

        return {
            "stability": report.to_dict(),
            "queue_size": len(self.task_queue),
            "completed": len(self.completed_tasks),
            "skipped": len(self.skipped_tasks),
            "pending_tasks": [
                {"name": t["name"], "priority": t["priority"].name, "type": t["type"]}
                for t in self.task_queue[:5]  # Show top 5
            ],
        }

# Convenience functions for common patterns

def create_stability_aware_system() -> Tuple[SystemHealthMonitor, AdaptiveTaskScheduler]:
    """创建完整的稳定性感知系统"""
    monitor = SystemHealthMonitor()
    scheduler = AdaptiveTaskScheduler(monitor)
    monitor.start_monitoring()
    return monitor, scheduler

def quick_stability_check() -> StabilityReport:
    """快速稳定性检查"""
    monitor = SystemHealthMonitor(enabled=False)
    return monitor.calculate_stability()

# Demo
if __name__ == "__main__":
    print("=" * 60)
    print("MSS Stability Monitor Demo")
    print("=" * 60)

    # 1. Quick check
    print("\n1. Quick Stability Check:")
    report = quick_stability_check()
    print(f"   Level: {report.level.name}")
    print(f"   Score: {report.score:.3f}")
    print(f"   Recommendation: {report.recommendation}")
    print(f"   Allowed tasks: {report.allowed_task_types}")

    # 2. Simulate tool calls
    print("\n2. Simulating Tool Calls:")
    monitor = SystemHealthMonitor(enabled=False)

    # Simulate some failures
    for i in range(10):
        success = i < 7  # 70% success rate
        monitor.record_tool_call(success, duration_ms=1000 + i * 100)

    report = monitor.calculate_stability()
    print(f"   After 10 calls (70% success):")
    print(f"   Level: {report.level.name}, Score: {report.score:.3f}")

    # 3. Task scheduler
    print("\n3. Adaptive Task Scheduler:")
    scheduler = AdaptiveTaskScheduler(monitor)

    # Register tasks
    def save_checkpoint():
        return "checkpoint saved"

    def heavy_analysis():
        return "analysis complete"

    def background_cleanup():
        return "cleanup done"

    scheduler.register_task("checkpoint", TaskPriority.CRITICAL, "checkpoint", save_checkpoint)
    scheduler.register_task("analysis", TaskPriority.NORMAL, "analysis", heavy_analysis)
    scheduler.register_task("cleanup", TaskPriority.BACKGROUND, "cleanup", background_cleanup)

    print(f"   Registered {len(scheduler.task_queue)} tasks")

    # Execute based on stability
    results = scheduler.execute_all_possible()
    print(f"   Executed: {results['executed']}")
    print(f"   Skipped: {results['skipped']}")

    print("\n" + "=" * 60)
