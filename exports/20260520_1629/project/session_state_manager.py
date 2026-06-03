"""Session State Manager — 减少对话上下文占用"""

import json
from datetime import datetime
from pathlib import Path

class SessionStateManager:
    """会话状态管理器 — 持久化状态减少上下文依赖"""
    
    def __init__(self, base_path="C:\\MSS-AI-Project"):
        self.base_path = Path(base_path)
        self.state_file = self.base_path / ".session_state.json"
        self.delta_file = self.base_path / ".session_delta.json"
        self.log_file = self.base_path / "session_execution.log"
        
    def checkpoint(self, state_dict):
        """创建检查点"""
        state = {
            "version": "1.0",
            "timestamp": datetime.now().isoformat(),
            "active_tasks": state_dict.get("active_tasks", []),
            "completed_tasks": state_dict.get("completed_tasks", []),
            "pending_decisions": state_dict.get("pending_decisions", []),
            "system_params": state_dict.get("system_params", {}),
        }
        
        with open(self.state_file, 'w', encoding='utf-8') as f:
            json.dump(state, f, indent=2, ensure_ascii=False)
        
        return f"State checkpointed: {self.state_file}"
    
    def restore(self):
        """从检查点恢复"""
        try:
            with open(self.state_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return None
    
    def log_execution(self, task_id, action, result):
        """记录执行日志到文件而非对话"""
        entry = {
            "timestamp": datetime.now().isoformat(),
            "task": task_id,
            "action": action,
            "result": result,
        }
        
        with open(self.log_file, 'a', encoding='utf-8') as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    
    def get_delta(self, previous_state, current_state):
        """计算状态变更增量"""
        changes = []
        
        for key in set(previous_state.keys()) | set(current_state.keys()):
            prev = previous_state.get(key)
            curr = current_state.get(key)
            
            if prev != curr:
                changes.append({
                    "field": key,
                    "from": prev,
                    "to": curr,
                })
        
        return changes


class TaskDeltaReporter:
    """增量任务状态报告"""
    
    def report_changes(self, previous_state, current_state):
        """只报告变更"""
        changes = []
        
        for tid, task in current_state.items():
            prev = previous_state.get(tid, {})
            
            if prev.get('status') != task['status']:
                changes.append({
                    'task': tid,
                    'from': prev.get('status', 'NEW'),
                    'to': task['status'],
                    'reason': task.get('change_reason', '')
                })
        
        if not changes:
            return "[STATUS] No changes since last update"
        
        lines = ["[CHANGES]"]
        for c in changes:
            lines.append(f"  {c['task']}: {c['from']} → {c['to']}")
            if c['reason']:
                lines.append(f"    Reason: {c['reason']}")
        
        return '\n'.join(lines)


class SilentTaskExecutor:
    """静默任务执行器"""
    
    def __init__(self, state_manager):
        self.state = state_manager
        self.report_interval = 5
    
    def execute_batch(self, tasks):
        """批量执行任务"""
        results = []
        
        for i, task in enumerate(tasks):
            result = self._execute_silent(task)
            results.append(result)
            
            self.state.log_execution(task['id'], 'execute', result['status'])
            
            if (i + 1) % self.report_interval == 0:
                self._report_batch(results[-self.report_interval:])
        
        return self._final_summary(results)
    
    def _execute_silent(self, task):
        """静默执行"""
        return {"task": task['id'], "status": "COMPLETED"}
    
    def _report_batch(self, batch_results):
        """批量报告"""
        passed = sum(1 for r in batch_results if r['status'] == 'COMPLETED')
        print(f"[BATCH] {passed}/{len(batch_results)} completed")
    
    def _final_summary(self, all_results):
        """最终摘要"""
        total = len(all_results)
        completed = sum(1 for r in all_results if r['status'] == 'COMPLETED')
        
        return {
            "total": total,
            "completed": completed,
            "failed": total - completed,
            "detail_level": "See session_execution.log for full details"
        }


if __name__ == "__main__":
    # 测试
    manager = SessionStateManager()
    
    test_state = {
        "active_tasks": ["SIM-003", "MIS-001"],
        "completed_tasks": ["GWAY-001", "TEST-001"],
        "pending_decisions": [],
        "system_params": {"T": 0.9992, "M_L": 1.0}
    }
    
    print(manager.checkpoint(test_state))
    restored = manager.restore()
    print(f"Restored: {len(restored['active_tasks'])} active tasks")
