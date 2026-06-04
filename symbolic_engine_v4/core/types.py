"""
MSS Symbolic Engine v4.0 - Core Types
"""

from enum import Enum, auto
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Any
import hashlib

class RelationType(Enum):
    """关系类型枚举"""
    IMPLIES = "implies"
    CONTRADICTS = "contradicts"
    INSTANCE_OF = "instance_of"
    DERIVES_FROM = "derives_from"
    ANALOGOUS = "analogous"
    TESTS = "tests"
    REFINES = "refines"

class NodeType(Enum):
    """节点类型枚举"""
    AXIOM = "axiom"
    THEOREM = "theorem"
    DEFINITION = "definition"
    LEMMA = "lemma"
    CONCEPT = "concept"
    HEURISTIC = "heuristic"

class LayerTier(Enum):
    """层级分类"""
    L1_CORE = "L1"
    L2_PROTECTIVE = "L2"
    L3_HEURISTIC = "L3"
    L4_CONTAMINATED = "L4"

@dataclass
class ConceptNode:
    """概念节点"""
    id: str
    title: str
    content: str
    node_type: NodeType = NodeType.CONCEPT
    layer: LayerTier = LayerTier.L3_HEURISTIC
    category: Optional[str] = None
    tags: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __hash__(self):
        return hash(self.id)

    def __eq__(self, other):
        if isinstance(other, ConceptNode):
            return self.id == other.id
        return False

@dataclass
class ConceptEdge:
    """概念边"""
    source: str
    target: str
    relation: RelationType
    weight: float = 1.0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __hash__(self):
        return hash(f"{self.source}->{self.target}:{self.relation.value}")

    def __eq__(self, other):
        if isinstance(other, ConceptEdge):
            return (self.source == other.source and
                    self.target == other.target and
                    self.relation == other.relation)
        return False

@dataclass
class QueryResult:
    """查询结果"""
    query_id: str
    path: List[ConceptNode]
    edges: List[ConceptEdge]
    confidence: float
    execution_time_ms: float
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class ValidationResult:
    """验证结果"""
    is_valid: bool
    violations: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    score: float = 0.0
