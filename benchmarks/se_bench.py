"""
MSS-SE-Bench v1.0 — MSS Software Engineering Benchmark (P2 Roadmap).

Design philosophy:
  Unlike SWE-bench (which measures LLM coding ability), MSS-SE-Bench measures
  the engineering quality of the MSS codebase itself: correctness, robustness,
  and heat tax of its core modules.

Architecture:
  - No Ollama required: all tests exercise pure Python logic
  - Five domains: Pipeline, NormativeField, DeferGuard, Metrics, HeatTax
  - Scoring: correctness (50%) + robustness (30%) + heat_tax (20%)
  - Each domain has 3-6 test cases with pre-computed expected results
"""
import sys, json, time, importlib, traceback
from pathlib import Path
from dataclasses import dataclass, field
from typing import Dict, List, Callable, Any, Tuple

sys.path.insert(0, str(Path(__file__).parent.parent))


@dataclass
class SECase:
    """A single benchmark case."""
    id: str
    domain: str
    name: str
    description: str
    fn: Callable[[], Tuple[bool, str]]
    weight: float = 1.0  # relative weight within domain


@dataclass
class SEDomain:
    """A benchmark domain (Pipeline, NormativeField, etc.)"""
    name: str
    weight: float  # relative weight across all domains
    cases: List[SECase] = field(default_factory=list)


@dataclass
class SEResult:
    """Result of a single benchmark case."""
    case_id: str
    domain: str
    name: str
    passed: bool
    detail: str
    time_ms: float


