#!/usr/bin/env python3
"""
MSS Approval Chain — multi-step gatekeeper for agent actions.

Inspired by OpenClaw's approval system (~15 modules):
- approval-request-filters → filter which actions need approval
- approval-auth → who is making the request
- approval-renderers → format for human review
- approval-handler → human decision (approve/deny)
- approval-forwarder → execute the approved action
- exec-approvals-allowlist → auto-approve safe actions

Differences from OpenClaw:
- Heat-tax-aware: high heat-tax actions auto-escalate
- Delta-aware: actions that would drop delta below threshold auto-block
- Trust budget: gradual instead of binary approve/deny
- No GUI — approval handlers are callables not UI renderers
"""

from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Callable, Dict, List, Optional, Set
import time


# ─── Data models ────────────────────────────────────────────

class ApprovalVerdict(Enum):
    APPROVED = auto()
    DENIED = auto()
    PENDING = auto()  # waiting for human
    AUTO_APPROVED = auto()  # allowlisted
    AUTO_DENIED = auto()  # safety filter caught it
    ESCALATED = auto()  # needs higher authority


class RiskLevel(Enum):
    NONE = 0       # no risk (reading a known file)
    LOW = 1        # low risk (calling a safe tool)
    MEDIUM = 2     # medium risk (calling an untrusted tool)
    HIGH = 3       # high risk (exec, network, file write)
    CRITICAL = 4   # critical (system command, destructive)


@dataclass
class ApprovalRequest:
    """An action that needs approval."""
    action: str
    target: str = ""
    args: Dict[str, Any] = field(default_factory=dict)
    risk: RiskLevel = RiskLevel.NONE
    heat_tax_estimate: float = 0.0
    delta_impact: float = 0.0  # estimated delta change
    trust_budget: float = 0.5
    requester: str = "unknown"


@dataclass
class ApprovalResult:
    verdict: ApprovalVerdict
    reason: str = ""
    by: str = "system"  # which component decided
    timestamp: float = field(default_factory=time.time)


# ─── Built-in filters ───────────────────────────────────────

def safety_filter(req: ApprovalRequest) -> Optional[ApprovalResult]:
    """First filter: block obviously dangerous actions.

    Like OpenClaw's dangerous-name-runtime + dangerous-tools.
    """
    DANGEROUS_PATTERNS = [
        "rm -rf", "format", "del /f", "drop table",
        "shutdown", "reboot", "chmod 777",
    ]
    # Check action + target + all args values
    combined = " ".join([req.action, req.target] + [str(v) for v in req.args.values()])
    action_lower = combined.lower()
    for pattern in DANGEROUS_PATTERNS:
        if pattern.lower() in action_lower:
            return ApprovalResult(ApprovalVerdict.AUTO_DENIED, f"Safety filter: blocked dangerous pattern '{pattern}'")
    return None


def heat_tax_filter(req: ApprovalRequest) -> Optional[ApprovalResult]:
    """Block actions with excessive heat tax."""
    if req.heat_tax_estimate > 0.5:
        return ApprovalResult(
            ApprovalVerdict.AUTO_DENIED,
            f"Heat tax {req.heat_tax_estimate:.2f} exceeds max 0.50"
        )
    if req.heat_tax_estimate > 0.2:
        return ApprovalResult(
            ApprovalVerdict.ESCALATED,
            f"Heat tax {req.heat_tax_estimate:.2f} requires escalation"
        )
    return None


def delta_filter(req: ApprovalRequest, delta_min: float = 0.5, delta_current: float = 0.7) -> Optional[ApprovalResult]:
    """Block actions that would drop delta below minimum."""
    if delta_current + req.delta_impact < delta_min:
        return ApprovalResult(
            ApprovalVerdict.AUTO_DENIED,
            f"Delta would drop to {delta_current + req.delta_impact:.2f} (min {delta_min:.2f})"
        )
    return None


def trust_budget_filter(req: ApprovalRequest) -> Optional[ApprovalResult]:
    """Auto-approve trusted agents, escalate low-trust ones."""
    if req.trust_budget >= 0.8:
        return ApprovalResult(ApprovalVerdict.AUTO_APPROVED, f"Trust budget {req.trust_budget:.2f} ≥ 0.80")
    if req.trust_budget < 0.3 and req.risk.value >= RiskLevel.MEDIUM.value:
        return ApprovalResult(
            ApprovalVerdict.ESCALATED,
            f"Low trust {req.trust_budget:.2f} + medium/high risk requires escalation"
        )
    return None


# ─── Approval Chain ─────────────────────────────────────────

