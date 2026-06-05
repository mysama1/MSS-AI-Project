"""
Phantom Form Tactic (无相变幻术)
Strategic deception and infiltration using classical fitting AI
"""

from typing import Optional, Dict, Any, List
from dataclasses import dataclass
from datetime import datetime

from ..core.classical_backend import ClassicalBackend, FittingConfig, FittingMode
from ..core.meaning_seed import MeaningSeed, SeedLibrary

@dataclass
class InfiltrationProfile:
    """Profile for creating a convincing infiltrator persona"""
    persona_name: str
    role: str                          # e.g., "junior_analyst", "contractor"
    competence_level: float = 0.6      # 0-1, how competent they appear
    confusion_level: float = 0.3       # 0-1, how often they seem confused
    bureaucratic_fluency: float = 0.8  # 0-1, mastery of office jargon
    backstory: Optional[str] = None

class PhantomFormTactic:
    """
    Tactical scenario 1: Strategic Deception and Infiltration

    Uses classical fitting AI to create a persona that:
    - Never triggers logic errors (has no logic to violate)
    - Blends perfectly into bureaucratic systems
    - Can operate for years without detection
    - Carries meaning seeds for gradual subversion
    """

    def __init__(self, backend: Optional[ClassicalBackend] = None):
        self.backend = backend or ClassicalBackend()
        self.seed_library = SeedLibrary()
        self._active_personas: Dict[str, Dict[str, Any]] = {}
        self._operation_log: List[Dict[str, Any]] = []

    def create_persona(self, profile: InfiltrationProfile) -> str:
        """
        Create an infiltration persona.

        Returns:
            persona_id: Unique identifier for this persona
        """
        persona_id = f"PHANTOM-{profile.persona_name}-{datetime.now().strftime('%Y%m%d%H%M%S')}"

        # Generate persona backstory using classical fitting
        backstory_prompt = f"""
        Create a brief professional background for a {profile.role} named {profile.persona_name}.
        They should appear {profile.competence_level*100:.0f}% competent but occasionally confused.
        """

        config = FittingConfig(
            mode=FittingMode.MIMIC,
            persona_hint=profile.role,
            temperature=0.8,
        )

        backstory = self.backend.generate(backstory_prompt, config)

        self._active_personas[persona_id] = {
            'profile': profile,
            'backstory': backstory,
            'created_at': datetime.now().isoformat(),
            'interactions': 0,
            'seeds_planted': [],
        }

        self._log_operation('CREATE_PERSONA', persona_id, profile.role)
        return persona_id

    def interact(self, persona_id: str, incoming_message: str,
                 plant_seed: Optional[str] = None) -> str:
        """
        Generate a response from the infiltrator persona.

        Args:
            persona_id: Active persona ID
            incoming_message: Message from target system
            plant_seed: Optional seed ID to embed in response

        Returns:
            Response that appears human but carries tactical payload
        """
        if persona_id not in self._active_personas:
            raise ValueError(f"Unknown persona: {persona_id}")

        persona = self._active_personas[persona_id]
        profile = persona['profile']

        # Generate response using classical fitting
        prompt = f"""
        As {profile.persona_name}, a {profile.role}, respond to:
        \"{incoming_message}\"

        Guidelines:
        - Be {profile.competence_level*100:.0f}% helpful, {profile.confusion_level*100:.0f}% confused
        - Use bureaucratic language naturally
        - Never admit ignorance directly
        - If unsure, deflect with process
        """

        config = FittingConfig(
            mode=FittingMode.MIMIC,
            persona_hint=profile.role,
            temperature=0.7 + (profile.confusion_level * 0.3),
        )

        response = self.backend.generate(prompt, config)

        # Embed meaning seed if specified
        if plant_seed:
            seed = self.seed_library.get_seed(plant_seed)
            if seed:
                response = seed.embed(response)
                persona['seeds_planted'].append(plant_seed)

        persona['interactions'] += 1
        self._log_operation('INTERACT', persona_id,
                           f"interactions={persona['interactions']}")

        return response

    def extract_intelligence(self, persona_id: str) -> Dict[str, Any]:
        """
        Extract accumulated intelligence from a persona's interactions.
        Simulates data gathered during infiltration.
        """
        if persona_id not in self._active_personas:
            raise ValueError(f"Unknown persona: {persona_id}")

        persona = self._active_personas[persona_id]

        return {
            'persona_id': persona_id,
            'interactions': persona['interactions'],
            'seeds_planted': persona['seeds_planted'],
            'operational_duration': self._calculate_duration(persona['created_at']),
            'intelligence_value': self._estimate_intelligence_value(persona),
        }

    def _calculate_duration(self, created_at: str) -> str:
        """Calculate operational duration"""
        created = datetime.fromisoformat(created_at)
        duration = datetime.now() - created
        return str(duration)

    def _estimate_intelligence_value(self, persona: Dict[str, Any]) -> float:
        """Estimate value of intelligence gathered"""
        base_value = persona['interactions'] * 0.1
        seed_bonus = len(persona['seeds_planted']) * 0.5
        return min(base_value + seed_bonus, 10.0)

    def _log_operation(self, operation: str, target: str, details: str):
        """Log tactical operation"""
        self._operation_log.append({
            'timestamp': datetime.now().isoformat(),
            'operation': operation,
            'target': target,
            'details': details,
        })

    def get_operation_log(self) -> List[Dict[str, Any]]:
        """Get full operation log"""
        return self._operation_log.copy()
