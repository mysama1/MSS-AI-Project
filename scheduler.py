"""
Scheduled Batch Jobs - Cron-like scheduling for MSS-AI
"""
import threading
import time
from datetime import datetime, timedelta
from typing import Callable, Dict, List, Optional
from dataclasses import dataclass, field
from enum import Enum

class JobStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

@dataclass
class ScheduledJob:
    """定时任务"""
    id: str
    name: str
    schedule: str
    task: Callable
    args: tuple = field(default_factory=tuple)
    kwargs: dict = field(default_factory=dict)
    status: JobStatus = JobStatus.PENDING
    last_run: Optional[str] = None
    next_run: Optional[str] = None
    run_count: int = 0
    enabled: bool = True

class JobScheduler:
    """任务调度器"""

    def __init__(self):
        self.jobs: Dict[str, ScheduledJob] = {}
        self._thread: Optional[threading.Thread] = None
        self._running = False
        self._lock = threading.Lock()

    def add_job(self, job: ScheduledJob) -> str:
        """添加任务"""
        with self._lock:
            self.jobs[job.id] = job
            job.next_run = self._calculate_next_run(job.schedule)
        return job.id

    def remove_job(self, job_id: str) -> bool:
        """移除任务"""
        with self._lock:
            if job_id in self.jobs:
                del self.jobs[job_id]
                return True
            return False

    def enable_job(self, job_id: str) -> bool:
        """启用任务"""
        with self._lock:
            if job_id in self.jobs:
                self.jobs[job_id].enabled = True
                return True
            return False

    def disable_job(self, job_id: str) -> bool:
        """禁用任务"""
        with self._lock:
            if job_id in self.jobs:
                self.jobs[job_id].enabled = False
                return True
            return False

    def start(self):
        """启动调度器"""
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()
        print("[Scheduler] Started")

    def stop(self):
        """停止调度器"""
        self._running = False
        if self._thread:
            self._thread.join(timeout=5)
        print("[Scheduler] Stopped")

    def _run_loop(self):
        """主循环"""
        while self._running:
            now = datetime.now()
            with self._lock:
                for job in self.jobs.values():
                    if not job.enabled or job.status == JobStatus.RUNNING:
                        continue
                    if job.next_run and datetime.fromisoformat(job.next_run) <= now:
                        job.status = JobStatus.RUNNING
                        job.last_run = now.isoformat()
                        job.run_count += 1
                        threading.Thread(target=self._execute_job, args=(job,), daemon=True).start()
                        job.next_run = self._calculate_next_run(job.schedule)
            time.sleep(30)

    def _execute_job(self, job: ScheduledJob):
        """执行任务"""
        try:
            job.task(*job.args, **job.kwargs)
            job.status = JobStatus.COMPLETED
        except Exception as e:
            print(f"[Scheduler] Job {job.id} failed: {e}")
            job.status = JobStatus.FAILED

    def _calculate_next_run(self, schedule: str) -> str:
        """计算下次运行时间"""
        now = datetime.now()
        if schedule.startswith("*/"):
            try:
                minutes = int(schedule.replace("*/", "").split()[0])
                return (now + timedelta(minutes=minutes)).isoformat()
            except:
                pass
        return (now + timedelta(minutes=5)).isoformat()

    def get_status(self) -> Dict:
        """获取调度器状态"""
        return {
            "running": self._running,
            "job_count": len(self.jobs),
            "jobs": [
                {
                    "id": j.id,
                    "name": j.name,
                    "status": j.status.value,
                    "enabled": j.enabled,
                    "last_run": j.last_run,
                    "next_run": j.next_run,
                    "run_count": j.run_count
                }
                for j in self.jobs.values()
            ]
        }

def create_scheduler() -> JobScheduler:
    return JobScheduler()
