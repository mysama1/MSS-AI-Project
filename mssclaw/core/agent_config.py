"""
Agent 配置 (re-export from agent.py).

DomainMode, HybridTier, HeatTaxBudgetConfig, DeltaConfig,
AutoDomainConfig, AgentConfig — 现定义于 mssclaw.core.agent.

本文件保留向后兼容, 推荐直接使用:
    from mssclaw.core.agent import AgentConfig, DomainMode
"""
from .agent import (
    DomainMode, HybridTier,
    HeatTaxBudgetConfig, DeltaConfig, AutoDomainConfig,
    AgentConfig,
)

__all__ = [
    "DomainMode", "HybridTier",
    "HeatTaxBudgetConfig", "DeltaConfig", "AutoDomainConfig",
    "AgentConfig",
]
