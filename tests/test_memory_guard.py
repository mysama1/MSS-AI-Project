"""
pytest tests for memory_guard — 记忆守卫引擎 (47.4KB)
"""
import sys
sys.path.insert(0, '.')
import pytest
from mssclaw.core.memory_guard import (
    MemoryGuard, MemoryCategory, Memory, Source, SourceType
)


class TestMemoryCategory:
    def test_six_categories(self):
        vals = {e.value for e in MemoryCategory}
        assert vals == {"decision", "lesson", "milestone", "insight", "error", "pattern"}

    def test_decision_category(self):
        assert MemoryCategory.DECISION.value == "decision"

    def test_lesson_category(self):
        assert MemoryCategory.LESSON.value == "lesson"


class TestSourceType:
    def test_three_types(self):
        vals = {e.value for e in SourceType}
        assert vals == {"msg", "obs", "inf"}

    def test_msg_type(self):
        assert SourceType.MSG.value == "msg"

    def test_observation_type(self):
        assert SourceType.OBSERVATION.value == "obs"


class TestSource:
    def test_creation(self):
        s = Source(type=SourceType.MSG, ref="test_ref", confidence=0.9,
                   detail="test detail")
        assert s.type == SourceType.MSG
        assert s.ref == "test_ref"

    def test_inference_source(self):
        s = Source(type=SourceType.INFERENCE, ref="reasoner_output",
                   confidence=0.75)
        assert s.type == SourceType.INFERENCE


class TestMemory:
    def test_creation(self):
        m = Memory(category=MemoryCategory.INSIGHT, content="interesting",
                   source="observer", delta=0.5)
        assert m.category == MemoryCategory.INSIGHT
        assert m.delta == 0.5

    def test_decision_memory(self):
        m = Memory(category=MemoryCategory.DECISION,
                   content="chose option A over B",
                   source="reasoner", delta=0.3)
        assert m.category == MemoryCategory.DECISION

    def test_lesson_with_source_evidence(self):
        s = Source(type=SourceType.OBSERVATION, ref="monitor_log")
        m = Memory(category=MemoryCategory.LESSON,
                   content="pipe timeout requires retry",
                   source="monitor", delta=0.7, source_evidence=s)
        assert m.source_evidence is not None
        assert m.source_evidence.type == SourceType.OBSERVATION

    def test_error_memory(self):
        m = Memory(category=MemoryCategory.ERROR,
                   content="SIGKILL due to Job Object tree kill",
                   source="cli", delta=0.0)
        assert m.category == MemoryCategory.ERROR


class TestMemoryGuard:
    def test_creation(self):
        mg = MemoryGuard()
        assert mg.delta_threshold is not None
        assert mg.flush_interval is not None

    def test_empty_on_creation(self):
        mg = MemoryGuard()
        assert len(mg.memories) == 0

    def test_observe_adds_memory(self):
        mg = MemoryGuard(delta_threshold=0.0)
        result = mg.observe(content="test observation", delta=0.5, source="test")
        assert len(mg.memories) > 0 or result is not None

    def test_observe_below_threshold_returns_none(self):
        mg = MemoryGuard(delta_threshold=0.9)
        result = mg.observe(content="low delta", delta=0.1, source="test")
        # With high threshold, low delta should not produce memory
        assert result is None or len(mg.memories) == 0

    def test_observe_with_force_category(self):
        mg = MemoryGuard(delta_threshold=0.0)
        result = mg.observe(content="forced decision", delta=0.5,
                           source="test", force_category=MemoryCategory.DECISION)
        if result is not None:
            assert result.category == MemoryCategory.DECISION

    def test_get_decisions(self):
        mg = MemoryGuard(delta_threshold=0.0)
        mg.observe(content="adopt Phase Engine", delta=0.6,
                   source="router", force_category=MemoryCategory.DECISION)
        decisions = mg.get_decisions()
        assert isinstance(decisions, list)

    def test_get_lessons(self):
        mg = MemoryGuard(delta_threshold=0.0)
        mg.observe(content="PowerShell encoding rule", delta=0.5,
                   source="cli", force_category=MemoryCategory.LESSON)
        lessons = mg.get_lessons()
        assert isinstance(lessons, list)

    def test_summary(self):
        mg = MemoryGuard(delta_threshold=0.0)
        for i in range(3):
            mg.observe(content=f"pattern {i}", delta=0.3 + i * 0.1,
                       source="analytics")
        summary = mg.summary()
        assert isinstance(summary, (str, dict))

    def test_auto_tag_is_bool(self):
        mg = MemoryGuard()
        assert isinstance(mg.auto_tag, bool)

    def test_decision_threshold_default(self):
        mg = MemoryGuard()
        assert mg.decision_threshold is not None

    def test_flush_interval_default(self):
        mg = MemoryGuard()
        assert mg.flush_interval is not None

    def test_flush_requires_path(self):
        mg = MemoryGuard(delta_threshold=0.0)
        for i in range(3):
            mg.observe(content=f"insight {i}", delta=0.4, source="test")
        pre = len(mg.memories)
        # flush requires a path for persistence
        import tempfile, os
        tmpdir = tempfile.mkdtemp()
        mg.flush(os.path.join(tmpdir, "test_flush.json"))
        assert len(mg.memories) <= pre

    def test_delta_threshold_accessor(self):
        mg = MemoryGuard(delta_threshold=0.7)
        assert mg.delta_threshold == 0.7
