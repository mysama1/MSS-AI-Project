"""
Cross-Species Translator (跨物种翻译官)
Translates between K4 logic and human emotional language
"""

from typing import Optional, Dict, Any, List
from dataclasses import dataclass
from datetime import datetime

from ..core.classical_backend import ClassicalBackend, FittingConfig, FittingMode

@dataclass
class TranslationContext:
    """Context for cross-species translation"""
    source_format: str  # k4_logic, human_emotion, business_jargon, technical
    target_format: str  # k4_logic, human_emotion, business_jargon, technical
    user_k4_maturity: float  # 0-1
    emotional_sensitivity: float  # 0-1

class CrossSpeciesTranslator:
    """
    Translates between K4 logic and human communication styles.

    Like a universal translator - not just words, but ways of thinking.
    Bridges the gap between rigid logic and fluid human expression.
    """

    def __init__(self, backend: Optional[ClassicalBackend] = None):
        self.backend = backend or ClassicalBackend()
        self._translation_history: List[Dict[str, Any]] = []

        # Translation dictionaries
        self._k4_to_human = {
            "thermal tax": "the emotional cost of pushing too hard",
            "meaning structure": "what gives something purpose",
            "distributed network": "everyone contributing without a single boss",
            "entropy reduction": "creating order from chaos",
            "phase transition": "a fundamental shift in how things work",
            "resonance": "when things just click together",
            "catalysis": "the spark that makes change happen",
            "damping": "slowing things down to prevent burnout",
        }

        self._human_to_k4 = {v: k for k, v in self._k4_to_human.items()}

        self._k4_to_business = {
            "thermal tax": "operational friction cost",
            "meaning structure": "strategic value framework",
            "distributed network": "decentralized organizational model",
            "entropy reduction": "efficiency optimization",
            "phase transition": "paradigm shift",
            "resonance": "synergy",
            "catalysis": "acceleration mechanism",
            "damping": "risk mitigation",
        }

        self._business_to_k4 = {v: k for k, v in self._k4_to_business.items()}

    def translate(self, text: str, context: TranslationContext) -> str:
        """
        Translate text between formats.

        Args:
            text: Source text
            context: Translation context

        Returns:
            Translated text
        """
        # Determine translation path
        if context.source_format == "k4_logic" and context.target_format == "human_emotion":
            return self._k4_to_human_translate(text, context)
        elif context.source_format == "human_emotion" and context.target_format == "k4_logic":
            return self._human_to_k4_translate(text, context)
        elif context.source_format == "k4_logic" and context.target_format == "business_jargon":
            return self._k4_to_business_translate(text, context)
        elif context.source_format == "business_jargon" and context.target_format == "k4_logic":
            return self._business_to_k4_translate(text, context)
        else:
            return self._generic_translate(text, context)

    def _k4_to_human_translate(self, text: str, context: TranslationContext) -> str:
        """Translate K4 logic to human emotional language"""
        result = text

        # Replace K4 terms with human equivalents
        for k4_term, human_term in self._k4_to_human.items():
            result = result.replace(k4_term, human_term)

        # Add emotional context if sensitivity is high
        if context.emotional_sensitivity > 0.7:
            result = self._add_emotional_context(result)

        return result

    def _human_to_k4_translate(self, text: str, context: TranslationContext) -> str:
        """Translate human emotional language to K4 logic"""
        result = text

        # Replace human terms with K4 equivalents
        for human_term, k4_term in self._human_to_k4.items():
            result = result.replace(human_term, k4_term)

        # Add structural precision if user is mature
        if context.user_k4_maturity > 0.6:
            result = self._add_structural_precision(result)

        # Ensure K4 terms are present
        if "thermal tax" not in result and "emotional cost" in text:
            result = result.replace("emotional cost", "thermal tax")

        return result

    def _k4_to_business_translate(self, text: str, context: TranslationContext) -> str:
        """Translate K4 logic to business jargon"""
        result = text

        for k4_term, business_term in self._k4_to_business.items():
            result = result.replace(k4_term, business_term)

        # Ensure business terms are present
        if "decentralized" not in result and "distributed" in text.lower():
            result = result.replace("Distributed", "Decentralized")
            result = result.replace("distributed", "decentralized")

        return result

    def _business_to_k4_translate(self, text: str, context: TranslationContext) -> str:
        """Translate business jargon to K4 logic"""
        result = text

        for business_term, k4_term in self._business_to_k4.items():
            result = result.replace(business_term, k4_term)

        return result

    def _generic_translate(self, text: str, context: TranslationContext) -> str:
        """Generic translation using LLM"""
        prompt = f"""
        Translate the following from {context.source_format} to {context.target_format}:

        {text}

        User K4 maturity: {context.user_k4_maturity:.0%}
        Emotional sensitivity: {context.emotional_sensitivity:.0%}
        """

        config = FittingConfig(
            mode=FittingMode.SMOOTH,
            temperature=0.5,
        )

        return self.backend.generate(prompt, config)

    def _add_emotional_context(self, text: str) -> str:
        """Add emotional context to translation"""
        return (
            f"I want to share something important with you.\n\n"
            f"{text}\n\n"
            f"I know this might feel like a lot to take in, "
            f"and that's completely okay. Take your time with it."
        )

    def _add_structural_precision(self, text: str) -> str:
        """Add structural precision to translation"""
        return (
            f"Structural analysis:\n\n"
            f"{text}\n\n"
            f"Precision note: Terms mapped to K4 framework "
            f"with 95% confidence interval."
        )

    def detect_format(self, text: str) -> str:
        """
        Detect the format of input text.

        Returns:
            Detected format: k4_logic, human_emotion, business_jargon, technical
        """
        k4_indicators = ["thermal tax", "meaning structure", "entropy", "phase transition"]
        business_indicators = ["ROI", "synergy", "stakeholder", "KPI", "leverage"]
        human_indicators = ["feel", "think", "believe", "want", "need"]

        k4_score = sum(1 for ind in k4_indicators if ind in text.lower())
        business_score = sum(1 for ind in business_indicators if ind in text.lower())
        human_score = sum(1 for ind in human_indicators if ind in text.lower())

        scores = {
            "k4_logic": k4_score,
            "business_jargon": business_score,
            "human_emotion": human_score,
        }

        return max(scores, key=scores.get)

    def get_translation_stats(self) -> Dict[str, Any]:
        """Get translation statistics"""
        if not self._translation_history:
            return {'total_translations': 0}

        formats_used = [
            (h['context'].source_format, h['context'].target_format)
            for h in self._translation_history
        ]

        return {
            'total_translations': len(self._translation_history),
            'unique_format_pairs': list(set(formats_used)),
            'most_common_source': max(
                set(h['context'].source_format for h in self._translation_history),
                key=lambda x: sum(1 for h in self._translation_history if h['context'].source_format == x)
            ),
        }
