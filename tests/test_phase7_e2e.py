"""Phase 7 E2E tests — impact simulation with real KB dependency graph."""
import pytest, time, sys
sys.path.insert(0, r'E:\AI_Workspace\MSS-AI\project')

from mssclaw.agents.activate_symbolic import ActivateSymbolicRouter


# ═══════════ Session-scoped router (build graph once) ═══════════
_ROUTER = None
def _get_router():
    global _ROUTER
    if _ROUTER is None:
        _ROUTER = ActivateSymbolicRouter()
        _ROUTER.route("what if A3 increases by 20%")  # trigger KB load
    return _ROUTER


class TestPhase7Simulation:
    def setup_method(self):
        self.router = _get_router()

    def test_simulate_whatif(self):
        plan = self.router.route("what if A3 increases by 20%")
        assert plan is not None
        assert plan.meta.get("source") == "simulate_impact"

    def test_simulate_decrease(self):
        plan = self.router.route("what if H601 decreases by 10%")
        assert plan is not None
        assert plan.meta.get("source") == "simulate_impact"

    def test_simulate_affect_system(self):
        plan = self.router.route("how does A3 change affect the system")
        assert plan is not None
        assert plan.meta.get("source") == "simulate_impact"
        assert plan.meta.get("target") is None

    def test_simulate_impact_on(self):
        plan = self.router.route("impact of A3 on H610")
        assert plan is not None
        assert plan.meta.get("source") == "simulate_impact"

    def test_sensitivity(self):
        plan = self.router.route("which nodes are most affected by A3")
        assert plan is not None
        assert plan.meta.get("source") == "simulate_sensitivity"
        assert plan.meta.get("total_ranked", 0) > 0

    def test_render_simulation(self):
        plan = self.router.route("what if A3 increases by 15%")
        rendered = plan.render()
        assert rendered
        assert "_Source: SYMBOL" in rendered
        assert "impact simulation" in rendered
        assert "A3" in rendered

    def test_render_sensitivity(self):
        plan = self.router.route("which nodes are most affected by H601")
        rendered = plan.render()
        assert rendered
        assert "_Source: SYMBOL" in rendered
        assert "sensitivity analysis" in rendered

    def test_chain_vs_simulate(self):
        """Chain query should NOT be intercepted by simulate."""
        plan = self.router.route("how does A3 affect H610")
        assert plan is not None
        src = plan.meta.get("source")
        assert src == "chain_reason", f"Expected chain, got {src}"


class TestPhase7Latency:
    def setup_method(self):
        self.router = _get_router()

    def test_simulate_under_500ms(self):
        t0 = time.perf_counter()
        self.router.route("what if A3 increases by 20%")
        elapsed = (time.perf_counter() - t0) * 1000
        assert elapsed < 500, f"Simulate: {elapsed:.1f}ms > 500ms"

    def test_sensitivity_under_500ms(self):
        t0 = time.perf_counter()
        self.router.route("which nodes are most affected by A3")
        elapsed = (time.perf_counter() - t0) * 1000
        assert elapsed < 500, f"Sensitivity: {elapsed:.1f}ms > 500ms"


class TestPhase7NonInterference:
    def setup_method(self):
        self.router = _get_router()

    def test_definition_not_simulate(self):
        plan = self.router.route("what is H610")
        if plan:
            src = plan.meta.get("source", "")
            assert not src.startswith("simulate"), f"Got simulate: {src}"

    def test_chain_not_simulate(self):
        plan = self.router.route("how does A3 affect H610")
        assert plan is not None
        assert plan.meta.get("source") == "chain_reason"
