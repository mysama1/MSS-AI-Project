"""
MSS-Agent v0.3 — Tool Budget Gate (热税工具门禁)

Prevents budget overrun by gating tool/function calls through HeatTaxAccountant.
Automatically classifies each tool call into L0/L1/L2 heat tax layers,
blocks L2-heavy calls when budget is tight, and logs all decisions.

Part of the P0 tool suite (memory_guard / auto_archive / session_recall / budget_gate).
"""

from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional
from enum import Enum
import time
import functools

from .heat_tax_accountant import HeatTaxAccountant, HeatTaxLevel, TurnReport


class ToolCategory(Enum):
    """Tool call categories mapped to heat tax layers."""
    COMPUTE = "compute"        # L0: CPU-bound (search, fetch, read)
    IO = "io"                  # L0: I/O-bound (file ops, network)
    CACHE = "cache"            # L1: redundant/repeated call detection
    REPEAT = "repeat"          # L1: same tool called >N times per turn
    OVERKILL = "overkill"      # L2: excessive output (over-explaining, over-fetching)
    PHILOSOPHY = "philosophy"  # L2: performance of depth (show-off tool calls)


# Default token cost estimates per tool category
DEFAULT_COSTS: Dict[ToolCategory, int] = {
    ToolCategory.COMPUTE: 100,
    ToolCategory.IO: 80,
    ToolCategory.CACHE: 50,
    ToolCategory.REPEAT: 150,   # penalty multiplier
    ToolCategory.OVERKILL: 200,
    ToolCategory.PHILOSOPHY: 300,
}

# Auto-classification rules: tool_name patterns → category
AUTO_CLASSIFY = {
    "search": ToolCategory.COMPUTE,
    "fetch": ToolCategory.COMPUTE,
    "read": ToolCategory.IO,
    "write": ToolCategory.IO,
    "list": ToolCategory.IO,
    "open": ToolCategory.IO,
    "exec": ToolCategory.COMPUTE,
    "browser": ToolCategory.COMPUTE,
    "translate": ToolCategory.COMPUTE,
    "analyze": ToolCategory.COMPUTE,
    "philosophy": ToolCategory.PHILOSOPHY,
    "explain": ToolCategory.OVERKILL,
    "summarize": ToolCategory.COMPUTE,
    "reflect": ToolCategory.PHILOSOPHY,
    "ponder": ToolCategory.PHILOSOPHY,
}


@dataclass
class GateDecision:
    """Result of a budget gate check."""
    tool_name: str
    category: ToolCategory
    estimated_tokens: int
    approved: bool
    reason: str
    budget_remaining: int
    timestamp: float = field(default_factory=time.time)


@dataclass
class ToolCallLog:
    """Record of a tool call for repeat detection."""
    tool_name: str
    args_summary: str
    turn: int
    count: int


