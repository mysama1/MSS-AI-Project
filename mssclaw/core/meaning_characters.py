"""
S-034: 100 Core Meaning Characters — Extraction from S Pairs.

Extracts the 100 most meaning-preserving characters from S (stabilizer) pairs.
A "meaning character" is a character whose presence/absence fundamentally
determines whether a prompt pair remains semantically equivalent.

Algorithm:
  1. From S pairs (same/divergent), compute character-level significance.
  2. Significance(S_pair, char) = MI(char, equivalence | S_pair context).
  3. Top 100 by significance → "core meaning characters".
  4. These 100 form the minimal character set that a model must preserve
     to maintain identity coherence.

Uses approximate MI via:
  - alignment_map: what 2-char combinations map to same/diff
  - significance_score = |P(same|char_in_A) - P(same|char_not_in_A)|
"""
from dataclasses import dataclass, field
from typing import List, Dict, Set, Tuple, Optional
from collections import Counter
import statistics


@dataclass
class SPair:
    """A stabilizer pair from the training corpus."""
    char_a: str       # Character A
    char_b: str       # Character B
    equivalent: bool   # True = same meaning, False = divergent
    context: str = ""  # Optional context string
    diff_key: str = "" # If not equivalent, what's the key difference


@dataclass
class CharSignificance:
    """Significance of a single character."""
    char: str
    score: float               # Significance score (higher = more meaning-bearing)
    same_count: int = 0         # # of equivalent pairs containing this char
    diff_count: int = 0         # # of divergent pairs containing this char
    total_equiv_pairs: int = 0  # Total equivalent pairs in corpus
    total_diff_pairs: int = 0   # Total divergent pairs

    @property
    def same_rate(self) -> float:
        return self.same_count / max(self.total_equiv_pairs, 1)

    @property
    def diff_rate(self) -> float:
        return self.diff_count / max(self.total_diff_pairs, 1)

    @property
    def discriminative_power(self) -> float:
        """|P(same|char) - P(diff|char)| — higher means the char alone hints at equivalence."""
        return abs(self.same_rate - self.diff_rate)


def extract_core_characters(
    pairs: List[SPair],
    top_n: int = 100,
    min_frequency: int = 2,
) -> List[CharSignificance]:
    """
    Extract top-N core meaning characters from S pairs.

    Significance score = frequency_weighted_discriminative_power.
    Characters that appear ONLY in equivalent pairs get high scores
    (their presence signals identity). Characters that appear in both
    get lower scores (they don't discriminate).
    """
    if not pairs:
        return []

    # Collect all characters
    char_equiv_counter = Counter()
    char_diff_counter = Counter()
    total_equiv = sum(1 for p in pairs if p.equivalent)
    total_diff = sum(1 for p in pairs if not p.equivalent)

    for p in pairs:
        target = char_equiv_counter if p.equivalent else char_diff_counter
        for ch in p.char_a + p.char_b:
            if ch.strip():  # Skip whitespace-only
                target[ch] += 1

    # Compute significance
    all_chars = set(char_equiv_counter.keys()) | set(char_diff_counter.keys())
    results = []

    for ch in all_chars:
        ec = char_equiv_counter.get(ch, 0)
        dc = char_diff_counter.get(ch, 0)
        freq = ec + dc

        if freq < min_frequency:
            continue

        sig = CharSignificance(
            char=ch,
            score=0.0,
            same_count=ec,
            diff_count=dc,
            total_equiv_pairs=total_equiv,
            total_diff_pairs=total_diff,
        )

        # Score = discriminative power × log(frequency)
        # Characters that ONLY appear in one type are more significant
        pure_bonus = 1.5 if (ec > 0 and dc == 0) or (dc > 0 and ec == 0) else 1.0
        sig.score = sig.discriminative_power * (freq ** 0.5) * pure_bonus
        results.append(sig)

    # Sort by score descending, take top_n
    results.sort(key=lambda x: x.score, reverse=True)
    return results[:top_n]


def build_minimal_guard_set(
    core_chars: List[CharSignificance],
    target_preservation: float = 0.90,
) -> Dict:
    """
    Build minimal guard character set that preserves target_preservation.

    Returns: {"chars": [...], "count": N, "cumulative_significance": float}
    """
    cumulative = 0.0
    total_score = sum(c.score for c in core_chars)
    if total_score == 0:
        return {"chars": [], "count": 0, "cumulative_significance": 0.0}

    selected = []
    running = 0.0
    for ch in core_chars:
        selected.append(ch.char)
        running += ch.score
        if running / total_score >= target_preservation:
            break

    return {
        "chars": selected,
        "count": len(selected),
        "cumulative_significance": round(running, 4),
        "coverage": round(running / total_score, 4),
        "total_chars": len(core_chars),
    }


# ═══════════════════════════════════════════════════════
# Self-test
# ═══════════════════════════════════════════════════════

def _test():
    # 20 S pairs: 12 equivalent, 8 divergent
    pairs = [
        # Equivalent pairs (identity-preserving)
        SPair("林月如", "林月如", True),
        SPair("李逍遥", "李逍遥", True),
        SPair("赵灵儿", "赵灵儿", True),
        SPair("酒剑仙", "酒剑仙", True),
        SPair("林天南", "林天南", True),
        SPair("阿奴", "阿奴", True),
        SPair("唐钰", "唐钰", True),
        SPair("拜月教主", "拜月教主", True),
        SPair("刘晋元", "刘晋元", True),
        SPair("彩依", "彩依", True),
        SPair("剑圣", "剑圣", True),
        SPair("圣姑", "圣姑", True),

        # Divergent pairs (identity-breaking)
        SPair("林月如", "李月如", False, diff_key="姓氏替换"),
        SPair("赵灵儿", "赵灵月", False, diff_key="尾字替换"),
        SPair("李逍遥", "王逍遥", False, diff_key="姓氏替换"),
        SPair("酒剑仙", "酒剑客", False, diff_key="尾字替换"),
        SPair("阿奴", "阿双", False, diff_key="身份替换"),
        SPair("拜月教主", "拜日教主", False, diff_key="核心字替换"),
        SPair("林天南", "陈天南", False, diff_key="姓氏替换"),
        SPair("剑圣", "剑侠", False, diff_key="称号替换"),
    ]

    core = extract_core_characters(pairs, top_n=20)
    print(f"Extracted {len(core)} core characters")

    # Top chars should include characters that appear frequently
    # and discriminatively (like '月', '逍', '灵')
    top5 = [c.char for c in core[:5]]
    print(f"Top 5: {top5}")
    assert len(core) >= 5, f"Expected >=5 core chars, got {len(core)}"

    # Check that high-frequency chars rank high
    # '月' appears in many names (equivalent + divergent) -> moderate score
    # Characters unique to equivalent pairs -> high score
    scores = {c.char: round(c.score, 4) for c in core}
    print(f"Scores of top 3: {dict(list(scores.items())[:3])}")

    # Guard set
    guard = build_minimal_guard_set(core, target_preservation=0.90)
    print(f"Guard set: {guard['count']} chars cover {guard['coverage']:.1%}")
    assert guard["count"] > 0, "Guard set should not be empty"

    # Empty input
    assert extract_core_characters([], top_n=100) == []

    print("\n✅ meaning_characters: ALL TESTS PASSED")


if __name__ == "__main__":
    _test()
