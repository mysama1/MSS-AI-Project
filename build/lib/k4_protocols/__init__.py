"""
K4 Protocols Package — K4 Civilization OS Protocol Suite

Modules:
  k4_rsca_genes           — Living Protocol Genes (RSCA-001 to RSCA-006)
  k4_guardian_protocol    — No.1 Ontological Weight Guardian Protocol
  k4_bidirectional_coupler — Physical Mirror Layer Bidirectional Coupler
  k4_logical_work         — H144 Logic Work Engine

MSS Anchor: A1-A6 full chain closure
Status: L2 Protective Belt (axiom-anchored, not yet empirically verified)
"""

from .k4_rsca_genes import (
    K4RSCAGenome, RSCAGene, GeneStatus, TriggerCondition
)
from .k4_guardian_protocol import (
    No1GuardianProtocol, GuardianConfig, GuardianState,
    SystemState, TValueSnapshot
)
from .k4_bidirectional_coupler import (
    K4BidirectionalCoupler, CouplerConfig, CouplerState,
    CouplerSignal, ChannelDirection, SignalType
)
from .k4_logical_work import (
    K4LogicalWorkEngine, LogicalWorkConfig, LogicalWorkState,
    LogicWorkResult, ParadoxInput, ParadoxType, WorkZone, WorkOutcome
)
from .k4_pi_adapter import (
    K4PiAdapter, K4PiBridge, BridgeConfig, BridgeDirection,
    BridgeSignal, HeatTaxReport, TranslationFidelity
)

__all__ = [
    # RSCA Genes
    "K4RSCAGenome", "RSCAGene", "GeneStatus", "TriggerCondition",
    # Guardian Protocol
    "No1GuardianProtocol", "GuardianConfig", "GuardianState",
    "SystemState", "TValueSnapshot",
    # Bidirectional Coupler
    "K4BidirectionalCoupler", "CouplerConfig", "CouplerState",
    "CouplerSignal", "ChannelDirection", "SignalType",
    # Logic Work
    "K4LogicalWorkEngine", "LogicalWorkConfig", "LogicalWorkState",
    "LogicWorkResult", "ParadoxInput", "ParadoxType",
    "WorkZone", "WorkOutcome",
    # K4-Pi Adapter
    "K4PiAdapter", "K4PiBridge", "BridgeConfig", "BridgeDirection",
    "BridgeSignal", "HeatTaxReport", "TranslationFidelity",
]

__version__ = "1.0.0"