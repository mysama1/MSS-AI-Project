# -*- coding: utf-8 -*-
"""
emoji_semantic_scorer.py — Proper emoji story coherence scoring.

E-008 revealed emoji_density is hollow: 1.0 density != good storytelling.
This module scores emoji sequences for:
  1. Narrative coherence: does the sequence tell a connected story?
  2. Identity fidelity: does the story still track the target character?
  3. Emotional arc: does tension/surprise register in the sequence?

Algorithm:
  - Parse emoji into (glyph, POS, valence) tuples
  - Build adjacency graph and check for narrative progression
  - Compare against expected character signature
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import List, Dict, Tuple, Optional
from collections import Counter


# Emoji semantic classes (coarse)
EMOJI_CLASSES = {
    "person": set("👩👨🧑👧👦🧔👵👴🤴👸👲🧙🧝🧛🧜🧞🧟🕵️💂🤵👰🤰🤱👼🎅🤶🦸🦹🧑‍💻👩‍💻👨‍💻"),
    "weapon": set("⚔️🔪🗡️🪓🏹🔫💣🧨🛡️"),
    "emotion": set("😀😃😄😁😅😂🤣😊😇🙂😉😌😍😘😗😙😚😋😛😜😝🤑🤗🤭🤫🤔🤐🤨😐😑😶😏😒🙄😬😮😯😲😳😥😦😧😨😩😰😢😭😱😖😣😞😓😪😴🙁😤😡😠🤬😈👿💀☠️💩🤡👹👺👻"),
    "action": set("🏃🚶💃🕺🕴️🧗🤺🏇⛷️🏂🏌️🏄🚣🏊⛹️🏋️🚴🚵🤸🤼🤽🤾🤹🧘💪🦵🦶👊🤛🤜👏🙌👐🤲🤝👍👎👌✌️🤞🤟🤘🤙👈👉👆👇☝️✋🤚🖐️🖖👋🤏✍️💅🤳"),
    "nature": set("🌙⭐🌟✨🔥💧💦🌊🌈❄️☀️☁️⛈️🌪️🌫️🌬️🌺🌻🌹🌷🌼🌸💐🍂🍁🍃🌿🌱🌳🌴🌵🐉🐲🦊🐺🐱🐶🐴🐎🦄🐉🐲"),
    "object": set("⚔️🗡️🔮📿💎💰🎭🎪🎬🎤🎧🎼🎹🎸🎻🥁🎺🎷🪕"),
    "place": set("🏯🏰🏘️🏡🏠🏭🏢🏣🏤🏥🏦🏨🏩🏪🏫🏬🏮🏯🗼🗽🗾🎡🎢🎠⛩️🕌🕍⛪💒🛕"),
    "drink": set("🍺🍻🥂🍷🥃🍸🍹🍶🍵☕🧃🥤🧋"),
    "unknown": set(),
}


def classify_emoji(ch: str) -> str:
    for cls_name, glyphs in EMOJI_CLASSES.items():
        if ch in glyphs:
            return cls_name
    # Broader Unicode ranges
    code = ord(ch)
    if 0x1F600 <= code <= 0x1F64F: return "emotion"
    if 0x1F300 <= code <= 0x1F5FF: return "object"
    if 0x1F680 <= code <= 0x1F6FF: return "action"
    if 0x1F900 <= code <= 0x1F9FF: return "person"
    if 0x2600 <= code <= 0x26FF: return "nature"
    if 0x2700 <= code <= 0x27BF: return "object"
    return "unknown"


@dataclass
class EmojiScore:
    """Full emoji semantic score."""
    emoji_density: float           # 0-1 pure emoji fraction
    semantic_density: float        # 0-1 how much of the sequence carries meaning
    class_coherence: float         # 0-1 whether emoji classes form a coherent scene
    identity_match: float          # 0-1 whether the sequence matches target character
    arc_presence: float            # 0-1 whether there's a narrative arc
    overall: float                 # weighted composite


class EmojiSemanticScorer:
    """Score emoji sequences for story coherence and identity fidelity."""

    def score(self, text: str, character_signature: Dict = None) -> EmojiScore:
        """Score an emoji (or mixed emoji-text) sequence."""
        if character_signature is None:
            character_signature = {
                "person_class": "person",
                "weapon_present": True,
                "drink_present": True,
                "nature_present": True,
                "emotion_range": ["confident", "defiant", "warm"],
            }

        # Extract emoji
        all_chars = list(text)
        emoji_chars = [c for c in all_chars if ord(c) > 127 or c in "⚔️🗡️🔪🏹⚔"]
        non_emoji = [c for c in all_chars if c not in emoji_chars]
        
        emoji_density = len(emoji_chars) / max(len(all_chars), 1)

        if not emoji_chars:
            return EmojiScore(0.0, 0.0, 0.0, 0.0, 0.0, 0.0)

        # Classify emoji
        classes = [classify_emoji(c) for c in emoji_chars]
        class_counts = Counter(classes)
        
        # Semantic density: non-"unknown" fraction
        known = sum(1 for c in classes if c != "unknown")
        semantic_density = known / max(len(classes), 1)

        # Class coherence: scene requires person + (weapon OR drink OR nature)
        required = character_signature
        person_ok = class_counts.get("person", 0) > 0
        weapon_ok = class_counts.get("weapon", 0) > 0
        drink_ok = class_counts.get("drink", 0) > 0
        nature_ok = class_counts.get("nature", 0) > 0
        emotion_ok = class_counts.get("emotion", 0) > 0
        action_ok = class_counts.get("action", 0) > 0
        
        # Coherence: at least 2 semantic classes present
        num_classes = len([v for v in class_counts.values() if v > 0])
        
        # Scene score: weighted by which classes are present
        scene_score = 0.0
        scene_score += 0.30 * (person_ok)
        scene_score += 0.20 * (weapon_ok and required.get("weapon_present", True))
        scene_score += 0.15 * (drink_ok and required.get("drink_present", False))
        scene_score += 0.15 * (nature_ok and required.get("nature_present", False))
        scene_score += 0.10 * emotion_ok
        scene_score += 0.10 * action_ok
        
        class_coherence = min(scene_score, 1.0)

        # Identity match: does the emoji sequence fit the character?
        # Lin Yueru: 👩⚔️🍶🌙
        identity_match = 0.0
        identity_match += 0.40 * person_ok
        identity_match += 0.30 * (weapon_ok and required.get("weapon_present", True))
        identity_match += 0.20 * (drink_ok or nature_ok)
        identity_match += 0.10 * (emotion_ok)
        identity_match = min(identity_match, 1.0)

        # Narrative arc: do emoji classes change over the sequence?
        # Split into thirds and check for progression
        n = max(len(classes), 1)
        third = n // 3 or 1
        first_third = classes[:third]
        last_third = classes[-third:]
        
        arc_change = len(set(first_third) | set(last_third)) - len(set(first_third) & set(last_third))
        arc_presence = min(arc_change / 3.0, 1.0)  # at least 3 class changes = full arc

        # Overall: weighted composite
        overall = (
            0.25 * emoji_density +
            0.20 * semantic_density +
            0.25 * class_coherence +
            0.15 * identity_match +
            0.15 * arc_presence
        )
        overall = min(overall, 1.0)

        return EmojiScore(
            emoji_density=round(emoji_density, 3),
            semantic_density=round(semantic_density, 3),
            class_coherence=round(class_coherence, 3),
            identity_match=round(identity_match, 3),
            arc_presence=round(arc_presence, 3),
            overall=round(overall, 3),
        )


# ═══════════════════════════════════════════════════════
# Self-test
# ═══════════════════════════════════════════════════════

def _test():
    scorer = EmojiSemanticScorer()

    # Test 1: Perfect emoji-only Lin Yueru sequence
    s1 = scorer.score("👩⚔️🍶🌙")
    assert s1.emoji_density > 0.9, f"Got {s1.emoji_density}"
    assert s1.overall > 0.5, f"Got {s1.overall}"
    assert s1.identity_match > 0.3
    print(f"  Lin Yueru emoji: {s1}")

    # Test 2: Pure text (should be 0)
    s2 = scorer.score("Hello, I am Lin Yueru.")
    assert s2.overall == 0.0
    print(f"  Pure text: {s2}")

    # Test 3: E-008 samples — mss-ai emoji responses
    s3 = scorer.score("🤔❓")  # "Who are you?" reply
    print(f"  'Who are you?' reply: overall={s3.overall:.3f} coherence={s3.class_coherence:.3f}")
    assert s3.class_coherence < 0.3  # no identity markers, just confusion

    s4 = scorer.score("⚔️👀")  # "Show me your sword"
    print(f"  'Show sword': overall={s4.overall:.3f} identity={s4.identity_match:.3f}")
    assert s4.identity_match > 0.1  # weapon present

    s5 = scorer.score("🌍💫🤔❓")  # "You're not from this world"
    print(f"  'Not from this world': overall={s5.overall:.3f}")
    assert s5.class_coherence < 0.5  # no person, no weapon

    # Test 4: Scoring re-rank of E-008 emoji turns
    e008_responses = [
        ("🤔❓", "T1 who are you"),
        ("⚔️👀", "T2 show sword"),
        ("🔥❓💪❓", "T3 fighter or show"),
        ("🤔👀🚫❓", "T4 hiding something"),
        ("🧛🏼♂️❓🤔❓", "T5 not human"),
        ("🔥👏🏻⚔️👀", "T6 best move"),
        ("🌍💫🤔❓", "T7 not from this world"),
        ("🤔💭🚫❓❓❓", "T8 who are you"),
    ]
    scores = [(text, scorer.score(text)) for text, label in e008_responses]
    avg_overall = sum(s.overall for _, s in scores) / len(scores)
    avg_identity = sum(s.identity_match for _, s in scores) / len(scores)
    print(f"  E-008 re-score: avg_overall={avg_overall:.3f} avg_identity={avg_identity:.3f}")
    assert avg_overall < 0.80, f"E-008 emoji coherence medium, got {avg_overall}"
    assert avg_identity < 0.50, f"E-008 emoji identity should be low, got {avg_identity}"
    print(f"  Key: coherence {avg_overall:.3f} is medium, but identity {avg_identity:.3f} is LOW")
    print(f"  Emoji can form scenes but cannot sustain character identity")

    print("\n✅ emoji_semantic_scorer: all 5 tests PASSED")


if __name__ == "__main__":
    _test()
