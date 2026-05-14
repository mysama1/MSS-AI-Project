"""
MSS-AI Checkpoint & Auto-Save System
Prevents progress loss from system instability
"""

import json
import time
import os
import threading
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional, Callable, Any
from datetime import datetime
from pathlib import Path

from mss_exceptions import SystemException, ValidationException, ErrorCode, ErrorLogger


@dataclass
class Checkpoint:
    """A single checkpoint snapshot"""
    id: str
    timestamp: float
    label: str
    data: Dict[str, Any]
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def age_seconds(self) -> float:
        return time.time() - self.timestamp
    
    @property
    def formatted_time(self) -> str:
        return datetime.fromtimestamp(self.timestamp).strftime("%Y-%m-%d %H:%M:%S")
    
    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "timestamp": self.timestamp,
            "formatted_time": self.formatted_time,
            "label": self.label,
            "data": self.data,
            "metadata": self.metadata
        }


class CheckpointManager:
    """
    Manages checkpoints for crash recovery.
    
    Features:
    - Automatic checkpoints on key operations
    - Time-based auto-save
    - Operation-count based auto-save
    - Recovery from last checkpoint
    - Checkpoint history with cleanup
    """
    
    def __init__(
        self,
        checkpoint_dir: str = "checkpoints",
        max_checkpoints: int = 10,
        auto_save_interval_sec: int = 300,  # 5 minutes
        auto_save_operations: int = 10,
        enabled: bool = True
    ):
        self.checkpoint_dir = Path(checkpoint_dir)
        self.max_checkpoints = max_checkpoints
        self.auto_save_interval_sec = auto_save_interval_sec
        self.auto_save_operations = auto_save_operations
        self.enabled = enabled
        
        self.checkpoints: List[Checkpoint] = []
        self.operation_count = 0
        self.last_auto_save = time.time()
        self.error_logger = ErrorLogger("checkpoint")
        
        # Ensure directory exists
        self.checkpoint_dir.mkdir(parents=True, exist_ok=True)
        
        # Load existing checkpoints
        self._load_existing()
    
    def _load_existing(self):
        """Load existing checkpoints from disk"""
        if not self.enabled:
            return
        
        checkpoint_files = sorted(
            self.checkpoint_dir.glob("checkpoint_*.json"),
            key=lambda p: p.stat().st_mtime
        )
        
        for cp_file in checkpoint_files[-self.max_checkpoints:]:
            try:
                with open(cp_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                cp = Checkpoint(
                    id=data["id"],
                    timestamp=data["timestamp"],
                    label=data.get("label", "loaded"),
                    data=data.get("data", {}),
                    metadata=data.get("metadata", {})
                )
                self.checkpoints.append(cp)
            except Exception as e:
                self.error_logger.log(
                    SystemException(f"Failed to load checkpoint {cp_file}: {e}")
                )
    
    def save(
        self,
        data: Dict[str, Any],
        label: str = "manual",
        metadata: Optional[Dict] = None
    ) -> Checkpoint:
        """Save a checkpoint"""
        if not self.enabled:
            return None
        
        checkpoint_id = f"cp_{int(time.time() * 1000)}"
        cp = Checkpoint(
            id=checkpoint_id,
            timestamp=time.time(),
            label=label,
            data=data,
            metadata=metadata or {}
        )
        
        # Add to memory
        self.checkpoints.append(cp)
        
        # Save to disk
        try:
            cp_path = self.checkpoint_dir / f"checkpoint_{checkpoint_id}.json"
            with open(cp_path, 'w', encoding='utf-8') as f:
                json.dump(cp.to_dict(), f, indent=2, ensure_ascii=False)
        except Exception as e:
            self.error_logger.log(
                SystemException(f"Failed to save checkpoint: {e}")
            )
        
        # Cleanup old checkpoints
        self._cleanup_old()
        
        return cp
    
    def _cleanup_old(self):
        """Remove old checkpoints beyond max_checkpoints"""
        while len(self.checkpoints) > self.max_checkpoints:
            old_cp = self.checkpoints.pop(0)
            cp_path = self.checkpoint_dir / f"checkpoint_{old_cp.id}.json"
            if cp_path.exists():
                try:
                    cp_path.unlink()
                except Exception:
                    pass
    
    def auto_check(self, data: Dict[str, Any], operation_label: str = "") -> Optional[Checkpoint]:
        """
        Check if auto-save should trigger.
        Call this after significant operations.
        """
        if not self.enabled:
            return None
        
        self.operation_count += 1
        should_save = False
        reason = ""
        
        # Check time-based
        elapsed = time.time() - self.last_auto_save
        if elapsed >= self.auto_save_interval_sec:
            should_save = True
            reason = f"time ({elapsed:.0f}s)"
        
        # Check operation-based
        elif self.operation_count >= self.auto_save_operations:
            should_save = True
            reason = f"operations ({self.operation_count})"
        
        if should_save:
            cp = self.save(
                data=data,
                label=f"auto_{reason}_{operation_label}",
                metadata={
                    "auto_save": True,
                    "reason": reason,
                    "operation_count": self.operation_count
                }
            )
            self.last_auto_save = time.time()
            self.operation_count = 0
            return cp
        
        return None
    
    def get_latest(self) -> Optional[Checkpoint]:
        """Get the most recent checkpoint"""
        if self.checkpoints:
            return self.checkpoints[-1]
        return None
    
    def recover(self) -> Optional[Dict[str, Any]]:
        """Recover data from the latest checkpoint"""
        latest = self.get_latest()
        if latest:
            return latest.data
        return None
    
    def list_checkpoints(self) -> List[Dict]:
        """List all checkpoints with info"""
        return [
            {
                "id": cp.id,
                "time": cp.formatted_time,
                "label": cp.label,
                "age_sec": int(cp.age_seconds),
                "data_keys": list(cp.data.keys())
            }
            for cp in reversed(self.checkpoints)
        ]
    
    def clear_all(self):
        """Clear all checkpoints"""
        for cp in self.checkpoints:
            cp_path = self.checkpoint_dir / f"checkpoint_{cp.id}.json"
            if cp_path.exists():
                cp_path.unlink()
        self.checkpoints = []


class SessionSnapshot:
    """
    Captures a complete snapshot of the MSS-AI session state.
    Can be used for recovery after crashes.
    """
    
    def __init__(self, checkpoint_manager: CheckpointManager):
        self.cp = checkpoint_manager
        self.components: Dict[str, Callable[[], Dict]] = {}
    
    def register(self, name: str, getter: Callable[[], Dict]):
        """Register a component for snapshotting"""
        self.components[name] = getter
    
    def capture(self, label: str = "snapshot") -> Checkpoint:
        """Capture current state of all registered components"""
        data = {}
        for name, getter in self.components.items():
            try:
                data[name] = getter()
            except Exception as e:
                data[name] = {"_error": str(e)}
        
        return self.cp.save(
            data=data,
            label=label,
            metadata={
                "components": list(self.components.keys()),
                "snapshot": True
            }
        )
    
    def restore(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Restore components from snapshot data"""
        results = {}
        for name, component_data in data.items():
            if name.startswith("_"):
                continue
            results[name] = component_data
        return results


class AutoSaver:
    """
    Background auto-save using threading.
    Periodically saves session state without blocking.
    """
    
    def __init__(
        self,
        snapshot: SessionSnapshot,
        interval_sec: int = 300,
        enabled: bool = True
    ):
        self.snapshot = snapshot
        self.interval_sec = interval_sec
        self.enabled = enabled
        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self.last_save_time: Optional[float] = None
        self.save_count = 0
    
    def start(self):
        """Start background auto-save thread"""
        if not self.enabled or self._thread is not None:
            return
        
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()
    
    def stop(self):
        """Stop background auto-save thread"""
        if self._thread is None:
            return
        
        self._stop_event.set()
        self._thread.join(timeout=5)
        self._thread = None
    
    def _run(self):
        """Background thread loop"""
        while not self._stop_event.is_set():
            self._stop_event.wait(self.interval_sec)
            if not self._stop_event.is_set():
                self._do_save()
    
    def _do_save(self):
        """Perform the save operation"""
        try:
            cp = self.snapshot.capture(label="background_auto")
            self.last_save_time = time.time()
            self.save_count += 1
        except Exception:
            pass  # Silent fail in background thread
    
    def force_save(self) -> Optional[Checkpoint]:
        """Force an immediate save"""
        try:
            cp = self.snapshot.capture(label="forced")
            self.last_save_time = time.time()
            self.save_count += 1
            return cp
        except Exception as e:
            return None
    
    @property
    def is_running(self) -> bool:
        return self._thread is not None and self._thread.is_alive()
    
    def status(self) -> Dict:
        return {
            "enabled": self.enabled,
            "running": self.is_running,
            "interval_sec": self.interval_sec,
            "save_count": self.save_count,
            "last_save": datetime.fromtimestamp(self.last_save_time).strftime("%H:%M:%S") if self.last_save_time else None
        }


# Demo
if __name__ == "__main__":
    print("=" * 60)
    print("MSS Checkpoint System Demo")
    print("=" * 60)
    
    # 1. Basic checkpoint
    print("\n1. Manual Checkpoints:")
    cm = CheckpointManager(checkpoint_dir="demo_checkpoints", max_checkpoints=5)
    
    cp1 = cm.save({"step": 1, "data": "initial"}, label="init")
    print(f"   Saved: {cp1.label} at {cp1.formatted_time}")
    
    cp2 = cm.save({"step": 2, "data": "processed"}, label="after_process")
    print(f"   Saved: {cp2.label} at {cp2.formatted_time}")
    
    # 2. Auto-check
    print("\n2. Auto-Check (operation-based):")
    for i in range(12):
        cp = cm.auto_check({"op": i}, operation_label=f"op_{i}")
        if cp:
            print(f"   Auto-saved: {cp.label}")
    
    # 3. List checkpoints
    print("\n3. Checkpoint History:")
    for info in cm.list_checkpoints():
        print(f"   [{info['time']}] {info['label']} (keys: {info['data_keys']})")
    
    # 4. Recovery
    print("\n4. Recovery:")
    recovered = cm.recover()
    print(f"   Recovered keys: {list(recovered.keys())}")
    print(f"   Data: {recovered}")
    
    # 5. Session snapshot
    print("\n5. Session Snapshot:")
    snapshot = SessionSnapshot(cm)
    snapshot.register("engine", lambda: {"status": "running", "version": "1.0"})
    snapshot.register("stats", lambda: {"requests": 42, "errors": 0})
    
    cp = snapshot.capture(label="full_snapshot")
    print(f"   Captured {len(snapshot.components)} components")
    print(f"   Data keys: {list(cp.data.keys())}")
    
    # Cleanup
    cm.clear_all()
    if os.path.exists("demo_checkpoints"):
        import shutil
        shutil.rmtree("demo_checkpoints")
    
    print("\n" + "=" * 60)
    print("Demo complete")
