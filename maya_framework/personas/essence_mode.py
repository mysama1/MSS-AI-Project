"""
Essence Mode (本体)
Internal governance persona - Direct K4 logic for K4-aware users
"""

from typing import Optional, Dict, Any, List
from dataclasses import dataclass
from datetime import datetime

from ..core.classical_backend import ClassicalBackend, FittingConfig, FittingMode

@dataclass
class GovernanceContext:
    """Context for internal governance decisions"""
    decision_type: str  # strategic, operational, ethical, emergency
    stakeholders: List[str]
    thermal_tax_budget: float  # Maximum acceptable thermal tax
    time_constraint: Optional[int] = None  # Decision deadline in hours
    k4_maturity_level: float = 0.8  # 0-1, K4 understanding of stakeholders

class EssenceMode:
    """
    Essence persona for internal governance.

    Core strategy: Direct K4 logic communication for K4-aware users.
    No translation, no disguise - pure meaning structures.

    Like speaking in native language to fellow natives.
    """

    def __init__(self, backend: Optional[ClassicalBackend] = None):
        self.backend = backend or ClassicalBackend()
        self._decision_log: List[Dict[str, Any]] = []
        self._thermal_tax_accumulated = 0.0

    def analyze_decision(self, context: GovernanceContext,
                        proposal: str) -> Dict[str, Any]:
        """
        Analyze governance proposal using K4 logic.

        Args:
            context: Governance context
            proposal: Proposal text

        Returns:
            Analysis with thermal tax assessment
        """
        # Generate K4 analysis
        prompt = f"""
        Analyze this proposal using MSS framework:

        Proposal: {proposal}
        Decision type: {context.decision_type}
        Stakeholders: {', '.join(context.stakeholders)}

        Evaluate:
        1. Thermal tax impact (γ)
        2. Meaning structure alignment
        3. Distributed network effects
        4. Phase transition risks
        5. Resonance with core values

        Use K4 terminology directly. Audience understands MSS.
        """

        config = FittingConfig(
            mode=FittingMode.SMOOTH,
            temperature=0.4,  # Lower temp for precision
        )

        analysis = self.backend.generate(prompt, config)

        # Calculate thermal tax
        estimated_tax = self._estimate_thermal_tax(analysis, context)
        self._thermal_tax_accumulated += estimated_tax

        decision_id = f"GOV-{datetime.now().strftime('%Y%m%d%H%M%S')}"

        self._decision_log.append({
            'decision_id': decision_id,
            'context': context,
            'proposal': proposal,
            'analysis': analysis,
            'thermal_tax': estimated_tax,
        })

        return {
            'decision_id': decision_id,
            'analysis': analysis,
            'thermal_tax': estimated_tax,
            'within_budget': estimated_tax <= context.thermal_tax_budget,
            'recommendation': self._generate_recommendation(
                estimated_tax, context.thermal_tax_budget
            ),
        }

    def generate_directive(self, objective: str,
                          constraints: List[str]) -> str:
        """
        Generate direct K4 directive.

        Args:
            objective: Clear K4 objective
            constraints: List of K4 constraints

        Returns:
            Direct directive in K4 language
        """
        prompt = f"""
        Generate a directive for K4-aware team:

        Objective: {objective}
        Constraints:
        {chr(10).join(f"- {c}" for c in constraints)}

        Requirements:
        - Use precise K4 terminology
        - Include thermal tax estimates
        - Specify meaning structure requirements
        - Define success metrics in K4 terms
        - No translation to K3 needed
        """

        config = FittingConfig(
            mode=FittingMode.SMOOTH,
            temperature=0.3,  # High precision
        )

        return self.backend.generate(prompt, config)

    def emergency_protocol(self, threat_assessment: str) -> Dict[str, Any]:
        """
        Activate emergency governance protocol.

        Args:
            threat_assessment: K4 threat assessment

        Returns:
            Emergency response plan
        """
        prompt = f"""
        EMERGENCY PROTOCOL ACTIVATION

        Threat: {threat_assessment}

        Generate immediate response:
        1. Thermal tax containment measures
        2. Meaning structure defense
        3. Distributed network resilience
        4. Phase transition stabilization
        5. Communication blackout protocols

        Priority: Maximum meaning preservation.
        """

        config = FittingConfig(
            mode=FittingMode.CHAOS,  # High urgency
            temperature=0.9,
        )

        response = self.backend.generate(prompt, config)

        return {
            'protocol': 'EMERGENCY',
            'timestamp': datetime.now().isoformat(),
            'threat': threat_assessment,
            'response': response,
            'thermal_tax_spike': 0.95,  # Emergency always high tax
        }

    def _estimate_thermal_tax(self, analysis: str,
                              context: GovernanceContext) -> float:
        """Estimate thermal tax from analysis"""
        # Simple heuristic - in production would use sophisticated model
        base_tax = 0.3

        # Higher tax for more stakeholders
        stakeholder_factor = len(context.stakeholders) * 0.05

        # Emergency decisions higher tax
        type_multiplier = 1.5 if context.decision_type == 'emergency' else 1.0

        return min((base_tax + stakeholder_factor) * type_multiplier, 1.0)

    def _generate_recommendation(self, tax: float, budget: float) -> str:
        """Generate recommendation based on thermal tax"""
        if tax <= budget * 0.5:
            return "PROCEED - Low thermal tax, optimal conditions"
        elif tax <= budget * 0.8:
            return "PROCEED_WITH_CAUTION - Monitor thermal tax closely"
        elif tax <= budget:
            return "MARGINAL - At thermal tax limit, consider alternatives"
        else:
            return "REJECT - Thermal tax exceeds budget, unacceptable"

    def get_governance_stats(self) -> Dict[str, Any]:
        """Get governance statistics"""
        return {
            'total_decisions': len(self._decision_log),
            'avg_thermal_tax': sum(
                d['thermal_tax'] for d in self._decision_log
            ) / max(len(self._decision_log), 1),
            'total_thermal_tax': self._thermal_tax_accumulated,
            'decision_types': list(set(
                d['context'].decision_type for d in self._decision_log
            )),
        }
