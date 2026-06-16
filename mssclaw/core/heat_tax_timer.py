"""
MSS Heat Tax Timer — 开发行为热税审计 (H623落地工具 #1).

追踪开发活动的热税支出,当效率持续低于阈值时发出警告。
基于 A3(热税预算)公理: 让"感觉自己在低效"变成"看到热税在燃烧却没有产出"。

用法:
    from mssclaw.core.heat_tax_timer import HeatTaxTimer
    timer = HeatTaxTimer(budget_hours=8)
    timer.start_task("coding", "实现用户登录")
    # ... 工作 ...
    timer.tick()  # 记录进度
    timer.end_task()
    print(timer.report())

自动检查:
    if timer.rolling_efficiency(30) < 0.3:
        timer.warn("当前效率偏低,建议切换任务或休息")
"""
from __future__ import annotations
import time, json
from dataclasses import dataclass, field
from typing import List, Optional, Dict
from pathlib import Path


@dataclass
class TaskRecord:
    """单次开发活动记录."""
    task_id: str
    activity_type: str  # coding | debugging | researching | meeting | reviewing
    description: str
    start_time: float
    end_time: float = 0
    heat_spent: float = 0  # 已用热税(分钟)
    progress_pct: float = 0  # 主观进度 0-100
    outcome: str = ""  # 产出描述
    efficiency: float = 0  # 效率 = 进度/热税


