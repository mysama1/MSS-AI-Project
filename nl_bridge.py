"""
Natural Language → Symbolic Reasoning Bridge
将自然语言查询转换为符号引擎可执行的推理请求

核心功能：
1. 查询解析：识别用户意图（推理/查询/验证/解释）
2. 实体提取：从文本中提取MSS概念节点ID
3. 关系映射：将自然语言关系映射为符号关系类型
4. 查询构建：生成符号引擎可执行的查询结构
"""

import re
import json
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from enum import Enum, auto

from symbolic_engine import (
    MSSKnowledgeGraph, ConceptNode, RelationEdge,
    NodeType, RelationType, InferenceResult
)
from kb_loader import KBLoader

class QueryIntent(Enum):
    """查询意图类型"""
    REASON = auto()      # 推理："A1能推出什么？"
    QUERY = auto()       # 查询："什么是A3？"
    VERIFY = auto()      # 验证："A2是否蕴含T1？"
    EXPLAIN = auto()     # 解释："解释热税机制"
    LIST = auto()        # 列表："列出所有L1公理"
    PATH = auto()        # 路径："从A1到T3的推导路径"
    UNKNOWN = auto()     # 未知意图

@dataclass
class NLQuery:
    """解析后的自然语言查询"""
    raw_text: str
    intent: QueryIntent
    entities: List[str]          # 提取的实体ID列表
    target_entity: Optional[str] # 目标实体（用于推理/验证）
    layer_filter: Optional[str]  # 层级过滤（L1/L2/L3）
    confidence: float            # 解析置信度

@dataclass
class BridgeResult:
    """桥接结果"""
    success: bool
    query_type: str
    symbolic_query: Optional[Dict]  # 符号查询结构
    nl_response: str                # 自然语言响应
    reasoning_result: Optional[Any] # 推理结果（如果有）
    confidence: float

