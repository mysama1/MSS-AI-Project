"""Tests for MSS Tactic — LLLM-inspired pure function with heat tax."""
import pytest
from mssclaw.core.mss_tactic import MSSTactic, TacticReport, TacticStep, CodeReviewTactic


class TestTacticStep:
    def test_creation(self):
        step = TacticStep(agent_name="test", action="respond",
                          heat_tax=0.05, delta_change=0.1)
        assert step.agent_name == "test"
        assert step.action == "respond"
        assert step.heat_tax == 0.05
        assert step.delta_change == 0.1

    def test_defaults(self):
        step = TacticStep(agent_name="a", action="receive", heat_tax=0.0, delta_change=0.0)
        assert step.token_count == 0
        assert step.latency_ms == 0.0
        assert step.metadata == {}

    def test_metadata(self):
        step = TacticStep(agent_name="a", action="tool_call",
                          heat_tax=0.03, delta_change=0.05,
                          metadata={"tool": "ruff_check", "target": "core.py"})
        assert step.metadata["tool"] == "ruff_check"


class TestTacticReport:
    def test_empty_report(self):
        r = TacticReport(task="test")
        assert r.task == "test"
        assert r.steps == []
        assert r.total_heat_tax == 0.0
        assert r.success

    def test_delta_closing(self):
        r = TacticReport(task="test", delta_start=0.5, delta_end=0.8)
        assert round(r.delta_closing, 2) == 0.3

    def test_delta_opening(self):
        r = TacticReport(task="test", delta_start=0.8, delta_end=0.5)
        assert round(r.delta_closing, 2) == -0.3

    def test_layered_heat_tax(self):
        r = TacticReport(task="test", elapsed_ms=1000)
        r.steps = [
            TacticStep(agent_name="a", action="respond",
                       heat_tax=0.1, delta_change=0.1, token_count=50000),
            TacticStep(agent_name="a", action="respond",
                       heat_tax=0.05, delta_change=-0.05, token_count=30000),
        ]
        r.total_heat_tax = 0.15
        assert r.l0_heat_tax > 0  # physical
        assert r.l1_heat_tax > 0  # logical
        assert r.l2_heat_tax > 0  # meaning (one step with delta<=0)

    def test_summary_format(self):
        r = TacticReport(task="review core.py", delta_start=0.5, delta_end=0.73)
        r.steps = [TacticStep(agent_name="a", action="respond",
                              heat_tax=0.1, delta_change=0.23)]
        r.total_heat_tax = 0.1
        summary = r.summary()
        assert "core.py" in summary
        assert "Steps: 1" in summary
        assert "0.50→0.73" in summary

    def test_error_handling(self):
        r = TacticReport(task="test")
        assert not r.errors
        r.errors.append("Something failed")
        assert len(r.errors) == 1


class TestMSSTactic:
    def test_base_not_implemented(self):
        t = MSSTactic()
        with pytest.raises(NotImplementedError):
            t._run("test")

    def test_record_step(self):
        t = MSSTactic()
        t.report = TacticReport(task="test")
        step = t.record("agent1", "respond", heat_tax=0.05, delta_change=0.1)
        assert step.agent_name == "agent1"
        assert t.report.total_heat_tax == 0.05
        assert len(t.report.steps) == 1

    def test_multiple_records(self):
        t = MSSTactic()
        t.report = TacticReport(task="test")
        t.record("a", "receive", heat_tax=0.01)
        t.record("a", "respond", heat_tax=0.05)
        t.record("b", "respond", heat_tax=0.03)
        assert t.report.total_heat_tax == 0.09
        assert len(t.report.steps) == 3


class TestCodeReviewTactic:
    def test_full_execution(self):
        tactic = CodeReviewTactic()
        result, report = tactic.call(task="core/pipeline.py")
        assert "Review" in str(result)
        assert "pipeline.py" in str(result)
        assert report.success
        assert len(report.steps) >= 4
        assert report.total_heat_tax > 0
        assert report.delta_end > report.delta_start  # gained openness

    def test_agent_names(self):
        tactic = CodeReviewTactic()
        result, report = tactic.call(task="test.py")
        agents = {s.agent_name for s in report.steps}
        assert "scanner" in agents
        assert "synthesizer" in agents

    def test_tool_call_recorded(self):
        tactic = CodeReviewTactic()
        _, report = tactic.call(task="test.py")
        tool_steps = [s for s in report.steps if s.action == "tool_call"]
        assert len(tool_steps) == 1
        assert tool_steps[0].metadata["tool"] == "ruff_check"

    def test_report_summary(self):
        tactic = CodeReviewTactic()
        _, report = tactic.call(task="test.py")
        summary = report.summary()
        assert "Heat:" in summary
        assert "Δ:" in summary
