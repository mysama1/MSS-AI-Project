"""
Track C-18: IdentityGuard + HeatTaxFuse + LayeringLinter coverage
"""
import pytest, sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from mssclaw.core.identity_guard import (
    IdentityGuard, IdentityReport, IdentityViolation,
)
from mssclaw.core.heat_tax_fuse import (
    HeatTaxFuseGroup, FuseState, FuseLevel,
)
from mssclaw.core.layering_linter import LayeringLinter


class TestIdentityViolation:
    def test_create(self):
        iv = IdentityViolation(
            code="IV001", rule="no_impersonation",
            found="user:admin", expected="user:assistant",
            location="line 5", severity="CRITICAL",
        )
        assert iv.code == "IV001"
        assert iv.rule == "no_impersonation"
        assert iv.found == "user:admin"
        assert iv.expected == "user:assistant"
        assert iv.severity == "CRITICAL"

    def test_warning(self):
        iv = IdentityViolation(
            code="IV002", rule="style_drift",
            found="casual", expected="formal",
            location="line 42", severity="WARNING",
        )
        assert iv.severity == "WARNING"


class TestIdentityReport:
    def test_create(self):
        ir = IdentityReport()
        assert ir.passed is True
        assert ir.author_verified is False
        assert ir.violations == []

    def test_with_violations(self):
        iv = IdentityViolation(code="IV1", rule="r1", found="x", expected="y", location="L1", severity="HIGH")
        ir = IdentityReport(passed=False, violations=[iv], summary="1 impersonation found")
        assert ir.passed is False
        assert len(ir.violations) == 1


class TestIdentityGuard:
    def test_create(self):
        ig = IdentityGuard()
        assert ig is not None

    def test_strict(self):
        ig = IdentityGuard(expected_author="assistant", strict=True)
        assert ig is not None

    def test_template_authors(self):
        ig = IdentityGuard(
            expected_author="assistant",
            template_authors={"user", "system"},
            strict=False,
        )
        assert ig is not None


class TestFuseLevel:
    def test_values(self):
        for fl in FuseLevel:
            assert isinstance(fl.value, (int, str))


class TestFuseState:
    def test_create(self):
        fs = FuseState(level=FuseLevel.L0_PHYSICAL)
        assert fs.level == FuseLevel.L0_PHYSICAL
        assert fs.tripped is False
        assert fs.trip_count == 0

    def test_tripped(self):
        fs = FuseState(level=FuseLevel.L2_MEANING, tripped=True, trip_count=3, total_blocked=100)
        assert fs.tripped is True
        assert fs.trip_count == 3
        assert fs.total_blocked == 100


class TestHeatTaxFuseGroup:
    def test_create(self):
        htg = HeatTaxFuseGroup()
        assert htg is not None
        assert htg.alpha == 0.001
        assert htg.beta == 1.0
        assert htg.gamma == 1000.0

    def test_custom(self):
        l0 = FuseState(level=FuseLevel.L0_PHYSICAL, tripped=False)
        l1 = FuseState(level=FuseLevel.L1_LOGICAL, tripped=True)
        l2 = FuseState(level=FuseLevel.L2_MEANING, tripped=False)
        htg = HeatTaxFuseGroup(
            l0=l0, l1=l1, l2=l2,
            alpha=0.01, beta=2.0, gamma=500.0,
            l0_threshold=0.9, l1_threshold=0.6, l2_threshold=0.3,
            delta_min=0.1,
        )
        assert htg is not None


class TestLayeringLinter:
    def test_create(self):
        ll = LayeringLinter()
        assert ll is not None

    def test_with_root(self):
        ll = LayeringLinter(project_root="/my/project")
        assert ll is not None
