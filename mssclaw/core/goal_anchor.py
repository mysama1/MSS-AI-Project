"""
MSS Goal Anchor — 开发目标意义场锚定 (H623落地工具 #2).

将开发目标形式化为意义场拓扑: 稳定子(A1) + 规范路径(A5) + 热税预算(A3) + 升维协议(A6).
任何时候执行 `mssclaw goal` 都能看到: 我在哪、要去哪、还剩多少燃料。

用法:
    mssclaw goal set "实现用户登录" --stable "必须密码+OTP,5次锁定" --budget 8h
    mssclaw goal status       # 查看当前目标
    mssclaw goal progress 65  # 更新进度
    mssclaw goal done         # 标记完成
    mssclaw goal stuck        # 卡住了 — A6升维建议
"""
from __future__ import annotations
import time, json, random
from dataclasses import dataclass, field
from typing import List, Optional
from pathlib import Path


@dataclass
class GoalAnchor:
    """开发目标的意义场拓扑."""

    title: str
    description: str = ""

    # A1: 稳定子 — 不可变核心需求
    stable_edges: List[str] = field(default_factory=list)

    # A5: 规范路径 — 预设开发步骤
    norm_paths: List[dict] = field(default_factory=list)

    # A3: 热税预算
    budget_hours: float = 8.0
    heat_spent_hours: float = 0.0

    # 进度追踪
    current_step: int = 0
    progress_pct: float = 0
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    completed: bool = False

    # A6: 卡住记录
    stuck_count: int = 0
    stuck_log: List[dict] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "title": self.title, "description": self.description,
            "stable_edges": self.stable_edges, "norm_paths": self.norm_paths,
            "budget_hours": self.budget_hours, "heat_spent_hours": self.heat_spent_hours,
            "current_step": self.current_step, "progress_pct": self.progress_pct,
            "created_at": self.created_at, "updated_at": self.updated_at,
            "completed": self.completed, "stuck_count": self.stuck_count,
            "stuck_log": self.stuck_log,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "GoalAnchor":
        g = cls(
            title=d["title"], description=d.get("description", ""),
            stable_edges=d.get("stable_edges", []),
            norm_paths=d.get("norm_paths", []),
            budget_hours=d.get("budget_hours", 8),
            heat_spent_hours=d.get("heat_spent_hours", 0),
            current_step=d.get("current_step", 0),
            progress_pct=d.get("progress_pct", 0),
            created_at=d.get("created_at", time.time()),
            updated_at=d.get("updated_at", time.time()),
            completed=d.get("completed", False),
            stuck_count=d.get("stuck_count", 0),
            stuck_log=d.get("stuck_log", []),
        )
        return g


