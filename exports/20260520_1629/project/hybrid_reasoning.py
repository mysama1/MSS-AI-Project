"""
MSS Hybrid Reasoning Engine v1.0
混合推理：符号推理（确定性）+ LLM（概率性）

架构：
1. 符号层：知识图谱验证 + 层级检查 + 矛盾检测
2. LLM层：语义理解 + 生成 + 开放域推理
3. 融合层：结果加权 + 置信度校准 + 冲突解决
"""

import json
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Any
from enum import Enum, auto

from symbolic_engine import MSSKnowledgeGraph, ConceptNode, RelationEdge, NodeType, RelationType
from symbolic_engine_v2 import GraphAlgorithms, LayerAwareReasoner
from mss_stability import SystemHealthMonitor, quick_stability_check


class ReasoningMode(Enum):
    """推理模式"""
    SYMBOLIC_ONLY = auto()      # 纯符号推理（最高确定性）
    LLM_ONLY = auto()           # 纯LLM推理（最高灵活性）
    HYBRID_SYMBOLIC_FIRST = auto()  # 符号优先，LLM补充
    HYBRID_LLM_FIRST = auto()   # LLM优先，符号验证
    ADAPTIVE = auto()           # 自适应选择模式


class FusionStrategy(Enum):
    """结果融合策略"""
    SYMBOLIC_WINS = auto()      # 符号结果优先（保守）
    LLM_WINS = auto()           # LLM结果优先（激进）
    WEIGHTED = auto()           # 加权融合
    CONSENSUS = auto()          # 共识融合（两者一致才通过）
    CASCADE = auto()            # 级联：符号失败→LLM fallback


@dataclass
class SymbolicResult:
    """符号推理结果"""
    proven: bool
    certainty: float
    explanation: str
    path: List[str] = field(default_factory=list)
    contradictions: List[str] = field(default_factory=list)
    layer_violations: List[str] = field(default_factory=list)
    execution_time_ms: float = 0.0


@dataclass
class LLMResult:
    """LLM推理结果"""
    text: str
    confidence: float
    layer: str  # L1/L2/L3/UNKNOWN
    forbidden_detected: List[str] = field(default_factory=list)
    rewrite_needed: bool = False
    execution_time_ms: float = 0.0


@dataclass
class HybridResult:
    """混合推理最终结果"""
    mode: ReasoningMode
    strategy: FusionStrategy
    symbolic_result: Optional[SymbolicResult]
    llm_result: Optional[LLMResult]
    final_answer: str
    final_confidence: float
    final_layer: str
    fusion_notes: List[str] = field(default_factory=list)
    execution_time_ms: float = 0.0


