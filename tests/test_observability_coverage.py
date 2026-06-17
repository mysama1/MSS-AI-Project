"""
Track C-3: Observability coverage — Span, TraceManager, TombstoneBrowser
"""
import pytest, time, sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from mssclaw.core.observability import Span, TraceManager, TombstoneBrowser, SpanStatus


class TestSpan:
    def test_create(self):
        s = Span(name="test_op", agent_name="test_agent")
        assert s.name == "test_op"
        assert s.agent_name == "test_agent"

    def test_defaults(self):
        s = Span()
        assert s.name == ""
        assert s.status == SpanStatus.STARTED
        assert s.duration_ms == 0.0
        assert s.heat_tax_at_start == 0.0
        assert s.delta_at_start == 1.0

    def test_custom_values(self):
        s = Span(id="s1", parent_id="p1", name="infer", agent_name="mma", status=SpanStatus.SUCCEEDED, heat_tax_at_start=0.3, delta_at_start=0.9)
        assert s.id == "s1"
        assert s.parent_id == "p1"
        assert s.name == "infer"
        assert s.status == SpanStatus.SUCCEEDED
        assert s.heat_tax_at_start == 0.3
        assert s.delta_at_start == 0.9

    def test_span_status_values(self):
        assert hasattr(SpanStatus, 'STARTED')
        assert hasattr(SpanStatus, 'SUCCEEDED')
        assert hasattr(SpanStatus, 'FAILED')
        assert hasattr(SpanStatus, 'TIMED_OUT')

    def test_tags(self):
        s = Span(name="op", tags=["gpu", "high_cost"])
        assert s.tags == ["gpu", "high_cost"]

    def test_metadata(self):
        s = Span(metadata={"model": "gpt-4", "tokens": 150})
        assert s.metadata == {"model": "gpt-4", "tokens": 150}

    def test_duration_default(self):
        s = Span(name="op")
        s.ended_at = time.time()
        s.duration_ms = (s.ended_at - s.started_at) * 1000
        assert s.duration_ms >= 0

    def test_error_field(self):
        s = Span(name="op", error="timeout")
        assert s.error == "timeout"


class TestTraceManager:
    def test_create(self):
        tm = TraceManager()
        assert tm is not None

    def test_default_max_spans(self):
        tm = TraceManager()
        assert tm.max_spans == 10000

    def test_custom_max_spans(self):
        tm = TraceManager(max_spans=500)
        assert tm.max_spans == 500

    def test_start_span(self):
        tm = TraceManager()
        s = tm.start_span("op1", agent_name="a1")
        assert isinstance(s, Span)
        assert s.name == "op1"

    def test_finish_span(self):
        tm = TraceManager()
        s = tm.start_span("op1", agent_name="a1")
        tm.finish_span(s.id)
        span = tm.get_span(s.id)
        assert span is not None

    def test_get_span_tree(self):
        tm = TraceManager()
        s1 = tm.start_span("root", agent_name="a")
        s2 = tm.start_span("child", agent_name="a", parent_id=s1.id)
        tree = tm.get_span_tree()
        assert tree is not None


class TestTombstoneBrowser:
    def test_create(self):
        tb = TombstoneBrowser()
        assert tb is not None

    def test_with_store_dir(self):
        tb = TombstoneBrowser(store_dir="/tmp/test_tombs")
        assert tb.store_dir == "/tmp/test_tombs"

    def test_record(self):
        tb = TombstoneBrowser()
        entry = tb.record("agent_x", "kill", {"status": "dead", "reason": "timeout"})
        assert entry is not None

    def test_record_and_search(self):
        tb = TombstoneBrowser()
        tb.record("agent_a", "error", {"msg": "timeout"})
        tb.record("agent_b", "error", {"msg": "crash"})
        results = tb.search(decision_type="error")
        assert len(results) >= 2

    def test_agent_decisions(self):
        tb = TombstoneBrowser()
        tb.record("agent_x", "hit", {"score": 0.9})
        decisions = tb.get_agent_decisions("agent_x")
        assert isinstance(decisions, list)

    def test_get_recent(self):
        tb = TombstoneBrowser()
        tb.record("a1", "type", {"key": "val"})
        recent = tb.get_recent(n=5)
        assert isinstance(recent, list)

    def test_stats(self):
        tb = TombstoneBrowser()
        s = tb.stats()
        assert isinstance(s, dict)
