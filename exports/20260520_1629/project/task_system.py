"""
MSS-AI 智能任务栏系统 v1.0
"""

import json
import os
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from enum import Enum
import hashlib

class TaskStatus(Enum):
    PENDING = "pending"
    ACTIVE = "active"
    COMPLETED = "completed"
    BLOCKED = "blocked"
    ARCHIVED = "archived"

class TaskPriority(Enum):
    P0 = 10
    P1 = 9
    P2 = 8
    P3 = 7
    P4 = 6

@dataclass
class Task:
    id: str
    name: str
    project: str
    status: TaskStatus
    priority: TaskPriority
    progress: float = 0.0
    phase: Optional[str] = None
    week: Optional[str] = None
    niche: str = ""
    note: str = ""
    dependencies: List[str] = field(default_factory=list)
    subtasks: List[str] = field(default_factory=list)
    created_at: str = ""
    updated_at: str = ""
    completed_at: Optional[str] = None
    
    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now().isoformat()
        if not self.updated_at:
            self.updated_at = self.created_at
    
    def to_dict(self) -> Dict:
        return {
            "id": self.id, "name": self.name, "project": self.project,
            "status": self.status.value, "priority": self.priority.value,
            "progress": self.progress, "phase": self.phase, "week": self.week,
            "niche": self.niche, "note": self.note,
            "dependencies": self.dependencies, "subtasks": self.subtasks,
            "created_at": self.created_at, "updated_at": self.updated_at,
            "completed_at": self.completed_at
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'Task':
        return cls(
            id=data["id"], name=data["name"], project=data["project"],
            status=TaskStatus(data["status"]), priority=TaskPriority(data["priority"]),
            progress=data["progress"], phase=data.get("phase"), week=data.get("week"),
            niche=data.get("niche", ""), note=data.get("note", ""),
            dependencies=data.get("dependencies", []), subtasks=data.get("subtasks", []),
            created_at=data["created_at"], updated_at=data["updated_at"],
            completed_at=data.get("completed_at")
        )

@dataclass
class Project:
    id: str
    name: str
    description: str
    status: str = "active"
    phase: str = ""
    progress: float = 0.0
    tasks: List[str] = field(default_factory=list)
    parent_project: Optional[str] = None
    child_projects: List[str] = field(default_factory=list)
    created_at: str = ""
    updated_at: str = ""
    
    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now().isoformat()
        if not self.updated_at:
            self.updated_at = self.created_at
    
    def to_dict(self) -> Dict:
        return {
            "id": self.id, "name": self.name, "description": self.description,
            "status": self.status, "phase": self.phase, "progress": self.progress,
            "tasks": self.tasks, "parent_project": self.parent_project,
            "child_projects": self.child_projects,
            "created_at": self.created_at, "updated_at": self.updated_at
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'Project':
        return cls(
            id=data["id"], name=data["name"], description=data["description"],
            status=data.get("status", "active"), phase=data.get("phase", ""),
            progress=data.get("progress", 0.0), tasks=data.get("tasks", []),
            parent_project=data.get("parent_project"),
            child_projects=data.get("child_projects", []),
            created_at=data["created_at"], updated_at=data["updated_at"]
        )

class TaskSystem:
    def __init__(self, data_dir: str = "C:\\MSS-AI-Project"):
        self.data_dir = data_dir
        self.tasks_file = os.path.join(data_dir, "task_system_data.json")
        self.projects: Dict[str, Project] = {}
        self.tasks: Dict[str, Task] = {}
        self.current_project: Optional[str] = None
        self._load_data()
    
    def _load_data(self):
        if os.path.exists(self.tasks_file):
            try:
                with open(self.tasks_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                for proj_data in data.get("projects", []):
                    proj = Project.from_dict(proj_data)
                    self.projects[proj.id] = proj
                for task_data in data.get("tasks", []):
                    task = Task.from_dict(task_data)
                    self.tasks[task.id] = task
                self.current_project = data.get("current_project")
            except Exception as e:
                print(f"加载失败：{e}")
                self._init_default_data()
        else:
            self._init_default_data()
    
    def _save_data(self):
        data = {
            "version": "1.0",
            "updated_at": datetime.now().isoformat(),
            "current_project": self.current_project,
            "projects": [p.to_dict() for p in self.projects.values()],
            "tasks": [t.to_dict() for t in self.tasks.values()]
        }
        try:
            with open(self.tasks_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"保存失败：{e}")
    
    def _init_default_data(self):
        self.projects["mss-ai"] = Project(
            id="mss-ai", name="MSS-AI项目", description="MSS理论AI工程化部署",
            phase="D", child_projects=["mss-research", "mss-product", "mss-infra"]
        )
        self.projects["mss-research"] = Project(
            id="mss-research", name="MSS理论研究", description="理论构建与验证",
            parent_project="mss-ai"
        )
        self.projects["mss-product"] = Project(
            id="mss-product", name="MSS产品化", description="工具产品开发",
            parent_project="mss-ai"
        )
        self.projects["mss-infra"] = Project(
            id="mss-infra", name="MSS基础设施", description="基础设施与部署",
            parent_project="mss-ai"
        )
        self.current_project = "mss-ai"
        self._save_data()
    
    def create_project(self, name: str, description: str, parent: Optional[str] = None) -> Project:
        proj_id = f"proj_{hashlib.md5(f'{name}{datetime.now()}'.encode()).hexdigest()[:8]}"
        project = Project(id=proj_id, name=name, description=description, parent_project=parent)
        self.projects[proj_id] = project
        if parent and parent in self.projects:
            self.projects[parent].child_projects.append(proj_id)
        self._save_data()
        return project
    
    def switch_project(self, project_id: str) -> bool:
        if project_id not in self.projects:
            return False
        self.current_project = project_id
        self._save_data()
        return True
    
    def create_task(self, name: str, priority: TaskPriority = TaskPriority.P2,
                   project: Optional[str] = None, **kwargs) -> Task:
        task_id = f"task_{hashlib.md5(f'{name}{datetime.now()}'.encode()).hexdigest()[:8]}"
        proj_id = project or self.current_project
        task = Task(id=task_id, name=name, project=proj_id, status=TaskStatus.PENDING,
                   priority=priority, progress=0.0, **kwargs)
        self.tasks[task_id] = task
        if proj_id and proj_id in self.projects:
            self.projects[proj_id].tasks.append(task_id)
        self._save_data()
        return task
    
    def update_task(self, task_id: str, **kwargs) -> bool:
        if task_id not in self.tasks:
            return False
        task = self.tasks[task_id]
        for key, value in kwargs.items():
            if hasattr(task, key):
                setattr(task, key, value)
        task.updated_at = datetime.now().isoformat()
        if task.status == TaskStatus.COMPLETED and not task.completed_at:
            task.completed_at = datetime.now().isoformat()
            task.progress = 100.0
        self._save_data()
        return True
    
    def get_active_tasks(self, project_id: Optional[str] = None) -> List[Task]:
        proj_id = project_id or self.current_project
        tasks = [t for t in self.tasks.values()
                if t.project == proj_id and t.status in [TaskStatus.PENDING, TaskStatus.ACTIVE]]
        tasks.sort(key=lambda t: (t.priority.value, -t.progress), reverse=True)
        return tasks
    
    def parse_command(self, command: str) -> Tuple[str, Dict]:
        command_lower = command.lower().strip()
        if any(w in command_lower for w in ["查看", "显示", "任务栏", "状态"]):
            return "show_status", {}
        if "继续推进" in command or ("继续" in command and "推进" in command):
            return "continue_project", {}
        if "切换到" in command:
            parts = command.split("到")
            if len(parts) > 1:
                return "switch_project", {"name": parts[1].strip()}
        if "创建任务" in command:
            parts = command.split("任务")
            if len(parts) > 1:
                return "create_task", {"name": parts[1].strip()}
        if "完成任务" in command:
            parts = command.split("任务")
            if len(parts) > 1:
                return "complete_task", {"name": parts[1].strip()}
        return "help", {}
    
    def execute_command(self, command: str) -> str:
        action, params = self.parse_command(command)
        if action == "show_status":
            return self._format_status()
        elif action == "continue_project":
            return self._continue_project()
        elif action == "switch_project":
            name = params.get("name", "")
            for pid, proj in self.projects.items():
                if name.lower() in proj.name.lower():
                    self.switch_project(pid)
                    return f"已切换到：{proj.name}"
            return f"未找到：{name}"
        elif action == "create_task":
            task = self.create_task(params.get("name", "新任务"))
            return f"已创建：{task.name} ({task.id})"
        elif action == "complete_task":
            name = params.get("name", "")
            for tid, task in self.tasks.items():
                if name.lower() in task.name.lower():
                    self.update_task(tid, status=TaskStatus.COMPLETED)
                    return f"已完成：{task.name}"
            return f"未找到：{name}"
        return self._format_help()
    
    def _format_status(self) -> str:
        if not self.current_project:
            return "未选择项目"
        project = self.projects[self.current_project]
        lines = ["="*50, f"项目：{project.name}", f"阶段：{project.phase or '未设置'}", f"进度：{project.progress}%", "="*50]
        active = self.get_active_tasks()
        if active:
            lines.append(f"\n活跃任务（{len(active)}个）：")
            for t in active[:10]:
                icon = "🟡" if t.status == TaskStatus.ACTIVE else "⚪"
                lines.append(f"  {icon} [{t.priority.name}] {t.name} ({t.progress}%)")
        completed = [t for t in self.tasks.values() if t.project == self.current_project and t.status == TaskStatus.COMPLETED]
        if completed:
            lines.append(f"\n已完成（{len(completed)}个）")
        lines.append("\n" + "="*50)
        return "\n".join(lines)
    
    def _continue_project(self) -> str:
        if not self.current_project:
            return "未选择项目"
        active = self.get_active_tasks()
        if not active:
            return "没有待处理任务"
        top = active[0]
        return f"继续推进：{top.name}\n优先级：{top.priority.name}\n进度：{top.progress}%\n建议：更新进度或处理阻塞"
    
    def _format_help(self) -> str:
        return "命令：查看任务栏 / 继续推进 / 切换到[项目] / 创建任务[名称] / 完成任务[名称]"

def get_task_system() -> TaskSystem:
    return TaskSystem()

if __name__ == "__main__":
    ts = get_task_system()
    print(ts.execute_command("查看任务栏"))
