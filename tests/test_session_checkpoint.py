"""Tests for MSS Session checkpoint/rollback/backtrack."""
import pytest
from mssclaw.core.mss_session import MSSSession, SessionCheckpoint


class TestSessionCheckpoint:
    def test_checkpoint_creates_snapshot(self):
        s = MSSSession("cp-001", auto_save=False)
        s.start()
        s.step("analyze", heat_tax=0.05, delta_change=+0.03)
        s.step("respond", heat_tax=0.02, delta_change=+0.01)
        cp = s.checkpoint("before_bug")
        assert cp.name == "before_bug"
        assert cp.step_count == 2
        assert cp.delta == s.cost.last_delta
        assert len(cp.steps_snapshot) == 2

    def test_rollback_restores_state(self):
        s = MSSSession("cp-002", auto_save=False)
        s.start()
        s.step("good", heat_tax=0.05, delta_change=+0.03)
        s.checkpoint("safe_point")
        s.step("bad", heat_tax=0.30, delta_change=-0.20)
        s.step("worse", heat_tax=0.30, delta_change=-0.15)

        ok, reason = s.rollback("safe_point")
        assert ok
        assert s.cost.total_steps == 1
        assert s.cost.total_heat_tax == 0.05
        assert len(s._steps) == 1

    def test_rollback_nonexistent(self):
        s = MSSSession("cp-003", auto_save=False)
        ok, reason = s.rollback("never_saved")
        assert not ok

    def test_backtrack_by_steps(self):
        s = MSSSession("cp-004", budget=2.0, delta_min=0.3, auto_save=False)
        s.start()
        for i in range(5):
            s.step(f"step_{i}", heat_tax=0.02, delta_change=+0.01)
        s.checkpoint("mid")

        for i in range(3):
            s.step(f"bad_{i}", heat_tax=0.10, delta_change=-0.05)

        ok, reason = s.backtrack(3)
        assert ok
        assert s.cost.total_steps == 5  # 8 - 3 = 5

    def test_backtrack_too_many(self):
        s = MSSSession("cp-005", auto_save=False)
        s.start()
        s.step("only_one")
        ok, reason = s.backtrack(5)
        assert not ok
        assert "Cannot backtrack" in reason

    def test_backtrack_zero(self):
        s = MSSSession("cp-006", auto_save=False)
        ok, reason = s.backtrack(0)
        assert not ok

    def test_list_checkpoints(self):
        s = MSSSession("cp-007", auto_save=False)
        s.start()
        s.checkpoint("init")
        s.step("a")
        s.checkpoint("after_a")
        s.step("b")
        s.checkpoint("after_b")

        cps = s.list_checkpoints()
        assert len(cps) == 3
        assert cps[0]["name"] == "init"
        assert cps[2]["name"] == "after_b"

    def test_multiple_checkpoints_rollback(self):
        s = MSSSession("cp-008", auto_save=False)
        s.start()
        s.step("s1", delta_change=+0.1)
        s.checkpoint("cp1")
        s.step("s2", delta_change=+0.1)
        s.checkpoint("cp2")
        s.step("s3", delta_change=-0.3)

        s.rollback("cp2")
        assert s.cost.total_steps == 2
        assert s.cost.last_delta == pytest.approx(0.7)

        s.rollback("cp1")
        assert s.cost.total_steps == 1
        assert s.cost.last_delta == pytest.approx(0.6)

    def test_checkpoint_delta_accurate(self):
        s = MSSSession("cp-009", auto_save=False)
        s.start()
        s.step("s1", heat_tax=0.05, delta_change=+0.05)
        cp = s.checkpoint("after_s1")
        assert cp.delta == pytest.approx(0.55)
        assert cp.heat_tax == pytest.approx(0.05)
