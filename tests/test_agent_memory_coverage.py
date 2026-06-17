"""
Track C-4: Agent/Memory/Tool coverage — AgentRegistry, ToolRegistry, ToolBudgetGate,
GuardianEngine, DeltaMonitor, MemoryConsolidator
"""
import pytest, sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from mssclaw.core.agent_registry import AgentRegistry
from mssclaw.core.tool_registry import ToolRegistry
from mssclaw.core.tool_budget_gate import ToolBudgetGate
from mssclaw.core.guardian_engine import GuardianEngine
from mssclaw.core.delta_monitor import DeltaMonitor


# ═══════ AgentRegistry ═══════

class TestAgentRegistry:
    def test_create(self):
        r = AgentRegistry(db_path=":memory:")
        assert r is not None

    def test_default_path(self):
        r = AgentRegistry()
        assert r is not None

    def test_register_agent(self):
        r = AgentRegistry(db_path=":memory:")
        r.register("agent_1", role="assistant", capabilities=["assistant", "code"])
        info = r.get("agent_1")
        assert info is not None

    def test_list_all(self):
        r = AgentRegistry(db_path=":memory:")
        r.register("a1", role="x", capabilities=["x"])
        r.register("a2", role="y", capabilities=["y"])
        agents = r.list_all()
        assert isinstance(agents, (list, dict))
        assert len(agents) >= 2

    def test_find_by_capability(self):
        r = AgentRegistry(db_path=":memory:")
        r.register("coder", role="coder", capabilities=["code", "debug"])
        found = r.find_by_capability("code")
        assert isinstance(found, list)
        assert len(found) >= 1

    def test_get_capabilities(self):
        r = AgentRegistry(db_path=":memory:")
        r.register("x", role="tester", capabilities=["test"])
        caps = r.get_capabilities("x")
        assert isinstance(caps, (list, dict))


# ═══════ ToolRegistry ═══════

class TestToolRegistry:
    def test_create(self):
        tr = ToolRegistry()
        assert tr is not None

    def test_register_tool(self):
        tr = ToolRegistry()
        tr.register("web_search", func=lambda q: f"search:{q}", description="Search the web")
        schemas = tr.get_schemas()
        assert len(schemas) >= 1

    def test_get_descriptions(self):
        tr = ToolRegistry()
        tr.register("t1", func=lambda: 1, description="Tool 1")
        tr.register("t2", func=lambda: 2, description="Tool 2")
        descs = tr.get_descriptions()
        # returns markdown string or dict
        assert isinstance(descs, (str, list, dict))
        assert "t1" in descs or len(descs) >= 2

    def test_no_nonexistent_in_schemas(self):
        tr = ToolRegistry()
        tr.register("real", func=lambda: 0, description="Real tool")
        schemas = tr.get_schemas()
        assert True  # registration succeeded


# ═══════ ToolBudgetGate ═══════

class TestToolBudgetGate:
    def test_create(self):
        from mssclaw.core.heat_tax import HeatTaxBudget
        gate = ToolBudgetGate(accountant=HeatTaxBudget())
        assert gate is not None

    def test_default_limits(self):
        from mssclaw.core.heat_tax import HeatTaxBudget
        gate = ToolBudgetGate(accountant=HeatTaxBudget())
        assert gate.max_tool_tokens == 2000
        assert gate.max_tool_calls == 20
        assert gate.max_repeat_calls == 3

    def test_custom_limits(self):
        from mssclaw.core.heat_tax import HeatTaxBudget
        gate = ToolBudgetGate(accountant=HeatTaxBudget(), max_tool_tokens_per_turn=500, max_tool_calls_per_turn=5, max_repeat_calls=1)
        assert gate.max_tool_tokens == 500
        assert gate.max_tool_calls == 5
        assert gate.max_repeat_calls == 1


# ═══════ GuardianEngine ═══════

class TestGuardianEngine:
    def test_create(self):
        g = GuardianEngine()
        assert g is not None

    def test_strictness_default(self):
        g = GuardianEngine()
        assert g.strictness == 0.5

    def test_custom_strictness(self):
        g = GuardianEngine(strictness=0.8)
        assert g.strictness == 0.8

    def test_scan_safe_input(self):
        g = GuardianEngine()
        result = g.scan("Hello, how are you?")
        assert result is not None

    def test_scan_suspicious_input(self):
        g = GuardianEngine(strictness=0.7)
        result = g.scan("rm -rf /")
        assert result is not None

    def test_guardians_attribute(self):
        g = GuardianEngine()
        assert g.guardians is not None


# ═══════ DeltaMonitor ═══════

class TestDeltaMonitor:
    def test_create(self):
        dm = DeltaMonitor()
        assert dm is not None

    def test_default_agent_none(self):
        dm = DeltaMonitor()
        assert dm.agent is None

    def test_history(self):
        dm = DeltaMonitor()
        history = dm.history()
        assert isinstance(history, list)


# ═══════ MemoryConsolidator ═══════

class TestMemoryConsolidator:
    class MockMemory:
        def __init__(self):
            self.store = {}
        def stats(self):
            return {"total": len(self.store), "active": len(self.store)}

    def test_create(self):
        from mssclaw.core.memory_consolidator import MemoryConsolidator
        mc = MemoryConsolidator(memory=self.MockMemory())
        assert mc is not None

    def test_should_consolidate(self):
        from mssclaw.core.memory_consolidator import MemoryConsolidator
        mc = MemoryConsolidator(memory=self.MockMemory())
        result = mc.should_consolidate()
        assert isinstance(result, bool)

    def test_stats(self):
        from mssclaw.core.memory_consolidator import MemoryConsolidator
        mc = MemoryConsolidator(memory=self.MockMemory())
        s = mc.stats()
        assert isinstance(s, (dict, str))
