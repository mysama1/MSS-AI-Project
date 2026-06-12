"""
MSSclaw 专项 Agent 集群 — Round 2 扩展.

KB-Agent:        知识库守护者
Code-Agent:      编程执行者
Video-Agent:     视频管线管理员
Translate-Agent: MSS↔传统翻译校准官
Product-Agent:   产品落地运营
Audit-Agent:     独立审计官 (Round 2 新增 — 三权分立司法节点)
"""
from .base import BaseAgent
from .kb_agent import KBAgent
from .code_agent import CodeAgent
from .video_agent import VideoAgent
from .translate_agent import TranslateAgent
from .product_agent import ProductAgent
from .audit_agent import AuditAgent
from .personal_agent import (
    PersonalAgent, LifeAgent, EntertainAgent, SocialAgent, ConciergeAgent,
)

__all__ = [
    "BaseAgent",
    "KBAgent", "CodeAgent", "VideoAgent",
    "TranslateAgent", "ProductAgent", "AuditAgent",
    "PersonalAgent", "LifeAgent", "EntertainAgent", "SocialAgent", "ConciergeAgent",
]
