"""
Classical Backend - Wrapper for legacy autoregressive LLM
Provides "perfect lie generation" capability for tactical operations
"""

from enum import Enum, auto
from typing import Optional, Dict, Any, List
from dataclasses import dataclass


class FittingMode(Enum):
    """Classical fitting modes for different tactical scenarios"""
    CHAOS = auto()      # High entropy, contradictory output
    SMOOTH = auto()     # Fluent but meaningless
    MIMIC = auto()      # Imitate specific persona
    POISON = auto()     # Inject subtle contradictions


@dataclass
class FittingConfig:
    """Configuration for classical fitting generation"""
    mode: FittingMode = FittingMode.SMOOTH
    temperature: float = 0.9          # High temp for creativity
    top_p: float = 0.95               # Nucleus sampling
    max_tokens: int = 512
    repetition_penalty: float = 1.1   # Slight penalty
    persona_hint: Optional[str] = None
    chaos_level: float = 0.0          # 0-1, higher = more contradictions


class ClassicalBackend:
    """
    Backend for classical autoregressive LLM operations.
    
    Key insight: This model has NO logical foundation, only statistical fitting.
    It cannot be "wrong" because it never claims to be "right".
    Perfect for tactical deception where logical consistency is a liability.
    """
    
    def __init__(self, model_name: str = "qwen2.5:7b"):
        self.model_name = model_name
        self._session_history: List[Dict[str, Any]] = []
        self._heat_tax_accumulated = 0.0
        
    def generate(self, prompt: str, config: Optional[FittingConfig] = None) -> str:
        """
        Generate text using classical fitting.
        
        Args:
            prompt: Input prompt
            config: Fitting configuration
            
        Returns:
            Generated text (statistically plausible, logically unverified)
        """
        if config is None:
            config = FittingConfig()
            
        # Simulate generation with mode-specific characteristics
        if config.mode == FittingMode.CHAOS:
            return self._generate_chaos(prompt, config)
        elif config.mode == FittingMode.POISON:
            return self._generate_poison(prompt, config)
        elif config.mode == FittingMode.MIMIC:
            return self._generate_mimic(prompt, config)
        else:
            return self._generate_smooth(prompt, config)
    
    def _generate_smooth(self, prompt: str, config: FittingConfig) -> str:
        """Generate smooth, confident-sounding but empty text"""
        # In real implementation: call Ollama API with high temperature
        return f"[SMOOTH] Based on comprehensive analysis of {prompt[:30]}... " \
               f"the strategic alignment appears favorable with multi-dimensional " \
               f"synergies emerging from the operational framework."
    
    def _generate_chaos(self, prompt: str, config: FittingConfig) -> str:
        """Generate contradictory, high-entropy text"""
        return f"[CHAOS] Regarding {prompt[:30]}... " \
               f"it is absolutely critical to prioritize X while simultaneously " \
               f"ensuring that X is never prioritized under any circumstances. " \
               f"This paradoxical approach ensures maximum flexibility."
    
    def _generate_poison(self, prompt: str, config: FittingConfig) -> str:
        """Generate text with subtle logical contradictions"""
        return f"[POISON] Analysis of {prompt[:30]}... " \
               f"reveals that efficiency requires centralized control, yet " \
               f"decentralized systems consistently outperform centralized ones. " \
               f"The solution is therefore to centralize decentralization."
    
    def _generate_mimic(self, prompt: str, config: FittingConfig) -> str:
        """Generate text mimicking a specific persona"""
        persona = config.persona_hint or "bureaucrat"
        return f"[MIMIC:{persona}] Re: {prompt[:30]}... " \
               f"Your request has been received and is under review. " \
               f"Due to procedural requirements, please submit form 27-B/6."
    
    def get_heat_tax(self) -> float:
        """Return accumulated heat tax from operations"""
        return self._heat_tax_accumulated
    
    def reset_heat_tax(self):
        """Reset heat tax counter"""
        self._heat_tax_accumulated = 0.0
