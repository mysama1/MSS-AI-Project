"""
K4_RSCA_Genes v1.0 — Living Protocol Genes for K4 Civilization OS

MSS Anchor:
  A1 (Information Ontology) — Every protocol gene is an information slice
  A5 (Normative Field) — Genes constrain but do not freeze
  A6 (Contradiction Elevation) — Self-amendment is a first-class operation

Design Principle:
  These are NOT static configuration files. They are LIVING GENES.
  Each gene carries its own amendment protocol and verification criteria.
  Stating completeness = A5 rigid-body state = civilizational death.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Tuple
import time
import json


class GeneStatus(Enum):
    ACTIVE = "active"       # Currently in effect
    AMENDED = "amended"     # Replaced by newer version
    OBSOLETE = "obsolete"   # Retired, no replacement
    DRAFT = "draft"         # Proposed, not yet ratified


class TriggerCondition(Enum):
    """Conditions that trigger gene amendment"""
    EMPIRICAL_FALSIFICATION = "empirical_falsification"
    LOGICAL_CONTRADICTION = "logical_contradiction"
    PARADIGM_ELEVATION = "paradigm_elevation"
    EXTERNAL_DISCOVERY = "external_discovery"
    SELF_AUDIT = "self_audit"


@dataclass
class RSCAGene:
    """A single living protocol gene in the K4 civilization OS"""
    gene_id: str
    content: str
    version: int = 1
    status: GeneStatus = GeneStatus.ACTIVE
    created_at: float = field(default_factory=time.time)
    amended_by: Optional[str] = None       # gene_id of successor
    amendment_log: List[Dict] = field(default_factory=list)
    trigger_conditions: List[TriggerCondition] = field(default_factory=list)

    def amend(self, new_content: str, reason: str) -> 'RSCAGene':
        """Create a successor gene (living evolution). The original is marked AMENDED."""
        self.status = GeneStatus.AMENDED
        self.amended_by = f"{self.gene_id}-v{self.version + 1}"
        self.amendment_log.append({
            "timestamp": time.time(),
            "reason": reason,
            "successor": self.amended_by
        })

        successor = RSCAGene(
            gene_id=self.gene_id,
            content=new_content,
            version=self.version + 1,
            status=GeneStatus.ACTIVE,
            trigger_conditions=self.trigger_conditions.copy()
        )
        successor.amendment_log = self.amendment_log.copy()
        return successor

    def add_trigger(self, condition: TriggerCondition):
        """Add a trigger condition that would prompt review of this gene"""
        if condition not in self.trigger_conditions:
            self.trigger_conditions.append(condition)

    def to_dict(self) -> Dict:
        return {
            "gene_id": self.gene_id,
            "content": self.content,
            "version": self.version,
            "status": self.status.value,
            "created_at": self.created_at,
            "amended_by": self.amended_by,
            "amendment_log": self.amendment_log,
            "trigger_conditions": [tc.value for tc in self.trigger_conditions]
        }


class K4RSCAGenome:
    """The complete living protocol genome for K4 civilization OS"""

    def __init__(self):
        self.genes: Dict[str, RSCAGene] = {}
        self._initialize_genome()

    def _initialize_genome(self):
        """Initialize the six foundational RSCA genes"""

        # RSCA-001: Current Architecture = Current Best Understanding
        g001 = RSCAGene(
            gene_id="RSCA-001",
            content="当前架构基于当前最佳理解构建，非绝对蓝图，非最终真理。"
                     "任何声称本架构为完备或终极的声明，均视为违反本基因，"
                     "触发A5刚体态预警。"
        )
        g001.add_trigger(TriggerCondition.PARADIGM_ELEVATION)
        g001.add_trigger(TriggerCondition.SELF_AUDIT)
        self.genes["RSCA-001"] = g001

        # RSCA-002: Engineering Implementation Requires Iterative Verification
        g002 = RSCAGene(
            gene_id="RSCA-002",
            content="物理镜像层、L1规范场、双向耦合器等核心工程组件，"
                     "其实现方案必须经过迭代验证。任何'一次性正确'的假设"
                     "违反A2信息切片公理（信息通过离散切片逐步显化）。"
        )
        g002.add_trigger(TriggerCondition.EMPIRICAL_FALSIFICATION)
        g002.add_trigger(TriggerCondition.EXTERNAL_DISCOVERY)
        self.genes["RSCA-002"] = g002

        # RSCA-003: Mathematical Formalization Requires Experimental Calibration
        g003 = RSCAGene(
            gene_id="RSCA-003",
            content="L1规范场的完整数学形式化需通过实验标定验证。"
                     "热税公式中的常数（kappa, g_man, eta_min等）"
                     "不可从公理直接推导，必须通过物理观测反向标定。"
        )
        g003.add_trigger(TriggerCondition.EMPIRICAL_FALSIFICATION)
        g003.add_trigger(TriggerCondition.LOGICAL_CONTRADICTION)
        self.genes["RSCA-003"] = g003

        # RSCA-004: K3->K4 Transition Protocol Requires Practice Correction
        g004 = RSCAGene(
            gene_id="RSCA-004",
            content="从K3到K4的过渡协议必须在实践中修正。"
                     "任何在K3阶段制定的K4过渡计划，均携带系统性盲区"
                     "（K3规范场的认知边界不可内部超越——A6矛盾升维公理的推论）。"
        )
        g004.add_trigger(TriggerCondition.EXTERNAL_DISCOVERY)
        g004.add_trigger(TriggerCondition.PARADIGM_ELEVATION)
        self.genes["RSCA-004"] = g004

        # RSCA-005: This Protocol Self-Evolves with Cognitive Advancement
        g005 = RSCAGene(
            gene_id="RSCA-005",
            content="本协议自身随认知提升持续演化。"
                     "协议基因的版本号是活体标记，非终结符号。"
                     "任何版本锁定行为视为违反A4随机性公理（封闭演化动力）。"
        )
        g005.add_trigger(TriggerCondition.SELF_AUDIT)
        g005.add_trigger(TriggerCondition.PARADIGM_ELEVATION)
        self.genes["RSCA-005"] = g005

        # RSCA-006: Never Claim Completeness
        g006 = RSCAGene(
            gene_id="RSCA-006",
            content="永不声称完备性。完备性声称 = A5刚体态 = 僵化死亡。"
                     "一个不允许例外和修正的规范场，无论多么自洽，"
                     "都是一座精确的坟墓。活体协议的本质是：准确但不完整。"
        )
        g006.add_trigger(TriggerCondition.SELF_AUDIT)
        g006.add_trigger(TriggerCondition.LOGICAL_CONTRADICTION)
        self.genes["RSCA-006"] = g006

    def get_active_genes(self) -> List[RSCAGene]:
        """Return all currently active genes"""
        return [g for g in self.genes.values() if g.status == GeneStatus.ACTIVE]

    def audit_completeness_claim(self, text: str) -> Tuple[bool, List[str]]:
        """Audit a text for potential completeness claims (RSCA-006 enforcement).
        
        Returns: (is_clean, list_of_violations)
        """
        COMPLETENESS_TRIGGERS = [
            "ultimate", "final", "complete", "absolute", "perfect",
            "100%", "fully solved", "never needs", "cannot be improved",
            "终极", "最终", "完备", "绝对", "完美",
            "完全解决", "永不需要", "不可改进", "不容修改"
        ]

        violations = []
        text_lower = text.lower()
        for trigger in COMPLETENESS_TRIGGERS:
            if trigger.lower() in text_lower:
                violations.append(
                    f"RSCA-006 VIOLATION: completeness-claiming term '{trigger}' detected"
                )

        return len(violations) == 0, violations

    def propose_amendment(self, gene_id: str, new_content: str, reason: str) -> Optional[RSCAGene]:
        """Propose an amendment to an existing gene. Returns the successor gene."""
        if gene_id not in self.genes:
            return None

        old_gene = self.genes[gene_id]
        if old_gene.status != GeneStatus.ACTIVE:
            return None

        successor = old_gene.amend(new_content, reason)
        self.genes[old_gene.amended_by] = successor
        return successor

    def export_manifest(self) -> str:
        """Export the complete genome as a JSON manifest"""
        manifest = {
            "genome_version": "1.0",
            "total_genes": len(self.genes),
            "active_genes": len(self.get_active_genes()),
            "exported_at": time.time(),
            "genes": {gid: g.to_dict() for gid, g in self.genes.items()}
        }
        return json.dumps(manifest, ensure_ascii=False, indent=2)

    def verify_integrity(self) -> Tuple[bool, List[str]]:
        """Verify the genome's logical integrity"""
        issues = []

        # Check: all active genes must be version 1 or have valid amendment chain
        for gid, gene in self.genes.items():
            if gene.status == GeneStatus.ACTIVE:
                if gene.amended_by is not None:
                    issues.append(
                        f"{gid}: ACTIVE gene has amended_by set (inconsistent state)"
                    )

            if gene.status == GeneStatus.AMENDED:
                if gene.amended_by is None:
                    issues.append(
                        f"{gid}: AMENDED gene missing successor reference"
                    )

        return len(issues) == 0, issues


