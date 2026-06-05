#!/usr/bin/env python3
"""
MSS-AI Task Manager
Safe JSON task bar manipulation with atomic writes and validation.
Replaces unreliable edit tool for task_bar_current.json updates.
"""

import json
import sys
import os
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Any, List

DEFAULT_TASK_BAR = Path("C:/MSS-AI-Project/task_bar_current.json")
BACKUP_DIR = Path("C:/MSS-AI-Project/backups")


class TaskManager:
    """Manages task_bar_current.json with safe atomic operations."""
    
    def __init__(self, task_bar_path: Optional[Path] = None):
        self.task_bar_path = task_bar_path or DEFAULT_TASK_BAR
        self.backup_dir = BACKUP_DIR
        self.backup_dir.mkdir(exist_ok=True)
        self.data = self._load()
    
    def _load(self) -> Dict[str, Any]:
        """Load task bar JSON with validation."""
        if not self.task_bar_path.exists():
            return self._create_default()
        
        try:
            with open(self.task_bar_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            self._validate(data)
            return data
        except (json.JSONDecodeError, KeyError) as e:
            print(f"[ERROR] Corrupted task bar: {e}")
            return self._create_default()
    
    def _create_default(self) -> Dict[str, Any]:
        """Create default task bar structure."""
        return {
            "version": "3.1",
            "last_sync": datetime.now().isoformat(),
            "system_state": {
                "M_L_claimed": 0,
                "framework_completeness": "25-30%",
                "verification_status": "0%",
                "T_value": 0.999,
                "gamma": "1.02γ₀"
            },
            "phase": "D",
            "phase_progress": 50,
            "tasks": {},
            "metadata": {
                "created": datetime.now().isoformat(),
                "notes": "Honest baseline mode"
            }
        }
    
    def _validate(self, data: Dict[str, Any]) -> None:
        """Validate task bar structure."""
        required = ["version", "last_sync", "phase"]
        for key in required:
            if key not in data:
                raise KeyError(f"Missing required key: {key}")
        # Accept both 'tasks' and 'active_tasks' structures
        if "tasks" not in data and "active_tasks" not in data:
            raise KeyError("Missing required key: tasks or active_tasks")
    
    def _backup(self) -> Path:
        """Create timestamped backup."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = self.backup_dir / f"task_bar_{timestamp}.json"
        with open(backup_path, 'w', encoding='utf-8') as f:
            json.dump(self.data, f, ensure_ascii=False, indent=2)
        return backup_path
    
    def _save(self) -> None:
        """Atomic save with backup."""
        self._backup()
        self.data["last_sync"] = datetime.now().isoformat()
        
        # Write to temp file first, then rename for atomicity
        temp_path = self.task_bar_path.with_suffix('.tmp')
        with open(temp_path, 'w', encoding='utf-8') as f:
            json.dump(self.data, f, ensure_ascii=False, indent=2)
        
        # Atomic rename
        temp_path.replace(self.task_bar_path)
        print(f"[OK] Task bar saved: {self.task_bar_path}")
    
    def get_task(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Get task by ID."""
        return self.data.get("tasks", {}).get(task_id)
    
    def update_task(self, task_id: str, **kwargs) -> Dict[str, Any]:
        """Update task fields. Creates if not exists."""
        if "tasks" not in self.data:
            self.data["tasks"] = {}
        
        if task_id not in self.data["tasks"]:
            self.data["tasks"][task_id] = {
                "id": task_id,
                "name": task_id,
                "progress": 0,
                "status": "pending",
                "axioms": [],
                "priority": 5,
                "created": datetime.now().isoformat()
            }
        
        task = self.data["tasks"][task_id]
        
        # Valid fields
        valid_fields = {"name", "progress", "status", "axioms", "priority", 
                       "notes", "deliverables", "blockers"}
        
        for key, value in kwargs.items():
            if key in valid_fields:
                task[key] = value
            else:
                print(f"[WARN] Ignoring invalid field: {key}")
        
        task["updated"] = datetime.now().isoformat()
        self._save()
        return task
    
    def update_progress(self, task_id: str, progress: int) -> Dict[str, Any]:
        """Update task progress (0-100)."""
        progress = max(0, min(100, progress))
        return self.update_task(task_id, progress=progress)
    
    def list_tasks(self, status: Optional[str] = None) -> List[Dict[str, Any]]:
        """List tasks, optionally filtered by status."""
        tasks = list(self.data.get("tasks", {}).values())
        if status:
            tasks = [t for t in tasks if t.get("status") == status]
        return sorted(tasks, key=lambda x: x.get("priority", 5), reverse=True)
    
    def _get_all_tasks(self) -> List[Dict[str, Any]]:
        """Get all tasks from various structures."""
        tasks = []
        # Handle dict-based tasks
        if "tasks" in self.data and isinstance(self.data["tasks"], dict):
            tasks.extend(self.data["tasks"].values())
        # Handle list-based active_tasks
        if "active_tasks" in self.data and isinstance(self.data["active_tasks"], list):
            tasks.extend(self.data["active_tasks"])
        if "ongoing_tasks" in self.data and isinstance(self.data["ongoing_tasks"], list):
            tasks.extend(self.data["ongoing_tasks"])
        if "completed_tasks" in self.data and isinstance(self.data["completed_tasks"], list):
            tasks.extend(self.data["completed_tasks"])
        return tasks
    
    def get_phase_summary(self) -> Dict[str, Any]:
        """Get phase summary with statistics."""
        tasks = self._get_all_tasks()
        if not tasks:
            return {"total": 0, "avg_progress": 0}
        
        total = len(tasks)
        # Handle both int and string progress
        def parse_progress(p):
            if isinstance(p, str):
                return float(p.replace('%', ''))
            return float(p) if p is not None else 0
        
        avg_progress = sum(parse_progress(t.get("progress", 0)) for t in tasks) / total
        completed = sum(1 for t in tasks if parse_progress(t.get("progress", 0)) >= 100)
        
        return {
            "phase": self.data.get("phase", "?"),
            "total_tasks": total,
            "completed": completed,
            "avg_progress": round(avg_progress, 1),
            "system_state": self.data.get("system_state", self.data.get("honesty_baseline", {}))
        }
    
    def set_system_state(self, **kwargs) -> None:
        """Update system state fields."""
        if "system_state" not in self.data:
            self.data["system_state"] = {}
        
        valid = {"M_L_claimed", "framework_completeness", "verification_status", 
                "T_value", "gamma", "notes"}
        
        for key, value in kwargs.items():
            if key in valid:
                self.data["system_state"][key] = value
        
        self._save()


def main():
    """CLI interface for task management."""
    import argparse
    
    parser = argparse.ArgumentParser(description="MSS-AI Task Manager")
    parser.add_argument("action", choices=["get", "update", "progress", "list", "summary", "state"])
    parser.add_argument("--task", "-t", help="Task ID")
    parser.add_argument("--progress", "-p", type=int, help="Progress (0-100)")
    parser.add_argument("--status", "-s", help="Task status")
    parser.add_argument("--field", "-f", action="append", nargs=2, metavar=("KEY", "VALUE"),
                       help="Update field (can be repeated)")
    
    args = parser.parse_args()
    
    tm = TaskManager()
    
    if args.action == "get" and args.task:
        task = tm.get_task(args.task)
        print(json.dumps(task, ensure_ascii=False, indent=2) if task else "Task not found")
    
    elif args.action == "update" and args.task:
        kwargs = {}
        if args.field:
            for key, value in args.field:
                # Try to parse as int/float
                try:
                    value = int(value)
                except ValueError:
                    try:
                        value = float(value)
                    except ValueError:
                        pass
                kwargs[key] = value
        task = tm.update_task(args.task, **kwargs)
        print(json.dumps(task, ensure_ascii=False, indent=2))
    
    elif args.action == "progress" and args.task and args.progress is not None:
        task = tm.update_progress(args.task, args.progress)
        print(f"Updated {args.task}: {task['progress']}%")
    
    elif args.action == "list":
        tasks = tm.list_tasks(args.status)
        for t in tasks:
            print(f"[{t['id']}] {t.get('name', '')}: {t.get('progress', 0)}% ({t.get('status', '?')})")
    
    elif args.action == "summary":
        summary = tm.get_phase_summary()
        print(json.dumps(summary, ensure_ascii=False, indent=2))
    
    elif args.action == "state":
        print(json.dumps(tm.data.get("system_state", {}), ensure_ascii=False, indent=2))
    
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
