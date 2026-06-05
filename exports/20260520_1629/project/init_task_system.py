"""
初始化任务系统 - 导入现有任务
"""

import json
from task_system import TaskSystem, Task, TaskStatus, TaskPriority

def init_from_legacy():
    """从旧版task_bar_current.json导入任务"""
    ts = TaskSystem()
    
    # 读取旧版任务栏
    try:
        with open("task_bar_current.json", "r", encoding="utf-8") as f:
            legacy = json.load(f)
    except:
        print("旧版任务栏不存在，创建默认任务")
        legacy = None
    
    # 创建Phase D任务
    default_tasks = [
        # D1 Week 1
        {"id": "D1-001", "name": "符号引擎v4.0架构设计", "priority": TaskPriority.P0, 
         "phase": "D1", "week": "Week 1", "niche": "AI核心"},
        {"id": "D1-002", "name": "API接口设计", "priority": TaskPriority.P1,
         "phase": "D1", "week": "Week 1", "niche": "AI核心"},
        # D1 Week 2
        {"id": "D1-003", "name": "图算法CSR优化", "priority": TaskPriority.P1,
         "phase": "D1", "week": "Week 2", "niche": "AI核心"},
        # D1 Week 3
        {"id": "D1-004", "name": "监控体系搭建", "priority": TaskPriority.P2,
         "phase": "D1", "week": "Week 3", "niche": "基础设施"},
        # D2 Week 5-6
        {"id": "D2-001", "name": "韧性扫描器SaaS化", "priority": TaskPriority.P1,
         "phase": "D2", "week": "Week 5", "niche": "产品工具"},
        # D2 Week 7-8
        {"id": "D2-002", "name": "合规扫描器API化", "priority": TaskPriority.P2,
         "phase": "D2", "week": "Week 7", "niche": "产品工具"},
        # D3 Week 9
        {"id": "D3-001", "name": "GRAV-EXP-001启动", "priority": TaskPriority.P0,
         "phase": "D3", "week": "Week 9", "niche": "理论研究"},
        {"id": "D3-002", "name": "数据采集系统", "priority": TaskPriority.P2,
         "phase": "D3", "week": "Week 9", "niche": "基础设施"},
        # D4 Week 13-16
        {"id": "D4-001", "name": "开源代码清理", "priority": TaskPriority.P3,
         "phase": "D4", "week": "Week 13", "niche": "基础设施"},
        {"id": "D4-002", "name": "社区建设运营", "priority": TaskPriority.P4,
         "phase": "D4", "week": "Week 15", "niche": "产品工具"},
    ]
    
    # 添加进行中的任务
    ongoing_tasks = [
        {"id": "SIM-003", "name": "SC-001长期演化", "priority": TaskPriority.P2,
         "status": TaskStatus.ACTIVE, "progress": 80.0, "niche": "模拟计算",
         "note": "50万步长期模拟后台运行中"},
        {"id": "MIS-001", "name": "MIS系统原型", "priority": TaskPriority.P2,
         "status": TaskStatus.ACTIVE, "progress": 77.8, "niche": "产品化",
         "note": "DEMO运行中"},
        {"id": "PHI-001", "name": "Φ币工程化", "priority": TaskPriority.P4,
         "status": TaskStatus.ACTIVE, "progress": 60.0, "niche": "货币系统",
         "note": "白皮书60%"},
        {"id": "CUPY-001", "name": "CuPy CUDA加速", "priority": TaskPriority.P3,
         "status": TaskStatus.BLOCKED, "progress": 50.0, "niche": "基础设施",
         "note": "版本冲突待解决"},
    ]
    
    # 创建所有任务
    for t in default_tasks:
        task = ts.create_task(
            name=t["name"],
            priority=t["priority"],
            phase=t.get("phase"),
            week=t.get("week"),
            niche=t.get("niche", "")
        )
        # 更新ID为预设值
        del ts.tasks[task.id]
        task.id = t["id"]
        ts.tasks[t["id"]] = task
    
    for t in ongoing_tasks:
        task = ts.create_task(
            name=t["name"],
            priority=t["priority"],
            niche=t.get("niche", ""),
            note=t.get("note", "")
        )
        # 更新状态
        task.status = t.get("status", TaskStatus.PENDING)
        task.progress = t.get("progress", 0.0)
        del ts.tasks[task.id]
        task.id = t["id"]
        ts.tasks[t["id"]] = task
    
    ts._save_data()
    
    print(f"初始化完成！")
    print(f"  项目数：{len(ts.projects)}")
    print(f"  任务数：{len(ts.tasks)}")
    print(f"\n活跃任务：")
    for task in ts.get_active_tasks()[:5]:
        print(f"  [{task.priority.name}] {task.name}")

if __name__ == "__main__":
    init_from_legacy()
