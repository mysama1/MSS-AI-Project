"""
pytest tests for mssclaw pipeline — 流式分支Pipeline + 生产指标
"""
import sys
sys.path.insert(0, '.')
import pytest
from mssclaw.core.pipeline import (
    PipeStatus, PipeResult, StreamEvent, BranchCondition,
    PipeNode, ProductionConfig, MetricsCollector, StreamingPipeline
)


# ═══════ Enum & Data Classes ═══════

class TestPipeStatus:
    def test_has_all_states(self):
        states = {e.value for e in PipeStatus}
        assert 'pending' in states
        assert 'done' in states
        assert 'failed' in states
        assert 'circuit_open' in states
        assert 'timed_out' in states

    def test_enum_uniqueness(self):
        vals = [e.value for e in PipeStatus]
        assert len(vals) == len(set(vals))


class TestPipeResult:
    def test_success_result(self):
        r = PipeResult(status=PipeStatus.DONE, output="result_42")
        assert r.status == PipeStatus.DONE
        assert r.output == "result_42"
        assert r.error is None
        assert r.heat_tax == 0.0

    def test_failure_result(self):
        r = PipeResult(status=PipeStatus.FAILED, error="timeout")
        assert r.status == PipeStatus.FAILED
        assert r.error == "timeout"

    def test_metadata_present(self):
        r = PipeResult(status=PipeStatus.DONE, metadata={"node": "search"})
        assert r.metadata["node"] == "search"

    def test_heat_tax_tracked(self):
        r = PipeResult(status=PipeStatus.DONE, heat_tax=2.5)
        assert r.heat_tax == 2.5


class TestStreamEvent:
    def test_output_event(self):
        e = StreamEvent("output", "search_pipe", data="found")
        assert e.event_type == "output"
        assert e.pipe_name == "search_pipe"
        assert e.data == "found"

    def test_progress_event(self):
        e = StreamEvent("progress", "llm_pipe", progress_pct=50.0)
        assert e.progress_pct == 50.0

    def test_timestamp_present(self):
        e = StreamEvent("done", "final")
        assert e.timestamp > 0

    def test_branch_event(self):
        e = StreamEvent("branch", "router", data="branch_a")
        assert e.event_type == "branch"


# ═══════ Branch Condition ═══════

class TestBranchCondition:
    def test_matches_positive(self):
        bc = BranchCondition(lambda r: r.output == "yes", "yes_pipe")
        r = PipeResult(status=PipeStatus.DONE, output="yes")
        assert bc.evaluate(r) is True

    def test_matches_negative(self):
        bc = BranchCondition(lambda r: r.output == "yes", "yes_pipe")
        r = PipeResult(status=PipeStatus.DONE, output="no")
        assert bc.evaluate(r) is False

    def test_name_default(self):
        bc = BranchCondition(lambda r: True, "target")
        assert "target" in bc.name

    def test_name_custom(self):
        bc = BranchCondition(lambda r: True, "target", name="my_branch")
        assert bc.name == "my_branch"


# ═══════ PipeNode ═══════

class TestPipeNode:
    def test_creation(self):
        def echo(ctx): return ctx
        node = PipeNode("echo", echo)
        assert node.name == "echo"
        assert node.fn is echo
        assert node.timeout_s == 30.0
        assert node.retry_count == 0

    def test_defer_after_empty(self):
        node = PipeNode("simple", lambda x: x)
        assert node.defer_after == []

    def test_defer_after_with_constraints(self):
        node = PipeNode("dangerous", lambda x: x,
                       defer_after=["commit", "backup"])
        assert len(node.defer_after) == 2
        assert "commit" in node.defer_after

    def test_branches_default(self):
        node = PipeNode("no_branches", lambda x: x)
        assert node.branches == []

    def test_fallback_default(self):
        node = PipeNode("solo", lambda x: x)
        assert node.fallback_pipe is None


# ═══════ ProductionConfig ═══════

