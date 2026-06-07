"""
MSS-Agent: 世界上第一个内置"意义场自检"的开源 Agent 框架.

MSS-Agent 不是 LangChain 的替代品——它是 LangChain 的"良心".
"""

__version__ = "0.2.1"
__author__ = "MSS-AI Project"
__license__ = "MIT"

from .core.agent import MSSAgent
from .core.heat_tax import HeatTaxBudget, HeatTaxLevel
from .core.delta import DeltaProtocol
from .core.memory import DeltaMemory

__all__ = ["MSSAgent", "HeatTaxBudget", "HeatTaxLevel", "DeltaProtocol", "DeltaMemory"]
