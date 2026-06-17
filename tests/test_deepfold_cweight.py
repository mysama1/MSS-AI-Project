"""
Track C-16: DeepFolder + CWeightGate coverage
"""
import pytest, sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from mssclaw.core.deep_fold import DeepFolder
from mssclaw.core.cweight_gate import CWeightGate, CWeightResult


class TestDeepFolder:
    def test_create(self):
        df = DeepFolder()
        assert df is not None

    def test_disabled(self):
        df = DeepFolder(enabled=False)
        assert df is not None

    def test_enabled(self):
        df = DeepFolder(enabled=True)
        assert df is not None


class TestCWeightResult:
    def test_create(self):
        cwr = CWeightResult()
        assert cwr.c0_forced_dichotomy is False
        assert cwr.c1_direction == "neutral"
        assert cwr.c2_vanity_strictness is False
        assert cwr.c3_delta_closed_by_pride is False
        assert cwr.decision_quality == "unknown"
        assert cwr.heat_adjustment == 0.0

    def test_detected_issues(self):
        cwr = CWeightResult(
            c0_forced_dichotomy=True,
            c1_direction="over_positive",
            c2_vanity_strictness=True,
            c3_delta_closed_by_pride=False,
            decision_quality="poor",
            extracted_info="contradiction between A3 and user claim",
            heat_adjustment=0.5,
        )
        assert cwr.decision_quality == "poor"
        assert cwr.heat_adjustment == 0.5
        assert cwr.c1_direction == "over_positive"
        assert cwr.extracted_info != ""


class TestCWeightGate:
    def test_create(self):
        cwg = CWeightGate()
        assert cwg is not None

    def test_with_audit_dir(self):
        cwg = CWeightGate(audit_dir="/tmp/cweight_audit")
        assert cwg is not None
