"""
Metrics Persistence Module - Save/load monitoring data to disk
"""
import json
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Optional
from dataclasses import dataclass, asdict

@dataclass
class MetricsSnapshot:
    """监控指标快照"""
    timestamp: str
    total_requests: int
    success_count: int
    failure_count: int
    avg_response_time: float
    min_response_time: float
    max_response_time: float
    cache_hit_rate: float
    gpu_memory_used: float
    health_score: float
    alert_count: int

class MetricsPersistence:
    """指标持久化管理器"""

    def __init__(self, data_dir: str = "./metrics_data"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(exist_ok=True)
        self.current_file = self.data_dir / f"metrics_{datetime.now().strftime('%Y%m%d')}.jsonl"

    def save_snapshot(self, snapshot: MetricsSnapshot):
        """保存指标快照"""
        with open(self.current_file, 'a', encoding='utf-8') as f:
            f.write(json.dumps(asdict(snapshot), ensure_ascii=False) + '\n')

    def load_history(self, days: int = 7) -> List[MetricsSnapshot]:
        """加载历史数据"""
        snapshots = []
        cutoff = datetime.now() - timedelta(days=days)

        for file in sorted(self.data_dir.glob("metrics_*.jsonl")):
            # 从文件名提取日期
            try:
                date_str = file.stem.replace('metrics_', '')
                file_date = datetime.strptime(date_str, '%Y%m%d')
                if file_date < cutoff:
                    continue
            except:
                continue

            with open(file, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line:
                        data = json.loads(line)
                        snapshots.append(MetricsSnapshot(**data))

        return snapshots

    def get_daily_summary(self, date: Optional[str] = None) -> Dict:
        """获取每日汇总"""
        if date is None:
            date = datetime.now().strftime('%Y%m%d')

        file_path = self.data_dir / f"metrics_{date}.jsonl"
        if not file_path.exists():
            return {"error": "No data for specified date"}

        snapshots = []
        with open(file_path, 'r', encoding='utf-8') as f:
            for line in f:
                if line.strip():
                    snapshots.append(json.loads(line))

        if not snapshots:
            return {"error": "Empty data file"}

        return {
            "date": date,
            "total_snapshots": len(snapshots),
            "total_requests": sum(s["total_requests"] for s in snapshots),
            "success_rate": sum(s["success_count"] for s in snapshots) / max(sum(s["total_requests"] for s in snapshots), 1),
            "avg_response_time": sum(s["avg_response_time"] for s in snapshots) / len(snapshots),
            "avg_health_score": sum(s["health_score"] for s in snapshots) / len(snapshots),
            "peak_gpu_memory": max(s["gpu_memory_used"] for s in snapshots),
            "total_alerts": sum(s["alert_count"] for s in snapshots)
        }

    def cleanup_old_data(self, keep_days: int = 30):
        """清理旧数据"""
        cutoff = datetime.now() - timedelta(days=keep_days)
        removed = 0

        for file in self.data_dir.glob("metrics_*.jsonl"):
            try:
                date_str = file.stem.replace('metrics_', '')
                file_date = datetime.strptime(date_str, '%Y%m%d')
                if file_date < cutoff:
                    file.unlink()
                    removed += 1
            except:
                continue

        return removed

def create_persistence(data_dir: str = "./metrics_data") -> MetricsPersistence:
    """工厂函数"""
    return MetricsPersistence(data_dir)
