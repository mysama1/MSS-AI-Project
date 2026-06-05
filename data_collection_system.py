"""
MSS Data Collection System
Collects and processes experimental data for GRAV-EXP-001 and other experiments
"""

import json
import time
from datetime import datetime
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from pathlib import Path

@dataclass
class DataPoint:
    """Single data point from experiment"""
    timestamp: str
    experiment_id: str
    subject_id: str
    measurement_type: str
    value: float
    unit: str
    metadata: Dict[str, Any]

    def to_dict(self) -> Dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict) -> 'DataPoint':
        return cls(**data)

class DataCollector:
    """Data collection manager"""

    def __init__(self, storage_dir: str = r"C:\MSS-AI-Project\data"):
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(exist_ok=True)
        self.buffer: List[DataPoint] = []
        self.buffer_size = 1000

        # Experiment registry
        self.experiments: Dict[str, Dict] = {}

    def register_experiment(self, experiment_id: str, config: Dict) -> bool:
        """Register a new experiment"""
        if experiment_id in self.experiments:
            return False

        self.experiments[experiment_id] = {
            "id": experiment_id,
            "config": config,
            "created_at": datetime.now().isoformat(),
            "status": "active",
            "data_points": 0
        }

        # Create experiment directory
        exp_dir = self.storage_dir / experiment_id
        exp_dir.mkdir(exist_ok=True)

        # Save config
        config_file = exp_dir / "config.json"
        with open(config_file, 'w', encoding='utf-8') as f:
            json.dump(config, f, ensure_ascii=False, indent=2)

        return True

    def collect(self, experiment_id: str, subject_id: str,
                measurement_type: str, value: float, unit: str,
                metadata: Optional[Dict] = None) -> bool:
        """Collect a single data point"""
        if experiment_id not in self.experiments:
            return False

        point = DataPoint(
            timestamp=datetime.now().isoformat(),
            experiment_id=experiment_id,
            subject_id=subject_id,
            measurement_type=measurement_type,
            value=value,
            unit=unit,
            metadata=metadata or {}
        )

        self.buffer.append(point)
        self.experiments[experiment_id]["data_points"] += 1

        # Flush if buffer is full
        if len(self.buffer) >= self.buffer_size:
            self.flush()

        return True

    def flush(self):
        """Flush buffer to disk"""
        if not self.buffer:
            return

        # Group by experiment
        by_experiment: Dict[str, List[DataPoint]] = {}
        for point in self.buffer:
            exp_id = point.experiment_id
            if exp_id not in by_experiment:
                by_experiment[exp_id] = []
            by_experiment[exp_id].append(point)

        # Save each experiment's data
        for exp_id, points in by_experiment.items():
            exp_dir = self.storage_dir / exp_id
            exp_dir.mkdir(exist_ok=True)

            # Append to daily file
            date_str = datetime.now().strftime("%Y%m%d")
            data_file = exp_dir / f"data_{date_str}.jsonl"

            with open(data_file, 'a', encoding='utf-8') as f:
                for point in points:
                    f.write(json.dumps(point.to_dict(), ensure_ascii=False) + '\n')

        # Clear buffer
        self.buffer.clear()
        print(f"Flushed {len(self.buffer)} data points to disk")

    def get_experiment_data(self, experiment_id: str,
                           start_time: Optional[str] = None,
                           end_time: Optional[str] = None) -> List[Dict]:
        """Get data for an experiment"""
        exp_dir = self.storage_dir / experiment_id
        if not exp_dir.exists():
            return []

        data = []

        # Read all JSONL files
        for data_file in sorted(exp_dir.glob("data_*.jsonl")):
            with open(data_file, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        point = json.loads(line)

                        # Filter by time if specified
                        if start_time and point['timestamp'] < start_time:
                            continue
                        if end_time and point['timestamp'] > end_time:
                            continue

                        data.append(point)
                    except json.JSONDecodeError:
                        continue

        return data

    def get_experiment_stats(self, experiment_id: str) -> Dict:
        """Get experiment statistics"""
        if experiment_id not in self.experiments:
            return {"error": "Experiment not found"}

        exp = self.experiments[experiment_id]
        data = self.get_experiment_data(experiment_id)

        # Calculate statistics
        if not data:
            return {
                "experiment_id": experiment_id,
                "status": exp["status"],
                "total_points": 0,
                "subjects": 0,
                "measurement_types": []
            }

        subjects = set(d['subject_id'] for d in data)
        measurement_types = set(d['measurement_type'] for d in data)

        # Calculate averages per measurement type
        averages = {}
        for mtype in measurement_types:
            values = [d['value'] for d in data if d['measurement_type'] == mtype]
            if values:
                averages[mtype] = {
                    "count": len(values),
                    "mean": sum(values) / len(values),
                    "min": min(values),
                    "max": max(values)
                }

        return {
            "experiment_id": experiment_id,
            "status": exp["status"],
            "total_points": len(data),
            "subjects": len(subjects),
            "measurement_types": list(measurement_types),
            "averages": averages
        }

    def close_experiment(self, experiment_id: str):
        """Close an experiment and flush remaining data"""
        if experiment_id not in self.experiments:
            return

        # Flush remaining buffer
        self.flush()

        # Update status
        self.experiments[experiment_id]["status"] = "completed"
        self.experiments[experiment_id]["completed_at"] = datetime.now().isoformat()

        # Save final metadata
        exp_dir = self.storage_dir / experiment_id
        metadata_file = exp_dir / "metadata.json"
        with open(metadata_file, 'w', encoding='utf-8') as f:
            json.dump(self.experiments[experiment_id], f, ensure_ascii=False, indent=2)

class RealTimeDataStream:
    """Real-time data streaming for live experiments"""

    def __init__(self, collector: DataCollector):
        self.collector = collector
        self.subscribers: List[Any] = []
        self.is_streaming = False

    def subscribe(self, callback):
        """Subscribe to data stream"""
        self.subscribers.append(callback)

    def start_stream(self, experiment_id: str, subject_id: str,
                     measurement_type: str, interval_seconds: float = 1.0):
        """Start real-time data collection"""
        self.is_streaming = True

        print(f"Starting data stream for {experiment_id}/{subject_id}")

        while self.is_streaming:
            # Simulate data collection (replace with actual sensor reading)
            import random
            value = random.gauss(9.8, 0.1)  # Simulated gravity measurement

            self.collector.collect(
                experiment_id=experiment_id,
                subject_id=subject_id,
                measurement_type=measurement_type,
                value=value,
                unit="m/s^2",
                metadata={"source": "simulated"}
            )

            # Notify subscribers
            for callback in self.subscribers:
                try:
                    callback({
                        "timestamp": datetime.now().isoformat(),
                        "value": value,
                        "unit": "m/s^2"
                    })
                except Exception as e:
                    print(f"Subscriber error: {e}")

            time.sleep(interval_seconds)

    def stop_stream(self):
        """Stop data stream"""
        self.is_streaming = False
        print("Data stream stopped")

# Example usage
if __name__ == "__main__":
    # Create collector
    collector = DataCollector()

    # Register experiment
    collector.register_experiment("GRAV-EXP-001", {
        "name": "高T个体引力效应实验",
        "type": "physics",
        "subjects": 32,
        "duration_days": 180
    })

    # Collect some data
    for i in range(10):
        collector.collect(
            experiment_id="GRAV-EXP-001",
            subject_id="SUB-001",
            measurement_type="gravity",
            value=9.8 + i * 0.01,
            unit="m/s^2",
            metadata={"location": "lab_1", "temperature": 20.5}
        )

    # Flush to disk
    collector.flush()

    # Get stats
    stats = collector.get_experiment_stats("GRAV-EXP-001")
    print(f"\nExperiment stats: {json.dumps(stats, indent=2, ensure_ascii=False)}")

    # Close experiment
    collector.close_experiment("GRAV-EXP-001")