class HeatTaxTimer:
    """
    热税计时器.

    budget_hours: 总预算(小时)
    warn_threshold: 低于此效率阈值时警告 (0-1)
    check_interval_min: 滚动平均窗口(分钟)
    """

    def __init__(self, budget_hours: float = 8, warn_threshold: float = 0.3,
                 check_interval_min: int = 30, save_path: str = None):
        self.budget_hours = budget_hours
        self.budget_minutes = budget_hours * 60
        self.warn_threshold = warn_threshold
        self.check_interval_min = check_interval_min
        self.save_path = Path(save_path or (Path.home() / ".mssclaw" / "heat_tax_log.json"))

        self._tasks: List[TaskRecord] = []
        self._current_task: Optional[TaskRecord] = None
        self._warnings: List[Dict] = []
        self._load()

    def start_task(self, activity_type: str, description: str, task_id: str = None) -> TaskRecord:
        """开始一个开发任务."""
        if self._current_task:
            self.end_task()

        if task_id is None:
            task_id = f"task_{int(time.time())}"

        task = TaskRecord(
            task_id=task_id,
            activity_type=activity_type,
            description=description,
            start_time=time.time(),
        )
        self._current_task = task
        self._tasks.append(task)
        self._save()
        return task

    def tick(self, progress_pct: float = None):
        """记录进度(每5-10分钟调用一次)."""
        if not self._current_task:
            return
        elapsed = (time.time() - self._current_task.start_time) / 60
        self._current_task.heat_spent = elapsed

        if progress_pct is not None:
            self._current_task.progress_pct = progress_pct
            if elapsed > 0:
                self._current_task.efficiency = progress_pct / max(elapsed, 1)

        # Auto-warn if efficiency drops
        eff = self.rolling_efficiency(self.check_interval_min)
        if eff < self.warn_threshold and self.heat_burned_pct() > 0.2:
            self.warn()

    def end_task(self, outcome: str = ""):
        """结束当前任务."""
        if not self._current_task:
            return
        self._current_task.end_time = time.time()
        self._current_task.heat_spent = (
            self._current_task.end_time - self._current_task.start_time
        ) / 60
        self._current_task.outcome = outcome
        if self._current_task.heat_spent > 0:
            self._current_task.efficiency = (
                self._current_task.progress_pct / max(self._current_task.heat_spent, 1)
            )
        self._current_task = None
        self._save()

    def rolling_efficiency(self, window_min: int = 30) -> float:
        """计算最近N分钟的平均效率."""
        now = time.time()
        recent = [
            t for t in self._tasks
            if t.efficiency > 0 and (now - t.start_time) / 60 < window_min
        ]
        if not recent:
            return 1.0
        return sum(t.efficiency for t in recent) / len(recent)

    def heat_burned(self) -> float:
        """已消耗热税(分钟)."""
        return sum(t.heat_spent for t in self._tasks)

    def heat_burned_pct(self) -> float:
        """已消耗热税占预算的百分比."""
        return self.heat_burned() / max(self.budget_minutes, 1)

    def warn(self) -> str:
        """触发效率警告."""
        eff = self.rolling_efficiency(self.check_interval_min)
        msg = (
            f"⚠️ 热税警告: 近{self.check_interval_min}分钟效率={eff:.2f} (阈值={self.warn_threshold})"
        )
        if self._current_task:
            msg += f"\n   当前任务: {self._current_task.description}"
            msg += f"\n   已用: {self._current_task.heat_spent:.0f}分钟"
            msg += f"\n   进度: {self._current_task.progress_pct:.0f}%"

        suggestions = self._escalation_suggestions()
        if suggestions:
            msg += f"\n   升维建议: {suggestions[0]}"

        self._warnings.append({
            "time": time.time(),
            "efficiency": eff,
            "task": self._current_task.description if self._current_task else "idle",
        })
        self._save()
        return msg

    def _escalation_suggestions(self) -> List[str]:
        """A6矛盾升维: 生成破局建议."""
        if not self._current_task:
            return []

        task = self._current_task
        suggestions = []

        if task.heat_spent > 30 and task.progress_pct < 20:
            suggestions.append("换角度: 这个问题真的是'{task.description}'吗? 考虑重新定义问题边界")

        if task.activity_type == "debugging" and task.heat_spent > 15:
            suggestions.append("换工具: 试试用调试器而非print, 或添加更细粒度的日志")

        if task.activity_type == "coding" and task.heat_spent > 45:
            suggestions.append("换方法: 考虑先写测试再实现(TDD), 或先完成最小可行版本")

        if len([w for w in self._warnings if time.time() - w["time"] < 3600]) > 3:
            suggestions.append("换问题: 这个功能真的需要现在实现吗? 考虑推迟到下一个迭代")

        return suggestions

    def report(self) -> str:
        """生成热税审计报告."""
        lines = ["=" * 50, "MSS Heat Tax Report", "=" * 50]
        lines.append(f"预算: {self.budget_hours:.1f}小时")
        lines.append(f"已用: {self.heat_burned()/60:.1f}小时 ({self.heat_burned_pct()*100:.0f}%)")
        lines.append(f"任务数: {len(self._tasks)}")
        lines.append(f"警告数: {len(self._warnings)}")
        lines.append(f"平均效率: {self.rolling_efficiency(9999):.2f}")
        lines.append("")

        if self._tasks:
            lines.append("任务明细:")
            for t in self._tasks:
                status = "进行中" if not t.end_time else "完成"
                lines.append(
                    f"  [{t.activity_type}] {t.description[:40]} "
                    f"({t.heat_spent:.0f}min, {t.progress_pct:.0f}%, eff={t.efficiency:.2f}, {status})"
                )

        if self._warnings:
            lines.append(f"\n⚠️ 警告历史 ({len(self._warnings)}次):")
            for w in self._warnings[-5:]:
                t = time.strftime("%H:%M", time.localtime(w["time"]))
                lines.append(f"  {t} | eff={w['efficiency']:.2f} | {w['task']}")

        return "\n".join(lines)

    def summary(self) -> Dict:
        """JSON格式摘要."""
        return {
            "budget_hours": self.budget_hours,
            "heat_burned_hours": round(self.heat_burned() / 60, 1),
            "heat_burned_pct": round(self.heat_burned_pct() * 100, 1),
            "task_count": len(self._tasks),
            "warning_count": len(self._warnings),
            "avg_efficiency": round(self.rolling_efficiency(9999), 2),
            "current_task": self._current_task.description if self._current_task else None,
            "escalations": self._escalation_suggestions(),
        }

    def _save(self):
        """持久化到文件."""
        try:
            self.save_path.parent.mkdir(parents=True, exist_ok=True)
            data = {
                "tasks": [
                    {
                        "id": t.task_id, "type": t.activity_type,
                        "desc": t.description, "start": t.start_time,
                        "end": t.end_time, "heat": t.heat_spent,
                        "progress": t.progress_pct, "efficiency": round(t.efficiency, 3),
                        "outcome": t.outcome,
                    }
                    for t in self._tasks
                ],
                "warnings": self._warnings,
            }
            with open(self.save_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    def _load(self):
        """从文件恢复."""
        try:
            if self.save_path.exists():
                with open(self.save_path, encoding="utf-8") as f:
                    data = json.load(f)
                for t in data.get("tasks", []):
                    if not t.get("start"):
                        continue
                    task = TaskRecord(
                        task_id=t["id"], activity_type=t.get("type", "unknown"),
                        description=t.get("desc", ""), start_time=t["start"],
                        end_time=t.get("end", 0), heat_spent=t.get("heat", 0),
                        progress_pct=t.get("progress", 0),
                        outcome=t.get("outcome", ""),
                    )
                    if task.heat_spent > 0:
                        task.efficiency = task.progress_pct / max(task.heat_spent, 1)
                    self._tasks.append(task)
                self._warnings = data.get("warnings", [])
        except Exception:
            pass


# ═══ CLI ═══
def cmd_timer(args_rest):
    """CLI入口: mssclaw timer [start|tick|end|report]"""
    timer = HeatTaxTimer()

    if not args_rest:
        print(timer.report())
        return

    cmd = args_rest[0]

    if cmd == "start":
        atype = args_rest[1] if len(args_rest) > 1 else "coding"
        desc = " ".join(args_rest[2:]) if len(args_rest) > 2 else "Untitled task"
        task = timer.start_task(atype, desc)
        print(f"▶ {task.activity_type}: {task.description}")
        print(f"  预算: {timer.budget_hours}h, 效率阈值: {timer.warn_threshold}")

    elif cmd == "tick":
        pct = int(args_rest[1]) if len(args_rest) > 1 else None
        timer.tick(pct)
        if timer._current_task:
            print(f"⏱ {timer._current_task.heat_spent:.0f}min, "
                  f"进度{timer._current_task.progress_pct:.0f}%, "
                  f"效率{timer._current_task.efficiency:.2f}")

    elif cmd == "end":
        outcome = " ".join(args_rest[1:]) if len(args_rest) > 1 else ""
        timer.end_task(outcome)
        print("⏹ 任务结束")
        print(f"  总热税: {timer.heat_burned()/60:.1f}h")

    elif cmd == "report":
        print(timer.report())

    elif cmd == "summary":
        import json as _j
        print(_j.dumps(timer.summary(), ensure_ascii=False, indent=2))

    else:
        print("mssclaw timer [start|tick|end|report|summary]")
