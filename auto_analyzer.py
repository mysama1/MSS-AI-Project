"""
MSS Auto-Analyzer
自动分析决策模块 - 为符号引擎提供智能决策支持

功能:
1. 知识库加载决策分析
2. 操作风险评估
3. 执行路径推荐
4. 资源使用监控
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Any
from enum import Enum, auto
import json
import os
import time
from datetime import datetime


class RiskLevel(Enum):
    """Risk assessment levels"""
    LOW = auto()
    MEDIUM = auto()
    HIGH = auto()
    CRITICAL = auto()


class ActionType(Enum):
    """Types of actions that can be analyzed"""
    LOAD_KNOWLEDGE = auto()
    MODIFY_GRAPH = auto()
    EXECUTE_QUERY = auto()
    RUN_INFERENCE = auto()
    EXPORT_DATA = auto()
    UPDATE_CONFIG = auto()


class Recommendation(Enum):
    """Possible recommendations"""
    PROCEED = auto()
    PROCEED_WITH_CAUTION = auto()
    DEFER = auto()
    ABORT = auto()
    NEEDS_MORE_INFO = auto()


@dataclass
class DecisionContext:
    """Context for decision making"""
    action_type: ActionType
    target: str
    current_state: Dict[str, Any]
    proposed_change: Optional[Dict[str, Any]] = None
    dependencies: List[str] = field(default_factory=list)
    constraints: List[str] = field(default_factory=list)


@dataclass
class AnalysisResult:
    """Result of automated analysis"""
    recommendation: Recommendation
    risk_level: RiskLevel
    confidence: float  # 0.0 to 1.0
    reasoning: str
    alternatives: List[str]
    estimated_impact: Dict[str, Any]
    execution_time_ms: Optional[int] = None


class AutoAnalyzer:
    """
    Automated decision analysis for MSS symbolic engine operations
    
    Provides structured decision support without requiring
    user intervention for routine operations.
    """
    
    def __init__(self, graph_stats: Optional[Dict] = None):
        self.graph_stats = graph_stats or {}
        self.operation_history: List[Dict] = []
        self.decision_log: List[Dict] = []
    
    def analyze_knowledge_base_loading(self, kb_path: str, 
                                      expected_entries: int = 0) -> AnalysisResult:
        """
        Analyze whether to proceed with knowledge base loading
        """
        start_time = time.time()
        
        # Check if file exists
        if not os.path.exists(kb_path):
            return AnalysisResult(
                recommendation=Recommendation.ABORT,
                risk_level=RiskLevel.HIGH,
                confidence=1.0,
                reasoning=f"Knowledge base path does not exist: {kb_path}",
                alternatives=["Check path", "Create sample data"],
                estimated_impact={"nodes_added": 0, "memory_increase_mb": 0}
            )
        
        # Analyze file content
        try:
            with open(kb_path, 'r', encoding='utf-8') as f:
                lines = [l.strip() for l in f if l.strip()]
                actual_entries = len(lines)
                
                # Validate JSON structure
                valid_entries = 0
                invalid_entries = 0
                layers_found = set()
                
                for line in lines[:10]:  # Sample first 10
                    try:
                        entry = json.loads(line)
                        valid_entries += 1
                        if 'layer' in entry:
                            layers_found.add(entry['layer'])
                    except json.JSONDecodeError:
                        invalid_entries += 1
                
                # Risk assessment
                if invalid_entries > 5:
                    risk = RiskLevel.HIGH
                    recommendation = Recommendation.ABORT
                    reasoning = f"High invalid JSON rate: {invalid_entries}/10 sample entries corrupted"
                elif actual_entries == 0:
                    risk = RiskLevel.MEDIUM
                    recommendation = Recommendation.DEFER
                    reasoning = "Knowledge base is empty"
                elif actual_entries > 1000:
                    risk = RiskLevel.MEDIUM
                    recommendation = Recommendation.PROCEED_WITH_CAUTION
                    reasoning = f"Large knowledge base ({actual_entries} entries). May impact performance."
                else:
                    risk = RiskLevel.LOW
                    recommendation = Recommendation.PROCEED
                    reasoning = f"Valid knowledge base: {actual_entries} entries, layers: {layers_found}"
                
                # Estimate impact
                avg_node_size_kb = 2  # Estimated
                memory_increase = (actual_entries * avg_node_size_kb) / 1024
                
                return AnalysisResult(
                    recommendation=recommendation,
                    risk_level=risk,
                    confidence=0.85,
                    reasoning=reasoning,
                    alternatives=[
                        "Load partial sample (first 50 entries)",
                        "Validate all entries before loading",
                        "Load in background with progress tracking"
                    ],
                    estimated_impact={
                        "nodes_added": actual_entries,
                        "memory_increase_mb": round(memory_increase, 2),
                        "layers": list(layers_found),
                        "load_time_estimate_sec": actual_entries * 0.01
                    },
                    execution_time_ms=int((time.time() - start_time) * 1000)
                )
                
        except Exception as e:
            return AnalysisResult(
                recommendation=Recommendation.ABORT,
                risk_level=RiskLevel.HIGH,
                confidence=1.0,
                reasoning=f"Error analyzing knowledge base: {str(e)}",
                alternatives=["Check file permissions", "Verify file format"],
                estimated_impact={"error": str(e)}
            )
    
    def analyze_graph_operation(self, operation: str, 
                               target_nodes: List[str],
                               context: DecisionContext) -> AnalysisResult:
        """
        Analyze a proposed graph operation
        """
        start_time = time.time()
        
        # Check node existence
        missing_nodes = [n for n in target_nodes if n not in self.graph_stats.get('nodes', {})]
        
        if missing_nodes:
            return AnalysisResult(
                recommendation=Recommendation.ABORT,
                risk_level=RiskLevel.HIGH,
                confidence=0.95,
                reasoning=f"Target nodes not in graph: {missing_nodes}",
                alternatives=["Add nodes first", "Check node IDs"],
                estimated_impact={"missing_nodes": len(missing_nodes)}
            )
        
        # Operation-specific analysis
        if operation == "delete":
            # Check if deleting critical nodes
            critical_nodes = [n for n in target_nodes if n.startswith('A')]  # Axioms
            if critical_nodes:
                return AnalysisResult(
                    recommendation=Recommendation.ABORT,
                    risk_level=RiskLevel.CRITICAL,
                    confidence=0.9,
                    reasoning=f"Attempting to delete critical axioms: {critical_nodes}",
                    alternatives=["Mark as deprecated instead", "Create backup first"],
                    estimated_impact={"critical_nodes_affected": len(critical_nodes)}
                )
        
        elif operation == "modify":
            return AnalysisResult(
                recommendation=Recommendation.PROCEED_WITH_CAUTION,
                risk_level=RiskLevel.MEDIUM,
                confidence=0.8,
                reasoning="Node modification may affect derived theorems. Verify consistency after.",
                alternatives=["Create new version instead", "Test in isolated subgraph"],
                estimated_impact={"affected_derivations": "unknown"}
            )
        
        # Default: proceed
        return AnalysisResult(
            recommendation=Recommendation.PROCEED,
            risk_level=RiskLevel.LOW,
            confidence=0.9,
            reasoning=f"Safe operation: {operation} on {len(target_nodes)} nodes",
            alternatives=[],
            estimated_impact={"nodes_affected": len(target_nodes)}
        )
    
    def analyze_query_complexity(self, query_params: Dict[str, Any]) -> AnalysisResult:
        """
        Analyze query complexity and recommend execution strategy
        """
        start_time = time.time()
        
        complexity_score = 0
        factors = []
        
        # Factor 1: Layer filtering
        if query_params.get('layer'):
            complexity_score += 1
            factors.append("Layer filter")
        
        # Factor 2: Keyword search
        if query_params.get('keyword'):
            complexity_score += 2
            factors.append("Keyword search (full scan)")
        
        # Factor 3: Path finding
        if query_params.get('path_find'):
            complexity_score += 3
            max_depth = query_params.get('max_depth', 5)
            factors.append(f"Path finding (depth {max_depth})")
            if max_depth > 5:
                complexity_score += 2
                factors.append("Deep path search")
        
        # Factor 4: Contradiction check
        if query_params.get('check_contradiction'):
            complexity_score += 2
            factors.append("Contradiction detection")
        
        # Recommendation based on complexity
        if complexity_score <= 2:
            recommendation = Recommendation.PROCEED
            risk = RiskLevel.LOW
            reasoning = f"Simple query ({complexity_score}/10 complexity). Fast execution expected."
        elif complexity_score <= 5:
            recommendation = Recommendation.PROCEED
            risk = RiskLevel.MEDIUM
            reasoning = f"Moderate complexity ({complexity_score}/10). May take 1-5 seconds."
        else:
            recommendation = Recommendation.PROCEED_WITH_CAUTION
            risk = RiskLevel.HIGH
            reasoning = f"High complexity query ({complexity_score}/10). Consider simplifying."
        
        return AnalysisResult(
            recommendation=recommendation,
            risk_level=risk,
            confidence=0.85,
            reasoning=reasoning,
            alternatives=[
                "Simplify query parameters",
                "Add more specific filters",
                "Cache results for reuse"
            ],
            estimated_impact={
                "complexity_score": complexity_score,
                "estimated_time_ms": complexity_score * 100,
                "factors": factors
            },
            execution_time_ms=int((time.time() - start_time) * 1000)
        )
    
    def get_system_status(self) -> Dict[str, Any]:
        """Get current system status for decision context"""
        return {
            "graph_nodes": self.graph_stats.get('total_nodes', 0),
            "graph_edges": self.graph_stats.get('total_edges', 0),
            "memory_usage_mb": self.graph_stats.get('memory_mb', 0),
            "last_operation": self.operation_history[-1] if self.operation_history else None,
            "uptime_seconds": time.time() - self.graph_stats.get('start_time', time.time())
        }
    
    def log_decision(self, context: DecisionContext, result: AnalysisResult) -> None:
        """Log decision for audit trail"""
        self.decision_log.append({
            "timestamp": datetime.now().isoformat(),
            "action_type": context.action_type.name,
            "target": context.target,
            "recommendation": result.recommendation.name,
            "risk_level": result.risk_level.name,
            "confidence": result.confidence,
            "reasoning": result.reasoning,
            "executed": False  # Updated after execution
        })


# --- Integration with Symbolic Engine ---

class SmartSymbolicReasoner:
    """
    Symbolic reasoner with integrated auto-analysis
    
    Wraps standard operations with automatic decision support.
    """
    
    def __init__(self, reasoner, analyzer: Optional[AutoAnalyzer] = None):
        self.reasoner = reasoner
        self.analyzer = analyzer or AutoAnalyzer()
        self.auto_mode = True  # If True, auto-execute LOW risk operations
    
    def smart_load_knowledge_base(self, kb_path: str, auto_execute: bool = True) -> Tuple[AnalysisResult, Optional[int]]:
        """
        Analyze and optionally execute knowledge base loading
        
        Returns: (analysis_result, nodes_loaded_or_none)
        """
        # Analyze
        analysis = self.analyzer.analyze_knowledge_base_loading(kb_path)
        
        # Auto-execute if appropriate
        if auto_execute and analysis.recommendation in [Recommendation.PROCEED]:
            if analysis.risk_level == RiskLevel.LOW:
                nodes_loaded = self.reasoner.load_from_knowledge_base(os.path.dirname(kb_path))
                analysis.estimated_impact["actual_nodes_loaded"] = nodes_loaded
                return analysis, nodes_loaded
        
        return analysis, None
    
    def smart_query(self, **query_params) -> Tuple[AnalysisResult, Optional[List]]:
        """
        Analyze and execute query with complexity assessment
        """
        analysis = self.analyzer.analyze_query_complexity(query_params)
        
        if analysis.recommendation in [Recommendation.PROCEED, Recommendation.PROCEED_WITH_CAUTION]:
            results = self.reasoner.graph.query(
                node_type=query_params.get('node_type'),
                layer=query_params.get('layer'),
                keyword=query_params.get('keyword')
            )
            return analysis, results
        
        return analysis, None
    
    def get_analysis_report(self) -> str:
        """Generate human-readable analysis report"""
        lines = [
            "=" * 60,
            "MSS Auto-Analyzer Report",
            "=" * 60,
            f"Total Decisions: {len(self.analyzer.decision_log)}",
            f"Auto-Execute Mode: {'ON' if self.auto_mode else 'OFF'}",
            "",
            "Recent Decisions:",
        ]
        
        for decision in self.analyzer.decision_log[-5:]:
            lines.append(f"  [{decision['risk_level']}] {decision['action_type']}: {decision['recommendation']}")
            lines.append(f"    → {decision['reasoning'][:80]}...")
        
        lines.append("=" * 60)
        return "\n".join(lines)


# --- Demo ---

def demo_auto_analyzer():
    """Demonstrate auto-analyzer capabilities"""
    print("=" * 60)
    print("MSS Auto-Analyzer Demo")
    print("=" * 60)
    
    from symbolic_engine import MSSKnowledgeGraph, SymbolicReasoner
    
    # Setup
    graph = MSSKnowledgeGraph()
    reasoner = SymbolicReasoner(graph)
    analyzer = AutoAnalyzer(graph.stats())
    smart = SmartSymbolicReasoner(reasoner, analyzer)
    
    # Demo 1: Knowledge base loading analysis
    print("\n1. Knowledge Base Loading Analysis:")
    print("-" * 40)
    
    # Test with existing file
    kb_path = "knowledge_base/anti_meme_defense_v12.2.jsonl"
    if os.path.exists(kb_path):
        result, loaded = smart.smart_load_knowledge_base(kb_path)
        print(f"File: {kb_path}")
        print(f"Recommendation: {result.recommendation.name}")
        print(f"Risk Level: {result.risk_level.name}")
        print(f"Reasoning: {result.reasoning}")
        print(f"Estimated Impact: {result.estimated_impact}")
        if loaded:
            print(f"Auto-loaded: {loaded} nodes")
    else:
        print(f"File not found: {kb_path}")
        # Show analysis anyway
        result, _ = smart.smart_load_knowledge_base(kb_path, auto_execute=False)
        print(f"Recommendation: {result.recommendation.name}")
        print(f"Reasoning: {result.reasoning}")
    
    # Demo 2: Query complexity analysis
    print("\n2. Query Complexity Analysis:")
    print("-" * 40)
    
    queries = [
        {"layer": "L1"},
        {"keyword": "ontology", "layer": "L1"},
        {"path_find": True, "max_depth": 10, "check_contradiction": True}
    ]
    
    for i, q in enumerate(queries, 1):
        result, _ = smart.smart_query(**q)
        print(f"\nQuery {i}: {q}")
        print(f"  Complexity Score: {result.estimated_impact.get('complexity_score', 'N/A')}")
        print(f"  Recommendation: {result.recommendation.name}")
        print(f"  Risk: {result.risk_level.name}")
        print(f"  Est. Time: {result.estimated_impact.get('estimated_time_ms', 'N/A')}ms")
    
    # Demo 3: System status
    print("\n3. System Status:")
    print("-" * 40)
    status = analyzer.get_system_status()
    for key, value in status.items():
        print(f"  {key}: {value}")
    
    # Demo 4: Report
    print("\n4. Analysis Report:")
    print("-" * 40)
    print(smart.get_analysis_report())
    
    print("\n" + "=" * 60)
    print("Demo complete")
    print("=" * 60)


if __name__ == "__main__":
    demo_auto_analyzer()
