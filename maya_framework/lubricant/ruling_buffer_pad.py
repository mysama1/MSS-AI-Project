"""
Ruling Buffer Pad (裁决缓冲垫)
Prevents rigid K4 rulings from causing system fractures
"""

from typing import Optional, Dict, Any, List
from dataclasses import dataclass
from datetime import datetime

from ..core.classical_backend import ClassicalBackend, FittingConfig, FittingMode

@dataclass
class RulingContext:
    """Context for ruling generation"""
    ruling_type: str  # accept, reject, modify, defer
    severity: float  # 0-1, severity of ruling
    stakeholder_impact: List[str]  # Affected stakeholders
    reversibility: float  # 0-1, how reversible the ruling is
    time_pressure: float  # 0-1, urgency

class RulingBufferPad:
    """
    Buffers rigid K4 rulings to prevent system fractures.

    Like a shock absorber - takes the impact of a hard decision
    and distributes it gradually.
    """

    def __init__(self, backend: Optional[ClassicalBackend] = None):
        self.backend = backend or ClassicalBackend()
        self._ruling_history: List[Dict[str, Any]] = []

    def buffer_ruling(self, k4_ruling: str, context: RulingContext) -> Dict[str, Any]:
        """
        Buffer a K4 ruling for human delivery.

        Args:
            k4_ruling: Raw K4 ruling
            context: Ruling context

        Returns:
            Buffered ruling with delivery strategy
        """
        # Determine buffering level
        buffer_level = self._calculate_buffer_level(context)

        # Generate buffered version
        buffered_ruling = self._apply_buffer(k4_ruling, buffer_level, context)

        # Generate delivery strategy
        delivery_strategy = self._generate_delivery_strategy(context, buffer_level)

        ruling_id = f"RULING-{datetime.now().strftime('%Y%m%d%H%M%S')}"

        self._ruling_history.append({
            'ruling_id': ruling_id,
            'k4_ruling': k4_ruling,
            'buffered_ruling': buffered_ruling,
            'buffer_level': buffer_level,
            'context': context,
        })

        return {
            'ruling_id': ruling_id,
            'buffered_ruling': buffered_ruling,
            'delivery_strategy': delivery_strategy,
            'buffer_level': buffer_level,
            'original_severity': context.severity,
            'effective_severity': context.severity * (1 - buffer_level * 0.3),
        }

    def _calculate_buffer_level(self, context: RulingContext) -> float:
        """Calculate required buffer level"""
        # Higher severity = more buffering
        severity_factor = context.severity

        # More stakeholders = more buffering
        stakeholder_factor = min(len(context.stakeholder_impact) * 0.1, 0.3)

        # Low reversibility = more buffering
        reversibility_factor = (1 - context.reversibility) * 0.3

        # High time pressure = less buffering (need to act)
        time_factor = (1 - context.time_pressure) * 0.2

        buffer_level = (severity_factor + stakeholder_factor +
                       reversibility_factor + time_factor)

        return min(buffer_level, 1.0)

    def _apply_buffer(self, k4_ruling: str, buffer_level: float,
                      context: RulingContext) -> str:
        """Apply buffering to ruling"""
        if buffer_level < 0.3:
            # Light buffer - just soften language
            return self._soften_language(k4_ruling)
        elif buffer_level < 0.6:
            # Medium buffer - add context and alternatives
            return self._add_context(k4_ruling, context)
        else:
            # Heavy buffer - gradual reveal with safety nets
            return self._heavy_buffer(k4_ruling, context)

    def _soften_language(self, ruling: str) -> str:
        """Soften language without changing meaning"""
        replacements = {
            "must": "should strongly consider",
            "cannot": "is not recommended",
            "will fail": "may face significant challenges",
            "impossible": "extremely difficult",
            "certainly": "with high probability",
        }

        result = ruling
        for hard, soft in replacements.items():
            result = result.replace(hard, soft)

        return result

    def _add_context(self, ruling: str, context: RulingContext) -> str:
        """Add context and alternatives"""
        softened = self._soften_language(ruling)

        context_addition = (
            f"\n\nContext: This ruling affects {len(context.stakeholder_impact)} "
            f"stakeholder groups. While the structural analysis suggests this path, "
            f"implementation can be adjusted based on feedback."
        )

        alternatives = (
            f"\n\nAlternatives to consider:\n"
            f"- Phased implementation over time\n"
            f"- Pilot program with subset of stakeholders\n"
            f"- Modified version with reduced scope"
        )

        return f"{softened}{context_addition}{alternatives}"

    def _heavy_buffer(self, ruling: str, context: RulingContext) -> str:
        """Apply heavy buffering with safety nets"""
        softened = self._soften_language(ruling)

        preamble = (
            "After careful analysis of multiple factors, "
            "the current recommendation is:\n\n"
        )

        safety_net = (
            f"\n\nImportant: This is a recommendation, not an absolute directive. "
            f"Given the impact on {len(context.stakeholder_impact)} groups, "
            f"we suggest:\n"
            f"1. Review period of 48-72 hours\n"
            f"2. Feedback collection from key stakeholders\n"
            f"3. Adjustment window before finalization\n"
            f"4. Clear reversal criteria if conditions change"
        )

        return f"{preamble}{softened}{safety_net}"

    def _generate_delivery_strategy(self, context: RulingContext,
                                    buffer_level: float) -> Dict[str, Any]:
        """Generate delivery strategy for buffered ruling"""
        if buffer_level < 0.3:
            return {
                'method': 'direct',
                'timing': 'immediate',
                'follow_up': 'none',
            }
        elif buffer_level < 0.6:
            return {
                'method': 'staged',
                'timing': 'within 24 hours',
                'follow_up': 'check_in_1_week',
            }
        else:
            return {
                'method': 'gradual',
                'timing': 'over_3_days',
                'follow_up': 'daily_check_ins',
                'support_resources': 'dedicated_liaison',
            }

    def get_ruling_stats(self) -> Dict[str, Any]:
        """Get ruling statistics"""
        if not self._ruling_history:
            return {'total_rulings': 0}

        avg_buffer = sum(r['buffer_level'] for r in self._ruling_history) / len(self._ruling_history)

        return {
            'total_rulings': len(self._ruling_history),
            'avg_buffer_level': avg_buffer,
            'high_buffer_rulings': sum(1 for r in self._ruling_history if r['buffer_level'] > 0.6),
        }
