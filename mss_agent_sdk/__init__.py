"""
MSS-Agent SDK v0.1
==================
阶段一核心交付物：外挂式逻辑审计SDK
让任意Python应用都能接入MSS意义锚定与逻辑合规检查。

核心设计原则：
- 零侵入：通过装饰器+上下文管理器接入，不改现有代码逻辑
- 双模运行：本地符号引擎（确定性）+ 远程MSS-AI（深度分析）
- 诚实基线：所有输出标注[Confidence]/[Layer]/[Boundary Note]
"""

__version__ = "0.1.0"
__author__ = "Redshift Tech"

from .client import MSSClient
from .decorators import mss_audit, mss_anchor
from .config import SDKConfig
from .mss_types import AuditResult, AnchorLevel, Confidence

__all__ = [
    "MSSClient",
    "mss_audit",
    "mss_anchor", 
    "SDKConfig",
    "AuditResult",
    "AnchorLevel",
    "Confidence",
]
