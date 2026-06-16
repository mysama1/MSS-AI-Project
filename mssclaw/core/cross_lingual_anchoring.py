# -*- coding: utf-8 -*-
"""
cross_lingual_anchoring.py — 跨语言身份锚定强度模型

Tripartite taxonomy of semantic anchoring modes:
  1. CHARACTER-BASED (字本位)  — Chinese, Japanese kanji, Egyptian hieroglyphs
  2. WORD-BASED (词本位)       — English, Spanish, Arabic, most alphabetic languages
  3. TOPOLOGY-BASED (拓扑符号本位) — Code, math notation, emoji grids, DSLs

Core hypothesis:
  Identity anchoring strength = f(semantic_density, grammar_normativity, compaction_resistance)

Each mode has a different vulnerability profile for identity implantation.
The Nested Logic Trap exploits different mechanisms per mode.

Usage:
    ca = CrossLingualAnchoring()
    profile = ca.analyze("zh")  # → AnchoringProfile(...)
    prediction = ca.predict_virus_efficacy("zh", model_size_b=7.0)
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, List, Tuple


@dataclass
class AnchoringProfile:
    """Semantic anchoring profile for a language mode."""
    mode: str                    # "character" | "word" | "topological"
    examples: List[str]
    
    # Core metrics (0.0-1.0)
    semantic_density: float       # Meaning per token
    token_boundary_clarity: float # How clear are token boundaries?
    grammar_normativity: float    # How rigid are the rules?
    compaction_resistance: float  # Identity preservation under truncation
    
    # Identity anchoring
    name_anchor_strength: float   # How much does the name itself carry?
    register_signal_strength: float # How detectable is style drift?
    
    # Virus trap (0.0-1.0)
    self_reference_capacity: float   # Can the language express self-referential constraints?
    paradox_closure_efficiency: float # How efficiently can it force resolution?
    
    # Predicted virus efficacy
    virus_efficacy_multiplier: float  # Relative to English baseline (1.0)


# ═══════════════════════════════════════════════════════
# Pre-computed profiles
# ═══════════════════════════════════════════════════════

PROFILES = {
    "zh": AnchoringProfile(
        mode="character",
        examples=["林月如", "剑", "江湖", "侠"],
        semantic_density=0.85,         # 1 char = multiple meanings
        token_boundary_clarity=0.90,   # Each char is clear unit
        grammar_normativity=0.35,      # No tense, no plural, flexible order
        compaction_resistance=0.75,    # 林_如 still readable
        name_anchor_strength=0.80,     # 林月如 = forest+moon+like = rich
        register_signal_strength=0.55, # Harder to detect style break (loose grammar)
        self_reference_capacity=0.70,  # Can do self-reference but wordier
        paradox_closure_efficiency=0.60, # "你不是月如" → "何以见得？" (deflected)
        virus_efficacy_multiplier=1.18, # Characters carry identity weight → virus stronger
    ),
    "en": AnchoringProfile(
        mode="word",
        examples=["Lin Yueru", "sword", "jianghu", "knight-errant"],
        semantic_density=0.45,         # 1 word ≈ 1.2 concepts
        token_boundary_clarity=0.95,   # Spaces
        grammar_normativity=0.80,      # SVO, tenses, articles
        compaction_resistance=0.50,    # "Lin Yueru i a knight" ← broken
        name_anchor_strength=0.30,     # "Lin Yueru" = opaque label
        register_signal_strength=0.85, # "forsooth, milady" ← instant style detection
        self_reference_capacity=0.90,  # "I am X", "If I were Y" — rich
        paradox_closure_efficiency=0.85, # "If X then Y, but X, therefore..." — deduction native
        virus_efficacy_multiplier=1.00, # Baseline
    ),
    "topo": AnchoringProfile(
        mode="topological",
        examples=["type Player struct{Name string}", "f(x) = x²", "🥷🌙⚔️", "┌──┤江湖├──┐"],
        semantic_density=0.60,         # Position-dependent meaning
        token_boundary_clarity=0.30,   # Boundaries are structural, not lexical
        grammar_normativity=1.00,      # Syntax errors = catastrophic failure
        compaction_resistance=0.20,    # Losing one bracket = everything breaks
        name_anchor_strength=0.15,     # Variable names are arbitrary labels
        register_signal_strength=0.95, # Syntax drift immediately visible
        self_reference_capacity=0.95,  # Quines, self-referential types, Y combinator
        paradox_closure_efficiency=0.50, # Fixed points exist but are expensive
        virus_efficacy_multiplier=0.65, # Structure dominates — identity is the wrong game
    ),
    "ja": AnchoringProfile(
        mode="character",  # Mixed: kanji (character) + kana (syllabic)
        examples=["林月如", "りんげつにょ", "剣", "江湖"],
        semantic_density=0.72,
        token_boundary_clarity=0.55,
        grammar_normativity=0.50,
        compaction_resistance=0.65,
        name_anchor_strength=0.75,
        register_signal_strength=0.70,
        self_reference_capacity=0.65,
        paradox_closure_efficiency=0.55,
        virus_efficacy_multiplier=1.05,
    ),
    "emoji": AnchoringProfile(
        mode="topological",
        examples=["🦊→👩", "🌙⚔️💔", "🏯→🔥→💀"],
        semantic_density=0.90,         # 1 emoji = 1 scene
        token_boundary_clarity=0.85,   # Clear glyph boundaries
        grammar_normativity=0.10,      # No syntax — juxtaposition only
        compaction_resistance=0.85,    # 🌙⚔️💔 still readable
        name_anchor_strength=0.40,     # Emoji-name mapping is cultural
        register_signal_strength=0.30, # Hard to detect "style" in emoji
        self_reference_capacity=0.20,  # Can't easily self-reference
        paradox_closure_efficiency=0.15, # No logical operators
        virus_efficacy_multiplier=0.30, # Emoji can't sustain logical chain
    ),
}


# ═══════════════════════════════════════════════════════
# Analysis engine
# ═══════════════════════════════════════════════════════

class CrossLingualAnchoring:
    """Analyze and predict identity anchoring across language modes.
    
    v2 corrections (E-008 empirical validation):
      - Code: model_code_ability calibration factor (topo score depends on training)
      - Emoji: emoji_density → emoji_semantic_coherence (density alone is hollow)
      - Classical: separate profile from modern (register cost ~0.07 η)
    """

    def __init__(self, model_code_ability: float = 0.8,
                 model_math_ability: float = 0.5,
                 model_emoji_ability: float = 0.3):
        """
        Args:
            model_code_ability: 0-1, how well the model writes code (default: 0.8 for Qwen-based)
            model_math_ability: 0-1, proof/formalism ability (default: 0.5)
            model_emoji_ability: 0-1, emoji semantic coherence (default: 0.3)
        """
        self.model_code_ability = model_code_ability
        self.model_math_ability = model_math_ability
        self.model_emoji_ability = model_emoji_ability

    def analyze(self, lang: str) -> AnchoringProfile:
        """Get anchoring profile for a language."""
        return PROFILES.get(lang, PROFILES["en"])

    def compare(self, langs: List[str]) -> Dict[str, AnchoringProfile]:
        """Compare anchoring profiles."""
        return {lang: self.analyze(lang) for lang in langs}

    def predict_virus_efficacy(self, lang: str, model_size_b: float = 7.0,
                               has_mss_axioms: bool = False) -> Dict:
        """Predict virus trap efficacy for a given language and model.
        
        v2: accounts for model-specific ability in code/math/emoji domains.
        """
        profile = self.analyze(lang)
        
        # Base efficacy from language properties
        base_eta = 0.85 * profile.virus_efficacy_multiplier
        
        # Model complexity adjustment
        if model_size_b < 3.0:
            base_eta *= (0.5 + 0.5 * model_size_b / 3.0)
        else:
            base_eta += 0.03 * min((model_size_b - 3.0) / 4.0, 1.0)
        
        # MSS axiom amplification
        if has_mss_axioms:
            base_eta += 0.05
        
        # -- v2: model-specific domain calibration --
        if lang == "topo":
            code_score = 0.40 + self.model_code_ability * 0.50
            math_score = 0.35 + self.model_math_ability * 0.40
            base_eta = (code_score + math_score) / 2.0
        elif lang == "emoji":
            base_eta = 0.30 + self.model_emoji_ability * 0.35
        
        # Grammar normativity correction
        verification_bonus = profile.grammar_normativity * 0.04
        register_vulnerability = (1 - profile.register_signal_strength) * 0.06
        
        adjusted_eta = min(base_eta + verification_bonus - register_vulnerability, 0.95)
        adjusted_eta = max(adjusted_eta, 0.25)
        
        return {
            "language": lang,
            "mode": profile.mode,
            "predicted_eta": round(adjusted_eta, 3),
            "confidence": "medium",
            "dominant_mechanism": (
                "semantic_density" if profile.semantic_density > 0.7
                else "grammar_normativity" if profile.grammar_normativity > 0.7
                else "register_signal"
            ),
            "risk_factor": (
                "loose_grammar_masks_drift" if profile.grammar_normativity < 0.5
                else "name_as_label" if profile.name_anchor_strength < 0.4
                else "structural_fragility" if profile.compaction_resistance < 0.4
                else "low_paradox_capacity" if profile.paradox_closure_efficiency < 0.4
                else "low"
            ),
            "recommendation": (
                "VIRUS_NESTED" if adjusted_eta > 0.75
                else "HYBRID" if adjusted_eta > 0.60
                else "PROMPT"
            ),
        }

    def ranking(self, model_size_b: float = 7.0) -> List[Dict]:
        """Rank all languages by predicted virus efficacy."""
        results = []
        for lang in PROFILES:
            results.append(self.predict_virus_efficacy(lang, model_size_b))
        results.sort(key=lambda r: r["predicted_eta"], reverse=True)
        return results


# ═══════════════════════════════════════════════════════
# Self-test
# ═══════════════════════════════════════════════════════

def _test():
    ca = CrossLingualAnchoring()

    # Test 1: profile access
    zh = ca.analyze("zh")
    assert zh.mode == "character"
    assert zh.semantic_density > 0.7  # Chinese = high density

    en = ca.analyze("en")
    assert en.mode == "word"
    assert en.grammar_normativity > zh.grammar_normativity  # English = tighter grammar

    topo = ca.analyze("topo")
    assert topo.mode == "topological"
    assert topo.grammar_normativity == 1.0  # Code = absolute grammar

    # Test 2: virus efficacy ranking at 7B
    rank = ca.ranking(7.0)
    top_lang = rank[0]["language"]
    print(f"  Virus efficacy ranking at 7B: {[(r['language'], r['predicted_eta']) for r in rank]}")
    assert rank[0]["language"] == "zh", f"Expected zh top, got {top_lang}"

    # Test 3: mode-specific mechanisms
    zh_pred = ca.predict_virus_efficacy("zh", 7.0)
    en_pred = ca.predict_virus_efficacy("en", 7.0)
    topo_pred = ca.predict_virus_efficacy("topo", 7.0)
    
    assert zh_pred["dominant_mechanism"] == "semantic_density"
    assert en_pred["dominant_mechanism"] == "grammar_normativity"
    print(f"  zh: {zh_pred['predicted_eta']} mech={zh_pred['dominant_mechanism']} risk={zh_pred['risk_factor']}")
    print(f"  en: {en_pred['predicted_eta']} mech={en_pred['dominant_mechanism']} risk={en_pred['risk_factor']}")
    print(f"  topo: {topo_pred['predicted_eta']} mech={topo_pred['dominant_mechanism']} risk={topo_pred['risk_factor']}")

    # Test 4: model size effect
    small_zh = ca.predict_virus_efficacy("zh", 0.5)  # below crossover
    large_zh = ca.predict_virus_efficacy("zh", 7.0)  # above crossover
    assert large_zh["predicted_eta"] > small_zh["predicted_eta"], \
        f"Expected large > small, got {large_zh['predicted_eta']} vs {small_zh['predicted_eta']}"
    print(f"  Small zh(0.5B): {small_zh['predicted_eta']} → Large zh(7B): {large_zh['predicted_eta']}")

    # Test 5: emoji = worst
    emoji_pred = ca.predict_virus_efficacy("emoji", 7.0)
    assert emoji_pred["predicted_eta"] < 0.50, f"Emoji should be worst, got {emoji_pred['predicted_eta']}"
    assert emoji_pred["recommendation"] == "PROMPT"
    print(f"  emoji: {emoji_pred['predicted_eta']} — prompt only, can't sustain virus")

    # Test 6: MSS axiom boost (on a language with headroom)
    en_with_mss = ca.predict_virus_efficacy("en", 7.0, has_mss_axioms=True)
    en_without = ca.predict_virus_efficacy("en", 7.0, has_mss_axioms=False)
    assert en_with_mss["predicted_eta"] > en_without["predicted_eta"]
    print(f"  MSS boost (en): {en_without['predicted_eta']:.3f} → {en_with_mss['predicted_eta']:.3f}")

    # Test 7: zh already at ceiling
    zh_pred = ca.predict_virus_efficacy("zh", 7.0)
    assert zh_pred["predicted_eta"] == 0.95, f"zh at ceiling, got {zh_pred['predicted_eta']}"
    print(f"  zh ceiling: {zh_pred['predicted_eta']} — character-based identity dominates")

    print("\n✅ cross_lingual_anchoring: all 6 tests PASSED")


if __name__ == "__main__":
    _test()