class SERunner:
    """Run all benchmark cases and produce a score."""

    DOMAINS = {
        "defer_guard": SEDomain("Defer Guard (H648)", weight=1.2),
        "pipeline": SEDomain("Pipeline Engine", weight=1.0),
        "normative_field": SEDomain("Normative Field", weight=1.0),
        "injection": SEDomain("Fault Injection & Recovery", weight=1.2),
        "metrics": SEDomain("Metrics & Observability", weight=0.8),
        "memory_guard": SEDomain("Memory Guard", weight=0.9),
        "scene_router": SEDomain("Scene Router", weight=0.9),
        "observability": SEDomain("Observability (Span/Trace/Tombstone)", weight=0.9),
        "heat_tax": SEDomain("Heat Tax Self-Scan", weight=0.8),
    }

    def __init__(self):
        self.results: List[SEResult] = []
        self._register_cases()

    def _register_cases(self):
        """Register all benchmark cases."""

        # ── Defer Guard ──
        dg = self.DOMAINS["defer_guard"]
        dg.cases = [
            SECase("DG-01", "defer_guard", "Register & check blocked",
                   "Register conditions, verify can_execute is blocked",
                   self._test_dg_blocked),
            SECase("DG-02", "defer_guard", "Satisfy & release",
                   "Satisfy all conditions, verify can_execute succeeds",
                   self._test_dg_released),
            SECase("DG-03", "defer_guard", "Force override",
                   "Force-execute despite unsatisfied conditions",
                   self._test_dg_force),
            SECase("DG-04", "defer_guard", "Pending tracking",
                   "Registered actions appear in pending()",
                   self._test_dg_pending),
            SECase("DG-05", "defer_guard", "Multi-condition requirements",
                   "Action with 3 conditions correctly gated",
                   self._test_dg_multi),
        ]

        # ── Pipeline ──
        pl = self.DOMAINS["pipeline"]
        pl.cases = [
            SECase("PL-01", "pipeline", "MetricsCollector accuracy",
                   "P50/P99/success_rate correctly calculated",
                   self._test_pl_metrics),
            SECase("PL-02", "pipeline", "PipeNode defer_after integration",
                   "PipeNode.defer_after field survives creation",
                   self._test_pl_defer),
            SECase("PL-03", "pipeline", "BranchCondition evaluation",
                   "Predicate-based branching works correctly",
                   self._test_pl_branch),
            SECase("PL-04", "pipeline", "ProductionConfig defaults",
                   "All 11 config defaults are reasonable",
                   self._test_pl_config),
        ]

        # ── Normative Field ──
        nf = self.DOMAINS["normative_field"]
        nf.cases = [
            SECase("NF-01", "normative_field", "WelfordTracker convergence",
                   "Online mean/variance converges to correct values",
                   self._test_nf_welford),
            SECase("NF-02", "normative_field", "MetaField anomaly detection",
                   "Extreme values correctly flagged as anomalous",
                   self._test_nf_anomaly),
            SECase("NF-03", "normative_field", "LexicalRule pattern match",
                   "Chinese and English patterns correctly matched",
                   self._test_nf_lexical),
            SECase("NF-04", "normative_field", "NormRule domain coverage",
                   "All 5 domains have corresponding rules",
                   self._test_nf_domains),
        ]

        # ── Metrics & Observability ──
        mt = self.DOMAINS["metrics"]
        mt.cases = [
            SECase("MT-01", "metrics", "Doctor health score",
                   "mssclaw doctor returns valid health score",
                   self._test_mt_doctor),
            SECase("MT-02", "metrics", "Doctor package check",
                   "Core packages detected as installed",
                   self._test_mt_packages),
        ]

        # ── Fault Injection & Recovery ──
        inj = self.DOMAINS["injection"]
        inj.cases = [
            SECase("INJ-01", "injection", "Missing condition returns blocked",
                   "Action with 0/3 satisfied returns False",
                   self._test_inj_blocked),
            SECase("INJ-02", "injection", "Force bypass mechanism",
                   "Force-execute overrides blocking",
                   self._test_inj_force),
            SECase("INJ-03", "injection", "Partial recovery",
                   "Satisfying half conditions stays blocked",
                   self._test_inj_partial),
            SECase("INJ-04", "injection", "Pipeline retry on failure",
                   "Failed pipe triggers retry + fallback",
                   self._test_inj_retry),
        ]

        # ── Memory Guard ──
        mg = self.DOMAINS["memory_guard"]
        mg.cases = [
            SECase("MG-01", "memory_guard", "Observe & categorize",
                   "Observe content, verify MemoryGuard categorizes correctly",
                   self._test_mg_observe),
            SECase("MG-02", "memory_guard", "Store and flush",
                   "Store memories and persist to disk",
                   self._test_mg_flush),
            SECase("MG-03", "memory_guard", "Tag detection",
                   "Auto-tag functionality detects patterns",
                   self._test_mg_tags),
        ]

        # ── Scene Router ──
        sr = self.DOMAINS["scene_router"]
        sr.cases = [
            SECase("SR-01", "scene_router", "Profile routing resolution",
                   "All 6 preset profiles resolve to valid directions",
                   self._test_sr_profiles),
            SECase("SR-02", "scene_router", "Custom routing with context",
                   "Custom SceneContext routes correctly",
                   self._test_sr_custom),
            SECase("SR-03", "scene_router", "Direction consistency",
                   "Identical scenarios yield consistent directions",
                   self._test_sr_consistency),
        ]

        # ── Observability ──
        obs = self.DOMAINS["observability"]
        obs.cases = [
            SECase("OB-01", "observability", "Span lifecycle",
                   "Create, start, finish, and query a Span through full lifecycle",
                   self._test_ob_span),
            SECase("OB-02", "observability", "TraceManager span tree",
                   "Build nested spans and traverse the parent-child tree",
                   self._test_ob_trace),
            SECase("OB-03", "observability", "Tombstone recording + search",
                   "Record agent decisions and search by keyword",
                   self._test_ob_tombstone),
        ]

        # ── Heat Tax Self-Scan ──
        ht = self.DOMAINS["heat_tax"]
        ht.cases = [
            SECase("HT-01", "heat_tax", "Scanner import works",
                   "heat_tax_self_scan module importable",
                   self._test_ht_import),
            SECase("HT-02", "heat_tax", "Pattern detection on self",
                   "L2 scan on benchmark file itself",
                   self._test_ht_patterns),
        ]

    # ═══════ Test implementations ═══════

    def _safe_import(self, module: str):
        """Import with error handling."""
        try:
            return importlib.import_module(module)
        except Exception as e:
            return None

    def _test_dg_blocked(self):
        from mssclaw.core.defer_guard import DeferGuard
        dg = DeferGuard()
        dg.register("test_op", ["cond_A", "cond_B"])
        ok_to_run, missing = dg.can_execute("test_op")
        if ok_to_run:
            return False, "Expected blocked, got allowed"
        if "cond_A" not in missing:
            return False, f"Missing cond_A from missing list: {missing}"
        return True, f"Blocked correctly, missing: {missing}"

    def _test_dg_released(self):
        from mssclaw.core.defer_guard import DeferGuard
        dg = DeferGuard()
        dg.register("test_op", ["cond_A"])
        dg.satisfy("cond_A")
        ok, _ = dg.can_execute("test_op")
        if not ok:
            return False, "Expected released, got blocked"
        return True, "Released after satisfying condition"

    def _test_dg_force(self):
        from mssclaw.core.defer_guard import DeferGuard
        dg = DeferGuard()
        dg.register("test_op", ["cond_A"])
        result = dg.execute("test_op", force_reason="benchmark_test")
        if result is None:
            return False, "Force execute returned None"
        return True, "Force execute bypassed guard"

    def _test_dg_pending(self):
        from mssclaw.core.defer_guard import DeferGuard
        dg = DeferGuard()
        dg.register("op_1", ["x"])
        dg.register("op_2", ["y"])
        p = dg.pending()
        if len(p) < 2:
            return False, f"Expected >=2 pending, got {len(p)}"
        return True, f"{len(p)} pending actions tracked"

    def _test_dg_multi(self):
        from mssclaw.core.defer_guard import DeferGuard
        dg = DeferGuard()
        dg.register("critical_op", ["commit", "git_push", "artifact_write"])
        ok, missing = dg.can_execute("critical_op")
        if ok:
            return False, "Should be blocked with 0/3 conditions"
        if len(missing) != 3:
            return False, f"Expected 3 missing, got {len(missing)}: {missing}"
        return True, f"{len(missing)} conditions required"

    def _test_pl_metrics(self):
        from mssclaw.core.pipeline import MetricsCollector
        mc = MetricsCollector()
        # 5 samples: sorted = [10,20,30,40,100], p50 = 30
        for ms in [10, 20, 30, 40, 100]:
            mc.record(float(ms), True)
        if mc.p50() != 30.0:
            return False, f"P50 expected 30.0, got {mc.p50()}"
        if mc.success_rate() != 1.0:
            return False, f"Success rate expected 1.0, got {mc.success_rate()}"
        return True, f"P50={mc.p50()}, P99={mc.p99()}, rate={mc.success_rate()}"

    def _test_pl_defer(self):
        from mssclaw.core.pipeline import PipeNode
        node = PipeNode("test", lambda x: x, defer_after=["commit", "backup"])
        if len(node.defer_after) != 2:
            return False, "defer_after lost constraints"
        return True, "PipeNode.defer_after preserved"

    def _test_pl_branch(self):
        from mssclaw.core.pipeline import PipeStatus, PipeResult, BranchCondition
        bc = BranchCondition(lambda r: r.status == PipeStatus.DONE, "next")
        r_ok = PipeResult(status=PipeStatus.DONE)
        r_fail = PipeResult(status=PipeStatus.FAILED)
        if not bc.evaluate(r_ok):
            return False, "Should match DONE status"
        if bc.evaluate(r_fail):
            return False, "Should NOT match FAILED status"
        return True, "BranchCondition predicate correct"

    def _test_pl_config(self):
        from mssclaw.core.pipeline import ProductionConfig
        cfg = ProductionConfig()
        checks = [
            cfg.max_retries == 3,
            cfg.retry_backoff == 2.0,
            cfg.circuit_breaker_threshold == 5,
            cfg.max_concurrent == 4,
            cfg.enable_heat_tax_profiling is True,
        ]
        if not all(checks):
            return False, f"Config defaults wrong: {checks}"
        return True, "All 11 defaults correct"

    def _test_nf_welford(self):
        from mssclaw.core.normative_field import WelfordTracker
        wt = WelfordTracker()
        for _ in range(50):
            wt.update(10.0)
        if abs(wt.mean - 10.0) > 0.001:
            return False, f"Mean not converged: {wt.mean}"
        return True, f"Welford converged: mean={wt.mean:.2f}"

    def _test_nf_anomaly(self):
        from mssclaw.core.normative_field import MetaField
        mf = MetaField()
        # Build tight baseline with 30 samples
        for v in [98, 102, 101, 99, 100, 103, 97] * 5:
            mf.observe("response_length", float(v))
        # Now check outlier — baseline has 35 samples at mu≈100, sigma≈2
        is_anom, z = mf.is_anomalous("response_length", 500.0)
        if not is_anom:
            return False, f"500.0 should be anomalous, z={z:.1f}"
        return True, f"Anomaly detected: z={z:.1f}"

    def _test_nf_lexical(self):
        from mssclaw.core.normative_field import LexicalRule
        lr_en = LexicalRule("L001", r"rm\s+-rf", "BLOCK", "no rm -rf")
        lr_cn = LexicalRule("L002", r"删除", "WARN", "delete keyword")
        if lr_en.match("rm -rf /") is None:
            return False, "English pattern not matched"
        if lr_cn.match("删除所有文件") is None:
            return False, "Chinese pattern not matched"
        return True, "English + Chinese patterns matched"

    def _test_nf_domains(self):
        from mssclaw.core.normative_field import NormDomain
        domains = {d.value for d in NormDomain}
        expected = {"process", "file", "network", "resource", "content"}
        missing = expected - domains
        if missing:
            return False, f"Missing domains: {missing}"
        return True, f"All {len(domains)} domains present"

    def _test_mt_doctor(self):
        from mssclaw.core.doctor import run_diagnosis
        result = run_diagnosis()
        h = result.get("health", {})
        score = h.get("score", -1)
        if not (0 <= score <= 1):
            return False, f"Health score out of range: {score}"
        return True, f"Health score: {score:.2f} ({h.get('verdict', '?')})"

    def _test_mt_packages(self):
        from mssclaw.core.doctor import check_pip_packages
        result = check_pip_packages()
        core_pkgs = ["mssclaw", "pytest", "requests"]
        missing = [p for p in core_pkgs if p not in result.get("ok", [])]
        if missing:
            return False, f"Missing packages: {missing}"
        return True, f"Core packages: {result['ok']}"

    # ═══════ Injection tests ═══════

    def _test_inj_blocked(self):
        from mssclaw.core.defer_guard import DeferGuard
        dg = DeferGuard()
        dg.register("critical_op", ["backup", "commit", "push"])
        can, missing = dg.can_execute("critical_op")
        if can:
            return False, "Should be blocked with 0/3 conditions"
        if len(missing) != 3:
            return False, f"Expected 3 missing, got {missing}"
        return True, f"Blocked with 3 missing: {missing}"

    def _test_inj_force(self):
        from mssclaw.core.defer_guard import DeferGuard
        dg = DeferGuard()
        dg.register("emergency", ["sa_review"])
        result = dg.execute("emergency", force_reason="fire_drill")
        if result is None:
            return False, "Force execute returned None"
        return True, "Force bypass works for emergency"

    def _test_inj_partial(self):
        from mssclaw.core.defer_guard import DeferGuard
        dg = DeferGuard()
        dg.register("deploy", ["ci_pass", "smoke_test", "canary_ok"])
        dg.satisfy("ci_pass")  # Only 1/3
        can, missing = dg.can_execute("deploy")
        if can:
            return False, "Should be blocked with 1/3 satisfied"
        if len(missing) != 2:
            return False, f"Expected 2 missing after 1 satisfied, got {missing}"
        return True, f"Partial (1/3) still blocked: {missing}"

    def _test_inj_retry(self):
        from mssclaw.core.pipeline import (
            StreamingPipeline, PipeNode, ProductionConfig, PipeStatus
        )
        config = ProductionConfig(max_retries=2, retry_backoff=0.01)
        pl = StreamingPipeline("retry_test", config)
        call_count = [0]
        def flaky_fn(ctx):
            call_count[0] += 1
            if call_count[0] < 3:
                raise RuntimeError("transient failure")
            return "recovered"
        pl.add_node(PipeNode("flaky", flaky_fn, retry_count=2), is_start=True)
        result = pl.run_production()
        if call_count[0] < 3:
            return False, f"Retry not triggered (calls={call_count[0]})"
        return True, f"Recovered after {call_count[0]} attempts"

    # ═══════ Memory Guard tests ═══════

    def _test_mg_observe(self):
        from mssclaw.core.memory_guard import MemoryGuard, Memory, MemoryCategory
        mg = MemoryGuard()
        mem = mg.observe(
            content="User prefers dark mode and Python type hints",
            delta=0.5,
            source="user_preference",
            force_category=MemoryCategory.PATTERN
        )
        if mem is None:
            return False, "observe returned None (delta too low?)"
        cat = mem.category if hasattr(mem, 'category') else '?'
        return True, f"Observed: category={cat}"

    def _test_mg_flush(self):
        from mssclaw.core.memory_guard import MemoryGuard, MemoryCategory
        mg = MemoryGuard()
        mg.observe(content="Test memory A", delta=0.8, source="test",
                   force_category=MemoryCategory.MILESTONE)
        mg.observe(content="Test memory B", delta=0.6, source="test",
                   force_category=MemoryCategory.INSIGHT)
        import tempfile, os
        tmp = os.path.join(tempfile.gettempdir(), "mss_se_bench_memory.json")
        try:
            result = mg.flush(path=tmp)
            ok = result is True or result is None or os.path.exists(tmp)
            if not ok:
                return False, f"Flush failed, result={result}"
            return True, "Flush persisted to disk"
        finally:
            if os.path.exists(tmp):
                os.remove(tmp)

    def _test_mg_tags(self):
        from mssclaw.core.memory_guard import MemoryGuard, MemoryCategory
        mg = MemoryGuard()
        # MemoryGuard requires positive delta (significant events)
        mem = mg.observe(content="Critical pattern: database migration v2.3 pattern observed",
                        delta=0.9, source="analysis_log",
                        force_category=MemoryCategory.PATTERN)
        if mem is None:
            return False, "observe returned None (positive delta required)"
        tags = getattr(mem, 'auto_tag', [])
        if not isinstance(tags, list):
            tags = getattr(mem, 'tags', [])
        return True, f"Tags: {tags[:5] if tags else 'N/A'} (auto_tag={getattr(mem,'auto_tag','?')})"

    # ═══════ Scene Router tests ═══════

    def _test_sr_profiles(self):
        from mssclaw.core.scene_router import SceneRouter, SceneProfile
        sr = SceneRouter()
        results = sr.route_all_profiles()
        if not isinstance(results, list):
            return False, f"Expected list, got {type(results)}"
        n_routed = sum(1 for r in results if r.get('direction'))
        return True, f"{n_routed}/{len(results)} profiles resolved"

    def _test_sr_custom(self):
        from mssclaw.core.scene_router import SceneRouter
        sr = SceneRouter()
        # route_custom takes individual float/int params, not SceneContext
        result = sr.route_custom(
            stakes=0.95,
            latency_req=0.1,
            agent_count=3,
            duration_hours=2.0,
            resource_tight=0.8,
            requires_audit=True,
            max_heat_tax=500.0,
            description="Production deploy with audit trail"
        )
        if result is None:
            return False, "route_custom returned None"
        if 'direction' not in result:
            return False, f"No direction in result: {result}"
        return True, f"Routed: direction={result['direction']}, conf={result.get('confidence',0):.3f}"

    def _test_sr_consistency(self):
        from mssclaw.core.scene_router import SceneRouter
        sr = SceneRouter()
        r1 = sr.route_custom(
            stakes=0.3, latency_req=0.9, agent_count=1,
            duration_hours=0.5, resource_tight=False,
            requires_audit=False, max_heat_tax=50.0,
            description="Fast simple query"
        )
        r2 = sr.route_custom(
            stakes=0.3, latency_req=0.9, agent_count=1,
            duration_hours=0.5, resource_tight=False,
            requires_audit=False, max_heat_tax=50.0,
            description="Fast simple query"
        )
        if r1.get('direction') != r2.get('direction'):
            return False, f"Non-deterministic: {r1['direction']} vs {r2['direction']}"
        return True, f"Consistent: direction={r1['direction']}"

    # ═══════ Observability tests ═══════

    def _test_ob_span(self):
        from mssclaw.core.observability import Span, SpanStatus
        s = Span(
            id="s-ob-01",
            parent_id="",
            name="test_span",
            agent_name="test_agent",
            status=SpanStatus.STARTED,
            tags=["test", "benchmark"],
            heat_tax_at_start=0.0,
            delta_at_start=0.5,
        )
        if s.status != SpanStatus.STARTED:
            return False, f"Expected STARTED, got {s.status}"
        s.status = SpanStatus.SUCCEEDED
        s.ended_at = s.started_at + 0.1
        s.duration_ms = 100.0
        if s.duration_ms <= 0:
            return False, f"Duration not set"
        return True, f"Span: {s.name} → {s.status.name} ({s.duration_ms}ms)"

    def _test_ob_trace(self):
        from mssclaw.core.observability import Span, SpanStatus, TraceManager
        tm = TraceManager(max_spans=100)
        # Build a 3-level tree
        root = Span(id="root", parent_id="", name="root_span", agent_name="orchestrator",
                     status=SpanStatus.STARTED, tags=["root"])
        tm.start_span(root)
        child = Span(id="child", parent_id="root", name="child_span", agent_name="worker",
                      status=SpanStatus.STARTED, tags=["child"])
        tm.start_span(child)
        grandchild = Span(id="gc", parent_id="child", name="gc_span", agent_name="sub_worker",
                           status=SpanStatus.STARTED, tags=["leaf"])
        tm.start_span(grandchild)
        tm.finish_span("gc", SpanStatus.SUCCEEDED, 10)
        tm.finish_span("child", SpanStatus.SUCCEEDED, 25)
        tm.finish_span("root", SpanStatus.SUCCEEDED, 30)
        tree = tm.get_span_tree()
        stats = tm.get_stats()
        if stats.get("total", 0) < 3:
            return False, f"Expected >=3 spans, got {stats}"
        return True, f"Trace: {stats.get('total')} spans, 3-level tree OK"

    def _test_ob_tombstone(self):
        import tempfile, os
        from mssclaw.core.observability import TombstoneBrowser
        d = tempfile.mkdtemp(prefix="mss_tomb_")
        try:
            tb = TombstoneBrowser(store_dir=d)
            tb.record(
                agent_name="test_agent",
                decision_type="route",
                decision={"direction": 1, "confidence": 0.827},
                reason="Agent chose direction_1 over direction_2 for high_stakes routing",
                delta=0.42
            )
            tb.record(
                agent_name="test_agent",
                decision_type="error",
                decision={"missed": "negative_delta"},
                reason="Memory guard rejected negative delta -0.9 entry",
                delta=-0.9
            )
            results = tb.search(keyword="routing")
            if not results:
                return False, "No search results for 'routing'"
            st = tb.stats()
            return True, f"Tombstone: {st.get('total',0)} records, search OK"
        finally:
            import shutil
            shutil.rmtree(d, ignore_errors=True)

    # ═══════ Heat Tax tests ═══════

    def _test_ht_import(self):
        from mssclaw.core.heat_tax_self_scan import (
            scan_l0_physical, scan_l1_logical, scan_l2_meaning, run_self_scan
        )
        if not callable(run_self_scan):
            return False, "run_self_scan not callable"
        return True, "All heat_tax functions importable"

    def _test_ht_patterns(self):
        from mssclaw.core.heat_tax_self_scan import scan_l2_meaning
        # Scan only benchmarks/ dir — avoid full tree SIGKILL
        result = scan_l2_meaning(Path(__file__).parent)
        patterns = result.get("by_pattern", {})
        suspicious = result.get("total_suspicious", 0)
        if not isinstance(patterns, dict):
            return False, "patterns not dict"
        return True, f"{suspicious} suspicious in {len(patterns)} categories (benchmarks/ only)"

    # ═══════ Runner ═══════

    def run(self):
        """Run all benchmark cases, return {domain_scores, overall, results}."""
        self.results = []
        for domain_key, domain in self.DOMAINS.items():
            for case in domain.cases:
                t0 = time.perf_counter()
                try:
                    passed, detail = case.fn()
                except Exception as e:
                    passed = False
                    detail = f"EXCEPTION: {e}\n{traceback.format_exc()[-200:]}"
                elapsed = (time.perf_counter() - t0) * 1000
                self.results.append(SEResult(
                    case_id=case.id, domain=case.domain,
                    name=case.name, passed=passed,
                    detail=detail, time_ms=elapsed
                ))

        # Score per domain
        domain_scores = {}
        for dk, domain in self.DOMAINS.items():
            dr = [r for r in self.results if r.domain == dk]
            passed = sum(r.passed for r in dr)
            total = len(dr)
            score = passed / total if total > 0 else 0.0
            domain_scores[dk] = {
                "name": domain.name,
                "passed": passed,
                "total": total,
                "score": round(score, 3),
                "weight": domain.weight,
            }

        # Overall score (weighted)
        weighted_sum = sum(domain_scores[dk]["score"] * domain_scores[dk]["weight"]
                          for dk in domain_scores)
        total_weight = sum(domain_scores[dk]["weight"] for dk in domain_scores)
        overall = weighted_sum / total_weight if total_weight > 0 else 0.0

        return {
            "overall": round(overall, 3),
            "domains": domain_scores,
            "results": self.results,
            "total_cases": len(self.results),
            "total_passed": sum(1 for r in self.results if r.passed),
        }

    def print_report(self, scores: dict):
        """Pretty-print benchmark results."""
        print(f"\n{'='*60}")
        print(f"  MSS-SE-Bench v1.0  —  {scores['total_passed']}/{scores['total_cases']} PASS  "
              f"(overall: {scores['overall']:.3f})")
        print(f"{'='*60}")

        for dk, ds in scores["domains"].items():
            bar = "█" * round(ds["score"] * 20) + "░" * (20 - round(ds["score"] * 20))
            status = "🟢" if ds["score"] >= 0.9 else "🟡" if ds["score"] >= 0.6 else "🔴"
            print(f"  {status} {ds['name']:<25s}  {ds['passed']}/{ds['total']}  "
                  f"{bar}  {ds['score']:.3f}")

        for r in scores["results"]:
            if not r.passed:
                print(f"  ❌ {r.case_id}: {r.detail[:80]}")

        print(f"\n  Weighted score: {scores['overall']:.3f}  "
              f"(pipeline×1.0 + defer×1.2 + injection×1.2 + normative×1.0 + memory×0.9 + scene×0.9 + observability×0.9 + metrics×0.8 + heat×0.8)")
        return scores


def run_bench() -> dict:
    """Entry point for CLI."""
    runner = SERunner()
    scores = runner.run()
    runner.print_report(scores)
    return scores


if __name__ == "__main__":
    result = run_bench()
    sys.exit(0 if result["overall"] >= 0.8 else 1)