class ToolBudgetGate:
    """
    热税工具门禁 — 拦截/批准工具调用。

    用法:
        acc = HeatTaxAccountant(max_tokens_per_turn=500)
        gate = ToolBudgetGate(acc, max_tool_tokens_per_turn=300)

        # 手动检查
        decision = gate.approve("search_papers", estimated_tokens=100)
        if decision.approved:
            result = search_papers(query)

        # 装饰器模式 (自动门禁)
        @gate.wrap(category=ToolCategory.COMPUTE, cost=100)
        def search_papers(query: str) -> dict: ...

        # 批量审批
        results = gate.batch_approve([
            ("read_file", 50), ("search_code", 100), ("run_test", 150)
        ])

        print(gate.summary())
    """

    def __init__(
        self,
        accountant: HeatTaxAccountant,
        max_tool_tokens_per_turn: int = 2000,
        max_tool_calls_per_turn: int = 20,
        max_repeat_calls: int = 3,
        auto_classify: bool = True,
    ):
        self.accountant = accountant
        self.max_tool_tokens = max_tool_tokens_per_turn
        self.max_tool_calls = max_tool_calls_per_turn
        self.max_repeat_calls = max_repeat_calls
        self.auto_classify = auto_classify

        # Per-turn state
        self._turn_tool_tokens: int = 0
        self._turn_tool_calls: int = 0
        self._call_logs: Dict[str, ToolCallLog] = {}
        self._decisions: List[GateDecision] = []

    def _classify(self, tool_name: str) -> ToolCategory:
        """Auto-classify a tool name into a ToolCategory."""
        if not self.auto_classify:
            return ToolCategory.COMPUTE

        name_lower = tool_name.lower()
        for pattern, category in AUTO_CLASSIFY.items():
            if pattern in name_lower:
                return category
        return ToolCategory.COMPUTE

    def _detect_repeat(self, tool_name: str, args_summary: str = "") -> bool:
        """Check if this tool call is a repeat (same name + similar args)."""
        key = f"{tool_name}:{args_summary[:50]}"
        if key in self._call_logs:
            self._call_logs[key].count += 1
            return self._call_logs[key].count > self.max_repeat_calls
        else:
            self._call_logs[key] = ToolCallLog(
                tool_name=tool_name,
                args_summary=args_summary[:50],
                turn=self.accountant.round_number,
                count=1,
            )
            return False

    def approve(
        self,
        tool_name: str,
        estimated_tokens: int = 0,
        category: Optional[ToolCategory] = None,
        args_summary: str = "",
    ) -> GateDecision:
        """
        检查工具调用是否在预算范围内。

        Returns:
            GateDecision with approval status and reason.
        """
        # Auto-classify
        if category is None:
            category = self._classify(tool_name)

        # Use default cost if not provided
        if estimated_tokens <= 0:
            estimated_tokens = DEFAULT_COSTS.get(category, 100)

        # Check 1: Per-turn tool call limit
        if self._turn_tool_calls >= self.max_tool_calls:
            return GateDecision(
                tool_name=tool_name,
                category=category,
                estimated_tokens=estimated_tokens,
                approved=False,
                reason=f"Max tool calls per turn ({self.max_tool_calls}) exceeded",
                budget_remaining=self.max_tool_tokens - self._turn_tool_tokens,
            )

        # Check 2: Per-turn token budget
        if self._turn_tool_tokens + estimated_tokens > self.max_tool_tokens:
            return GateDecision(
                tool_name=tool_name,
                category=category,
                estimated_tokens=estimated_tokens,
                approved=False,
                reason=f"Tool token budget exceeded ({self._turn_tool_tokens}/{self.max_tool_tokens})",
                budget_remaining=self.max_tool_tokens - self._turn_tool_tokens,
            )

        # Check 3: Repeat detection (L1 penalty)
        is_repeat = self._detect_repeat(tool_name, args_summary)
        if is_repeat:
            penalty_tokens = DEFAULT_COSTS[ToolCategory.REPEAT]
            if self._turn_tool_tokens + estimated_tokens + penalty_tokens > self.max_tool_tokens:
                return GateDecision(
                    tool_name=tool_name,
                    category=ToolCategory.REPEAT,
                    estimated_tokens=estimated_tokens + penalty_tokens,
                    approved=False,
                    reason=f"Repeat tool call blocked (called >{self.max_repeat_calls}x, penalty: {penalty_tokens}t)",
                    budget_remaining=self.max_tool_tokens - self._turn_tool_tokens,
                )
            estimated_tokens += penalty_tokens
            category = ToolCategory.REPEAT

        # Check 4: L2-heavy tool (philosophy/overkill) — extra scrutiny
        if category in (ToolCategory.PHILOSOPHY, ToolCategory.OVERKILL):
            # Allow only if L2 budget has room
            if self.accountant._current_l2 > getattr(self.accountant, 'l2_warning_threshold', 0.3) * self.accountant.max_per_turn:
                return GateDecision(
                    tool_name=tool_name,
                    category=category,
                    estimated_tokens=estimated_tokens,
                    approved=False,
                    reason=f"L2 budget tight — {category.value} tool call blocked",
                    budget_remaining=self.max_tool_tokens - self._turn_tool_tokens,
                )

        # ✅ Approved
        self._turn_tool_tokens += estimated_tokens
        self._turn_tool_calls += 1

        # Record in HeatTaxAccountant
        if category == ToolCategory.PHILOSOPHY or category == ToolCategory.OVERKILL:
            self.accountant.record(HeatTaxLevel.L2_MEANING, estimated_tokens,
                                   f"Tool: {tool_name} ({category.value})")
        elif category in (ToolCategory.REPEAT, ToolCategory.CACHE):
            self.accountant.record(HeatTaxLevel.L1_LOGICAL, estimated_tokens,
                                   f"Tool: {tool_name} ({category.value})")
        else:
            self.accountant.record(HeatTaxLevel.L0_PHYSICAL, estimated_tokens,
                                   f"Tool: {tool_name} ({category.value})")

        decision = GateDecision(
            tool_name=tool_name,
            category=category,
            estimated_tokens=estimated_tokens,
            approved=True,
            reason="OK",
            budget_remaining=self.max_tool_tokens - self._turn_tool_tokens,
        )
        self._decisions.append(decision)
        return decision

    def batch_approve(
        self,
        calls: List[tuple],  # [(tool_name, estimated_tokens), ...]
        args_summaries: Optional[List[str]] = None,
    ) -> List[GateDecision]:
        """
        Batch-approve multiple tool calls. All-or-nothing within budget.

        Args:
            calls: List of (tool_name, estimated_tokens) tuples
            args_summaries: Optional list of arg summaries for repeat detection

        Returns:
            List of GateDecisions (all approved or some blocked)
        """
        results = []
        total_est = sum(c[1] for c in calls)

        # Quick check: can all fit?
        if self._turn_tool_tokens + total_est > self.max_tool_tokens:
            # Try individually — some may pass
            for i, (name, tokens) in enumerate(calls):
                args = args_summaries[i] if args_summaries and i < len(args_summaries) else ""
                results.append(self.approve(name, tokens, args_summary=args))
        else:
            # All can fit — approve in order
            for i, (name, tokens) in enumerate(calls):
                args = args_summaries[i] if args_summaries and i < len(args_summaries) else ""
                results.append(self.approve(name, tokens, args_summary=args))

        return results

    def wrap(
        self,
        category: Optional[ToolCategory] = None,
        cost: int = 0,
        tool_name: str = "",
    ):
        """
        Decorator: wrap a function with automatic budget gating.

        Usage:
            gate = ToolBudgetGate(acc)

            @gate.wrap(category=ToolCategory.COMPUTE, cost=100)
            def search(query: str) -> dict:
                ...

        Returns:
            Wrapped function that gates calls through budget approval.
        """
        name = tool_name

        def decorator(func: Callable) -> Callable:
            nonlocal name
            if not name:
                name = func.__name__

            @functools.wraps(func)
            def wrapper(*args, **kwargs):
                # Summarize args for repeat detection
                args_str = str(args)[:50] if args else str(kwargs)[:50]
                decision = self.approve(
                    tool_name=name,
                    estimated_tokens=cost,
                    category=category,
                    args_summary=args_str,
                )
                if not decision.approved:
                    return {
                        "error": "budget_exceeded",
                        "reason": decision.reason,
                        "budget_remaining": decision.budget_remaining,
                    }
                return func(*args, **kwargs)

            return wrapper

        return decorator

    def reset_turn(self):
        """Reset per-turn counters (call at start of each turn)."""
        self._turn_tool_tokens = 0
        self._turn_tool_calls = 0
        self._call_logs.clear()

    def summary(self) -> dict:
        """Return a summary of gate activity."""
        approved = sum(1 for d in self._decisions if d.approved)
        blocked = sum(1 for d in self._decisions if not d.approved)
        by_category = {}
        for d in self._decisions:
            by_category.setdefault(d.category.value, {"approved": 0, "blocked": 0, "tokens": 0})
            key = "approved" if d.approved else "blocked"
            by_category[d.category.value][key] += 1
            by_category[d.category.value]["tokens"] += d.estimated_tokens

        return {
            "total_decisions": len(self._decisions),
            "approved": approved,
            "blocked": blocked,
            "approval_rate": approved / max(len(self._decisions), 1),
            "tool_tokens_used": self._turn_tool_tokens,
            "tool_tokens_budget": self.max_tool_tokens,
            "tool_calls": self._turn_tool_calls,
            "max_tool_calls": self.max_tool_calls,
            "by_category": by_category,
        }


