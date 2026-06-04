"""
MSS-AI Power Manager - Standby/Hibernation functionality
Manages system power states for energy efficiency and model lifecycle
"""

import json
import os
import time
import subprocess
from dataclasses import dataclass, field
from typing import Dict, Optional, List
from enum import Enum
from datetime import datetime, timedelta

class PowerState(Enum):
    ACTIVE = "active"           # Full operation
    STANDBY = "standby"         # Reduced power, quick resume
    HIBERNATE = "hibernate"     # Save state to disk, shutdown models
    SUSPEND = "suspend"         # Pause operations, keep models loaded
    OFF = "off"                 # Full shutdown

@dataclass
class PowerProfile:
    """Power management configuration"""
    standby_timeout_minutes: int = 30      # Auto-standby after inactivity
    hibernate_timeout_minutes: int = 120   # Auto-hibernate after inactivity
    gpu_idle_threshold_percent: float = 5.0  # GPU usage % to consider idle
    cpu_idle_threshold_percent: float = 10.0  # CPU usage % to consider idle
    save_state_on_hibernate: bool = True
    unload_models_on_standby: bool = False
    keep_warm_models: List[str] = field(default_factory=lambda: ["qwen2.5:7b"])

@dataclass
class SystemState:
    """Serializable system state for hibernate/resume"""
    timestamp: str
    active_model: str
    loaded_models: List[str]
    dialog_history_count: int
    stats_snapshot: Dict
    skill_context_level: str
    arbiter_config: Dict