class HybridReasoningEngine:
    """
    MSS 混合推理引擎
    
    结合符号推理的确定性和LLM的灵活性
    """
    
    def __init__(
        self,
        knowledge_graph: Optional[MSSKnowledgeGraph] = None,
        mode: ReasoningMode = ReasoningMode.HYBRID_SYMBOLIC_FIRST,
        strategy: FusionStrategy = FusionStrategy.CASCADE,
        symbolic_weight: float = 0.7,
        llm_weight: float = 0.3,
        certainty_threshold: float = 0.6,
    ):
        self.kg = knowledge_graph or MSSKnowledgeGraph()
        self.mode = mode
        self.strategy = strategy
        self.symbolic_weight = symbolic_weight
        self.llm_weight = llm_weight
        self.certainty_threshold = certainty_threshold
        
        # Sub-engines
        self.symbolic_algo = GraphAlgorithms(self.kg)
        self.layer_reasoner = LayerAwareReasoner(self.kg)
        
        # Statistics
        self.stats = {
            "symbolic_calls": 0,
            "llm_calls": 0,
            "fusion_calls": 0,
            "symbolic_success": 0,
            "llm_success": 0,
            "conflicts": 0,
        }
    
    def _symbolic_reason(self, query: str, context: List[str] = None) -> SymbolicResult:
        """
        符号推理层
        
        基于知识图谱的确定性推理
        """
        start = time.time()
        self.stats["symbolic_calls"] += 1
        
        # Parse query for node references
        nodes_mentioned = self._extract_nodes(query)
        
        contradictions = []
        layer_violations = []
        path = []
        proven = False
        certainty = 0.0
        explanation = ""
        
        if len(nodes_mentioned) >= 2:
            # Try to find path between nodes
            source, target = nodes_mentioned[0], nodes_mentioned[1]
            path_result = self.symbolic_algo.shortest_path(source, target)
            
            if path_result.result.name == "PROVEN":
                proven = True
                certainty = path_result.certainty
                path = path_result.steps
                path_strs = [str(p) for p in path]
                explanation = f"Path found: {' -> '.join(path_strs)}"
            else:
                explanation = f"No direct path from {source} to {target}"
            
            # Check contradictions
            if source in self.kg.nodes and target in self.kg.nodes:
                source_node = self.kg.nodes[source]
                target_node = self.kg.nodes[target]
                
                # Layer violation check
                if source_node.layer == "L1" and target_node.layer == "L3":
                    # Direct L1->L3 is suspicious
                    layer_violations.append(f"Direct L1->L3 connection: {source}->{target}")
                
                # Check for contradictions in path
                for step in path:
                    if "CONTRADICTS" in str(step):
                        contradictions.append(step)
        
        # Check for contradictions in context
        if context:
            for item in context:
                contradictions.extend(self._check_context_contradictions(item))
        
        if proven and not contradictions and not layer_violations:
            self.stats["symbolic_success"] += 1
        
        execution_time = (time.time() - start) * 1000
        
        return SymbolicResult(
            proven=proven,
            certainty=certainty,
            explanation=explanation,
            path=path,
            contradictions=contradictions,
            layer_violations=layer_violations,
            execution_time_ms=execution_time,
        )
    
    def _llm_reason(self, query: str, context: List[str] = None) -> LLMResult:
        """
        LLM推理层（模拟）
        
        实际实现中会调用Ollama API
        这里用确定性模拟来演示架构
        """
        start = time.time()
        self.stats["llm_calls"] += 1
        
        # Simulate LLM processing
        # In real implementation, this would call Ollama
        text = f"[LLM simulated response for: {query[:50]}...]"
        confidence = 0.75  # Simulated
        layer = "L2"  # Simulated
        forbidden = []
        rewrite = False
        
        self.stats["llm_success"] += 1
        
        execution_time = (time.time() - start) * 1000
        
        return LLMResult(
            text=text,
            confidence=confidence,
            layer=layer,
            forbidden_detected=forbidden,
            rewrite_needed=rewrite,
            execution_time_ms=execution_time,
        )
    
    def _fuse_results(
        self,
        symbolic: SymbolicResult,
        llm: LLMResult,
        strategy: FusionStrategy
    ) -> Tuple[str, float, str, List[str]]:
        """
        融合符号和LLM结果
        
        Returns: (answer, confidence, layer, notes)
        """
        self.stats["fusion_calls"] += 1
        notes = []
        
        # Check for conflicts
        conflict = False
        if symbolic.proven and llm.confidence < 0.5:
            conflict = True
            notes.append("Conflict: Symbolic proven but LLM low confidence")
        elif not symbolic.proven and llm.confidence > 0.8:
            conflict = True
            notes.append("Conflict: Symbolic not proven but LLM high confidence")
        
        if conflict:
            self.stats["conflicts"] += 1
        
        # Apply fusion strategy
        if strategy == FusionStrategy.SYMBOLIC_WINS:
            if symbolic.proven:
                answer = symbolic.explanation
                confidence = symbolic.certainty
                layer = "L1" if symbolic.path else "L2"
            else:
                answer = llm.text
                confidence = llm.confidence * 0.5  # Penalty for symbolic failure
                layer = llm.layer
            
        elif strategy == FusionStrategy.LLM_WINS:
            answer = llm.text
            confidence = llm.confidence
            layer = llm.layer
            
        elif strategy == FusionStrategy.WEIGHTED:
            # Weighted combination
            if symbolic.proven:
                sym_score = symbolic.certainty * self.symbolic_weight
            else:
                sym_score = 0.0
            
            llm_score = llm.confidence * self.llm_weight
            total_score = sym_score + llm_score
            
            if symbolic.proven and total_score > self.certainty_threshold:
                answer = f"[Symbolic+LLM] {symbolic.explanation} | {llm.text}"
                confidence = total_score
                layer = "L2"
            else:
                answer = llm.text
                confidence = llm.confidence
                layer = llm.layer
                
        elif strategy == FusionStrategy.CONSENSUS:
            if symbolic.proven and llm.confidence > 0.7:
                answer = f"[Consensus] {symbolic.explanation}"
                confidence = (symbolic.certainty + llm.confidence) / 2
                layer = "L2"
            else:
                answer = "[No consensus] Insufficient evidence"
                confidence = 0.3
                layer = "L3"
                notes.append("No consensus between symbolic and LLM")
                
        elif strategy == FusionStrategy.CASCADE:
            # Try symbolic first, fallback to LLM
            if symbolic.proven and symbolic.certainty > self.certainty_threshold:
                answer = symbolic.explanation
                confidence = symbolic.certainty
                layer = "L1" if not symbolic.layer_violations else "L2"
            else:
                answer = llm.text
                confidence = llm.confidence
                layer = llm.layer
                notes.append("Symbolic failed, falling back to LLM")
        
        else:
            answer = llm.text
            confidence = llm.confidence
            layer = llm.layer
        
        return answer, confidence, layer, notes
    
    def reason(self, query: str, context: List[str] = None) -> HybridResult:
        """
        主推理入口
        
        根据模式选择推理策略
        """
        start = time.time()
        
        # Check stability
        stability = quick_stability_check()
        
        # Adjust mode based on stability
        effective_mode = self.mode
        if stability.level.name == "CRITICAL":
            effective_mode = ReasoningMode.SYMBOLIC_ONLY
        elif stability.level.name == "DEGRADED":
            if self.mode == ReasoningMode.HYBRID_LLM_FIRST:
                effective_mode = ReasoningMode.HYBRID_SYMBOLIC_FIRST
        
        # Execute reasoning
        symbolic_result = None
        llm_result = None
        
        if effective_mode == ReasoningMode.SYMBOLIC_ONLY:
            symbolic_result = self._symbolic_reason(query, context)
            final_answer = symbolic_result.explanation
            final_confidence = symbolic_result.certainty
            final_layer = "L1" if symbolic_result.proven else "L3"
            fusion_notes = ["Symbolic-only mode"]
            
        elif effective_mode == ReasoningMode.LLM_ONLY:
            llm_result = self._llm_reason(query, context)
            final_answer = llm_result.text
            final_confidence = llm_result.confidence
            final_layer = llm_result.layer
            fusion_notes = ["LLM-only mode"]
            
        elif effective_mode == ReasoningMode.HYBRID_SYMBOLIC_FIRST:
            symbolic_result = self._symbolic_reason(query, context)
            llm_result = self._llm_reason(query, context)
            final_answer, final_confidence, final_layer, fusion_notes = self._fuse_results(
                symbolic_result, llm_result, self.strategy
            )
            fusion_notes.append("Symbolic-first hybrid")
            
        elif effective_mode == ReasoningMode.HYBRID_LLM_FIRST:
            llm_result = self._llm_reason(query, context)
            symbolic_result = self._symbolic_reason(query, context)
            final_answer, final_confidence, final_layer, fusion_notes = self._fuse_results(
                symbolic_result, llm_result, self.strategy
            )
            fusion_notes.append("LLM-first hybrid")
            
        elif effective_mode == ReasoningMode.ADAPTIVE:
            # Choose based on query characteristics
            if self._is_structured_query(query):
                symbolic_result = self._symbolic_reason(query, context)
                if symbolic_result.proven and symbolic_result.certainty > 0.8:
                    final_answer = symbolic_result.explanation
                    final_confidence = symbolic_result.certainty
                    final_layer = "L1"
                    fusion_notes = ["Adaptive: Symbolic sufficient"]
                else:
                    llm_result = self._llm_reason(query, context)
                    final_answer, final_confidence, final_layer, fusion_notes = self._fuse_results(
                        symbolic_result, llm_result, FusionStrategy.CASCADE
                    )
                    fusion_notes.append("Adaptive: Symbolic insufficient, used LLM")
            else:
                llm_result = self._llm_reason(query, context)
                final_answer = llm_result.text
                final_confidence = llm_result.confidence
                final_layer = llm_result.layer
                fusion_notes = ["Adaptive: Unstructured query, LLM only"]
        
        execution_time = (time.time() - start) * 1000
        
        return HybridResult(
            mode=effective_mode,
            strategy=self.strategy,
            symbolic_result=symbolic_result,
            llm_result=llm_result,
            final_answer=final_answer,
            final_confidence=final_confidence,
            final_layer=final_layer,
            fusion_notes=fusion_notes,
            execution_time_ms=execution_time,
        )
    
    def _extract_nodes(self, text: str) -> List[str]:
        """从文本中提取节点ID（简单启发式）"""
        nodes = []
        # Look for uppercase letter + number pattern (e.g., A1, T2, H3)
        import re
        matches = re.findall(r'\b([A-Z]\d+)\b', text)
        nodes.extend(matches)
        return nodes
    
    def _check_context_contradictions(self, text: str) -> List[str]:
        """检查上下文中的矛盾"""
        contradictions = []
        # Simple heuristic: check for negation patterns
        negation_words = ["not", "no", "never", "false", "contradict"]
        for word in negation_words:
            if word in text.lower():
                contradictions.append(f"Potential negation: '{word}' in context")
        return contradictions
    
    def _is_structured_query(self, query: str) -> bool:
        """判断查询是否是结构化查询（适合符号推理）"""
        # Structured queries contain node references, logical operators, etc.
        structured_indicators = ["->", "implies", "if", "then", "prove", "verify"]
        return any(ind in query.lower() for ind in structured_indicators)
    
    def get_stats(self) -> Dict:
        """获取推理统计"""
        return {
            **self.stats,
            "symbolic_success_rate": (
                self.stats["symbolic_success"] / max(self.stats["symbolic_calls"], 1)
            ),
            "llm_success_rate": (
                self.stats["llm_success"] / max(self.stats["llm_calls"], 1)
            ),
            "conflict_rate": (
                self.stats["conflicts"] / max(self.stats["fusion_calls"], 1)
            ),
        }


