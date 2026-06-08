"""
MSS-Agent: 世界上第一个内置"意义场自检"的开源 Agent 框架.

MSS-Agent 不是 LangChain 的替代品——它是 LangChain 的"良心".
"""

__version__ = "0.3.7"
__author__ = "MSS-AI Project"
__license__ = "MIT"

from .core.agent import MSSAgent
from .core.heat_tax import HeatTaxBudget, HeatTaxLevel
from .core.delta import DeltaProtocol
from .core.memory import DeltaMemory
from .core.delta_quick_audit import DeltaQuickAudit, DeltaResult, Tier, SessionState
from .core.domain_detector import DomainDetector
from .core.fewshot_builder import FewShotBuilder
from .core.agent_config import AgentConfig
from .core.heat_tax_accountant import HeatTaxAccountant
from .core.agent_orchestrator import AgentOrchestrator
from .core.delta_callback import MSSHybridCallback, MSSHybridWrapper
from .core.tool_budget_gate import ToolBudgetGate, ToolCategory
from .core.memory_guard import MemoryGuard, MemoryCategory, Memory
from .core.auto_archive import AutoArchiver, EntryDiagnosis
from .core.session_recall_summarizer import SessionRecallSummarizer, SessionSummary

__all__ = [
    "MSSAgent", "HeatTaxBudget", "HeatTaxLevel",
    "DeltaProtocol", "DeltaMemory",
    "DeltaQuickAudit", "DeltaResult", "Tier", "SessionState",
    "DomainDetector", "FewShotBuilder",
    "AgentConfig", "HeatTaxAccountant", "AgentOrchestrator",
    "MSSHybridCallback", "MSSHybridWrapper",
    "ToolBudgetGate", "ToolCategory",
    "MemoryGuard", "MemoryCategory", "Memory",
    "AutoArchiver", "EntryDiagnosis",
    "SessionRecallSummarizer", "SessionSummary",
]
