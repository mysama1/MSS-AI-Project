"""
核心类型定义
"""

from enum import Enum, auto
from typing import Optional, Dict, Any
from dataclasses import dataclass

class NodeType(Enum):
    """节点类型"""
    CONCEPT = "concept"           # 概念节点
    AXIOM = "axiom"              # 公理节点
    THEOREM = "theorem"          # 定理节点
    DEFINITION = "definition"     # 定义节点
    LEMMA = "lemma"              # 引理节点
    ENTITY = "entity"            # 实体节点
    PROPERTY = "property"        # 属性节点

class EdgeType(Enum):
    """边类型"""
    IMPLIES = "implies"          # 蕴含
    EQUIVALENT = "equivalent"    # 等价
    CONTRADICTS = "contradicts"  # 矛盾
    DEPENDS = "depends"          # 依赖
    INSTANCE = "instance"        # 实例
    SUBCLASS = "subclass"        # 子类
    PART_OF = "part_of"          # 部分

class ReasoningMode(Enum):
    """推理模式"""
    STRICT = "strict"            # 严格模式（仅逻辑推理）
    HEURISTIC = "heuristic"      # 启发式（允许近似）
    HYBRID = "hybrid"            # 混合模式（符号+LLM）

class ValidationLevel(Enum):
    """验证级别"""
    SYNTAX = "syntax"            # 语法检查
    SEMANTIC = "semantic"        # 语义检查
    LOGICAL = "logical"          # 逻辑一致性
    COMPLETENESS = "completeness" # 完整性

@dataclass
class ConceptNode:
    """概念节点"""
    id: str
    name: str
    node_type: NodeType
    layer: int                   # L0/L1/L2/L3
    properties: Dict[str, Any] = None
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.properties is None:
            self.properties = {}
        if self.metadata is None:
            self.metadata = {}

@dataclass  
class RelationEdge:
    """关系边"""
    source: str                  # 源节点ID
    target: str                  # 目标节点ID
    edge_type: EdgeType
    weight: float = 1.0          # 权重
    bidirectional: bool = False  # 是否双向
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}