class GoalManager:
    """目标锚点管理器."""

    def __init__(self, save_path: str = None):
        self.save_path = Path(save_path or (Path.home() / ".mssclaw" / "current_goal.json"))
        self.goal: Optional[GoalAnchor] = None
        self._load()

    def set_goal(self, title: str, description: str = "", stable_edges: List[str] = None,
                 norm_paths: List[str] = None, budget_hours: float = 8) -> GoalAnchor:
        """设定当前开发目标."""
        paths = []
        if norm_paths:
            for i, step in enumerate(norm_paths):
                paths.append({"step": i + 1, "name": step, "done": False})
        else:
            # Auto-generate norm paths
            for step in ["需求分析", "接口设计", "实现", "测试", "评审"]:
                paths.append({"step": len(paths) + 1, "name": step, "done": False})

        self.goal = GoalAnchor(
            title=title, description=description,
            stable_edges=stable_edges or [],
            norm_paths=paths,
            budget_hours=budget_hours,
        )
        self._save()
        return self.goal

    def update_progress(self, progress_pct: float):
        """更新进度."""
        if not self.goal:
            return
        self.goal.progress_pct = min(100, max(0, progress_pct))
        self.goal.updated_at = time.time()

        # Auto-advance norm paths based on progress
        total_steps = len(self.goal.norm_paths)
        if total_steps > 0:
            new_step = int(progress_pct / (100 / total_steps))
            for i in range(new_step):
                if i < total_steps:
                    self.goal.norm_paths[i]["done"] = True
            self.goal.current_step = new_step

        self._save()

    def record_stuck(self, reason: str = "") -> List[str]:
        """记录卡住事件 — 触发A6升维."""
        if not self.goal:
            return []

        self.goal.stuck_count += 1
        self.goal.stuck_log.append({
            "time": time.time(),
            "progress": self.goal.progress_pct,
            "step": self.goal.current_step,
            "reason": reason,
        })
        self._save()

        return self._generate_escalations()

    def _generate_escalations(self) -> List[str]:
        """A6: 生成升维建议."""
        if not self.goal:
            return []

        suggestions = []
        stuck_n = self.goal.stuck_count

        if stuck_n == 1:
            suggestions.append("🔧 换工具: 试试用不同的方法/工具解决当前问题")
            suggestions.append("📖 换角度: 重新审视问题定义, 可能问题本身的边界需要调整")
        elif stuck_n == 2:
            suggestions.append("👥 换人: 邀请同事 pair programming, 或者去问一句")
            suggestions.append("🔄 换方法: 如果一直在修bug, 试试先写测试缩小范围")
        elif stuck_n == 3:
            suggestions.append("❓ 换问题: 这个功能真的需要现在实现吗? 考虑推迟")
            suggestions.append("💤 换节奏: 休息15分钟, 让潜意识处理")
        else:
            suggestions.append("🎯 降维: 拆解为更小的子任务, 逐个击破")
            suggestions.append("📝 输出当前状态文档, 明天带着新视角回来")

        return suggestions

    def complete(self, outcome: str = "") -> dict:
        """标记完成."""
        if not self.goal:
            return {}
        self.goal.completed = True
        self.goal.progress_pct = 100
        self.goal.updated_at = time.time()
        for p in self.goal.norm_paths:
            p["done"] = True
        self.goal.current_step = len(self.goal.norm_paths)

        elapsed_h = (time.time() - self.goal.created_at) / 3600
        self.goal.heat_spent_hours = elapsed_h

        summary = {
            "title": self.goal.title,
            "budget_hours": self.goal.budget_hours,
            "actual_hours": round(elapsed_h, 1),
            "efficiency": round(self.goal.progress_pct / max(elapsed_h, 0.1), 1),
            "stuck_count": self.goal.stuck_count,
            "outcome": outcome,
        }
        self._save()
        return summary

    def status(self) -> str:
        """生成当前状态报告 — '任何时候抬头都知道'."""
        if not self.goal:
            return "🎯 没有活跃的开发目标\n   设定: mssclaw goal set \"目标描述\""

        g = self.goal
        lines = [
            "=" * 50,
            f"🎯 {g.title}",
            "=" * 50,
        ]

        if g.description:
            lines.append(f"描述: {g.description}")

        # A1: 稳定子
        if g.stable_edges:
            lines.append("\n📌 稳定子 (不可变):")
            for e in g.stable_edges:
                lines.append(f"   · {e}")

        # A5: 规范路径 + 进度
        if g.norm_paths:
            lines.append(f"\n📋 规范路径 ({g.progress_pct:.0f}%):")
            for p in g.norm_paths:
                icon = "✅" if p["done"] else "⏳" if p["step"] == g.current_step + 1 else "⬜"
                lines.append(f"   {icon} {p['step']}. {p['name']}")

        # A3: 热税
        elapsed_h = (time.time() - g.created_at) / 3600
        budget_pct = elapsed_h / max(g.budget_hours, 0.1) * 100
        efficiency = g.progress_pct / max(elapsed_h, 0.1)
        bar = "█" * int(min(budget_pct / 5, 20)) + "░" * max(0, 20 - int(min(budget_pct / 5, 20)))

        lines.append(f"\n🔥 热税预算: [{bar}] {budget_pct:.0f}%")
        lines.append(f"   预算: {g.budget_hours}h | 已用: {elapsed_h:.1f}h | 效率: {efficiency:.1f}%/h")

        # A6: 卡住历史
        if g.stuck_count > 0:
            lines.append(f"\n⚠️ 卡住记录: {g.stuck_count}次")
            lines.append(f"   最近: {g.stuck_log[-1].get('reason', '未知')}" if g.stuck_log else "")

        # 建议
        if efficiency < 20 and not g.completed:
            lines.append(f"\n💡 当前效率偏低, 考虑使用 mssclaw goal stuck")

        return "\n".join(lines)

    def _save(self):
        if self.goal:
            try:
                self.save_path.parent.mkdir(parents=True, exist_ok=True)
                with open(self.save_path, "w", encoding="utf-8") as f:
                    json.dump(self.goal.to_dict(), f, ensure_ascii=False, indent=2)
            except Exception:
                pass

    def _load(self):
        try:
            if self.save_path.exists():
                with open(self.save_path, encoding="utf-8") as f:
                    self.goal = GoalAnchor.from_dict(json.load(f))
        except Exception:
            pass


# ═══ CLI ═══
def cmd_goal(args_rest):
    """CLI入口: mssclaw goal [set|status|progress|done|stuck]"""
    mgr = GoalManager()

    if not args_rest:
        print(mgr.status())
        return

    cmd = args_rest[0]

    if cmd == "set":
        title = " ".join(args_rest[1:]) if len(args_rest) > 1 else "Untitled"
        stable = []
        budget = 8.0

        # Parse --stable and --budget
        remaining = args_rest[1:]
        for i, a in enumerate(remaining):
            if a == "--stable" and i + 1 < len(remaining):
                stable = [s.strip() for s in remaining[i + 1].split(",")]
            if a == "--budget" and i + 1 < len(remaining):
                try:
                    budget = float(remaining[i + 1].replace("h", ""))
                except ValueError:
                    pass

        g = mgr.set_goal(title, stable_edges=stable, budget_hours=budget)
        print(f"🎯 目标已锚定: {g.title}")
        print(f"   稳定子: {len(g.stable_edges)}条")
        print(f"   预算: {g.budget_hours}h")
        print(f"   规范路径: {len(g.norm_paths)}步")

    elif cmd == "status":
        print(mgr.status())

    elif cmd == "progress":
        if len(args_rest) > 1:
            try:
                pct = float(args_rest[1])
                mgr.update_progress(pct)
                print(f"📊 进度更新: {pct:.0f}%")
            except ValueError:
                print("用法: mssclaw goal progress <百分比>")
        print(mgr.status())

    elif cmd == "done":
        outcome = " ".join(args_rest[1:]) if len(args_rest) > 1 else ""
        s = mgr.complete(outcome)
        if s:
            print(f"✅ 目标完成: {s['title']}")
            print(f"   预算: {s['budget_hours']}h | 实际: {s['actual_hours']}h")
            print(f"   效率: {s['efficiency']}%/h | 卡住: {s['stuck_count']}次")

    elif cmd == "stuck":
        reason = " ".join(args_rest[1:]) if len(args_rest) > 1 else ""
        suggestions = mgr.record_stuck(reason)
        print(f"🆘 卡住记录 #{mgr.goal.stuck_count if mgr.goal else 0}")
        print(f"\nA6 升维建议:")
        for s in suggestions:
            print(f"  {s}")

    else:
        print("mssclaw goal [set|status|progress|done|stuck]")
