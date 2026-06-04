"""
MSS Symbolic Engine v4.0

Production-grade symbolic reasoning engine with:
- CSR sparse matrix graph storage
- A* pathfinding with layer heuristics
- Plugin system for dynamic rules
- Query caching layer
"""

__version__ = "4.0.0"
__author__ = "MSS Project"

from .core import (
    ConceptNode, ConceptEdge, QueryResult, ValidationResult,
    RelationType, NodeType, LayerTier, CSRGraph
)
from .parser import JSONLParser

__all__ = [
    'ConceptNode', 'ConceptEdge', 'QueryResult', 'ValidationResult',
    'RelationType', 'NodeType', 'LayerTier', 'CSRGraph', 'JSONLParser'
]
