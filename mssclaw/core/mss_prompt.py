#!/usr/bin/env python3
"""
MSS Prompt — first-class typed object with heat tax + delta semantics.
Architecture inspired by LLLM's Prompt (template+parser+tools+handlers),
extended with MSS meaning conservation fields.

Usage:
    p = MSSPrompt(
        path="code_review/system",
        template="Review {target} for stability violations.",
        parser=MSSParser(xml_tags=["violations", "score"]),
        tools=[get_defer_guard_status],
        heat_tax_budget=0.3,       # A3: max heat tax this prompt is allowed
        delta_min=0.5,             # Δ: minimum openness the output must maintain
        normative_constraints=["no_bare_except_pass"],  # H628: stable subset
    )
    rendered = p(target="mssclaw/core/pipeline.py")
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional
import re


@dataclass
class MSSParser:
    """Output parser with MSS validation — maps to LLLM's DefaultTagParser."""
    xml_tags: List[str] = field(default_factory=list)
    required_xml_tags: List[str] = field(default_factory=list)
    md_tags: List[str] = field(default_factory=list)
    signal_tags: List[str] = field(default_factory=list)
    min_confidence: float = 0.0

    def parse(self, raw: str) -> Dict[str, Any]:
        result: Dict[str, Any] = {"raw": raw, "xml_tags": {}, "md_tags": {}, "signal_tags": {}}
        # Parse XML tags
        for tag in self.xml_tags:
            m = re.search(rf"<{tag}>(.*?)</{tag}>", raw, re.DOTALL)
            if m:
                result["xml_tags"][tag] = [m.group(1).strip()]
        # Parse markdown code blocks
        for tag in self.md_tags:
            m = re.search(rf"```{tag}\n(.*?)```", raw, re.DOTALL)
            if m:
                result["md_tags"][tag] = [m.group(1).strip()]
        # Validate required
        for req_tag in self.required_xml_tags:
            if req_tag not in result["xml_tags"]:
                result.setdefault("errors", []).append(f"Missing required tag: <{req_tag}>")
        return result

    def validate(self, raw: str) -> List[str]:
        """Return list of missing required tags."""
        errors = []
        for req in self.required_xml_tags:
            if not re.search(rf"<{req}>", raw):
                errors.append(req)
        return errors


@dataclass
class MSSPrompt:
    """
    MSS Prompt — like LLLM's Prompt but with meaning conservation.

    maps to LLLM: Prompt(path, prompt, parser, on_exception, on_interrupt)
    extends with:   heat_tax_budget, delta_min, normative_constraints
    """
    path: str
    template: str
    parser: Optional[MSSParser] = None
    tools: List[Callable] = field(default_factory=list)

    # ─── MSS extensions ───────────────────────────────────────
    heat_tax_budget: float = 0.3      # A3: max allowed heat tax for this prompt
    delta_min: float = 0.5            # Δ: minimum openness threshold
    normative_constraints: List[str] = field(default_factory=list)
    description: str = ""

    # ─── LLLM-compatible fields ───────────────────────────────
    on_exception: Optional[str] = None  # fallback prompt on parse failure
    on_interrupt: Optional[str] = None  # fallback prompt on tool interrupt
    max_retries: int = 3

    def __call__(self, **template_args) -> str:
        """Render template with variable substitution. (LLLM-compatible)"""
        try:
            return self.template.format(**template_args)
        except KeyError as e:
            missing = str(e).strip("'")
            raise ValueError(
                f"Prompt '{self.path}' missing template variable: {missing}. "
                f"Available: {self.template_vars}"
            )

    @property
    def template_vars(self) -> set:
        """Return set of expected {variable} names."""
        return set(re.findall(r"\{(\w+)\}", self.template))

    def validate_args(self, args: Dict[str, Any]) -> List[str]:
        """Return list of missing template variables."""
        return [v for v in self.template_vars if v not in args]

    def can_execute(self, current_heat_tax: float, current_delta: float) -> tuple:
        """
        Check if prompt can execute within meaning constraints.

        Returns (can_execute: bool, reason: str).
        H648 Defer Guard pattern: blocks execution if constraints violated.
        """
        if current_heat_tax >= self.heat_tax_budget:
            return False, (
                f"Heat tax {current_heat_tax:.2f} >= budget {self.heat_tax_budget:.2f}. "
                f"Suggestion: reduce tool usage or simplify prompt."
            )
        if current_delta < self.delta_min:
            return False, (
                f"Delta {current_delta:.2f} < minimum {self.delta_min:.2f}. "
                f"Suggestion: introduce new information to increase openness."
            )
        return True, "OK"


# ─── Demo ─────────────────────────────────────────────────────

if __name__ == "__main__":
    # Minimal usage
    p = MSSPrompt(
        path="greet/system",
        template="Analyze {target} and return findings in <violations> and <score> tags.",
        parser=MSSParser(
            xml_tags=["violations", "score"],
            required_xml_tags=["violations"],
        ),
        heat_tax_budget=0.3,
        delta_min=0.5,
        normative_constraints=["no_bare_except_pass"],
    )

    rendered = p(target="mssclaw/core/pipeline.py")
    print(f"Rendered ({len(rendered)} chars):")
    print(f"  {rendered[:80]}...")
    print(f"  Template vars: {p.template_vars}")
    print(f"  Missing if only {{target}}: {p.validate_args({'target': 'test.py'})}")
    print(f"  Missing if empty: {p.validate_args({})}")

    ok, reason = p.can_execute(current_heat_tax=0.1, current_delta=0.7)
    print(f"  Defer check (low tax, high delta): {ok} ({reason})")

    blocked, reason = p.can_execute(current_heat_tax=0.35, current_delta=0.3)
    print(f"  Defer check (budget exceeded): {blocked} ({reason})")

    # Parse test
    raw_output = "<violations>3 found: unsafe subprocess, hardcoded path, missing lock</violations><score>0.4</score>"
    parsed = p.parser.parse(raw_output)
    print(f"  Parsed: {parsed}")
    print(f"  Validation errors: {p.parser.validate(raw_output)}")
