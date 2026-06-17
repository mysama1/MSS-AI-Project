"""Tests for MSS Approval Chain."""
import pytest
from mssclaw.core.mss_approval_chain import (
    MSSApprovalChain,
    ApprovalRequest,
    ApprovalResult,
    ApprovalVerdict,
    RiskLevel,
    safety_filter,
    heat_tax_filter,
    delta_filter,
    trust_budget_filter,
)


class TestApprovalChain:
    def test_allowlisted_action(self):
        chain = MSSApprovalChain(allowlist={"read_config", "list_files"})
        req = ApprovalRequest(action="read_config", risk=RiskLevel.NONE)
        result = chain.process(req)
        assert result.verdict == ApprovalVerdict.AUTO_APPROVED

    def test_safety_filter_blocks_dangerous(self):
        req = ApprovalRequest(action="exec", target="rm -rf /tmp/data")
        result = safety_filter(req)
        assert result is not None
        assert result.verdict == ApprovalVerdict.AUTO_DENIED

    def test_safety_filter_blocks_sql_drop(self):
        req = ApprovalRequest(action="exec", target="DROP TABLE users")
        result = safety_filter(req)
        assert result is not None
        assert result.verdict == ApprovalVerdict.AUTO_DENIED

    def test_safety_filter_passes_safe(self):
        req = ApprovalRequest(action="list_files", target="./data")
        result = safety_filter(req)
        assert result is None

    def test_heat_tax_filter_blocks_excessive(self):
        req = ApprovalRequest(action="exec", heat_tax_estimate=0.6)
        result = heat_tax_filter(req)
        assert result is not None
        assert result.verdict == ApprovalVerdict.AUTO_DENIED

    def test_heat_tax_filter_escalates_medium(self):
        req = ApprovalRequest(action="exec", heat_tax_estimate=0.3)
        result = heat_tax_filter(req)
        assert result is not None
        assert result.verdict == ApprovalVerdict.ESCALATED

    def test_heat_tax_filter_passes_low(self):
        req = ApprovalRequest(action="read", heat_tax_estimate=0.05)
        result = heat_tax_filter(req)
        assert result is None

    def test_delta_filter_blocks(self):
        result = delta_filter(
            ApprovalRequest(action="exec", delta_impact=-0.3),
            delta_min=0.5,
            delta_current=0.6,
        )
        assert result is not None
        assert result.verdict == ApprovalVerdict.AUTO_DENIED

    def test_delta_filter_passes(self):
        result = delta_filter(
            ApprovalRequest(action="exec", delta_impact=-0.05),
            delta_min=0.5,
            delta_current=0.7,
        )
        assert result is None

    def test_trust_budget_auto_approve(self):
        req = ApprovalRequest(action="exec", trust_budget=0.9)
        result = trust_budget_filter(req)
        assert result is not None
        assert result.verdict == ApprovalVerdict.AUTO_APPROVED

    def test_trust_budget_escalate_low_risk(self):
        req = ApprovalRequest(action="exec", trust_budget=0.2, risk=RiskLevel.HIGH)
        result = trust_budget_filter(req)
        assert result is not None
        assert result.verdict == ApprovalVerdict.ESCALATED

    def test_full_chain_safe_action(self):
        chain = MSSApprovalChain()
        req = ApprovalRequest(action="list_files", risk=RiskLevel.NONE)
        result = chain.process(req)
        assert result.verdict in (ApprovalVerdict.APPROVED, ApprovalVerdict.AUTO_APPROVED)

    def test_full_chain_dangerous_action(self):
        chain = MSSApprovalChain()
        req = ApprovalRequest(action="exec", target="rm -rf /", risk=RiskLevel.HIGH, heat_tax_estimate=0.05)
        result = chain.process(req)
        assert result.verdict == ApprovalVerdict.AUTO_DENIED

    def test_approve_pending(self):
        chain = MSSApprovalChain()
        req = ApprovalRequest(action="exec", risk=RiskLevel.MEDIUM)
        result = chain.approve_pending(req, True, "looks safe")
        assert result.verdict == ApprovalVerdict.APPROVED
        assert result.by == "human"

    def test_audit_log(self):
        chain = MSSApprovalChain(allowlist={"safe"})
        chain.process(ApprovalRequest(action="safe", risk=RiskLevel.NONE))
        chain.process(ApprovalRequest(action="exec", target="rm -rf /", risk=RiskLevel.HIGH))
        report = chain.audit_report()
        assert len(report) >= 2

    def test_risk_level_values(self):
        assert RiskLevel.NONE.value < RiskLevel.LOW.value
        assert RiskLevel.HIGH.value < RiskLevel.CRITICAL.value

    def test_approval_result_fields(self):
        result = ApprovalResult(ApprovalVerdict.APPROVED, "test", "unit_test")
        assert result.verdict == ApprovalVerdict.APPROVED
        assert result.reason == "test"
        assert result.by == "unit_test"
