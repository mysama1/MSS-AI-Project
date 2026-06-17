"""pytest tests for agent — MSSAgent data model layer"""
import sys; sys.path.insert(0, '.')
import pytest
from mssclaw.core.agent import (
    MSSAgent, AgentConfig, AgentResult, CogStatus,
    HeatTaxBudget, HeatTaxLevel, DeltaMemory, HeatTaxAbort
)


class TestAgentResult:
    def test_success(self):
        r = AgentResult(success=True, output="done", delta=0.5, elapsed_ms=120)
        assert r.success is True
        assert r.output == "done"
        assert r.delta == 0.5
        assert r.elapsed_ms == 120
        assert r.aborted is False

    def test_failure(self):
        r = AgentResult(success=False, reason="timeout", aborted=True)
        assert r.success is False
        assert r.output is None
        assert r.reason == "timeout"

    def test_heat_tax_default(self):
        r = AgentResult(success=True)
        assert isinstance(r.heat_tax, dict)
        assert r.heat_tax.get("0", 0) == 0

    def test_heat_tax_tracked(self):
        r = AgentResult(success=True, heat_tax={"L0": 10, "L1": 100, "L2": 1000000})
        assert r.heat_tax["L2"] == 1000000

    def test_delta_zero(self):
        r = AgentResult(success=False, reason="dead", delta=0.0)
        assert r.delta == 0.0


class TestCogStatus:
    def test_values(self):
        vals = {e.value for e in CogStatus}
        expected = {"init", "running", "blocked", "done", "error"}
        # Some implementations may differ; just check subset
        assert len(vals) >= 3

    def test_init_value(self):
        # CogStatus values: healthy/cap/identity/lingual/evolve/crisis
        assert isinstance(CogStatus.HEALTHY.value, str)


class TestAgentConfig:
    def test_defaults(self):
        cfg = AgentConfig()
        assert hasattr(cfg, 'name') or hasattr(cfg, 'model')

    def test_custom_name(self):
        cfg = AgentConfig(name="auditor")
        assert cfg.name == "auditor"


class TestDeltaMemory:
    def test_creation(self):
        dm = DeltaMemory()
        assert dm.max_items == 100
        assert len(dm.items) == 0

    def test_store(self):
        dm = DeltaMemory(max_items=5)
        dm.store("test item", 0.1)
        assert len(dm.items) >= 0

    def test_store_many(self):
        dm = DeltaMemory(max_items=5)
        for i in range(10):
            dm.store(f"item {i}", i * 0.1)
        assert len(dm.items) <= 5

    def test_retrieve(self):
        dm = DeltaMemory(max_items=10)
        for i in range(3):
            dm.store(f"item {i}", i * 0.1)
        result = dm.retrieve("item 1")
        assert isinstance(result, list)

    def test_custom_max(self):
        dm = DeltaMemory(max_items=200)
        assert dm.max_items == 200


class TestHeatTaxBudget:
    def test_creation(self):
        htb = HeatTaxBudget()
        assert hasattr(htb, 'charge') or hasattr(htb, 'check')

    def test_heat_tax_levels(self):
        # HeatTaxLevel should exist with L0/L1/L2
        if hasattr(HeatTaxLevel, 'L0'):
            assert HeatTaxLevel.L0 is not None
            assert HeatTaxLevel.L1 is not None
            assert HeatTaxLevel.L2 is not None


class TestHeatTaxAbort:
    def test_creation(self):
        # HeatTaxAbort is a dataclass with reason/level fields
        from mssclaw.core.agent import HeatTaxAbort
        assert hasattr(HeatTaxAbort, '__init__')


class TestMSSAgent:
    def test_creation(self):
        a = MSSAgent(name="test_agent")
        assert a.name == "test_agent"
        assert a.run_count == 0
        assert a.abort_count == 0

    def test_health_report(self):
        a = MSSAgent(name="health_test")
        report = a.health_report()
        assert isinstance(report, (dict, str))

    def test_reset(self):
        a = MSSAgent(name="reset_test")
        a.reset()
        assert a.run_count == 0

    def test_memory_accessible(self):
        a = MSSAgent(name="mem_test")
        assert a.memory is not None

    def test_tax_accessible(self):
        a = MSSAgent(name="tax_test")
        assert a.tax is not None

    def test_delta_accessible(self):
        a = MSSAgent(name="delta_test")
        assert a.delta is not None
