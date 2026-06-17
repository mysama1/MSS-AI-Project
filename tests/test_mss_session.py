"""Tests for MSS Session — persistent agent session."""
import json
import os
import pytest
import tempfile
from mssclaw.core.mss_session import MSSSession, SessionStep, SessionIdentity, SessionCost


class TestMSSSession:
    def test_create_and_start(self):
        s = MSSSession("test-001")
        s.start()
        assert s._active
        assert s.identity.session_id == "test-001"

    def test_step_records(self):
        s = MSSSession("test-002")
        s.start()
        step = s.step("analyze", heat_tax=0.05, delta_change=+0.03)
        assert step is not None
        assert step.action == "analyze"
        assert s.cost.total_steps == 1
        assert s.cost.total_heat_tax == 0.05

    def test_step_blocks_when_not_active(self):
        s = MSSSession("test-003", auto_save=False)
        step = s.step("analyze")
        assert step is None

    def test_heat_tax_budget_exhausted(self):
        s = MSSSession("test-004", budget=0.05, auto_save=False)
        s.start()
        s.step("a", heat_tax=0.03)
        s.step("b", heat_tax=0.03)  # exhausts budget
        step = s.step("c", heat_tax=0.03)  # blocked
        assert step is None

    def test_delta_min_block(self):
        s = MSSSession("test-005", delta_min=0.5, auto_save=False)
        s.start()
        s.cost.last_delta = 0.4  # force below min
        step = s.step("analyze")
        assert step is None

    def test_save_and_load(self):
        with tempfile.TemporaryDirectory() as tmp:
            # Override sessions dir
            old_dir = MSSSession.SESSIONS_DIR
            MSSSession.SESSIONS_DIR = type(MSSSession.SESSIONS_DIR)(tmp)

            try:
                s = MSSSession("test-006", auto_save=False)
                s.start()
                s.step("analyze", heat_tax=0.05, summary="test step")
                s.step("respond", heat_tax=0.02, summary="response")
                s.save()

                # Load
                s2 = MSSSession.load("test-006")
                assert s2.identity.session_id == "test-006"
                assert s2.cost.total_steps == 2
                assert s2.cost.total_heat_tax == 0.07
                assert len(s2._steps) == 2
            finally:
                MSSSession.SESSIONS_DIR = old_dir

    def test_list_sessions(self):
        with tempfile.TemporaryDirectory() as tmp:
            old_dir = MSSSession.SESSIONS_DIR
            MSSSession.SESSIONS_DIR = type(MSSSession.SESSIONS_DIR)(tmp)

            try:
                s1 = MSSSession("list-001", auto_save=False)
                s1.save()
                s2 = MSSSession("list-002", auto_save=False)
                s2.save()

                sessions = MSSSession.list_sessions()
                assert "list-001" in sessions
                assert "list-002" in sessions
            finally:
                MSSSession.SESSIONS_DIR = old_dir

    def test_fork(self):
        s = MSSSession("test-007", auto_save=False)
        s.start()
        s.step("analyze", heat_tax=0.05, delta_change=+0.03)
        s.step("respond", heat_tax=0.02, delta_change=+0.01)

        child = s.fork("deep dive")
        assert child.cost.total_steps == 2
        assert child.cost.total_heat_tax == 0.07
        assert child.identity.parent_id == "test-007"
        assert child.identity.label == "deep dive"

    def test_molt(self):
        s = MSSSession("test-008", auto_save=False)
        s.start()
        before = s.cost.last_delta
        s.molt("learned something")
        assert s.cost.last_delta > before
        assert s.cost.molting_count == 1

    def test_report(self):
        s = MSSSession("test-009", auto_save=False)
        s.start()
        s.step("analyze")
        report = s.report()
        assert report["total_steps"] == 1
        assert "identity" in report

    def test_empty_report(self):
        s = MSSSession("test-010", auto_save=False)
        report = s.report()
        assert report["status"] == "empty"

    def test_hooks(self):
        called = []
        s = MSSSession("test-011", auto_save=False)
        s.hooks.post_step.append(lambda ctx: called.append("post"))
        s.hooks.on_lock.append(lambda ctx: called.append("lock"))

        s.start()
        s.step("analyze")
        s.cost.budget_remaining = 0  # force lock
        s.step("blocked")
        assert "post" in called
        assert "lock" in called

    def test_delta_tracking(self):
        s = MSSSession("test-012", delta_min=0.3, auto_save=False)
        s.start()
        assert s.cost.last_delta == 0.5
        s.step("good", delta_change=+0.1)
        assert s.cost.last_delta == 0.6
        s.step("bad", delta_change=-0.3)  # not below min yet
        assert s.cost.last_delta == 0.3

    def test_identity_fields(self):
        s = MSSSession("test-013", label="Code Review")
        assert s.identity.session_id == "test-013"
        assert s.identity.label == "Code Review"
        assert s.identity.parent_id is None
