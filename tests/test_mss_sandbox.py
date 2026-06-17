"""Tests for MSS Sandbox — LLLM-inspired agent Python interpreter."""
import pytest
from mssclaw.core.mss_sandbox import MSSSandbox, MEANING_SAFE_IMPORTS


class TestMSSSandbox:
    def test_basic_execution(self):
        sb = MSSSandbox()
        result = sb.run("x = 42; print(x)")
        assert "42" in result

    def test_persistent_namespace(self):
        sb = MSSSandbox()
        sb.run("x = 42")
        result = sb.run("print(x * 2)")
        assert "84" in result

    def test_heat_tax_accumulates(self):
        sb = MSSSandbox()
        assert sb.heat_tax_spent == 0.0
        sb.run("x = 1")
        assert sb.heat_tax_spent > 0.0

    def test_delta_increases_on_success(self):
        sb = MSSSandbox()
        before = sb.delta_current
        sb.run("x = 1; print(x)")
        assert sb.delta_current >= before

    def test_delta_decreases_on_error(self):
        sb = MSSSandbox(delta_min=0.3)
        before = sb.delta_current
        sb.run("x = 1/0")
        assert sb.delta_current < before

    def test_heat_tax_budget_lock(self):
        sb = MSSSandbox(heat_tax_budget=0.05, delta_min=0.3)
        # Exhaust budget
        for _ in range(5):
            try:
                sb.run("x = 1")
            except RuntimeError:
                break
        assert sb._locked or sb.heat_tax_spent >= sb.heat_tax_budget

    def test_delta_min_block(self):
        sb = MSSSandbox(delta_min=0.8)  # impossible to maintain
        sb.delta_current = 0.6
        with pytest.raises(RuntimeError, match="Delta"):
            sb.run("x = 1")

    def test_can_execute(self):
        sb = MSSSandbox()
        ok, _ = sb.can_execute()
        assert ok

    def test_inject_tool(self):
        def dummy_tool(x: int) -> int:
            return x * 2

        sb = MSSSandbox()
        sb.inject("DOUBLE", dummy_tool)
        result = sb.run("print(DOUBLE(21))")
        assert "42" in result

    def test_import_whitelist_blocks_os(self):
        sb = MSSSandbox(delta_min=0.3)
        result = sb.run("import os; print(os.name)")
        assert "not in the MSS meaning-safe import list" in result

    def test_import_whitelist_allows_json(self):
        sb = MSSSandbox()
        result = sb.run("import json; print(json.dumps({'a': 1}))")
        assert '"a"' in result

    def test_call_count(self):
        sb = MSSSandbox()
        assert sb.call_count == 0
        sb.run("x = 1")
        sb.run("y = 2")
        assert sb.call_count == 2

    def test_reset(self):
        sb = MSSSandbox()
        sb.run("x = 42")
        sb.reset()
        assert sb.heat_tax_spent == 0.0
        assert sb.call_count == 0
        assert not sb._locked

    def test_status(self):
        sb = MSSSandbox()
        status = sb.status()
        assert "heat_tax_spent" in status
        assert "delta_current" in status
        assert "call_count" in status
        assert "degradation_risk" in status

    def test_degradation_risk(self):
        sb = MSSSandbox(delta_min=0.3)
        for _ in range(10):
            sb.run("x = 1")
        status = sb.status()
        assert status["degradation_risk"] > 0
        
    # NOTE: test_timeout disabled — Windows Job Object kills the entire
    # process tree when thread runs infinite loop, not just the thread.
    # def test_timeout(self):
    #     sb = MSSSandbox(timeout=0.01, delta_min=0.3, heat_tax_budget=1.0)
    #     with pytest.raises(TimeoutError):
    #         sb.run("while True: pass")

    def test_tool_injected_survives_reset(self):
        sb = MSSSandbox()
        sb.inject("MY_TOOL", lambda: 42)
        sb.reset()
        result = sb.run("print(MY_TOOL())")
        assert "42" in result

    def test_error_tracking(self):
        sb = MSSSandbox(delta_min=0.3)
        sb.run("x = 1/0")
        assert len(sb._errors) == 1
        assert "ZeroDivisionError" in sb._errors[0]

    def test_safe_imports_list_contains_essentials(self):
        assert "json" in MEANING_SAFE_IMPORTS
        assert "re" in MEANING_SAFE_IMPORTS
        assert "math" in MEANING_SAFE_IMPORTS
        assert "os" not in MEANING_SAFE_IMPORTS
        assert "subprocess" not in MEANING_SAFE_IMPORTS
