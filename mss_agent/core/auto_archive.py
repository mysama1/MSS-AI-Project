"""
MSS-Agent v0.3 — Auto Archive (KB条目自动标注)

Auto-tags, classifies, and validates KB (knowledge base) entries:
- Auto-layer assignment (L0-L4) based on title/summary/content analysis
- Auto-category extraction
- Axiom reference validation
- t-value estimation from content novelty
- Batch processing with stats reporting

Part of the P0 tool suite (memory_guard / auto_archive / session_recall / budget_gate).
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set
from enum import Enum
import re
import json
import os
from pathlib import Path


class KBLayer(Enum):
    """MSS knowledge base layers."""
    L0_FOUNDATION = "L0_FOUNDATION"       # Core axioms, foundational concepts
    L1_CORE_THEORY = "L1_CORE_THEORY"     # Derived theorems, frameworks
    L2_APPLIED_THEORY = "L2_APPLIED_THEORY"  # Case studies, empirical findings
    L3_STRATEGIC = "L3_STRATEGIC"         # Deployment strategies, best practices
    L4_META = "L4_META"                   # Self-referential, meta-framework


# Auto-layering rules: title/summary patterns → layer
LAYER_PATTERNS = [
    (re.compile(r'\b(?:axiom|公理|foundation|基础|core theory|核心理论|postulate)\b', re.I),
     KBLayer.L0_FOUNDATION),
    (re.compile(r'\b(?:theorem|定理|framework|框架|protocol|协议|deriv|推导)\b', re.I),
     KBLayer.L1_CORE_THEORY),
    (re.compile(r'\b(?:case|案例|experiment|实验|empirical|实证|data|数据|benchmark|基准|combat|战斗|round)\b', re.I),
     KBLayer.L2_APPLIED_THEORY),
    (re.compile(r'\b(?:deploy|部署|strategy|策略|best practice|最佳实践|guide|指南|sop|操作)\b', re.I),
     KBLayer.L3_STRATEGIC),
    (re.compile(r'\b(?:meta|元|self.ref|自指|recursion|递归|audit|审计|critique|批评)\b', re.I),
     KBLayer.L4_META),
]

# Known categories with keyword patterns
CATEGORY_PATTERNS = {
    "heat_tax": [r'\bheat.?tax\b', r'\b热税\b', r'\bheat tax\b'],
    "delta_protocol": [r'\bdelta\b', r'\bΔ\b', r'\bdelta protocol\b'],
    "orchestrator": [r'\borchestrat\b', r'\b编排\b', r'\bmulti.agent\b'],
    "agent": [r'\bagent\b', r'\b代理\b', r'\bmss.agent\b'],
    "axiom": [r'\baxiom\b', r'\b公理\b', r'\bA[1-7]\b'],
    "parasitic_criticism": [r'\bparasit\b', r'\b寄生\b', r'\bK3\b'],
    "combat": [r'\bcombat\b', r'\b战斗\b', r'\bwarfare\b', r'\bround\b'],
    "architecture": [r'\barchitect\b', r'\b架构\b', r'\bthree.?layer\b', r'\b三层\b'],
    "knowledge": [r'\bknowledge\b', r'\b知识\b', r'\bkb\b'],
    "validation": [r'\bvalid\b', r'\b验证\b', r'\bempirical\b', r'\b实证\b', r'\bbenchmark\b'],
    "godel": [r'\bg.?del\b', r'\bincompleteness\b', r'\b不完备\b'],
    "cot": [r'\bchain.of.thought\b', r'\bcot\b', r'\b思维链\b'],
}

# Axiom reference patterns
AXIOM_PATTERNS = {
    "A1_λ": [r'\bA1\b', r'\bmeaning.?field\b', r'\b意义场\b', r'\bλ\b'],
    "A2": [r'\bA2\b', r'\bformal distinction\b', r'\b形式区分\b'],
    "A3_T>0": [r'\bA3\b', r'\bheat tax\b', r'\b热税\b', r'\bT\s*>\s*0\b'],
    "A4_Ξ": [r'\bA4\b', r'\bdark matter\b', r'\b暗物质\b', r'\bΞ\b'],
    "A5_α": [r'\bA5\b', r'\bself.reference\b', r'\b自指\b', r'\bα\b'],
    "A6_Δ>0": [r'\bA6\b', r'\bdelta\b', r'\bΔ\b', r'\bΔ\s*>\s*0\b'],
    "A7": [r'\bA7\b', r'\bcompleteness\b', r'\b完备性\b'],
}


@dataclass
class EntryDiagnosis:
    """Diagnosis result for a single KB entry."""
    h_id: str
    filename: str
    suggested_layer: Optional[KBLayer] = None
    suggested_categories: List[str] = field(default_factory=list)
    detected_axioms: List[str] = field(default_factory=list)
    missing_fields: List[str] = field(default_factory=list)
    estimated_t_value: float = 0.5
    issues: List[str] = field(default_factory=list)
    score: float = 0.0  # Overall quality score 0-1


class AutoArchiver:
    """
    KB条目自动标注器 — 批量分类、标记、校验。

    用法:
        archiver = AutoArchiver()

        # 诊断单条
        diag = archiver.diagnose(entry_dict)

        # 批量诊断
        results = archiver.diagnose_batch("knowledge_base/L2_APPLIED_THEORY/")

        # 生成报告
        print(archiver.report(results))
    """

    def __init__(self, min_t_value: float = 0.5, max_t_value: float = 0.98):
        self.min_t = min_t_value
        self.max_t = max_t_value

    def diagnose(self, entry: dict, filename: str = "") -> EntryDiagnosis:
        """
        诊断单条KB条目。

        Args:
            entry: Dict with keys: h_id, title, summary, content, axioms_referenced, etc.
            filename: Source filename for context

        Returns:
            EntryDiagnosis with suggestions and issues.
        """
        h_id = entry.get("h_id", "?")
        title = entry.get("title", "")
        summary = entry.get("summary", "")
        content = entry.get("content", "")
        axioms = entry.get("axioms_referenced", [])
        t_value = entry.get("t_value", 0.5)

        full_text = f"{title} {summary} {content}"

        diag = EntryDiagnosis(h_id=h_id, filename=filename)

        # 1. Suggest layer
        diag.suggested_layer = self._suggest_layer(full_text)

        # 2. Suggest categories
        diag.suggested_categories = self._suggest_categories(full_text)

        # 3. Detect axiom references
        diag.detected_axioms = self._detect_axioms(full_text)

        # 4. Check missing fields (required: h_id, title, t_value, category, summary)
        for field in ["h_id", "title", "t_value", "category", "summary"]:
            if field not in entry or not entry[field]:
                diag.missing_fields.append(field)

        # 5. Estimate t_value
        diag.estimated_t_value = self._estimate_t_value(entry, full_text)

        # 6. Collect issues
        if axioms and set(axioms) != set(diag.detected_axioms):
            missing_in_entry = set(diag.detected_axioms) - set(axioms)
            extra_in_entry = set(axioms) - set(diag.detected_axioms)
            if missing_in_entry:
                diag.issues.append(f"Detected axioms not in entry: {missing_in_entry}")
            if extra_in_entry:
                diag.issues.append(f"Axioms in entry but not detected in text: {extra_in_entry}")

        if not diag.suggested_categories:
            diag.issues.append("No categories detected — entry may be too generic")

        if t_value < self.min_t:
            diag.issues.append(f"t_value ({t_value}) below minimum ({self.min_t})")

        # 7. Quality score
        diag.score = self._compute_score(diag)

        return diag

    def _suggest_layer(self, text: str) -> Optional[KBLayer]:
        """Suggest KB layer based on text content."""
        for pattern, layer in LAYER_PATTERNS:
            if pattern.search(text):
                return layer
        return None

    def _suggest_categories(self, text: str) -> List[str]:
        """Extract categories from text keywords."""
        cats = []
        for cat_name, patterns in CATEGORY_PATTERNS.items():
            for pat in patterns:
                if re.search(pat, text, re.I):
                    cats.append(cat_name)
                    break  # Only add once per category
        return cats

    def _detect_axioms(self, text: str) -> List[str]:
        """Detect which axioms are referenced in the text."""
        found = []
        for axiom, patterns in AXIOM_PATTERNS.items():
            for pat in patterns:
                if re.search(pat, text, re.I):
                    found.append(axiom)
                    break
        return sorted(found)

    def _estimate_t_value(self, entry: dict, full_text: str) -> float:
        """Estimate t_value from content quality signals."""
        base = 0.5

        # Signal 1: Content length (minimum meaningful content)
        content_len = len(full_text)
        if content_len > 200: base += 0.05
        if content_len > 500: base += 0.05
        if content_len > 1000: base += 0.05

        # Signal 2: Structured content (tables, lists, headings)
        if re.search(r'\|.*\|.*\|', full_text): base += 0.05  # Table
        if full_text.count('\n') > 5: base += 0.03            # Multi-paragraph

        # Signal 3: Axiom references
        axioms = self._detect_axioms(full_text)
        base += min(len(axioms), 3) * 0.03

        # Signal 4: Existing t_value adjustment
        existing_t = entry.get("t_value", 0.5)
        if existing_t > base:
            base = (base + existing_t) / 2  # Blend with existing

        return round(min(max(base, self.min_t), self.max_t), 2)

    def _compute_score(self, diag: EntryDiagnosis) -> float:
        """Compute an overall quality score (0-1)."""
        score = 0.5

        # Has layer suggestion
        if diag.suggested_layer: score += 0.1
        # Has categories
        if diag.suggested_categories: score += min(len(diag.suggested_categories), 3) * 0.05
        # Has axiom references
        if diag.detected_axioms: score += min(len(diag.detected_axioms), 5) * 0.03
        # No missing fields
        if not diag.missing_fields: score += 0.1
        # No issues
        if not diag.issues: score += 0.1
        # t_value above threshold
        if diag.estimated_t_value >= self.min_t: score += 0.05

        return min(round(score, 2), 1.0)

    def diagnose_batch(self, directory: str) -> List[EntryDiagnosis]:
        """
        批量诊断目录下所有KB条目。

        Args:
            directory: Path to KB layer directory

        Returns:
            List of EntryDiagnosis results.
        """
        results = []
        dirpath = Path(directory)

        if not dirpath.exists():
            return results

        for fpath in sorted(dirpath.glob("*.jsonl")):
            try:
                with open(fpath, 'r', encoding='utf-8') as f:
                    entry = json.loads(f.readline())
                diag = self.diagnose(entry, filename=fpath.name)
                results.append(diag)
            except Exception as e:
                results.append(EntryDiagnosis(
                    h_id="?",
                    filename=fpath.name,
                    issues=[f"Parse error: {e}"],
                ))

        return results

    def report(self, diagnoses: List[EntryDiagnosis]) -> str:
        """Generate a human-readable report from diagnoses."""
        total = len(diagnoses)
        if total == 0:
            return "No entries to report."

        valid = [d for d in diagnoses if not d.issues]
        with_layer = [d for d in diagnoses if d.suggested_layer]
        with_cats = [d for d in diagnoses if d.suggested_categories]
        avg_t = sum(d.estimated_t_value for d in diagnoses) / total
        avg_score = sum(d.score for d in diagnoses) / total

        lines = [
            f"## Auto-Archive Report ({total} entries)",
            f"",
            f"| Metric | Value |",
            f"|--------|-------|",
            f"| Total entries | {total} |",
            f"| Clean (no issues) | {len(valid)} ({len(valid)/total*100:.0f}%) |",
            f"| Has layer suggestion | {len(with_layer)} ({len(with_layer)/total*100:.0f}%) |",
            f"| Has categories | {len(with_cats)} ({len(with_cats)/total*100:.0f}%) |",
            f"| Avg estimated t_value | {avg_t:.2f} |",
            f"| Avg quality score | {avg_score:.2f} |",
            f"",
        ]

        # Layer distribution
        lyr_count = {}
        for d in with_layer:
            key = d.suggested_layer.value
            lyr_count[key] = lyr_count.get(key, 0) + 1
        if lyr_count:
            lines.append("**Layer distribution:**")
            for lyr, cnt in sorted(lyr_count.items()):
                lines.append(f"- {lyr}: {cnt}")

        # Top issues
        all_issues = {}
        for d in diagnoses:
            for issue in d.issues:
                key = issue.split(":")[0]
                all_issues[key] = all_issues.get(key, 0) + 1
        if all_issues:
            lines.append("")
            lines.append("**Top issues:**")
            for issue, cnt in sorted(all_issues.items(), key=lambda x: -x[1])[:5]:
                lines.append(f"- {issue}: {cnt} entries")

        return "\n".join(lines)


# ── CLI 自检 ──

if __name__ == "__main__":
    print("=== Auto Archive Demo ===\n")

    archiver = AutoArchiver()

    # Test entries
    test_entries = [
        {
            "h_id": "H590",
            "title": "Gödel第二定理在自纠AI中的工程实证",
            "summary": "验证Gödel第二定理对LLM自纠的工程限制。A6框架预测的Δ>0条件下AI自纠能力",
            "content": "## Framework\nThe Delta protocol (A6) governs when intervention is needed.\n\n| Model | Detect | Correct |\n|-------|--------|--------|\n| GPT-3.5 | 81.5% | 26.8% |\n| Claude | 10.1% | 29.1% |",
            "axioms_referenced": ["A6_Δ>0"],
            "t_value": 0.95,
            "category": "combat_round5",
        },
        {
            "h_id": "H100",
            "title": "三层架构部署最佳实践指南",
            "summary": "如何在生产环境中部署MSS三层架构的实践指南",
            "content": "Deploy L0 separately from L1/L2. Use async event loop for L1 observation.",
            "axioms_referenced": [],
            "t_value": 0.4,
            "category": "",
        },
        {
            "h_id": "H7",
            "title": "MSS公理体系v1.0元层次审计",
            "summary": "对MSS本身的框架进行递归审计，检查自指一致性",
            "content": "This is a meta-audit of the MSS framework itself. The Gödel question applies: can the framework audit itself? A7 says no.",
            "axioms_referenced": ["A7", "A1_λ"],
            "t_value": 0.82,
            "category": "meta",
        },
    ]

    for entry in test_entries:
        diag = archiver.diagnose(entry)
        print(f"  [{diag.h_id}] {entry['title'][:50]}")
        print(f"    Layer: {diag.suggested_layer.value if diag.suggested_layer else '?'}")
        print(f"    Categories: {diag.suggested_categories}")
        print(f"    Axioms: {diag.detected_axioms}")
        print(f"    t_value: {diag.estimated_t_value} (was {entry['t_value']})")
        print(f"    Score: {diag.score:.2f}")
        if diag.issues:
            print(f"    ⚠️ Issues: {diag.issues}")
        if diag.missing_fields:
            print(f"    ❌ Missing: {diag.missing_fields}")
        print()

    # Report
    diags = [archiver.diagnose(e) for e in test_entries]
    print(archiver.report(diags))