class NLToSymbolicBridge:
    """自然语言到符号推理的桥接器"""

    # 意图识别关键词模式
    INTENT_PATTERNS = {
        QueryIntent.REASON: [
            r"推出|推导|蕴含|证明|得到|结论|结果",
            r"从.*到|由.*可知|根据.*得出",
            r"为什么|为何|怎么.*得到",
        ],
        QueryIntent.VERIFY: [
            r"是否|验证|检查|确认|对吗|正确吗",
            r".*蕴含.*吗|.*推出.*吗|.*证明.*吗",
        ],
        QueryIntent.EXPLAIN: [
            r"解释|说明|阐述|什么是|介绍",
            r"如何理解|怎么理解|含义",
        ],
        QueryIntent.LIST: [
            r"列出|所有|哪些|有什么|包括",
            r".*的列表|.*清单",
        ],
        QueryIntent.PATH: [
            r"路径|推导链|证明链|步骤|过程",
            r"怎么.*推导|如何.*证明",
        ],
        QueryIntent.QUERY: [
            r"什么是|哪里|哪个|谁|多少",
        ],
    }

    # 实体ID提取模式
    ENTITY_PATTERNS = [
        r"[A-Z]\d+",           # A1, A2, T1, T2 等
        r"Ω-[A-Z]\d+",          # Ω-E001 等
        r"H\d+",                # H1, H123 等
        r"[A-Z]{2,}[A-Z\d]*",   # MSS, AMFI 等（大写缩写）
    ]

    # 层级过滤关键词
    LAYER_PATTERNS = {
        "L1": [r"L1|硬核|公理|基础|底层|核心"],
        "L2": [r"L2|保护带|定理|推导|中间层"],
        "L3": [r"L3|试探法|启发式|应用|上层"],
    }

    def __init__(self, kb_graph: Optional[MSSKnowledgeGraph] = None):
        self.graph = kb_graph
        self.entity_cache: Dict[str, str] = {}  # 名称 -> ID 映射
        if kb_graph:
            self._build_entity_cache()

    def _build_entity_cache(self):
        """构建实体名称缓存"""
        if not self.graph:
            return
        for node_id, node in self.graph.nodes.items():
            # 缓存ID本身
            self.entity_cache[node_id.lower()] = node_id
            # 缓存名称
            if node.name:
                self.entity_cache[node.name.lower()] = node_id
            # 缓存内容关键词
            if node.content:
                # 提取2-4字中文词组作为关键词
                import re
                keywords = re.findall(r'[\u4e00-\u9fff]{2,4}', node.content)
                for kw in keywords[:3]:  # 只缓存前3个关键词
                    self.entity_cache[kw.lower()] = node_id

    def parse(self, text: str) -> NLQuery:
        """解析自然语言查询"""
        text_lower = text.lower()

        # 1. 识别意图
        intent = self._detect_intent(text)

        # 2. 提取实体
        entities = self._extract_entities(text)

        # 3. 识别目标实体
        target = entities[-1] if len(entities) > 1 else None

        # 4. 检测层级过滤
        layer = self._detect_layer_filter(text)

        # 5. 计算置信度
        confidence = self._calculate_confidence(intent, entities, text)

        return NLQuery(
            raw_text=text,
            intent=intent,
            entities=entities,
            target_entity=target,
            layer_filter=layer,
            confidence=confidence
        )

    def _detect_intent(self, text: str) -> QueryIntent:
        """检测查询意图"""
        scores = {intent: 0 for intent in QueryIntent}

        for intent, patterns in self.INTENT_PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, text, re.IGNORECASE):
                    scores[intent] += 1

        # 如果没有匹配，默认为 QUERY
        if max(scores.values()) == 0:
            return QueryIntent.QUERY

        return max(scores, key=scores.get)

    def _extract_entities(self, text: str) -> List[str]:
        """提取文本中的实体ID"""
        entities = []

        # 模式匹配
        for pattern in self.ENTITY_PATTERNS:
            matches = re.findall(pattern, text, re.IGNORECASE)
            entities.extend(matches)

        # 缓存查找（模糊匹配）
        for cached_name, node_id in self.entity_cache.items():
            if cached_name in text.lower() and node_id not in entities:
                entities.append(node_id)

        # 去重保持顺序
        seen = set()
        unique = []
        for e in entities:
            e_upper = e.upper()
            if e_upper not in seen:
                seen.add(e_upper)
                unique.append(e_upper)

        return unique

    def _detect_layer_filter(self, text: str) -> Optional[str]:
        """检测层级过滤条件"""
        for layer, patterns in self.LAYER_PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, text, re.IGNORECASE):
                    return layer
        return None

    def _calculate_confidence(self, intent: QueryIntent, entities: List[str], text: str) -> float:
        """计算解析置信度"""
        confidence = 0.5

        # 意图明确度
        if intent != QueryIntent.UNKNOWN:
            confidence += 0.2

        # 实体识别度
        if entities:
            confidence += min(len(entities) * 0.1, 0.2)

        # 文本长度（太短可能信息不足）
        if len(text) >= 10:
            confidence += 0.1

        return min(confidence, 1.0)

    def to_symbolic_query(self, nl_query: NLQuery) -> Optional[Dict]:
        """将自然语言查询转换为符号查询"""
        if nl_query.intent == QueryIntent.REASON:
            return self._build_reason_query(nl_query)
        elif nl_query.intent == QueryIntent.VERIFY:
            return self._build_verify_query(nl_query)
        elif nl_query.intent == QueryIntent.QUERY:
            return self._build_query_query(nl_query)
        elif nl_query.intent == QueryIntent.EXPLAIN:
            return self._build_explain_query(nl_query)
        elif nl_query.intent == QueryIntent.LIST:
            return self._build_list_query(nl_query)
        elif nl_query.intent == QueryIntent.PATH:
            return self._build_path_query(nl_query)
        else:
            return None

    def _build_reason_query(self, query: NLQuery) -> Dict:
        """构建推理查询"""
        return {
            "type": "reason",
            "source": query.entities[0] if query.entities else None,
            "target": query.target_entity,
            "layer_filter": query.layer_filter,
            "max_depth": 5,
        }

    def _build_verify_query(self, query: NLQuery) -> Dict:
        """构建验证查询"""
        return {
            "type": "verify",
            "source": query.entities[0] if len(query.entities) > 0 else None,
            "target": query.entities[1] if len(query.entities) > 1 else query.target_entity,
            "relation": "IMPLIES",
        }

    def _build_query_query(self, query: NLQuery) -> Dict:
        """构建查询查询"""
        return {
            "type": "query",
            "entity": query.entities[0] if query.entities else None,
            "layer_filter": query.layer_filter,
        }

    def _build_explain_query(self, query: NLQuery) -> Dict:
        """构建解释查询"""
        return {
            "type": "explain",
            "entity": query.entities[0] if query.entities else None,
            "include_dependencies": True,
            "max_depth": 3,
        }

    def _build_list_query(self, query: NLQuery) -> Dict:
        """构建列表查询"""
        return {
            "type": "list",
            "layer_filter": query.layer_filter or "L1",
            "node_type": None,
        }

    def _build_path_query(self, query: NLQuery) -> Dict:
        """构建路径查询"""
        return {
            "type": "path",
            "source": query.entities[0] if len(query.entities) > 0 else None,
            "target": query.entities[1] if len(query.entities) > 1 else None,
            "max_length": 10,
        }

    def execute(self, text: str, reasoner=None) -> BridgeResult:
        """执行完整的桥接流程"""
        # 1. 解析
        nl_query = self.parse(text)

        # 2. 转换为符号查询
        symbolic_query = self.to_symbolic_query(nl_query)

        if not symbolic_query:
            return BridgeResult(
                success=False,
                query_type="unknown",
                symbolic_query=None,
                nl_response="无法解析查询意图，请尝试使用更明确的表述。",
                reasoning_result=None,
                confidence=nl_query.confidence
            )

        # 3. 执行符号查询（如果有推理器）
        reasoning_result = None
        if reasoner and self.graph:
            reasoning_result = self._execute_symbolic(symbolic_query, reasoner)

        # 4. 生成自然语言响应
        nl_response = self._generate_response(nl_query, symbolic_query, reasoning_result)

        return BridgeResult(
            success=True,
            query_type=symbolic_query["type"],
            symbolic_query=symbolic_query,
            nl_response=nl_response,
            reasoning_result=reasoning_result,
            confidence=nl_query.confidence
        )

    def _execute_symbolic(self, query: Dict, reasoner) -> Any:
        """执行符号查询"""
        qtype = query.get("type")

        if qtype == "reason":
            source = query.get("source")
            target = query.get("target")
            if source and target:
                return reasoner.check_implication(source, target)
            elif source:
                # 查找所有可推导的节点
                return reasoner.find_all_derivable(source)

        elif qtype == "verify":
            source = query.get("source")
            target = query.get("target")
            if source and target:
                return reasoner.check_implication(source, target)

        elif qtype == "query":
            entity = query.get("entity")
            if entity and entity in self.graph.nodes:
                return self.graph.nodes[entity]

        elif qtype == "list":
            layer = query.get("layer_filter")
            return [n for n in self.graph.nodes.values() if n.layer == layer]

        return None

    def _generate_response(self, nl_query: NLQuery, symbolic_query: Dict, result: Any) -> str:
        """生成自然语言响应"""
        qtype = symbolic_query.get("type")

        if qtype == "reason":
            if result:
                if hasattr(result, 'result'):
                    status = "可证明" if result.result == InferenceResult.PROVEN else "不可证明"
                    return f"推理结果：{nl_query.entities[0]} → {nl_query.target_entity} 是【{status}】的。"
                else:
                    return f"从 {nl_query.entities[0]} 可以推导出的结论包括：{', '.join(str(r) for r in result[:5])}"
            return f"正在分析 {nl_query.entities[0]} 的推导关系..."

        elif qtype == "verify":
            if result and hasattr(result, 'result'):
                status = "成立" if result.result == InferenceResult.PROVEN else "不成立"
                return f"验证结果：该命题是【{status}】的。"
            return "无法验证该命题，请检查实体ID是否正确。"

        elif qtype == "query":
            if result and isinstance(result, ConceptNode):
                return f"【{result.name}】({result.layer})\n{result.content[:200]}..."
            return f"未找到实体：{symbolic_query.get('entity')}"

        elif qtype == "explain":
            entity = symbolic_query.get("entity")
            return f"正在解释 {entity} 的含义和背景..."

        elif qtype == "list":
            if result:
                items = [f"- {n.name} ({n.id})" for n in result[:10]]
                return f"找到 {len(result)} 个结果：\n" + "\n".join(items)
            return "未找到匹配的项目。"

        elif qtype == "path":
            return f"正在查找从 {symbolic_query.get('source')} 到 {symbolic_query.get('target')} 的推导路径..."

        return "查询已接收，正在处理..."

