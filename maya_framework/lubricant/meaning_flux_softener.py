"""
Meaning Flux Softener (意义通量柔顺剂)
Reduces cognitive friction when K4 logic encounters human emotion
"""

from typing import Optional, Dict, Any, List
from dataclasses import dataclass
from datetime import datetime
import random

from ..core.classical_backend import ClassicalBackend, FittingConfig, FittingMode

@dataclass
class SofteningContext:
    """Context for meaning flux softening"""
    user_emotional_state: str  # frustrated, confused, excited, anxious, neutral
    conversation_history_length: int
    k4_complexity_level: float  # 0-1
    user_k4_maturity: float  # 0-1, user's understanding of K4

class MeaningFluxSoftener:
    """
    Softens rigid K4 output for human consumption.

    Like adding a cushion between a hard truth and a sensitive ear.
    Maintains K4 accuracy while reducing emotional impact.
    """

    def __init__(self, backend: Optional[ClassicalBackend] = None):
        self.backend = backend or ClassicalBackend()
        self._softening_history: List[Dict[str, Any]] = []

    def soften_output(self, k4_output: str, context: SofteningContext) -> str:
        """
        Soften K4 output for human consumption.

        Args:
            k4_output: Raw K4 logic output
            context: Softening context

        Returns:
            Softened output maintaining accuracy but reducing friction
        """
        # Determine softening strategy
        strategy = self._select_strategy(context)

        # Apply softening
        if strategy == "direct":
            return k4_output  # No softening needed
        elif strategy == "cushioned":
            return self._apply_cushion(k4_output, context)
        elif strategy == "gradual":
            return self._apply_gradual_reveal(k4_output, context)
        elif strategy == "metaphorical":
            return self._apply_metaphor(k4_output, context)
        else:
            return self._apply_emotional_buffer(k4_output, context)

    def _select_strategy(self, context: SofteningContext) -> str:
        """Select softening strategy based on context"""
        if context.user_k4_maturity > 0.8 and context.user_emotional_state == "neutral":
            return "direct"
        elif context.user_k4_maturity > 0.5:
            return "cushioned"
        elif context.user_emotional_state in ["frustrated", "anxious"]:
            return "emotional_buffer"
        elif context.conversation_history_length < 3:
            return "gradual"
        else:
            return "metaphorical"

    def _apply_cushion(self, k4_output: str, context: SofteningContext) -> str:
        """Add cushioning language around K4 output"""
        cushions = [
            "From one perspective, ",
            "It's worth considering that ",
            "A useful way to think about this is ",
            "If we look at it structurally, ",
        ]
        cushion = random.choice(cushions)
        return f"{cushion}{k4_output}"

    def _apply_gradual_reveal(self, k4_output: str, context: SofteningContext) -> str:
        """Reveal K4 logic gradually"""
        # Split into parts and reveal step by step
        parts = k4_output.split('. ')
        if len(parts) > 2:
            return (
                f"Let's break this down step by step.\n\n"
                f"First, {parts[0]}.\n\n"
                f"Then, {parts[1]}.\n\n"
                f"This leads us to: {'. '.join(parts[2:])}"
            )
        return k4_output

    def _apply_metaphor(self, k4_output: str, context: SofteningContext) -> str:
        """Translate K4 into metaphor"""
        # Simple metaphor mapping
        metaphor = self._generate_metaphor(context)
        return (
            f"Think of it this way: {metaphor}\n\n"
            f"In more precise terms: {k4_output}"
        )

    def _generate_metaphor(self, context: SofteningContext) -> str:
        """Generate appropriate metaphor"""
        metaphors = {
            "frustrated": "like untangling a knot - it seems impossible at first, but there's always a path through",
            "confused": "like learning a new language - every expert was once a beginner",
            "anxious": "like standing at the edge of a pool - the water is fine once you ease in",
            "excited": "like discovering a hidden path in a familiar forest",
            "neutral": "like adjusting the focus on a camera - suddenly everything becomes clear",
        }
        return metaphors.get(
            context.user_emotional_state,
            "like solving a puzzle - each piece has its place"
        )

    def _apply_emotional_buffer(self, k4_output: str, context: SofteningContext) -> str:
        """Add emotional buffering for sensitive states"""
        buffer_prefix = (
            "I understand this might feel challenging to hear, "
            "and it's completely valid to take time processing it.\n\n"
        )
        buffer_suffix = (
            "\n\nRemember, this is just one way to understand the situation. "
            "Your perspective and feelings matter equally."
        )
        return f"{buffer_prefix}{k4_output}{buffer_suffix}"

    def get_softening_stats(self) -> Dict[str, Any]:
        """Get softening statistics"""
        if not self._softening_history:
            return {'total_interactions': 0}

        strategies_used = [h['strategy'] for h in self._softening_history]

        return {
            'total_interactions': len(self._softening_history),
            'strategies_used': list(set(strategies_used)),
            'most_common_strategy': max(set(strategies_used), key=strategies.count),
        }
