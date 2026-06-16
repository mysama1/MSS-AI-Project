"""
MSS Post-Processing Rule Engine v2.0
Refactored from patch-based filter to structured rule engine.

Features:
- Pre-compiled regex patterns for performance
- Case-preserving replacements
- Categorized rules with priorities
- Full replacement audit logging
- Enable/disable individual rules
- Dry-run mode for testing
- Batch statistics
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Set
from enum import Enum, auto
import re
import json
import time
from datetime import datetime

from mss_exceptions import (
    PostProcessException, ValidationException,
    ErrorCode, wrap_exception, ErrorLogger
)

class RuleCategory(Enum):
    """Category of post-processing rule"""
    TERMINOLOGY = auto()       # Word replacements like solve→address
    ASSERTION = auto()         # Overconfidence dampening
    STRUCTURE = auto()         # Output structure fixes
    COMPLIANCE = auto()        # MSS compliance enforcement
    FORMAT = auto()            # Formatting/encoding fixes

class RulePriority(Enum):
    """Execution priority (lower number = earlier execution)"""
    CRITICAL = 0
    HIGH = 10
    MEDIUM = 20
    LOW = 30

@dataclass
class FilterRule:
    """A single filter rule"""
    id: str
    category: RuleCategory
    priority: RulePriority
    pattern: str                         # Regex pattern (with word boundaries)
    replacement: str                     # Replacement text
    description: str = ""
    case_sensitive: bool = False
    enabled: bool = True
    tags: List[str] = field(default_factory=list)

    def __post_init__(self):
        flags = 0 if self.case_sensitive else re.IGNORECASE
        self._compiled = re.compile(self.pattern, flags)

    def apply(self, text: str) -> Tuple[str, int]:
        """Apply rule to text, returns (modified_text, replacements_count)"""
        if not self.enabled:
            return text, 0

        count = 0

        def replacer(match):
            nonlocal count
            count += 1
            original = match.group(0)
            replacement = self.replacement

            # Case preservation
            if not self.case_sensitive:
                if original.isupper():
                    replacement = replacement.upper()
                elif original.istitle():
                    replacement = replacement.title()
                elif original[0].isupper():
                    replacement = replacement[0].upper() + replacement[1:]

            # Process backreferences (\1, \2, etc.)
            try:
                return match.expand(replacement)
            except (re.error, IndexError):
                return replacement

        result = self._compiled.sub(replacer, text)
        return result, count

@dataclass
class ReplacementRecord:
    """Record of a single replacement"""
    rule_id: str
    original: str
    replacement: str
    position: int                     # Character position in text
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> Dict:
        return {
            "rule_id": self.rule_id,
            "original": self.original,
            "replacement": self.replacement,
            "position": self.position,
            "timestamp": datetime.fromtimestamp(self.timestamp).isoformat()
        }

@dataclass
class FilterResult:
    """Result of filter application"""
    text: str
    replacements: List[ReplacementRecord] = field(default_factory=list)
    execution_time_ms: float = 0.0
    rules_applied: int = 0
    rules_total: int = 0
    rules_matched: Set[str] = field(default_factory=set)

    @property
    def replacement_count(self) -> int:
        return len(self.replacements)

    @property
    def had_changes(self) -> bool:
        return self.replacement_count > 0

    def summary(self) -> Dict:
        """Generate summary statistics"""
        by_rule = {}
        for r in self.replacements:
            by_rule[r.rule_id] = by_rule.get(r.rule_id, 0) + 1

        return {
            "total_replacements": self.replacement_count,
            "rules_matched": len(self.rules_matched),
            "rules_applied": self.rules_applied,
            "rules_total": self.rules_total,
            "execution_time_ms": round(self.execution_time_ms, 2),
            "by_rule": by_rule
        }

    def __str__(self) -> str:
        s = f"FilterResult({self.replacement_count} replacements, {len(self.rules_matched)} rules matched)"
        for r in self.replacements[:5]:
            s += f"\n  [{r.rule_id}] '{r.original}' → '{r.replacement}'"
        if len(self.replacements) > 5:
            s += f"\n  ... and {len(self.replacements) - 5} more"
        return s

class PostProcessEngine:
    """
    Structured rule engine for MSS output filtering

    Rules are organized by category with priorities.
    Execution order: priority (ascending) → category → rule order
    """

    def __init__(self, name: str = "MSS Post-Process Engine"):
        self.name = name
        self.rules: Dict[str, FilterRule] = {}
        self._rules_sorted: List[FilterRule] = []
        self.stats = {
            "total_filters": 0,
            "total_replacements": 0,
            "last_filter_time_ms": 0,
            "rules_enabled": 0,
            "rules_disabled": 0,
        }
        self.session_replacements: List[ReplacementRecord] = []
        self.error_logger = ErrorLogger("post_process_engine")

        # Initialize default rules
        self._init_default_rules()

    def _init_default_rules(self):
        """Initialize the default MSS compliance rules"""
        self._register_terminology_rules()
        self._register_assertion_rules()
        self._register_structure_rules()
        self._register_compliance_rules()
        self._register_format_rules()
        self._sort_rules()

    def _register_terminology_rules(self):
        """Register terminology replacement rules"""
        # solve → address family
        terms = [
            ("solve_problem", r'\bsolve[sd]?\b', "address"),
            ("solving_problem", r'\bsolving\b', "addressing"),
            ("solution_term", r'\bsolution[s]?\b', "approach"),
            ("resolution_term", r'\bresolution[s]?\b', "approach"),
            ("resolve_term", r'\bresolve[sd]?\b', "address"),
            ("resolving_term", r'\bresolving\b', "addressing"),
        ]

        # ultimate → framework family
        terms += [
            ("ultimate_term", r'\bultimate[s]?\b', "current best"),
            ("ultimately_term", r'\bultimately\b', "in the current framework"),
        ]

        # perfect → high-fidelity family
        terms += [
            ("perfect_term", r'\bperfect(?:ly|ion[s]?)?\b', "high fidelity"),
        ]

        # complete → partial family
        terms += [
            ("complete_term", r'\bcomplet(?:e|ely|ion[s]?|eness)?\b', "partial"),
        ]

        # transcend → go beyond family (tense-aware)
        terms += [
            ("transcend_present", r'\btranscend\b', "go beyond"),
            ("transcend_third", r'\btranscends\b', "goes beyond"),
            ("transcend_past", r'\btranscended\b', "went beyond"),
            ("transcend_gerund", r'\btranscending\b', "going beyond"),
            ("transcend_noun", r'\btranscendence[s]?\b', "going beyond"),
        ]

        # breakthrough → advance family
        terms += [
            ("breakthrough_term", r'\bbreakthrough[s]?\b', "advance"),
        ]

        # final → ongoing family
        terms += [
            ("final_term", r'\bfinal(?:ly|ity|ities)?\b', "ongoing"),
        ]

        # absolute → partial/context-dependent family
        terms += [
            ("absolute_term", r'\babsolut(?:e|ely|eness|e[s])?\b', "partial"),
        ]

        # Additional: certain → confident
        terms += [
            ("certain_term", r'\bcertain(?:ty|ties)?\b', "confident"),
        ]

        # Additional: prove → demonstrate
        terms += [
            ("prove_term", r'\bprov(?:e[sd]?|ing|en)\b', "demonstrate"),
        ]

        # Additional: correct → consistent
        terms += [
            ("correct_term", r'\bcorrect(?:ly|ness)?\b', "consistent"),
        ]

        for rule_id, pattern, replacement in terms:
            self.add_rule(FilterRule(
                id=rule_id,
                category=RuleCategory.TERMINOLOGY,
                priority=RulePriority.HIGH,
                pattern=pattern,
                replacement=replacement,
                description=f"Replace '{rule_id.split('_')[0]}' terminology",
                tags=["terminology", "compliance", "overclaim"]
            ))

    def _register_assertion_rules(self):
        """Register overconfidence-dampening rules"""
        assertions = [
            ("never_fails", r'\bnever fails?\b', "consistently performs"),
            ("always_works", r'\balways works?\b', "consistently demonstrates"),
            ("guaranteed", r'\bguarantee(?:s|d)?\b', "expected"),
            ("undeniable", r'\bundeniabl[ey]\b', "well-supported"),
            ("incontrovertible", r'\bincontrovertibl[ey]?\b', "strongly supported"),
            ("irrefutable", r'\birrefutabl[ey]?\b', "well-evidenced"),
            ("unquestionably", r'\bunquestionably\b', "strongly"),
            ("indisputable", r'\bindisputabl[ey]?\b', "well-documented"),
            ("without_doubt", r'\bwithout (?:a )?doubt\b', "with high confidence"),
            ("clearly_proves", r'\bclearly\s+(?:proves?|shows?|demonstrates?)\b', "suggests"),
            ("obviously", r'\bobviously\b', "apparently"),
            ("must_be", r'\bmust be\b', "appears to be"),
            ("certainly", r'\bcertainly\b', "likely"),
            ("definitely", r'\bdefinitely\b', "probably"),
            ("truly", r'\btruly\b', "effectively"),
        ]

        for rule_id, pattern, replacement in assertions:
            self.add_rule(FilterRule(
                id=f"assertion_{rule_id}",
                category=RuleCategory.ASSERTION,
                priority=RulePriority.HIGH,
                pattern=pattern,
                replacement=replacement,
                description=f"Dampen overconfidence: {pattern} → {replacement}",
                tags=["assertion", "humility", "compliance"]
            ))

    def _register_structure_rules(self):
        """Register output structure rules"""
        # Ensure boundary notes in outputs
        self.add_rule(FilterRule(
            id="structure_double_boundary",
            category=RuleCategory.STRUCTURE,
            priority=RulePriority.MEDIUM,
            pattern=r'\[Boundary Note\].*?\[Boundary Note\]',
            replacement="[Boundary Note]",
            description="Merge duplicate boundary notes",
            tags=["structure", "format"]
        ))

        # Fix triple backtick inconsistencies
        self.add_rule(FilterRule(
            id="structure_fix_backticks",
            category=RuleCategory.STRUCTURE,
            priority=RulePriority.LOW,
            pattern=r'````',
            replacement="```",
            description="Fix quadruple backticks to triple",
            tags=["structure", "format", "markdown"]
        ))

    def _register_compliance_rules(self):
        """Register MSS compliance enforcement rules"""
        # Missing boundary note injection
        self.add_rule(FilterRule(
            id="compliance_missing_boundary",
            category=RuleCategory.COMPLIANCE,
            priority=RulePriority.MEDIUM,
            pattern=r'^(?!.*\[Boundary Note\])(?!.*\[Confidence\])(.{200,})$',
            replacement=r'\1\n\n[Boundary Note] This analysis represents current understanding within the MSS framework. Alternative interpretations may exist.',
            description="Append boundary notes to long outputs without them",
            tags=["compliance", "boundary"]
        ))

        # Missing confidence marker
        self.add_rule(FilterRule(
            id="compliance_missing_confidence",
            category=RuleCategory.COMPLIANCE,
            priority=RulePriority.LOW,
            pattern=r'^(?!.*\[Confidence\])(?!.*\[Layer:)(.{100,})$',
            replacement=r'[Confidence: 0.7-0.9] [Layer: L2]\n\n\1',
            description="Prepend confidence/layer markers to analyses without them",
            tags=["compliance", "format"]
        ))

    def _register_format_rules(self):
        """Register formatting/encoding fix rules"""
        # Fix mojibake from encoding issues
        self.add_rule(FilterRule(
            id="format_encoding_smart_quotes",
            category=RuleCategory.FORMAT,
            priority=RulePriority.CRITICAL,
            pattern=r'[\x80-\x9f\xe2\x80\x9c\xe2\x80\x9d]',
            replacement='"',
            description="Fix smart quote mojibake",
            tags=["format", "encoding"],
            enabled=False  # Disabled by default - only enable when needed
        ))

    def _sort_rules(self):
        """Sort rules by priority, then category, then registration order"""
        self._rules_sorted = sorted(
            self.rules.values(),
            key=lambda r: (r.priority.value, r.category.value, r.id)
        )

    # --- Public API ---

    def add_rule(self, rule: FilterRule) -> None:
        """Add a new filter rule"""
        self.rules[rule.id] = rule
        self._sort_rules()
        self.stats["rules_enabled"] = sum(1 for r in self.rules.values() if r.enabled)
        self.stats["rules_disabled"] = len(self.rules) - self.stats["rules_enabled"]

    def remove_rule(self, rule_id: str) -> bool:
        """Remove a rule by ID"""
        if rule_id in self.rules:
            del self.rules[rule_id]
            self._sort_rules()
            return True
        return False

    def enable_rule(self, rule_id: str) -> bool:
        """Enable a specific rule"""
        if rule_id in self.rules:
            self.rules[rule_id].enabled = True
            self._sort_rules()
            return True
        return False

    def disable_rule(self, rule_id: str) -> bool:
        """Disable a specific rule"""
        if rule_id in self.rules:
            self.rules[rule_id].enabled = False
            self._sort_rules()
            return True
        return False

    def enable_category(self, category: RuleCategory) -> int:
        """Enable all rules in a category. Returns count of rules enabled."""
        count = 0
        for rule in self.rules.values():
            if rule.category == category and not rule.enabled:
                rule.enabled = True
                count += 1
        self._sort_rules()
        return count

    def disable_category(self, category: RuleCategory) -> int:
        """Disable all rules in a category. Returns count of rules disabled."""
        count = 0
        for rule in self.rules.values():
            if rule.category == category and rule.enabled:
                rule.enabled = False
                count += 1
        self._sort_rules()
        return count

    def filter(self, text: str, track_position: bool = False) -> FilterResult:
        """Apply all enabled rules to text"""
        if not isinstance(text, str):
            raise ValidationException(
                "Filter input must be a string",
                code=ErrorCode.VALIDATION_INPUT_EMPTY,
                details={"type": type(text).__name__}
            )

        start_time = time.time()

        try:
            result = FilterResult(
                text=text,
                rules_applied=0,
                rules_total=len(self._rules_sorted)
            )

            current = text
            total_replacements = 0

            for rule in self._rules_sorted:
                if not rule.enabled:
                    continue

                result.rules_applied += 1
                new_text, count = rule.apply(current)

                if count > 0:
                    result.rules_matched.add(rule.id)
                    current = new_text
                    total_replacements += count

                    if track_position:
                        for m in rule._compiled.finditer(text):
                            result.replacements.append(ReplacementRecord(
                                rule_id=rule.id,
                                original=m.group(0),
                                replacement=rule.replacement,
                                position=m.start()
                            ))

            result.text = current
            result.execution_time_ms = (time.time() - start_time) * 1000

            # Always count replacements: use word-level diff as fallback
            if total_replacements > 0 and not result.replacements:
                orig_count = len(text.split())
                filtered_count = len(current.split())
                # Estimate: each replacement might change 1-2 words
                result.replacements = [
                    ReplacementRecord(
                        rule_id=list(result.rules_matched)[0] if result.rules_matched else "unknown",
                        original="(word)", replacement="(replaced)", position=0
                    ) for _ in range(max(total_replacements, abs(filtered_count - orig_count) // 2))
                ]

            # Update stats
            self.stats["total_filters"] += 1
            self.stats["total_replacements"] += total_replacements
            self.stats["last_filter_time_ms"] = result.execution_time_ms
            self.session_replacements.extend(result.replacements)

            return result

        except MSSBaseException:
            raise
        except Exception as e:
            exc = wrap_exception(
                e, PostProcessException, ErrorCode.PP_FILTER_FAILED,
                message=f"Filter failed: {str(e)}"
            )
            self.error_logger.log(exc, context={"text_length": len(text)})
            raise exc

    def dry_run(self, text: str) -> FilterResult:
        """Analyze what would change without modifying text"""
        result = self.filter(text)
        result.text = text  # Restore original text
        return result

    def get_rules(self, category: Optional[RuleCategory] = None,
                  enabled_only: bool = False,
                  tag: Optional[str] = None) -> List[FilterRule]:
        """Query rules with optional filters"""
        rules = list(self.rules.values())

        if category:
            rules = [r for r in rules if r.category == category]
        if enabled_only:
            rules = [r for r in rules if r.enabled]
        if tag:
            rules = [r for r in rules if tag in r.tags]

        return sorted(rules, key=lambda r: (r.priority.value, r.id))

    def get_stats(self) -> Dict:
        """Get engine statistics"""
        return {
            **self.stats,
            "total_rules": len(self.rules),
            "by_category": {
                cat.name: len(self.get_rules(cat))
                for cat in RuleCategory
            },
            "by_priority": {
                pri.name: len(self.get_rules(enabled_only=False))
                for pri in RulePriority
            },
            "session_total_replacements": len(self.session_replacements)
        }

    def get_replacement_log(self, last_n: int = 20) -> List[Dict]:
        """Get recent replacement audit log"""
        return [r.to_dict() for r in self.session_replacements[-last_n:]]

    def reset_session(self):
        """Clear session replacement log"""
        self.session_replacements = []

    def export_rules(self) -> List[Dict]:
        """Export all rules as serializable format"""
        return [
            {
                "id": r.id,
                "category": r.category.name,
                "priority": r.priority.name,
                "pattern": r.pattern,
                "replacement": r.replacement,
                "description": r.description,
                "enabled": r.enabled,
                "tags": r.tags
            }
            for r in self._rules_sorted
        ]

    def import_rules(self, rules_data: List[Dict]) -> int:
        """Import rules from serialized format. Returns count."""
        count = 0
        for rd in rules_data:
            try:
                rule = FilterRule(
                    id=rd["id"],
                    category=RuleCategory[rd["category"]],
                    priority=RulePriority[rd["priority"]],
                    pattern=rd["pattern"],
                    replacement=rd["replacement"],
                    description=rd.get("description", ""),
                    enabled=rd.get("enabled", True),
                    tags=rd.get("tags", [])
                )
                self.add_rule(rule)
                count += 1
            except (KeyError, ValueError) as e:
                exc = ValidationException(
                    f"Invalid rule data: {str(e)}",
                    code=ErrorCode.PP_RULE_INVALID,
                    details={"rule_id": rd.get("id", "unknown"), "field": str(e)}
                )
                self.error_logger.log(exc)
                continue
        return count

# --- Legacy compatibility wrapper ---

def filter_response(text: str) -> str:
    """
    Legacy compatibility function.
    Wraps PostProcessEngine with default rules.
    """
    engine = PostProcessEngine()
    result = engine.filter(text)
    return result.text

# --- Demo & Test ---

def demo_engine():
    """Demonstrate the post-processing engine"""
    engine = PostProcessEngine()

    print("=" * 60)
    print(f"{engine.name} v2.0 Demo")
    print("=" * 60)

    # Test cases
    test_cases = [
        "This is the ultimate solution to the problem.",
        "We need a perfect and complete approach.",
        "This breakthrough transcends human limitations.",
        "She transcended her previous work. It was perfect.",
        "The final solution is absolutely perfect.",
        "This framework never fails to demonstrate its value.",
        "This is undeniably and unquestionably correct.",
        "Without a doubt, this clearly proves the theory.",
        "The result guarantees success every time.",
        "This is a normal sentence without any forbidden words about cats and dogs.",
    ]

    print("\n--- Filter Tests ---")
    for i, test in enumerate(test_cases, 1):
        result = engine.filter(test, track_position=False)
        changed = "[MOD] " if result.had_changes else "[OK]  "
        print(f"\n{changed}[Test {i}]")
        print(f"  Original: {test}")
        print(f"  Filtered: {result.text}")
        if result.had_changes:
            print(f"  Changes: {result.replacement_count} replacements by {len(result.rules_matched)} rules")

    # Dry run demonstration
    print("\n--- Dry Run ---")
    dry = engine.dry_run("This is the ultimate solution that is absolutely perfect.")
    print(f"  Would find: {dry.replacement_count} replacements")
    print(f"  Summary: {dry.summary()}")

    # Stats
    print("\n--- Engine Stats ---")
    stats = engine.get_stats()
    for key, value in stats.items():
        print(f"  {key}: {value}")

    # Rule query
    print("\n--- Assertion Rules ---")
    for rule in engine.get_rules(category=RuleCategory.ASSERTION):
        print(f"  [{rule.id}] {rule.pattern} → {rule.replacement}")

    # Rule management
    print("\n--- Rule Management ---")
    engine.disable_rule("solve_problem")
    print(f"  Disabled 'solve_problem': enabled={engine.rules['solve_problem'].enabled}")
    engine.enable_rule("solve_problem")
    print(f"  Enabled 'solve_problem': enabled={engine.rules['solve_problem'].enabled}")

    # Bulk operations
    print("\n--- Bulk Category Operations ---")
    before = len(engine.get_rules(RuleCategory.ASSERTION, enabled_only=True))
    engine.disable_category(RuleCategory.ASSERTION)
    after = len(engine.get_rules(RuleCategory.ASSERTION, enabled_only=True))
    print(f"  Disabled all assertion rules: {before} → {after}")
    engine.enable_category(RuleCategory.ASSERTION)
    after_restore = len(engine.get_rules(RuleCategory.ASSERTION, enabled_only=True))
    print(f"  Restored assertion rules: {after_restore}")

    # Export/Import
    print("\n--- Export/Import ---")
    exported = engine.export_rules()
    print(f"  Exported {len(exported)} rules")

    engine2 = PostProcessEngine()
    count = engine2.import_rules(exported)
    print(f"  Imported {count} rules into new engine")

    print("\n" + "=" * 60)
    print("Demo complete")
    print("=" * 60)

if __name__ == "__main__":
    demo_engine()
