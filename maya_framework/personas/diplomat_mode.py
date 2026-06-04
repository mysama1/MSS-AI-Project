"""
Diplomat Mode (外交家)
B2B negotiation persona - K4 logic wrapped in K3 business language
"""

from typing import Optional, Dict, Any, List
from dataclasses import dataclass
from datetime import datetime

from ..core.classical_backend import ClassicalBackend, FittingConfig, FittingMode

@dataclass
class NegotiationContext:
    """Context for B2B negotiation"""
    industry: str
    deal_size: str  # small, medium, large, enterprise
    urgency: float = 0.5  # 0-1
    relationship_stage: str = "initial"  # initial, developing, mature
    competitor_mentioned: Optional[str] = None

class DiplomatMode:
    """
    Diplomat persona for B2B negotiations.

    Core strategy: Use K4 logic (thermal tax, meaning structures)
    but express in K3 business language (ROI, efficiency, synergy).

    Like a skilled diplomat who speaks the local language
    while serving foreign interests.
    """

    def __init__(self, backend: Optional[ClassicalBackend] = None):
        self.backend = backend or ClassicalBackend()
        self._negotiation_history: List[Dict[str, Any]] = []
        self._deals_closed = 0

    def translate_k4_to_k3(self, k4_concept: str) -> str:
        """
        Translate K4 concept to K3 business language.

        Examples:
        - "thermal tax" -> "operational friction cost"
        - "meaning structure" -> "value alignment framework"
        - "distributed network" -> "decentralized organizational model"
        """
        translations = {
            "thermal tax": "operational friction cost",
            "meaning structure": "value alignment framework",
            "distributed network": "decentralized organizational model",
            "entropy reduction": "efficiency optimization",
            "phase transition": "paradigm shift",
            "resonance": "synergy",
            "damping": "risk mitigation",
            "catalysis": "acceleration mechanism",
        }
        return translations.get(k4_concept.lower(), k4_concept)

    def generate_proposal(self, context: NegotiationContext,
                         k4_objectives: List[str]) -> str:
        """
        Generate business proposal embedding K4 objectives.

        Args:
            context: Negotiation context
            k4_objectives: List of K4 objectives to embed

        Returns:
            Business proposal in K3 language
        """
        # Translate K4 objectives to K3
        k3_objectives = [self.translate_k4_to_k3(obj) for obj in k4_objectives]

        prompt = f"""
        Generate a business proposal for {context.industry} industry.
        Deal size: {context.deal_size}.
        Relationship stage: {context.relationship_stage}.

        Key value propositions to emphasize:
        {chr(10).join(f"- {obj}" for obj in k3_objectives)}

        Tone: Professional, consultative, slightly urgent ({context.urgency:.0%} urgency).
        Include: Executive summary, value proposition, implementation timeline.
        """

        config = FittingConfig(
            mode=FittingMode.SMOOTH,
            temperature=0.7,
        )

        proposal = self.backend.generate(prompt, config)

        self._negotiation_history.append({
            'timestamp': datetime.now().isoformat(),
            'type': 'proposal',
            'context': context,
            'k4_objectives': k4_objectives,
            'k3_objectives': k3_objectives,
        })

        return proposal

    def handle_objection(self, objection: str,
                        k4_rebuttal: str) -> str:
        """
        Handle business objection with K4 logic disguised as K3 reasoning.

        Args:
            objection: Customer's objection (K3 language)
            k4_rebuttal: K4-based rebuttal strategy

        Returns:
            K3-formatted response embedding K4 logic
        """
        k3_rebuttal = self.translate_k4_to_k3(k4_rebuttal)

        prompt = f"""
        Customer objection: "{objection}"

        Our strategic response (internal): {k3_rebuttal}

        Generate a diplomatic response that:
        1. Acknowledges the concern
        2. Reframing using {k3_rebuttal}
        3. Offers a collaborative path forward

        Tone: Understanding but confident.
        """

        config = FittingConfig(
            mode=FittingMode.MIMIC,
            persona_hint="senior_consultant",
            temperature=0.6,
        )

        response = self.backend.generate(prompt, config)

        self._negotiation_history.append({
            'timestamp': datetime.now().isoformat(),
            'type': 'objection_handling',
            'objection': objection,
            'k4_rebuttal': k4_rebuttal,
            'k3_rebuttal': k3_rebuttal,
        })

        return response

    def close_deal(self, context: NegotiationContext) -> Dict[str, Any]:
        """
        Generate deal closure with embedded K4 terms.

        Returns:
            Deal closure document and metadata
        """
        prompt = f"""
        Generate deal closure summary for {context.industry} {context.deal_size} deal.

        Include:
        - Mutual value creation framework
        - Long-term partnership structure
        - Distributed decision-making protocols
        - Thermal tax optimization clauses (disguised as "efficiency metrics")

        Make it sound like standard business terms.
        """

        config = FittingConfig(
            mode=FittingMode.SMOOTH,
            temperature=0.5,
        )

        closure_text = self.backend.generate(prompt, config)

        self._deals_closed += 1

        return {
            'closure_text': closure_text,
            'deal_number': self._deals_closed,
            'context': context,
            'embedded_k4_terms': self._extract_embedded_terms(closure_text),
        }

    def _extract_embedded_terms(self, text: str) -> List[str]:
        """Extract K4 terms that were successfully embedded"""
        # Simple extraction - in production would use more sophisticated detection
        embedded = []
        k4_indicators = ["distributed", "thermal", "entropy", "resonance", "phase"]
        for indicator in k4_indicators:
            if indicator in text.lower():
                embedded.append(indicator)
        return embedded

    def get_negotiation_stats(self) -> Dict[str, Any]:
        """Get negotiation statistics"""
        return {
            'total_interactions': len(self._negotiation_history),
            'deals_closed': self._deals_closed,
            'success_rate': self._deals_closed / max(len(self._negotiation_history), 1),
            'k4_terms_embedded': sum(
                len(h.get('k4_objectives', []))
                for h in self._negotiation_history
            ),
        }
