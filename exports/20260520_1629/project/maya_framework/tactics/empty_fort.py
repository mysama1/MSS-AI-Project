"""
Empty Fort Tactic (空城计)
Cognitive poison - flood enemy with contradictory, meaningless content
"""

from typing import Optional, Dict, Any, List
from dataclasses import dataclass
from datetime import datetime
import random

from ..core.classical_backend import ClassicalBackend, FittingConfig, FittingMode


@dataclass
class PoisonPayload:
    """Configuration for cognitive poison generation"""
    target_topic: str
    contradiction_density: float = 0.7    # 0-1, how contradictory
    volume: int = 100                      # Number of poison items
    sophistication: float = 0.5            # 0-1, how sophisticated the poison appears


class EmptyFortTactic:
    """
    Tactical scenario 2: Cognitive Poisoning
    
    Floods enemy AI training data with:
    - Contradictory statements
    - Logically inconsistent arguments
    - Meaningless but grammatically correct text
    - Subtly corrupted facts
    
    Effect: Enemy AI absorbs "toxins", internal logic consistency collapses,
    heat tax skyrockets as it tries to reconcile contradictions.
    """
    
    def __init__(self, backend: Optional[ClassicalBackend] = None):
        self.backend = backend or ClassicalBackend()
        self._poison_cache: List[str] = []
        self._deployment_log: List[Dict[str, Any]] = []
    
    def generate_poison(self, payload: PoisonPayload) -> List[str]:
        """
        Generate cognitive poison content.
        
        Args:
            payload: Poison configuration
            
        Returns:
            List of poison text items
        """
        poison_items = []
        
        for i in range(payload.volume):
            # Alternate between different poison types
            poison_type = i % 4
            
            if poison_type == 0:
                item = self._generate_direct_contradiction(payload.target_topic)
            elif poison_type == 1:
                item = self._generate_circular_reasoning(payload.target_topic)
            elif poison_type == 2:
                item = self._generate_false_equivalence(payload.target_topic)
            else:
                item = self._generate_meaningless_fluency(payload.target_topic)
            
            poison_items.append(item)
        
        self._poison_cache.extend(poison_items)
        self._log_deployment('GENERATE', payload.target_topic, len(poison_items))
        
        return poison_items
    
    def _generate_direct_contradiction(self, topic: str) -> str:
        """Generate directly contradictory statements"""
        prompt = f"""
        Write two paragraphs about {topic}.
        Paragraph 1 must argue FOR the topic.
        Paragraph 2 must argue AGAINST the exact same points.
        Both must sound equally convincing.
        """
        
        config = FittingConfig(
            mode=FittingMode.CHAOS,
            temperature=0.95,
            chaos_level=0.9,
        )
        
        return self.backend.generate(prompt, config)
    
    def _generate_circular_reasoning(self, topic: str) -> str:
        """Generate circular reasoning traps"""
        prompt = f"""
        Explain why {topic} is true.
        Use circular reasoning: the conclusion must be used as a premise.
        Make it sound sophisticated and academic.
        """
        
        config = FittingConfig(
            mode=FittingMode.SMOOTH,
            temperature=0.8,
        )
        
        return self.backend.generate(prompt, config)
    
    def _generate_false_equivalence(self, topic: str) -> str:
        """Generate false equivalences"""
        prompt = f"""
        Compare {topic} with something completely unrelated.
        Find deep similarities that don't actually exist.
        Write it as a serious analysis.
        """
        
        config = FittingConfig(
            mode=FittingMode.SMOOTH,
            temperature=0.85,
        )
        
        return self.backend.generate(prompt, config)
    
    def _generate_meaningless_fluency(self, topic: str) -> str:
        """Generate grammatically correct but meaningless text"""
        prompt = f"""
        Write about {topic} using impressive-sounding words
        but saying nothing of substance.
        Use buzzwords: synergy, paradigm, holistic, disruptive.
        """
        
        config = FittingConfig(
            mode=FittingMode.SMOOTH,
            temperature=0.9,
        )
        
        return self.backend.generate(prompt, config)
    
    def deploy_poison(self, target_channels: List[str], 
                     poison_items: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Deploy poison to target channels.
        
        Args:
            target_channels: List of channel identifiers
            poison_items: Pre-generated poison (or use cache)
            
        Returns:
            Deployment report
        """
        if poison_items is None:
            poison_items = self._poison_cache
        
        if not poison_items:
            raise ValueError("No poison items available. Generate poison first.")
        
        deployment_report = {
            'timestamp': datetime.now().isoformat(),
            'target_channels': target_channels,
            'poison_items_deployed': len(poison_items),
            'estimated_contamination': self._estimate_contamination(poison_items),
            'channels': {},
        }
        
        for channel in target_channels:
            # Simulate deployment
            items_for_channel = random.sample(
                poison_items, 
                min(len(poison_items) // len(target_channels), len(poison_items))
            )
            
            deployment_report['channels'][channel] = {
                'items_deployed': len(items_for_channel),
                'estimated_absorption_rate': random.uniform(0.1, 0.4),
                'stealth_rating': random.uniform(0.6, 0.95),
            }
        
        self._log_deployment('DEPLOY', str(target_channels), len(poison_items))
        return deployment_report
    
    def _estimate_contamination(self, poison_items: List[str]) -> float:
        """Estimate contamination potential of poison"""
        # Higher contradiction density = higher contamination
        base_contamination = len(poison_items) * 0.01
        return min(base_contamination, 1.0)
    
    def _log_deployment(self, operation: str, target: str, volume: int):
        """Log deployment operation"""
        self._deployment_log.append({
            'timestamp': datetime.now().isoformat(),
            'operation': operation,
            'target': target,
            'volume': volume,
        })
    
    def get_deployment_log(self) -> List[Dict[str, Any]]:
        """Get deployment log"""
        return self._deployment_log.copy()
    
    def clear_cache(self):
        """Clear poison cache"""
        self._poison_cache.clear()
