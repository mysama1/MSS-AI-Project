"""
MSS 符号推理引擎 v4.0

生产级模块化符号推理引擎，支持：
- CSR稀疏矩阵图数据结构
- 插件化规则系统
- 多级缓存
- RESTful API

作者：QClaw
日期：2026-05-20
版本：4.0.0
"""

__version__ = "4.0.0"
__author__ = "QClaw"

from .core.graph import CSRGraph
from .core.node import ConceptNode
from .core.edge import RelationEdge
from .core.types import NodeType, EdgeType, ReasoningMode

__all__ = [
    "CSRGraph",
    "ConceptNode", 
    "RelationEdge",
    "NodeType",
    "EdgeType",
    "ReasoningMode",
]