class TestProductionConfig:
    def test_defaults(self):
        cfg = ProductionConfig()
        assert cfg.max_retries == 3
        assert cfg.retry_delay_ms == 200
        assert cfg.retry_backoff == 2.0
        assert cfg.circuit_breaker_threshold == 5
        assert cfg.max_concurrent == 4

    def test_custom(self):
        cfg = ProductionConfig(
            max_retries=5,
            circuit_breaker_threshold=3,
            alert_on_p99_ms=1000.0
        )
        assert cfg.max_retries == 5
        assert cfg.circuit_breaker_threshold == 3
        assert cfg.alert_on_p99_ms == 1000.0


# ═══════ MetricsCollector ═══════

class TestMetricsCollector:
    def test_new_collector_empty(self):
        mc = MetricsCollector()
        assert mc.p50() == 0.0
        assert mc.p99() == 0.0
        assert mc.success_rate() == 1.0

    def test_record_success(self):
        mc = MetricsCollector()
        mc.record(100.0, True)
        assert mc.success_count == 1
        assert mc.fail_count == 0
        assert mc.success_rate() == 1.0

    def test_record_failure(self):
        mc = MetricsCollector()
        mc.record(50.0, False, error_type="timeout")
        assert mc.fail_count == 1
        assert mc.error_types["timeout"] == 1

    def test_p50_correct(self):
        mc = MetricsCollector()
        for ms in [10, 20, 30, 40, 100]:
            mc.record(ms, True)
        assert mc.p50() == 30.0

    def test_p99_correct(self):
        mc = MetricsCollector()
        # 100 samples [1.0, 2.0, ..., 100.0]
        # int(100 * 0.99) = 99, s[99] = 100.0
        for i in range(100):
            mc.record(float(i + 1), True)
        assert mc.p99() == 100.0

    def test_avg_correct(self):
        mc = MetricsCollector()
        mc.record(10.0, True)
        mc.record(20.0, True)
        assert mc.avg() == 15.0

    def test_mixed_success_rate(self):
        mc = MetricsCollector()
        mc.record(10, True)
        mc.record(20, True)
        mc.record(30, False, "crash")
        mc.record(40, False, "crash")
        assert mc.success_rate() == 0.5

    def test_to_dict(self):
        mc = MetricsCollector()
        mc.record(100, True)
        mc.record(200, False, "timeout")
        d = mc.to_dict()
        assert d["total_calls"] == 2
        assert d["success"] == 1
        assert d["fail"] == 1
        assert "latency_ms" in d
        assert d["latency_ms"]["p50"] > 0
        assert "timeout" in str(d["error_distribution"])

    def test_circuit_trips(self):
        mc = MetricsCollector()
        mc.record_circuit_trip()
        mc.record_circuit_trip()
        assert mc.circuit_trips == 2


# ═══════ StreamingPipeline ═══════

class TestStreamingPipeline:
    def test_pipeline_creation(self):
        pl = StreamingPipeline("test_pipe")
        assert pl.name == "test_pipe"
        assert len(pl.nodes) == 0
        assert pl.start_pipe is None

    def test_pipeline_default_name(self):
        pl = StreamingPipeline()
        assert pl.name == "default"

    def test_add_node(self):
        pl = StreamingPipeline()
        node = PipeNode("stage1", lambda ctx: ctx.get("input"))
        pl.add_node(node)
        assert "stage1" in pl.nodes
        assert pl.nodes["stage1"] is node

    def test_set_start(self):
        pl = StreamingPipeline()
        node = PipeNode("entry", lambda ctx: "started")
        pl.add_node(node, is_start=True)
        assert pl.start_pipe == "entry"

    def test_multiple_nodes(self):
        pl = StreamingPipeline()
        pl.add_node(PipeNode("a", lambda c: c))
        pl.add_node(PipeNode("b", lambda c: c))
        assert len(pl.nodes) == 2

    def test_register_edge(self):
        pl = StreamingPipeline()
        pl.add_node(PipeNode("a", lambda c: c))
        pl.add_node(PipeNode("b", lambda c: c))
        # edges are stored in self.edges dict
        pl.edges["a"] = ["b"]
        assert pl.edges["a"] == ["b"]

    def test_context_initialized(self):
        pl = StreamingPipeline()
        assert isinstance(pl.context, dict)

    def test_heat_tax_total_starts_zero(self):
        pl = StreamingPipeline()
        assert pl.heat_tax_total == 0.0