class MSSApprovalChain:
    """Multi-step approval pipeline: filter → auth → human → execute.

    Usage:
        chain = MSSApprovalChain(allowlist={"vdp_scan", "benchmark"})
        chain.add_auto_filter(safety_filter)
        chain.set_human_handler(my_approval_ui)

        result = chain.process(ApprovalRequest(
            action="exec",
            target="rm -rf /tmp/cache",
            risk=RiskLevel.HIGH,
        ))
        if result.verdict in (ApprovalVerdict.APPROVED, ApprovalVerdict.AUTO_APPROVED):
            execute_command(...)
    """

    def __init__(
        self,
        allowlist: Optional[Set[str]] = None,
        delta_min: float = 0.5,
        delta_current: float = 0.7,
    ):
        self.allowlist: Set[str] = allowlist or set()
        self.delta_min = delta_min
        self.delta_current = delta_current
        self._auto_filters: List[Callable] = [
            safety_filter,
            heat_tax_filter,
        ]
        self._human_handler: Optional[Callable] = None
        self._executor: Optional[Callable] = None
        self._audit_log: List[ApprovalResult] = []

    def add_auto_filter(self, fn: Callable) -> None:
        """Add an automatic filter (no human needed)."""
        self._auto_filters.append(fn)

    def set_human_handler(self, fn: Callable) -> None:
        """Set handler for PENDING decisions."""
        self._human_handler = fn

    def set_executor(self, fn: Callable) -> None:
        """Set handler to actually execute approved actions."""
        self._executor = fn

    def process(self, req: ApprovalRequest) -> ApprovalResult:
        """Run the full approval chain on a request."""

        # Step 0: Allowlist check
        if req.action in self.allowlist:
            result = ApprovalResult(ApprovalVerdict.AUTO_APPROVED, f"Action '{req.action}' is allowlisted")
            self._audit_log.append(result)
            return result

        # Step 1: Auto-filters (safety, heat tax, etc.)
        for filter_fn in self._auto_filters:
            result = filter_fn(req)
            if result is not None:
                self._audit_log.append(result)
                return result

        # Step 1b: Delta filter (uses instance state)
        result = delta_filter(req, self.delta_min, self.delta_current)
        if result is not None:
            self._audit_log.append(result)
            return result

        # Step 1c: Trust budget filter
        result = trust_budget_filter(req)
        if result is not None:
            self._audit_log.append(result)
            return result

        # Step 2: Human decision if needed
        if req.risk.value >= RiskLevel.MEDIUM.value:
            if self._human_handler:
                result = self._human_handler(req)
                if result is not None:
                    self._audit_log.append(result)
                    return result
            return ApprovalResult(ApprovalVerdict.PENDING, f"Awaiting human approval for risk level {req.risk.name}")

        # Step 3: Approved
        result = ApprovalResult(ApprovalVerdict.APPROVED, "All filters passed")
        self._audit_log.append(result)
        return result

    def approve_pending(self, req: ApprovalRequest, approved: bool, reason: str = "") -> ApprovalResult:
        """Resolve a PENDING decision."""
        if self._executor and approved:
            self._executor(req)
        result = ApprovalResult(
            ApprovalVerdict.APPROVED if approved else ApprovalVerdict.DENIED,
            reason,
            "human",
        )
        self._audit_log.append(result)
        return result

    def audit_report(self) -> List[Dict[str, Any]]:
        return [
            {"verdict": r.verdict.name, "reason": r.reason, "by": r.by}
            for r in self._audit_log[-20:]
        ]


# ─── Demo ─────────────────────────────────────────────────────

if __name__ == "__main__":
    chain = MSSApprovalChain(
        allowlist={"list_files", "read_config"},
        delta_min=0.5,
        delta_current=0.7,
    )

    # Custom human handler (in real use, this would be UI)
    def cli_human(req: ApprovalRequest) -> Optional[ApprovalResult]:
        print(f"\n⚠️  {req.action}({req.target}) — risk: {req.risk.name}, heat: {req.heat_tax_estimate:.2f}")
        choice = input("Approve? (y/n): ").strip().lower()
        return ApprovalResult(
            ApprovalVerdict.APPROVED if choice == "y" else ApprovalVerdict.DENIED,
            f"User chose '{choice}'",
            "human",
        )

    chain.set_human_handler(cli_human)

    # Test cases
    for action, target, risk in [
        ("read_config", "config.json", RiskLevel.NONE),
        ("vdp_scan", "core.py", RiskLevel.LOW),
        ("exec", "rm -rf /tmp/cache", RiskLevel.HIGH),
        ("exec", "python analyze.py", RiskLevel.MEDIUM),
    ]:
        req = ApprovalRequest(action=action, target=target, risk=risk, heat_tax_estimate=0.05)
        result = chain.process(req)
        print(f"  {action}({target}) → {result.verdict.name}: {result.reason}")

    print(f"\nAudit: {chain.audit_report()}")