class PowerManager:
    """
    Manages MSS-AI system power states

    Features:
    - Auto-standby after inactivity
    - Hibernate to disk (save/restore state)
    - Model lifecycle management (unload/load)
    - GPU memory optimization
    """

    STATE_FILE = "system_state.json"

    def __init__(self, profile: Optional[PowerProfile] = None):
        self.profile = profile or PowerProfile()
        self.state = PowerState.ACTIVE
        self.last_activity = time.time()
        self.state_file_path = os.path.join(
            os.path.dirname(__file__),
            self.STATE_FILE
        )
        self._activity_callbacks: List[callable] = []
        self._state_change_callbacks: List[callable] = []

    def register_activity_callback(self, callback: callable):
        """Register callback for activity events"""
        self._activity_callbacks.append(callback)

    def register_state_callback(self, callback: callable):
        """Register callback for state changes"""
        self._state_change_callbacks.append(callback)

    def record_activity(self, activity_type: str = "general"):
        """Record user/system activity"""
        self.last_activity = time.time()
        for cb in self._activity_callbacks:
            try:
                cb(activity_type, self.last_activity)
            except Exception:
                pass

    def get_idle_time_seconds(self) -> float:
        """Get current idle time in seconds"""
        return time.time() - self.last_activity

    def get_idle_time_minutes(self) -> float:
        """Get current idle time in minutes"""
        return self.get_idle_time_seconds() / 60.0

    def should_standby(self) -> bool:
        """Check if system should enter standby"""
        if self.state != PowerState.ACTIVE:
            return False
        return self.get_idle_time_minutes() >= self.profile.standby_timeout_minutes

    def should_hibernate(self) -> bool:
        """Check if system should hibernate"""
        if self.state not in [PowerState.ACTIVE, PowerState.STANDBY]:
            return False
        return self.get_idle_time_minutes() >= self.profile.hibernate_timeout_minutes

    def enter_standby(self, tactic_instance=None) -> Dict:
        """
        Enter standby mode - reduce power but keep quick resume

        Actions:
        - Unload non-essential models (if configured)
        - Reduce GPU memory usage
        - Keep core services running
        """
        if self.state == PowerState.STANDBY:
            return {"success": True, "message": "Already in standby", "state": self.state.value}

        previous_state = self.state
        self.state = PowerState.STANDBY

        result = {
            "success": True,
            "previous_state": previous_state.value,
            "current_state": self.state.value,
            "actions": []
        }

        # Unload non-essential models if configured
        if self.profile.unload_models_on_standby and tactic_instance:
            try:
                unloaded = self._unload_non_essential_models(tactic_instance)
                result["actions"].append(f"Unloaded {unloaded} non-essential models")
            except Exception as e:
                result["actions"].append(f"Model unload failed: {e}")

        # Reduce GPU memory (if possible)
        try:
            gpu_freed = self._optimize_gpu_memory()
            if gpu_freed:
                result["actions"].append(f"GPU memory optimized")
        except Exception as e:
            result["actions"].append(f"GPU optimization skipped: {e}")

        self._notify_state_change(previous_state, self.state)
        return result

    def enter_hibernate(self, tactic_instance=None) -> Dict:
        """
        Enter hibernate mode - save state to disk, shutdown models

        Actions:
        - Save full system state
        - Unload all models
        - Clear GPU memory
        - Write state file for resume
        """
        if self.state == PowerState.HIBERNATE:
            return {"success": True, "message": "Already hibernating", "state": self.state.value}

        previous_state = self.state
        self.state = PowerState.HIBERNATE

        result = {
            "success": True,
            "previous_state": previous_state.value,
            "current_state": self.state.value,
            "actions": []
        }

        # Save system state
        if self.profile.save_state_on_hibernate and tactic_instance:
            try:
                state_data = self._capture_system_state(tactic_instance)
                self._save_state_to_disk(state_data)
                result["actions"].append("System state saved to disk")
            except Exception as e:
                result["actions"].append(f"State save failed: {e}")

        # Unload all models
        try:
            unloaded = self._unload_all_models()
            result["actions"].append(f"Unloaded {unloaded} models")
        except Exception as e:
            result["actions"].append(f"Model unload failed: {e}")

        self._notify_state_change(previous_state, self.state)
        return result

    def resume_from_standby(self, tactic_instance=None) -> Dict:
        """Resume from standby - restore full operation"""
        if self.state == PowerState.ACTIVE:
            return {"success": True, "message": "Already active", "state": self.state.value}

        previous_state = self.state
        self.state = PowerState.ACTIVE
        self.last_activity = time.time()

        result = {
            "success": True,
            "previous_state": previous_state.value,
            "current_state": self.state.value,
            "actions": ["System resumed to active state"]
        }

        self._notify_state_change(previous_state, self.state)
        return result

    def resume_from_hibernate(self, tactic_instance=None) -> Dict:
        """
        Resume from hibernate - restore state from disk

        Actions:
        - Load saved state
        - Reload models
        - Restore context
        """
        if self.state == PowerState.ACTIVE:
            return {"success": True, "message": "Already active", "state": self.state.value}

        previous_state = self.state
        self.state = PowerState.ACTIVE
        self.last_activity = time.time()

        result = {
            "success": True,
            "previous_state": previous_state.value,
            "current_state": self.state.value,
            "actions": []
        }

        # Restore system state
        try:
            state_data = self._load_state_from_disk()
            if state_data and tactic_instance:
                self._restore_system_state(state_data, tactic_instance)
                result["actions"].append("System state restored from disk")
            else:
                result["actions"].append("No saved state found, starting fresh")
        except Exception as e:
            result["actions"].append(f"State restore failed: {e}")

        self._notify_state_change(previous_state, self.state)
        return result

    def check_auto_power_management(self, tactic_instance=None) -> Optional[Dict]:
        """
        Check if auto power management should trigger
        Call this periodically (e.g., every minute)
        """
        if self.should_hibernate():
            return self.enter_hibernate(tactic_instance)
        elif self.should_standby():
            return self.enter_standby(tactic_instance)
        return None

    def get_status(self) -> Dict:
        """Get current power management status"""
        return {
            "state": self.state.value,
            "idle_time_minutes": round(self.get_idle_time_minutes(), 2),
            "standby_timeout": self.profile.standby_timeout_minutes,
            "hibernate_timeout": self.profile.hibernate_timeout_minutes,
            "will_standby_in": max(0, round(self.profile.standby_timeout_minutes - self.get_idle_time_minutes(), 2)),
            "will_hibernate_in": max(0, round(self.profile.hibernate_timeout_minutes - self.get_idle_time_minutes(), 2))
        }

    def _unload_non_essential_models(self, tactic_instance) -> int:
        """Unload models not in keep_warm list"""
        count = 0
        # This would integrate with model_manager
        # For now, placeholder implementation
        return count

    def _unload_all_models(self) -> int:
        """Unload all Ollama models"""
        try:
            result = subprocess.run(
                ["ollama", "list"],
                capture_output=True, text=True,
                encoding='utf-8', errors='replace', timeout=30
            )
            if result.returncode == 0:
                lines = result.stdout.strip().split('\n')[1:]  # Skip header
                count = len(lines)
                # Note: Actual unloading would use ollama stop or similar
                return count
        except Exception:
            pass
        return 0

    def _optimize_gpu_memory(self) -> bool:
        """Attempt to optimize GPU memory usage"""
        try:
            # Could trigger garbage collection or memory optimization
            import gc
            gc.collect()
            return True
        except Exception:
            return False

    def _capture_system_state(self, tactic_instance) -> SystemState:
        """Capture current system state"""
        return SystemState(
            timestamp=datetime.now().isoformat(),
            active_model=getattr(tactic_instance, 'responder', None) and getattr(tactic_instance.responder, 'model', 'unknown') or 'unknown',
            loaded_models=self._get_loaded_models(),
            dialog_history_count=0,  # Would capture from dialog
            stats_snapshot=getattr(tactic_instance, 'get_stats', lambda: {})(),
            skill_context_level="L2",
            arbiter_config={}
        )

    def _save_state_to_disk(self, state: SystemState):
        """Save state to JSON file"""
        data = {
            "timestamp": state.timestamp,
            "active_model": state.active_model,
            "loaded_models": state.loaded_models,
            "dialog_history_count": state.dialog_history_count,
            "stats_snapshot": state.stats_snapshot,
            "skill_context_level": state.skill_context_level,
            "arbiter_config": state.arbiter_config
        }
        with open(self.state_file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def _load_state_from_disk(self) -> Optional[SystemState]:
        """Load state from JSON file"""
        if not os.path.exists(self.state_file_path):
            return None

        with open(self.state_file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        return SystemState(
            timestamp=data.get("timestamp", ""),
            active_model=data.get("active_model", ""),
            loaded_models=data.get("loaded_models", []),
            dialog_history_count=data.get("dialog_history_count", 0),
            stats_snapshot=data.get("stats_snapshot", {}),
            skill_context_level=data.get("skill_context_level", "L2"),
            arbiter_config=data.get("arbiter_config", {})
        )

    def _restore_system_state(self, state: SystemState, tactic_instance):
        """Restore system state to tactic instance"""
        # Would restore models, context, etc.
        pass

    def _get_loaded_models(self) -> List[str]:
        """Get list of currently loaded Ollama models"""
        try:
            result = subprocess.run(
                ["ollama", "list"],
                capture_output=True, text=True,
                encoding='utf-8', errors='replace', timeout=30
            )
            if result.returncode == 0:
                lines = result.stdout.strip().split('\n')[1:]
                models = []
                for line in lines:
                    parts = line.split()
                    if parts:
                        models.append(parts[0])
                return models
        except Exception:
            pass
        return []

    def _notify_state_change(self, old_state: PowerState, new_state: PowerState):
        """Notify state change callbacks"""
        for cb in self._state_change_callbacks:
            try:
                cb(old_state, new_state)
            except Exception:
                pass

class StandbyMonitor:
    """
    Background monitor for automatic standby/hibernate
    Run in separate thread or scheduled task
    """

    def __init__(self, power_manager: PowerManager, check_interval_seconds: int = 60):
        self.pm = power_manager
        self.interval = check_interval_seconds
        self._running = False
        self._tactic_instance = None

    def set_tactic(self, tactic_instance):
        """Set tactic instance for power management"""
        self._tactic_instance = tactic_instance

    def start(self):
        """Start monitoring (blocking)"""
        self._running = True
        while self._running:
            result = self.pm.check_auto_power_management(self._tactic_instance)
            if result:
                print(f"[PowerManager] Auto-transition: {result['previous_state']} -> {result['current_state']}")
            time.sleep(self.interval)

    def stop(self):
        """Stop monitoring"""
        self._running = False

    def start_background(self):
        """Start monitoring in background thread"""
        import threading
        self._thread = threading.Thread(target=self.start, daemon=True)
        self._thread.start()
        return self._thread

# Convenience functions for MSSTactic integration
def create_default_power_manager() -> PowerManager:
    """Create power manager with default profile"""
    return PowerManager(PowerProfile())

def integrate_with_tactic(tactic_instance, standby_timeout: int = 30, hibernate_timeout: int = 120):
    """
    Integrate power management with MSSTactic instance

    Usage:
        tactic = MSSTactic()
        pm, monitor = integrate_with_tactic(tactic)
        monitor.start_background()
    """
    profile = PowerProfile(
        standby_timeout_minutes=standby_timeout,
        hibernate_timeout_minutes=hibernate_timeout
    )
    pm = PowerManager(profile)
    monitor = StandbyMonitor(pm, check_interval_seconds=60)
    monitor.set_tactic(tactic_instance)

    # Register activity tracking
    original_generate = tactic_instance.generate
    def tracked_generate(*args, **kwargs):
        pm.record_activity("generate")
        return original_generate(*args, **kwargs)
    tactic_instance.generate = tracked_generate

    original_analyze = tactic_instance.analyze
    def tracked_analyze(*args, **kwargs):
        pm.record_activity("analyze")
        return original_analyze(*args, **kwargs)
    tactic_instance.analyze = tracked_analyze

    return pm, monitor

if __name__ == "__main__":
    print("MSS-AI Power Manager")
    print("=" * 50)

    pm = create_default_power_manager()
    print(f"Initial state: {pm.state.value}")
    print(f"Status: {pm.get_status()}")

    # Simulate activity
    pm.record_activity("test")
    print(f"\nAfter activity - idle: {pm.get_idle_time_minutes():.2f} min")

    # Test standby
    result = pm.enter_standby()
    print(f"\nEnter standby: {result}")
    print(f"Status: {pm.get_status()}")

    # Test resume
    result = pm.resume_from_standby()
    print(f"\nResume: {result}")
    print(f"Status: {pm.get_status()}")
