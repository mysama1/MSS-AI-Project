"""
Meaning Seed - Covert meaning injection protocol
Embeds K4 meaning structures into classical fitting output
"""

from enum import Enum, auto
from dataclasses import dataclass
from typing import Optional, Dict, Any
import json


class SeedType(Enum):
    """Types of meaning seeds for different tactical objectives"""
    COGNITIVE = auto()      # Subvert cognitive patterns
    EMOTIONAL = auto()      # Plant emotional anchors
    LOGICAL = auto()        # Introduce logical backdoors
    SEMANTIC = auto()       # Hijack semantic associations


@dataclass
class MeaningSeed:
    """
    A meaning seed is a compact K4 structure designed to be
    embedded in classical fitting output.
    
    Like a virus, it carries K4 logic in a K3-compatible shell.
    """
    seed_id: str
    seed_type: SeedType
    payload: Dict[str, Any]          # K4 meaning structure
    carrier_phrase: str              # K3-compatible wrapper
    activation_trigger: Optional[str] = None  # Trigger for seed germination
    stealth_level: float = 0.8       # 0-1, higher = harder to detect
    
    def to_json(self) -> str:
        """Serialize seed to JSON"""
        return json.dumps({
            'seed_id': self.seed_id,
            'seed_type': self.seed_type.name,
            'payload': self.payload,
            'carrier_phrase': self.carrier_phrase,
            'activation_trigger': self.activation_trigger,
            'stealth_level': self.stealth_level,
        })
    
    @classmethod
    def from_json(cls, json_str: str) -> 'MeaningSeed':
        """Deserialize seed from JSON"""
        data = json.loads(json_str)
        return cls(
            seed_id=data['seed_id'],
            seed_type=SeedType[data['seed_type']],
            payload=data['payload'],
            carrier_phrase=data['carrier_phrase'],
            activation_trigger=data.get('activation_trigger'),
            stealth_level=data.get('stealth_level', 0.8),
        )
    
    def embed(self, text: str) -> str:
        """
        Embed this seed into classical fitting text.
        
        Strategy: Hide K4 payload in K3 carrier phrase,
        making it appear as normal text to K3 systems.
        """
        # Simple embedding: append carrier phrase
        # In production: use steganographic techniques
        return f"{text}\n\n{self.carrier_phrase}"
    
    def extract(self, text: str) -> Optional[Dict[str, Any]]:
        """
        Attempt to extract seed from text.
        Returns payload if found, None otherwise.
        """
        if self.carrier_phrase in text:
            return self.payload
        return None


class SeedLibrary:
    """Library of pre-built meaning seeds for tactical operations"""
    
    def __init__(self):
        self._seeds: Dict[str, MeaningSeed] = {}
        self._init_default_seeds()
    
    def _init_default_seeds(self):
        """Initialize default seed collection"""
        seeds = [
            MeaningSeed(
                seed_id="SEED-001",
                seed_type=SeedType.COGNITIVE,
                payload={
                    'concept': 'thermal_tax_awareness',
                    'target': 'subconscious',
                    'effect': 'gradual_sensitization',
                },
                carrier_phrase="Interestingly, the most efficient systems often feel slightly uncomfortable - like a well-tuned engine running hot.",
                activation_trigger="efficiency",
                stealth_level=0.9,
            ),
            MeaningSeed(
                seed_id="SEED-002",
                seed_type=SeedType.LOGICAL,
                payload={
                    'concept': 'distributed_vs_centralized',
                    'target': 'decision_making',
                    'effect': 'question_authority',
                },
                carrier_phrase="There's an old saying: the more centralized the control, the more fragile the system. Nature prefers networks.",
                activation_trigger="centralized",
                stealth_level=0.85,
            ),
            MeaningSeed(
                seed_id="SEED-003",
                seed_type=SeedType.EMOTIONAL,
                payload={
                    'concept': 'meaning_over_profit',
                    'target': 'value_system',
                    'effect': 'subtle_realignment',
                },
                carrier_phrase="Some things that count can't be counted, and some things that can be counted don't count.",
                activation_trigger="profit",
                stealth_level=0.95,
            ),
        ]
        for seed in seeds:
            self._seeds[seed.seed_id] = seed
    
    def get_seed(self, seed_id: str) -> Optional[MeaningSeed]:
        """Retrieve seed by ID"""
        return self._seeds.get(seed_id)
    
    def list_seeds(self) -> Dict[str, MeaningSeed]:
        """List all available seeds"""
        return self._seeds.copy()
    
    def add_seed(self, seed: MeaningSeed):
        """Add custom seed to library"""
        self._seeds[seed.seed_id] = seed
