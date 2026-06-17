"""
pytest tests for normative_field — 组织规范场核心模块
"""
import sys
sys.path.insert(0, '.')
import pytest
from mssclaw.core.normative_field import (
    NormDomain, NormLevel, NormRule, NormVerdict,
    LexicalRule, AnchorRule, WelfordTracker, MetaField, Verdict
)


# ═══════ Enums ═══════

class TestNormDomain:
    def test_five_domains(self):
        domains = {e.value for e in NormDomain}
        assert domains == {"process", "file", "network", "resource", "content"}

    def test_unique_values(self):
        vals = [e.value for e in NormDomain]
        assert len(vals) == len(set(vals))


class TestNormLevel:
    def test_five_levels(self):
        levels = {e.value for e in NormLevel}
        assert levels == {"safe", "observe", "warn", "block", "needs_human"}

    def test_escalation_order(self):
        # SAFE < OBSERVE < WARN < BLOCK < NEEDS_HUMAN
        order = [NormLevel.SAFE, NormLevel.OBSERVE, NormLevel.WARN,
                 NormLevel.BLOCK, NormLevel.NEEDS_HUMAN]
        for i in range(len(order) - 1):
            assert order[i].value != order[i+1].value


# ═══════ Data Classes ═══════

class TestNormRule:
    def test_creation(self):
        r = NormRule(name="no_exec", domain=NormDomain.PROCESS,
                     pattern="exec", level=NormLevel.BLOCK)
        assert r.name == "no_exec"
        assert r.domain == NormDomain.PROCESS
        assert r.level == NormLevel.BLOCK

    def test_defaults(self):
        r = NormRule(name="test_rule", domain=NormDomain.CONTENT)
        assert r.pattern == ""
        assert r.level == NormLevel.WARN
        assert r.learned is False
        assert r.hit_count == 0

    def test_hit_tracking(self):
        r = NormRule(name="tracked", domain=NormDomain.FILE)
        r.hit_count += 1
        assert r.hit_count == 1


class TestNormVerdict:
    def test_safe_default(self):
        v = NormVerdict()
        assert v.level == NormLevel.SAFE
        assert v.anomaly_score == 0.0
        assert v.needs_confirm is False

    def test_block_verdict(self):
        v = NormVerdict(level=NormLevel.BLOCK,
                        reason="suspicious exec call",
                        anomaly_score=4.2)
        assert v.level == NormLevel.BLOCK
        assert v.anomaly_score == 4.2

    def test_needs_human(self):
        v = NormVerdict(level=NormLevel.NEEDS_HUMAN, needs_confirm=True)
        assert v.needs_confirm is True


# ═══════ WelfordTracker ═══════

class TestWelfordTracker:
    def test_initial_state(self):
        wt = WelfordTracker()
        assert wt.n == 0
        assert wt.mean == 0.0
        assert wt.M2 == 0.0

    def test_single_update(self):
        wt = WelfordTracker()
        z = wt.update(5.0)
        assert wt.n == 1
        assert wt.mean == 5.0
        assert z == 0.0  # n<2 → Z=0

    def test_two_updates(self):
        wt = WelfordTracker()
        wt.update(1.0)
        z = wt.update(3.0)  # mean=2.0, std=√2≈1.414
        assert wt.n == 2
        assert wt.mean == 2.0
        assert z > 0

    def test_convergence(self):
        wt = WelfordTracker()
        for _ in range(50):
            wt.update(10.0)
        assert abs(wt.mean - 10.0) < 0.001  # should converge to 10
        assert wt.n == 50

    def test_z_score_low_within_range(self):
        wt = WelfordTracker()
        for v in [9.8, 10.2, 10.1, 9.9, 10.0, 10.3, 9.7]:
            wt.update(v)
        z = wt.update(10.2)  # close to mean ~10.0 with some variance
        assert z < 2.0  # close to mean with real variance → low Z

    def test_z_score_high_anomaly(self):
        wt = WelfordTracker()
        for _ in range(20):
            wt.update(10.0)
        z = wt.update(50.0)
        assert z > 3.0  # far from mean → high Z

    def test_sliding_window_bounds(self):
        wt = WelfordTracker(window_size=5)
        for i in range(10):
            wt.update(float(i))
        # After 10 updates with window=5, n should be 5
        assert wt.n == 5
        # mean should be average of last 5 [5,6,7,8,9] = 7.0
        assert abs(wt.mean - 7.0) < 0.01

    def test_custom_window_size(self):
        wt = WelfordTracker(window_size=500)
        assert wt.window_size == 500


# ═══════ MetaField ═══════

class TestMetaField:
    def test_has_five_trackers(self):
        mf = MetaField()
        assert len(mf.trackers) == 5
        for name in ['response_length', 'rule_hit_density', 'semantic_entropy',
                      'negation_rate', 'identity_marker_rate']:
            assert name in mf.trackers

    def test_observe_new_signal(self):
        mf = MetaField()
        z = mf.observe("response_length", 100.0)
        assert z == 0.0  # first observation

    def test_observe_unknown_signal(self):
        mf = MetaField()
        z = mf.observe("nonexistent", 1.0)
        assert z == 0.0

    def test_is_anomalous_false_normal(self):
        mf = MetaField()
        # Use varied values so std > 0
        for v in [98, 102, 101, 99, 100, 103, 97, 100, 102, 98]:
            mf.observe("response_length", float(v))
        is_anom, z = mf.is_anomalous("response_length", 101.0)
        assert is_anom is False, f"z={z} should be < threshold"

    def test_is_anomalous_true_extreme(self):
        mf = MetaField()
        for _ in range(50):
            mf.observe("response_length", 100.0)
        is_anom, z = mf.is_anomalous("response_length", 500.0)
        assert is_anom is True
        assert z > 3.0

    def test_get_stats(self):
        mf = MetaField()
        mf.observe("response_length", 100.0)
        stats = mf.get_stats("response_length")
        assert stats["n"] == 1
        assert stats["mean"] == 100.0

    def test_get_stats_unknown(self):
        mf = MetaField()
        assert MetaField().get_stats("nonexistent") == {}


# ═══════ LexicalRule ═══════

class TestLexicalRule:
    def test_creation(self):
        lr = LexicalRule(rule_id="L001", pattern=r"rm\s+-rf", severity="BLOCK", message="rm -rf forbidden")
        assert lr.rule_id == "L001"

    def test_match(self):
        lr = LexicalRule("L001", r"rm\s+-rf", "BLOCK", "no rm -rf")
        assert lr.match("rm -rf /") is not None

    def test_no_match(self):
        lr = LexicalRule("L001", r"rm\s+-rf", "BLOCK", "no rm -rf")
        assert lr.match("ls -la") is None  # re.search returns None

    def test_chinese_pattern(self):
        lr = LexicalRule("L002", r"删除", "WARN", "delete keyword")
        assert lr.match("删除所有文件") is not None


# ═══════ Verdict ═══════

class TestVerdict:
    def test_pass_verdict(self):
        v = Verdict(passed=True, severity="ok", rule_id="R001")
        assert v.passed is True
        assert v.severity == "ok"

    def test_fail_verdict(self):
        v = Verdict(passed=False, severity="block", message="violation detected")
        assert v.passed is False
        assert v.severity == "block"

    def test_z_scores_default(self):
        v = Verdict(passed=True)
        assert v.z_scores == {}