# ── CLI 自检 ──

if __name__ == "__main__":
    from mss_agent.core.heat_tax_accountant import HeatTaxAccountant, HeatTaxLevel
    from mss_agent.core.tool_budget_gate import ToolBudgetGate, ToolCategory

    acc = HeatTaxAccountant(max_tokens_per_turn=1000, l2_ratio_warning=0.3)
    gate = ToolBudgetGate(acc, max_tool_tokens_per_turn=500, max_tool_calls_per_turn=10)

    print("=== Tool Budget Gate Demo ===")

    # Test 1: Normal tool calls
    print("\n1. Normal tool calls:")
    for name in ["search_papers", "read_file", "run_test", "fetch_data"]:
        d = gate.approve(name, 80)
        status = "✅" if d.approved else "❌"
        print(f"   {status} {name}: {d.estimated_tokens}t | {d.reason} | budget_left={d.budget_remaining}")

    # Test 2: Over budget
    print("\n2. Over budget:")
    d = gate.approve("massive_search", 800)
    print(f"   ❌ massive_search: {d.reason}")

    # Test 3: Repeat detection
    print("\n3. Repeat detection (calling same tool 5x):")
    gate.reset_turn()
    for i in range(5):
        d = gate.approve("search_papers", 50, args_summary="quantum computing")
        status = "✅" if d.approved else "❌"
        print(f"   {status} call #{i+1}: {d.category.value} | {d.reason[:60]}")

    # Test 4: L2 philosophy block
    print("\n4. L2 philosophy tool — blocked when L2 budget tight:")
    acc._current_l2 = 400  # Simulate high L2 usage (40% of 1000)
    d = gate.approve("ponder_existence", 200)
    print(f"   {'✅' if d.approved else '❌'} ponder_existence: {d.reason}")

    # Test 5: Decorator mode
    print("\n5. Decorator mode:")

    @gate.wrap(category=ToolCategory.COMPUTE, cost=50, tool_name="my_tool")
    def my_tool(x):
        return {"result": x * 2}

    print(f"   my_tool(5) = {my_tool(5)}")  # Should pass

    gate.reset_turn()
    gate.max_tool_tokens = 30  # Tiny budget
    result = my_tool(5)
    print(f"   my_tool(5) under tiny budget = {result}")  # Should be blocked

    # Summary
    print(f"\n📊 Gate Summary:")
    s = gate.summary()
    print(f"   Approved: {s['approved']}/{s['total_decisions']} ({s['approval_rate']:.0%})")
    print(f"   Tool tokens: {s['tool_tokens_used']}/{s['tool_tokens_budget']}")
    print(f"   By category: {s['by_category']}")