def create_bridge_with_kb(kb_dir: str = "knowledge_base") -> NLToSymbolicBridge:
    """使用知识库创建桥接器"""
    loader = KBLoader(kb_dir)
    count = loader.load_all()
    print(f"Loaded {count} entries for bridge")
    graph = loader.to_graph()
    return NLToSymbolicBridge(graph)

# Demo
if __name__ == "__main__":
    print("=" * 60)
    print("NL → Symbolic Bridge Demo")
    print("=" * 60)

    # 创建桥接器（不加载知识库，仅演示解析）
    bridge = NLToSymbolicBridge()

    test_queries = [
        "A1能推出什么结论？",
        "验证A2是否蕴含T1",
        "什么是A3终极热税？",
        "解释热税机制",
        "列出所有L1公理",
        "从A1到T3的推导路径是什么？",
    ]

    for query in test_queries:
        print(f"\n查询: {query}")
        parsed = bridge.parse(query)
        print(f"  意图: {parsed.intent.name}")
        print(f"  实体: {parsed.entities}")
        print(f"  目标: {parsed.target_entity}")
        print(f"  层级: {parsed.layer_filter}")
        print(f"  置信度: {parsed.confidence:.2f}")

        symbolic = bridge.to_symbolic_query(parsed)
        print(f"  符号查询: {json.dumps(symbolic, ensure_ascii=False)}")