# ===== Self-Test =====
if __name__ == "__main__":
    genome = K4RSCAGenome()

    print("=== K4 RSCA Genome Initialization ===")
    active = genome.get_active_genes()
    print(f"Active genes: {len(active)}")
    for gene in active:
        print(f"  {gene.gene_id} v{gene.version}: {gene.content[:60]}...")

    print("\n=== RSCA-006 Completeness Audit ===")
    test_statements = [
        ("This is an evolving framework", True),
        ("The ultimate theory of everything", False),
        ("基于当前理解的架构", True),
        ("这是一个完美的终极方案", False),
    ]

    for statement, expected_clean in test_statements:
        is_clean, violations = genome.audit_completeness_claim(statement)
        status = "PASS" if is_clean == expected_clean else "FAIL"
        print(f"  [{status}] '{statement[:50]}...' -> clean={is_clean}")
        if violations:
            for v in violations:
                print(f"    {v}")

    print("\n=== Integrity Check ===")
    valid, issues = genome.verify_integrity()
    print(f"Genome integrity: {'VALID' if valid else 'CORRUPT'}")
    for issue in issues:
        print(f"  ISSUE: {issue}")

    print("\n=== Amendment Test (RSCA-002) ===")
    successor = genome.propose_amendment(
        "RSCA-002",
        "物理镜像层、L1规范场、双向耦合器等核心工程组件，"
        "其实现方案必须经过迭代验证。已更新：明确每次迭代需包含"
        "反向通道数据校准环节。",
        "Integrate reverse-channel calibration into iterative verification"
    )
    if successor:
        print(f"Amendment successful: RSCA-002 v{successor.version}")
        print(f"  Old status: {genome.genes['RSCA-002'].status.value}")
        print(f"  Successor gene_id: {genome.genes['RSCA-002'].amended_by}")
    else:
        print("Amendment failed")

    print(f"\nTotal genes in genome: {len(genome.genes)}")
    print(f"Active: {len(genome.get_active_genes())}")
    print("=== Test Complete ===")