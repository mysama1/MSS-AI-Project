"""
MSS-Agent v0.3 — T-Value Auto-Filter (D5-034)

Auto-assigns T-values to KB entries and conversation content using a
multi-signal scoring model. Designed for processing high-volume K3
information streams with minimal human intervention.

Signals:
  - Structural quality (tables, headings, references)
  - Axiom alignment (which A1-A7 axioms are referenced)
  - Empirical grounding (numbers, data, benchmarks)
  - Source reliability (DOI, URL, paper reference)
  - Semantic depth (educated vocabulary vs generic)
  - Recency (newer = higher baseline)
  - Self-reference risk (talking about MSS itself vs external topics)
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
from enum import Enum
import re
import math
from datetime import datetime, timedelta


class TFilterReason(Enum):
    """Why an item received a particular T-value."""
    LOW_STRUCTURE = "low_structure"
    LOW_EMPIRICAL = "low_empirical"
    SELF_REFERENCE_HEAVY = "self_reference_heavy"
    OUTDATED = "outdated"
    GENERIC_CONTENT = "generic_content"
    NO_AXIOMS = "no_axioms"
    HIGH_QUALITY = "high_quality"
    WELL_STRUCTURED = "well_structured"
    EMPIRICALLY_GROUNDED = "empirically_grounded"


@dataclass
class TScore:
    """Complete T-value scoring result."""
    t_value: float              # 0.0 to 1.0
    confidence: float           # How confident the model is in this score
    signals: Dict[str, float]   # Individual signal scores
    reasons: List[TFilterReason]
    tier: str                   # "high" (>0.7), "medium" (0.4-0.7), "low" (<0.4)


class TValueFilter:
    """
    T值自动筛选器 — 多信号评分模型。

    用法:
        filter = TValueFilter()

        # 评分单条
        score = filter.score_entry("Some KB content...", date="2026-06-01")

        # 批量筛选
        results = filter.filter_batch(entries, min_t=0.4)

        # 生成拒绝原因
        print(filter.explain(score))
    """

    def __init__(
        self,
        self_reference_penalty: float = 0.15,  # Penalty for heavily self-referential content
        recency_decay_days: int = 90,          # Days before content starts losing recency score
        min_empirical_signals: int = 2,        # Minimum numeric/statistical references
        structure_bonus: float = 0.1,          # Bonus for well-structured content
    ):
        self.self_ref_penalty = self_reference_penalty
        self.recency_decay = recency_decay_days
        self.min_empirical = min_empirical_signals
        self.structure_bonus = structure_bonus

    def score_entry(
        self,
        content: str,
        date: Optional[str] = None,
        axioms: Optional[List[str]] = None,
        category: Optional[str] = None,
        source: str = "",
    ) -> TScore:
        """
        Score a single KB entry or content piece.

        Returns TScore with t_value, confidence, signal breakdown, and reasons.
        """
        signals = {}
        reasons = []

        # 1. Structure score (0-1)
        struct = self._score_structure(content)
        signals["structure"] = struct
        if struct > 0.6:
            reasons.append(TFilterReason.WELL_STRUCTURED)
        elif struct < 0.2:
            reasons.append(TFilterReason.LOW_STRUCTURE)

        # 2. Empirical score (0-1)
        empirical = self._score_empirical(content)
        signals["empirical"] = empirical
        if empirical > 0.5:
            reasons.append(TFilterReason.EMPIRICALLY_GROUNDED)
        elif empirical < 0.15:
            reasons.append(TFilterReason.LOW_EMPIRICAL)

        # 3. Axiom alignment (0-1)
        axiom_score = self._score_axioms(axioms or [])
        signals["axioms"] = axiom_score
        if axiom_score == 0:
            reasons.append(TFilterReason.NO_AXIOMS)

        # 4. Recency (0-1)
        recency = self._score_recency(date)
        signals["recency"] = recency
        if recency < 0.3:
            reasons.append(TFilterReason.OUTDATED)

        # 5. Self-reference detection (0-1, reverse)
        self_ref = self._score_self_reference(content)
        signals["self_reference"] = self_ref
        if self_ref > 0.5:
            reasons.append(TFilterReason.SELF_REFERENCE_HEAVY)

        # 6. Semantic depth (0-1)
        depth = self._score_depth(content)
        signals["depth"] = depth
        if depth < 0.2:
            reasons.append(TFilterReason.GENERIC_CONTENT)

        # 7. Source quality (0-1)
        source_quality = self._score_source(source, content)
        signals["source"] = source_quality

        # ── Combine signals into final T-value ──
        weights = {
            "structure": 0.20,
            "empirical": 0.25,
            "axioms": 0.20,
            "recency": 0.10,
            "self_reference": -0.15,  # Negative weight (more self-ref = lower)
            "depth": 0.15,
            "source": 0.10,
        }

        t_val = sum(signals.get(k, 0) * w for k, w in weights.items())

        # Add structure bonus
        if struct > 0.6:
            t_val += self.structure_bonus

        # Apply self-reference penalty
        if self_ref > 0.5:
            t_val -= self.self_ref_penalty

        # Clamp
        t_val = max(0.0, min(1.0, t_val))
        t_val = round(t_val, 2)

        # Confidence: agreements among signals (standard deviation inverted)
        signal_values = [abs(v) for v in signals.values()]
        if signal_values:
            mean = sum(signal_values) / len(signal_values)
            variance = sum((v - mean) ** 2 for v in signal_values) / len(signal_values)
            confidence = round(1.0 / (1.0 + math.sqrt(variance)), 2)
        else:
            confidence = 0.3

        if t_val > 0.7:
            reasons.append(TFilterReason.HIGH_QUALITY)

        tier = "high" if t_val > 0.7 else ("medium" if t_val > 0.4 else "low")

        return TScore(
            t_value=t_val,
            confidence=confidence,
            signals=signals,
            reasons=reasons,
            tier=tier,
        )

    def _score_structure(self, text: str) -> float:
        """Score structural quality: tables, headings, lists, length."""
        score = 0.0
        if re.search(r'\|.*\|.*\|', text): score += 0.3  # Table
        if len(re.findall(r'^#{1,4}\s', text, re.M)): score += 0.2  # Headings
        if re.search(r'^[-\*]\s', text, re.M): score += 0.1  # Bullet lists
        if len(text) > 200: score += 0.1
        if len(text) > 500: score += 0.1
        if len(text) > 1000: score += 0.1
        if '\n\n' in text: score += 0.1  # Paragraph breaks
        return min(score, 1.0)

    def _score_empirical(self, text: str) -> float:
        """Score empirical grounding: numbers, percentages, data references."""
        score = 0.0
        numbers = len(re.findall(r'\b\d+\.?\d*\b', text))
        if numbers >= 5: score += 0.3
        elif numbers >= 2: score += 0.15
        if re.search(r'\d+%', text): score += 0.15
        if re.search(r'\bn\s*=\s*\d+', text, re.I): score += 0.15  # Sample size
        if re.search(r'\b(?:DOI|doi|arXiv|PMID)\b', text): score += 0.15
        if re.search(r'\b(?:benchmark|基准|measured|tested|verified)\b', text, re.I): score += 0.1
        if re.search(r'\b(?:±|CI|confidence|p\s*[<>=])\b', text): score += 0.15  # Statistics
        return min(score, 1.0)

    def _score_axioms(self, axioms: List[str]) -> float:
        """Score based on axiom coverage."""
        if not axioms: return 0.0
        return min(len(axioms) / 4.0, 1.0)  # 4+ axioms = full score

    def _score_recency(self, date_str: Optional[str]) -> float:
        """Score based on how recent the content is."""
        if not date_str: return 0.5  # Unknown date = moderate
        try:
            dt = datetime.fromisoformat(date_str[:10])
            age_days = (datetime.now() - dt).days
            if age_days < 0: return 1.0
            if age_days <= 7: return 1.0
            if age_days <= 30: return 0.8
            if age_days <= self.recency_decay: return 0.5
            # Exponential decay beyond threshold
            excess = age_days - self.recency_decay
            return max(0.1, 0.5 * math.exp(-excess / 180))
        except:
            return 0.5

    def _score_self_reference(self, text: str) -> float:
        """Detect heavy self-reference (talking about MSS itself)."""
        patterns = [
            r'\bMSS\b', r'\bmss.agent\b', r'\bheat.?tax\b', r'\bDelta\b',
            r'\b三层\b', r'\bmeaning.?field\b', r'\b意义场\b',
            r'\bK[34]\b', r'\bparasitic criticism\b', r'\b寄生性批评\b',
            r'\bGödel\b', r'\b公理\b', r'\b公理体系\b',
        ]
        matches = sum(1 for p in patterns if re.search(p, text, re.I))
        density = matches / max(len(text.split()), 1) * 100
        return min(density / 5.0, 1.0)  # Normalize

    def _score_depth(self, text: str) -> float:
        """Score semantic depth vs generic content."""
        score = 0.0
        # Academic/technical vocabulary density
        academic_words = [
            r'\b(?:framework|architecture|protocol|empirical|theoretical|novel|mechanism)\b',
            r'\b(?:框架|架构|协议|实证|理论|机制|范式|本体|认识)\b',
        ]
        for pat in academic_words:
            if re.search(pat, text, re.I):
                score += 0.1

        # Generic filler detection
        generic = re.findall(r'\b(?:basically|essentially|obviously|clearly|simply|just|very|really)\b', text, re.I)
        if len(generic) > 5:
            score -= 0.1

        # Sentence complexity (avg sentence length)
        sentences = re.split(r'[.!?。！？\n]', text)
        sentences = [s for s in sentences if len(s.split()) > 3]
        if sentences:
            avg_len = sum(len(s.split()) for s in sentences) / len(sentences)
            if avg_len > 10: score += 0.1
            if avg_len > 20: score += 0.1

        return max(0.0, min(score, 1.0))

    def _score_source(self, source: str, text: str) -> float:
        """Score source reliability."""
        score = 0.3  # Baseline
        if re.search(r'(?:DOI|doi|10\.\d{4,})', source + text):
            score += 0.4
        if 'github.com' in source or 'pypi.org' in source:
            score += 0.2
        if 'zenodo.org' in source or 'osf.io' in source:
            score += 0.2
        if 'arxiv.org' in source:
            score += 0.15
        return min(score, 1.0)

    def filter_batch(
        self,
        entries: List[dict],
        min_t: float = 0.4,
    ) -> Tuple[List[dict], List[dict], List[dict]]:
        """
        Batch-filter entries by T-value.

        Returns: (high, medium, low) tier lists
        """
        high, medium, low = [], [], []
        for entry in entries:
            content = entry.get('content', '') or entry.get('summary', '')
            score = self.score_entry(
                content=content,
                date=entry.get('date'),
                axioms=entry.get('axioms_referenced', []),
                category=entry.get('category'),
                source=entry.get('_path', ''),
            )
            entry['_t_score'] = score
            if score.tier == 'high':
                high.append(entry)
            elif score.tier == 'medium':
                medium.append(entry)
            else:
                low.append(entry)
        return high, medium, low

    def explain(self, score: TScore) -> str:
        """Generate human-readable explanation of a T-score."""
        lines = [f"T-value: {score.t_value:.2f} ({score.tier} tier, confidence: {score.confidence:.2f})"]
        lines.append(f"Signals: {', '.join(f'{k}={v:.2f}' for k, v in score.signals.items())}")
        if score.reasons:
            lines.append(f"Reasons: {', '.join(r.value for r in score.reasons)}")
        return '\n'.join(lines)


# ── CLI 自检 ──

if __name__ == "__main__":
    print("=== T-Value Auto-Filter Demo ===\n")

    filt = TValueFilter()

    # Test high-quality entry
    high = filt.score_entry(
        content="## Framework\n\nThe A6 Delta protocol governs when intervention is needed.\n\n| Model | Detect | Correct |\n|-------|--------|--------|\n| GPT-3.5 | 81.5% | 26.8% |\n\nVerified with n=150 samples, p<0.01.\n\nDOI: 10.5281/zenodo.20587900",
        date="2026-06-08",
        axioms=["A6_Δ>0", "A3_T>0", "A1_λ"],
    )
    print(f"[HIGH] {filt.explain(high)}\n")

    # Test low-quality entry
    low = filt.score_entry(
        content="basically this is just a very simple thing that obviously works",
        date="2025-01-01",
        axioms=[],
    )
    print(f"[LOW]  {filt.explain(low)}\n")

    # Test self-reference heavy
    sr = filt.score_entry(
        content="MSS framework is designed for the MSS-Agent system which uses MSS axioms to validate MSS entries. The MSS architecture is based on MSS principles including MSS heat-tax and MSS Delta protocol.",
        date="2026-06-01",
        axioms=["A1_λ"],
    )
    print(f"[SELF-REF]  {filt.explain(sr)}")

    # Batch filter demo
    print(f"\n--- Batch Filter ---")
    entries = [
        {"content": "## Analysis\n| p<0.01 | n=200 |", "date": "2026-06-08", "axioms_referenced": ["A6", "A3"]},
        {"content": "just a note", "date": "2025-01-01", "axioms_referenced": []},
        {"content": "MSS MSS MSS MSS", "date": "2026-06-01", "axioms_referenced": ["A1"]},
    ]
    high, mid, low = filt.filter_batch(entries, min_t=0.4)
    print(f"  High: {len(high)} | Medium: {len(mid)} | Low: {len(low)}")
