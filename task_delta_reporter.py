"""Task Delta Reporter 鈥?澧為噺鐘舵€佹姤鍛?""

import json
from pathlib import Path

class TaskDeltaReporter:
    """鍙姤鍛婁换鍔＄姸鎬佸彉鏇?""

    def __init__(self, task_file="E:\\AI_Workspace\\MSS-AI\\project\\task_bar_current.json"):
        self.task_file = Path(task_file)
        self.previous_state = self._load_current()

    def _load_current(self):
        """鍔犺浇褰撳墠鐘舵€?""
        try:
            with open(self.task_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return {}

    def report_changes(self):
        """鎶ュ憡鑷笂娆℃鏌ヤ互鏉ョ殑鍙樻洿"""
        current = self._load_current()
        changes = []

        # 妫€鏌ユ墍鏈変换鍔＄被鍒?
        for category in ['active_tasks', 'completed_tasks', 'standby_tasks', 'pending_tasks', 'archived_tasks']:
            prev_items = {t['id']: t for t in self.previous_state.get(category, [])}
            curr_items = {t['id']: t for t in current.get(category, [])}

            # 妫€娴嬬姸鎬佸彉鏇?
            for tid, task in curr_items.items():
                if tid in prev_items:
                    prev_cat = self._find_task_category(self.previous_state, tid)
                    curr_cat = category
                    if prev_cat != curr_cat:
                        changes.append({
                            'task': tid,
                            'name': task['name'],
                            'from': prev_cat,
                            'to': curr_cat,
                        })
                else:
                    # 鏂颁换鍔?
                    changes.append({
                        'task': tid,
                        'name': task['name'],
                        'from': 'NEW',
                        'to': category,
                    })

        # 鏇存柊鐘舵€?
        self.previous_state = current

        if not changes:
            return "[STATUS] No task changes since last update"

        lines = ["[TASK CHANGES]"]
        for c in changes:
            lines.append(f"  {c['task']} ({c['name']}): {c['from']} 鈫?{c['to']}")

        return '\n'.join(lines)

    def _find_task_category(self, state, task_id):
        """鏌ユ壘浠诲姟鎵€鍦ㄧ被鍒?""
        for category in ['active_tasks', 'completed_tasks', 'standby_tasks', 'pending_tasks', 'archived_tasks']:
            for task in state.get(category, []):
                if task['id'] == task_id:
                    return category
        return 'UNKNOWN'

    def get_summary(self):
        """鑾峰彇褰撳墠鎽樿"""
        current = self._load_current()

        summary = {
            'active': len(current.get('active_tasks', [])),
            'completed': len(current.get('completed_tasks', [])),
            'standby': len(current.get('standby_tasks', [])),
            'pending': len(current.get('pending_tasks', [])),
            'archived': len(current.get('archived_tasks', [])),
        }

        return f"[TASKS] Active:{summary['active']} Completed:{summary['completed']} Standby:{summary['standby']} Pending:{summary['pending']} Archived:{summary['archived']}"

if __name__ == "__main__":
    reporter = TaskDeltaReporter()
    print(reporter.get_summary())
    print(reporter.report_changes())
