"""
Track C-9: PlanAgent + Type2 Control coverage
plan_agent: GoalDef, TaskDef, PlanAgent, TaskStatus
type2: TypeIICase, TrialResult, ExperimentReport, MCDPResolver, ConflictArbiter, etc.
"""
import pytest, sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from mssclaw.core.plan_agent import GoalDef, TaskDef, TaskStatus
from mssclaw.core.type2_control_experiment import (
    TypeIICase, TypeIIControlExperiment, TrialResult,
    ExperimentReport, MCDPResolver, ConflictArbiter,
    PhaseScheduler, PhaseSchedulerV2, TensionLevel,
)


# ═══ PlanAgent ═══
class TestGoalDef:
    def test_create(self):
        g = GoalDef(goal_id="g1", description="test goal")
        assert g.goal_id == "g1"
        assert g.description == "test goal"
        assert g.status == "created"

    def test_with_tasks(self):
        t1 = TaskDef(task_id="t1", description="do thing", required_capability="basic")
        g = GoalDef(goal_id="g2", description="multi task", tasks={"t1": t1}, task_order=["t1"])
        assert g.tasks["t1"].task_id == "t1"
        assert g.task_order == ["t1"]

    def test_completed(self):
        g = GoalDef(goal_id="g3", description="done", status="completed", completed_at=100.0)
        assert g.status == "completed"


class TestTaskDef:
    def test_create(self):
        t = TaskDef(task_id="t1", description="test task", required_capability="code_gen")
        assert t.task_id == "t1"
        assert t.description == "test task"
        assert t.required_capability == "code_gen"
        assert t.status == "pending"
        assert t.priority == 1
        assert t.max_retries == 2

    def test_with_deps(self):
        t = TaskDef(
            task_id="t2", description="dep task", required_capability="review",
            dependencies=["t1"], priority=3, timeout_seconds=600,
        )
        assert t.dependencies == ["t1"]
        assert t.priority == 3
        assert t.timeout_seconds == 600

    def test_result(self):
        t = TaskDef(
            task_id="t3", description="result task", required_capability="audit",
            result={"score": 95}, error="", status="completed", retries=1,
            assigned_to="agent-a",
        )
        assert t.result == {"score": 95}
        assert t.status == "completed"
        assert t.assigned_to == "agent-a"


class TestTaskStatus:
    def test_values(self):
        for s in TaskStatus:
            assert isinstance(s.value, str)


# ═══ Type2 Control ═══
class TestTypeIICase:
    def test_create(self):
        c = TypeIICase(id="c1", stable_a="choose X", stable_b="choose Y", tension=0.7, context="decision", golden="Y")
        assert c.id == "c1"
        assert c.tension == 0.7
        assert c.golden == "Y"
        assert c.resources == 1000
        assert c.recipients == 5


class TestTrialResult:
    def test_create(self):
        tr = TrialResult(
            case_id="c1", tension=0.7, direction=1, success=True,
            eta=0.8, heat_tax=5, latency=1.5,
        )
        assert tr.case_id == "c1"
        assert tr.success is True
        assert tr.eta == 0.8

    def test_stuck(self):
        tr = TrialResult(
            case_id="c2", tension=0.9, direction=1, success=False,
            eta=0.1, heat_tax=50, latency=30.0,
            stuck=True, stability="unstable",
        )
        assert tr.stuck is True
        assert tr.stability == "unstable"


class TestExperimentReport:
    def test_create(self):
        r = ExperimentReport(total_trials=100, trials_per_direction=50)
        assert r.total_trials == 100
        assert r.trials_per_direction == 50
        assert r.d1_success_rate == 0.0

    def test_with_results(self):
        r = ExperimentReport(
            total_trials=100, trials_per_direction=50,
            d1_success_rate=0.8, d2_success_rate=0.6,
            d1_avg_eta=0.7, d2_avg_eta=0.5,
        )
        assert r.d1_success_rate == 0.8
        assert r.d2_success_rate == 0.6


class TestTypeIIControlExperiment:
    def test_create(self):
        exp = TypeIIControlExperiment(rounds_per_case=10)
        assert exp is not None


class TestMCDPResolver:
    def test_create(self):
        r = MCDPResolver()
        assert r is not None


class TestConflictArbiter:
    def test_create(self):
        ca = ConflictArbiter()
        assert ca is not None


class TestPhaseScheduler:
    def test_create(self):
        ps = PhaseScheduler()
        assert ps is not None


class TestPhaseSchedulerV2:
    def test_create(self):
        ps = PhaseSchedulerV2()
        assert ps is not None


class TestTensionLevel:
    def test_values(self):
        for t in TensionLevel:
            assert isinstance(t.value, (float, int, str))
