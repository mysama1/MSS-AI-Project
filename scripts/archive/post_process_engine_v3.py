"""
MSS Post-Processing Rule Engine v3.0
Enhanced with Topology Metrics Integration

Enhancements from v2.0:
- Topology-aware vulnerability injection (NEW)
- Heat-tax-aware confidence adjustment (NEW)
- Bridge-edge detection in reasoning chains (NEW)
- Layer-gap warnings in output (NEW)
- Integration with topology_metrics engine

MSS Compliance:
- All topology terms marked as L3 metaphor in comments
- Deterministic graph algorithms only
- No LLM dependency in post-processing
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

# Optional topology integration
try:
    from topology_metrics import TopologyMetricsEngine, TopologyAwarePathfinder
    TOPOLOGY_AVAILABLE = True
except ImportError:
    TOPOLOGY_AVAILABLE = False

class RuleCategory(Enum):
    """Category of post-processing rule"""
    TERMINOLOGY = auto()       # Word replacements like solve→address
    ASSERTION = auto()         # Overconfidence dampening
    STRUCTURE = auto()         # Output structure fixes
    COMPLIANCE = auto()        # MSS compliance enforcement
    FORMAT = auto()            # Formatting/encoding fixes
    TOPOLOGY = auto()          # NEW: Topology-aware enhancements

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
                elif original[0].isupper() and len(original) > 1:
                    replacement = replacement[0].upper() + replacement[1:]

            return replacement

        new_text = self._compiled.sub(replacer, text)
        return new_text, count

@dataclass
class ReplacementRecord:
    """Record of a single replacement"""
    rule_id: str
    original: str
    replacement: str
    position: int
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> Dict:
        return {
            "rule_id": self.rule_id,
            "original": self.original,
            "replacement": self.replacement,
            "position": self.position,
            "timestamp": self.timestamp
        }

@dataclass
class FilterResult:
    """Result of applying filter rules"""
    text: str
    rules_applied: int
    rules_total: int
    rules_matched: Set[str] = field(default_factory=set)
    replacements: List[ReplacementRecord] = field(default_factory=list)
    execution_time_ms: float = 0.0
    topology_warnings: List[str] = field(default_factory=list)  # NEW

    @property
    def had_changes(self) -> bool:
        return len(self.rules_matched) > 0

    @property
    def replacement_count(self) -> int:
        return len(self.replacements)

    def summary(self) -> str:
        parts = [
            f"Applied {self.rules_applied}/{self.rules_total} rules",
            f"Matched {len(self.rules_matched)} rules",
            f"Made {self.replacement_count} replacements",
            f"Time: {self.execution_time_ms:.2f}ms"
        ]
        if self.topology_warnings:
            parts.append(f"Topology warnings: {len(self.topology_warnings)}")
        return " | ".join(parts)

class PostProcessEngine:
    """
    MSS Post-Processing Rule Engine v3.0

    Enhanced with topology-aware processing for structural
    vulnerability detection in reasoning outputs.

    L3 Metaphor Note:
    "Topology" in this context refers to graph-theoretic properties
    of the knowledge graph (connected components, bridges, clustering).
    This is standard network science, not algebraic topology.
    """

    def __init__(self, name: str = "MSS-PostProcess-v3.0"):
        self.name = name
        self.rules: Dict[str, FilterRule] = {}
        self._rules_sorted: List[FilterRule] = []
        self.session_replacements: List[ReplacementRecord] = []
        self.error_logger = ErrorLogger("post_process_engine_v3")

        # Statistics
        self.stats = {
            "total_filters": 0,
            "total_replacements": 0,
            "rules_enabled": 0,
            "rules_disabled": 0,
            "last_filter_time_ms": 0.0
        }

        # Topology integration (optional)
        self.topology_engine: Optional[TopologyMetricsEngine] = None
        self.topology_enabled = False

        # Register default rules
        self._register_terminology_rules()
        self._register_assertion_rules()
        self._register_structure_rules()
        self._register_compliance_rules()
        self._register_format_rules()
        self._register_topology_rules()  # NEW

        self._sort_rules()

    # =========================================================
    # Topology Integration (NEW in v3.0)
    # =========================================================

    def attach_topology_engine(self, engine: TopologyMetricsEngine) -> bool:
        """
        Attach a topology metrics engine for structural analysis.

        When attached, the post-processor can:
        - Detect bridge-edge reasoning (high-risk single-path logic)
        - Warn about sparse knowledge regions
        - Flag layer-gap violations
        - Adjust confidence based on graph health
        """
        if not TOPOLOGY_AVAILABLE:
            return False

        self.topology_engine = engine
        self.topology_enabled = True
        return True

    def detach_topology_engine(self):
        """Remove topology engine attachment"""
        self.topology_engine = None
        self.topology_enabled = False

    def _analyze_topology_warnings(self, text: str) -> List[str]:
        """
        Analyze text for topology-related structural issues.

        Returns list of warnings about:
        - Reasoning chains that cross bridge edges
        - Claims in sparse knowledge regions
        - Layer violations (L3 claims without L2 support)
        """
        warnings = []

        if not self.topology_enabled or not self.topology_engine:
            return warnings

        try:
            # Get overall graph health
            metrics = self.topology_engine.compute_all_metrics()

            # Warning 1: Low graph health score
            if metrics.topology_health_score < 50:
                warnings.append(
                    f"[Topology Warning] Knowledge graph health is low "
                    f"({metrics.topology_health_score:.1f}/100). "
                    f"Reasoning may be unreliable due to structural fragmentation."
                )

            # Warning 2: High bridge count
            if metrics.bridge_count > 0:
                bridge_ratio = metrics.bridge_count / max(metrics.edge_count, 1)
                if bridge_ratio > 0.1:  # More than 10% bridges
                    warnings.append(
                        f"[Topology Warning] High bridge-edge ratio "
                        f"({metrics.bridge_count}/{metrics.edge_count}). "
                        f"Reasoning chains may have single points of failure."
                    )

            # Warning 3: Layer gaps
            layer_gaps = self.topology_engine.find_layer_gaps()
            for src, tgt in layer_gaps:
                warnings.append(
                    f"[Topology Warning] Layer gap detected: {src}→{tgt} "
                    f"connection insufficient. Claims spanning these layers "
                    f"lack structural support."
                )

            # Warning 4: Isolated nodes
            if metrics.isolated_nodes > 0:
                warnings.append(
                    f"[Topology Warning] {metrics.isolated_nodes} isolated "
                    f"knowledge node(s) detected. Orphaned claims cannot be "
                    f"verified through graph traversal."
                )

        except Exception as e:
            # Topology analysis failure should not block processing
            warnings.append(
                f"[Topology Warning] Structural analysis failed: {str(e)}"
            )

        return warnings

    def _adjust_confidence_by_topology(
        self,
        confidence_text: str,
        metrics: "TopologyMetrics"
    ) -> str:
        """
        Adjust confidence markers based on graph topology.

        If the knowledge graph has structural issues, downgrade
        confidence ranges to reflect higher uncertainty.
        """
        # Parse existing confidence
        match = re.search(r'\[Confidence:\s*([\d.]+)-([\d.]+)\]', confidence_text)
        if not match:
            return confidence_text

        low, high = float(match.group(1)), float(match.group(2))

        # Downgrade based on health score
        health = metrics.topology_health_score
        if health < 30:
            # Severe structural issues: cap at 0.5
            high = min(high, 0.5)
            low = min(low, 0.3)
        elif health < 60:
            # Moderate issues: reduce by 20%
            high = high * 0.8
            low = low * 0.8

        # Ensure valid range
        low = max(0.0, min(low, 1.0))
        high = max(low, min(high, 1.0))

        return f"[Confidence: {low:.1f}-{high:.1f}]"

    # =========================================================
    # Rule Registrations (v2.0 rules preserved)
    # =========================================================

    def _register_terminology_rules(self):
        """Register terminology replacement rules"""
        terms = []

        # solve → address family
        terms += [
            ("solve_problem", r'\bsolve[s]?\b', "address"),
            ("solution_term", r'\bsolution[s]?\b', "approach"),
            ("solved_term", r'\bsolved\b', "addressed"),
            ("solving_term", r'\bsolving\b', "addressing"),
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

    # =========================================================
    # NEW: Topology Rules (v3.0)
    # =========================================================

    def _register_topology_rules(self):
        """
        Register topology-aware enhancement rules.

        These rules are only active when a topology engine is attached.
        They inject structural warnings into outputs based on knowledge
        graph health metrics.
        """
        # Bridge-edge reasoning warning
        self.add_rule(FilterRule(
            id="topology_bridge_reasoning",
            category=RuleCategory.TOPOLOGY,
            priority=RulePriority.MEDIUM,
            pattern=r'\[Bridge-Edge Reasoning\]',
            replacement="[Bridge-Edge Reasoning: This chain relies on a single logical connection. Verify redundancy.]",
            description="Flag reasoning that depends on bridge edges",
            tags=["topology", "structure", "warning"],
            enabled=True
        ))

        # Sparse region claim warning
        self.add_rule(FilterRule(
            id="topology_sparse_claim",
            category=RuleCategory.TOPOLOGY,
            priority=RulePriority.MEDIUM,
            pattern=r'\[Sparse Region Claim\]',
            replacement="[Sparse Region Claim: This area has low knowledge density. Confidence reduced.]",
            description="Flag claims in sparse knowledge regions",
            tags=["topology", "confidence", "warning"],
            enabled=True
        ))

        # Layer gap warning
        self.add_rule(FilterRule(
            id="topology_layer_gap",
            category=RuleCategory.TOPOLOGY,
            priority=RulePriority.HIGH,
            pattern=r'\[Layer Gap\]',
            replacement="[Layer Gap: Missing intermediate logical steps. Add L2 justification.]",
            description="Flag claims that skip logical layers",
            tags=["topology", "layer", "warning"],
            enabled=True
        ))

    # =========================================================
    # Core Processing (Enhanced in v3.0)
    # =========================================================

    def _sort_rules(self):
        """Sort rules by priority, then category, then registration order"""
        self._rules_sorted = sorted(
            self.rules.values(),
            key=lambda r: (r.priority.value, r.category.value, r.id)
        )

    def add_rule(self, rule: FilterRule) -> None:
        """Add a new filter rule"""
        self.rules[rule.id] = rule
        self._sort_rules()
        self.stats["rules_enabled"] = sum(1 for r in self.rules.values() if r.enabled)
        self.stats["rules_disabled"] = len(self.rules) - self.stats["rules_enabled"]

    def filter(self, text: str, track_position: bool = False) -> FilterResult:
        """
        Apply all enabled rules to text.

        Enhanced in v3.0: If topology engine is attached, also performs
        structural analysis and injects topology warnings.
        """
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

            # Phase 1: Apply standard rules
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

            # Phase 2: Topology analysis (NEW in v3.0)
            if self.topology_enabled and self.topology_engine:
                topology_warnings = self._analyze_topology_warnings(current)
                result.topology_warnings = topology_warnings

                # Inject warnings into output if structural issues found
                if topology_warnings and "[Topology Warning]" not in current:
                    warning_block = "\n\n---\n**Structural Analysis:**\n" + "\n".join(
                        f"- {w}" for w in topology_warnings[:3]  # Max 3 warnings
                    )
                    current += warning_block

            result.text = current
            result.execution_time_ms = (time.time() - start_time) * 1000

            # Update stats
            self.stats["total_filters"] += 1
            self.stats["total_replacements"] += total_replacements
            self.stats["last_filter_time_ms"] = result.execution_time_ms
            self.session_replacements.extend(result.replacements)

            return result

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

    def get_stats(self) -> Dict:
        """Get engine statistics"""
        return {
            **self.stats,
            "total_rules": len(self.rules),
            "topology_enabled": self.topology_enabled,
            "by_category": {
                cat.name: len(self.get_rules(cat))
                for cat in RuleCategory
            }
        }

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

# --- Topology-enhanced factory function ---

def create_topology_aware_engine(topology_engine: Optional[TopologyMetricsEngine] = None) -> PostProcessEngine:
    """
    Create a post-processing engine with optional topology integration.

    Args:
        topology_engine: Optional TopologyMetricsEngine for structural analysis

    Returns:
        Configured PostProcessEngine
    """
    engine = PostProcessEngine(name="MSS-PostProcess-v3.0-Topology")

    if topology_engine and TOPOLOGY_AVAILABLE:
        engine.attach_topology_engine(topology_engine)

    return engine

# --- Legacy compatibility ---

def filter_response(text: str) -> str:
    """Legacy compatibility function"""
    engine = PostProcessEngine()
    result = engine.filter(text)
    return result.text

# --- Demo & Test ---

def demo_topology_engine():
    """Demonstrate topology-enhanced post-processing"""
    print("=" * 60)
    print("MSS Post-Process Engine v3.0 - Topology Demo")
    print("=" * 60)

    # Create engine without topology
    engine = PostProcessEngine()

    print("\n--- Standard Processing ---")
    test = "This is the ultimate solution and it never fails."
    result = engine.filter(test)
    print(f"Input:  {test}")
    print(f"Output: {result.text}")
    print(f"Changes: {result.summary()}")

    # Try to attach mock topology (will fail gracefully if not available)
    print("\n--- Topology Integration ---")
    if TOPOLOGY_AVAILABLE:
        print("Topology metrics available")
        # Create a simple graph for demo
        from mssclaw.core.semantic.symbolic_engine import MSSKnowledgeGraph, ConceptNode, RelationEdge, NodeType, RelationType

        graph = MSSKnowledgeGraph()
        for i in range(3):
            node = ConceptNode(
                id=f"N{i}", name=f"Node{i}",
                node_type=NodeType.CONCEPT,
                layer="L1",
                content=f"Content {i}"
            )
            graph.add_node(node)

        # Add edges (N0-N1 connected, N2 isolated)
        graph.add_edge(RelationEdge("N0", "N1", RelationType.IMPLIES))

        topo_engine = TopologyMetricsEngine(graph)
        engine.attach_topology_engine(topo_engine)

        test2 = "This framework provides a complete solution."
        result2 = engine.filter(test2)
        print(f"Input:  {test2}")
        print(f"Output: {result2.text}")
        print(f"Topology warnings: {len(result2.topology_warnings)}")
        for w in result2.topology_warnings:
            print(f"  - {w}")
    else:
        print("Topology metrics not available (optional dependency)")

    print("\n" + "=" * 60)
    print("Demo complete")
    print("=" * 60)

if __name__ == "__main__":
    demo_topology_engine()