# Demo
if __name__ == "__main__":
    print("=" * 60)
    print("MSS Hybrid Reasoning Engine Demo")
    print("=" * 60)
    
    # Create test graph
    from test_symbolic_v2 import create_test_graph
    graph = create_test_graph()
    
    # Create engine
    engine = HybridReasoningEngine(
        knowledge_graph=graph,
        mode=ReasoningMode.HYBRID_SYMBOLIC_FIRST,
        strategy=FusionStrategy.CASCADE,
    )
    
    # Test queries
    queries = [
        "Prove A1 implies H1",
        "What is the relationship between T1 and T2?",
        "Explain the contradiction between A1 and H2",
    ]
    
    for query in queries:
        print(f"\nQuery: {query}")
        result = engine.reason(query)
        print(f"  Mode: {result.mode.name}")
        print(f"  Strategy: {result.strategy.name}")
        print(f"  Answer: {result.final_answer}")
        print(f"  Confidence: {result.final_confidence:.2f}")
        print(f"  Layer: {result.final_layer}")
        print(f"  Time: {result.execution_time_ms:.1f}ms")
        if result.fusion_notes:
            print(f"  Notes: {', '.join(result.fusion_notes)}")
    
    print("\n" + "=" * 60)
    print("Statistics:")
    stats = engine.get_stats()
    for key, value in stats.items():
        if isinstance(value, float):
            print(f"  {key}: {value:.3f}")
        else:
            print(f"  {key}: {value}")
    print("=" * 60)
