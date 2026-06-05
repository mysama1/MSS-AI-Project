"""
Tactical Heat Tax Monitor
Tracks heat tax accumulation during tactical operations
"""

from typing import Dict, Any, Optional
from dataclasses import dataclass
from datetime import datetime

@dataclass
class HeatTaxSnapshot:
    """Snapshot of heat tax at a point in time"""
    timestamp: str
    operation: str
    heat_tax: float
    threshold: float
    status: str  # 'safe', 'warning', 'critical'

class TacticalHeatTaxMonitor:
    """
    Monitors heat tax during tactical operations.

    Key insight: Classical fitting operations generate heat tax
    that must be tracked to prevent system overload.
    """

    def __init__(self, warning_threshold: float = 0.6,
                 critical_threshold: float = 0.9):
        self.warning_threshold = warning_threshold
        self.critical_threshold = critical_threshold
        self._current_heat_tax = 0.0
        self._history: list[HeatTaxSnapshot] = []

    def record_operation(self, operation: str, heat_tax_delta: float):
        """
        Record heat tax from an operation.

        Args:
            operation: Name of operation
            heat_tax_delta: Heat tax generated
        """
        self._current_heat_tax += heat_tax_delta

        status = 'safe'
        if self._current_heat_tax >= self.critical_threshold:
            status = 'critical'
        elif self._current_heat_tax >= self.warning_threshold:
            status = 'warning'

        snapshot = HeatTaxSnapshot(
            timestamp=datetime.now().isoformat(),
            operation=operation,
            heat_tax=self._current_heat_tax,
            threshold=self.critical_threshold,
            status=status,
        )
        self._history.append(snapshot)

        return status

    def get_current_status(self) -> Dict[str, Any]:
        """Get current heat tax status"""
        return {
            'current_heat_tax': self._current_heat_tax,
            'warning_threshold': self.warning_threshold,
            'critical_threshold': self.critical_threshold,
            'status': self._get_status_string(),
        }

    def _get_status_string(self) -> str:
        """Get status as string"""
        if self._current_heat_tax >= self.critical_threshold:
            return 'critical'
        elif self._current_heat_tax >= self.warning_threshold:
            return 'warning'
        return 'safe'

    def reset(self):
        """Reset heat tax to zero"""
        self._current_heat_tax = 0.0

    def get_history(self) -> list[HeatTaxSnapshot]:
        """Get heat tax history"""
        return self._history.copy()
