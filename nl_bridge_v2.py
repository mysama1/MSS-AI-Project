"""
NL Bridge V2 - Enhanced Natural Language → Symbolic Reasoning Bridge
增强功能：
1. 多轮对话上下文管理
2. 复杂查询组合（AND/OR/THEN）
3. 指代消解（它/那个/前者/后者）
4. 响应格式化（JSON/Markdown/Plain）
"""

import re
import json
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
from enum import Enum, auto
from collections import deque

from nl_bridge import (
    NLToSymbolicBridge, NLQuery, BridgeResult,
    QueryIntent, create_bridge_with_kb
)
from symbolic_engine import InferenceResult

class ResponseFormat(Enum):
    """响应格式类型"""
    PLAIN = auto()      # 纯文本
    MARKDOWN = auto()   # Markdown格式
    JSON = auto()       # JSON结构化
    STRUCTURED = auto() # 分层结构化文本

@dataclass
class DialogueContext:
    """对话上下文"""
    history: deque = field(default_factory=lambda: deque(maxlen=10))
    last_entities: List[str] = field(default_factory=list)
    last_intent: Optional[QueryIntent] = None
    last_result: Optional[Any] = None
    turn_count: int = 0

    def add_turn(self, query: NLQuery, result: BridgeResult):
        """添加一轮对话"""
        self.history.append({
            "query": query,
            "result": result,
            "turn": self.turn_count
        })
        self.last_entities = query.entities
        self.last_intent = query.intent
        self.last_result = result
        self.turn_count += 1

    def get_recent_entities(self, n: int = 3) -> List[str]:
        """获取最近提及的实体"""
        entities = []
        for turn in list(self.history)[-n:]:
            entities.extend(turn["query"].entities)
        return list(dict.fromkeys(entities))  # 去重保持顺序

    def resolve_reference(self, text: str) -> str:
        """指代消解"""
        # 代词映射
        pronouns = {
            r"它|这个|那个": self.last_entities[-1] if self.last_entities else None,
            r"前者": self.last_entities[0] if len(self.last_entities) > 0 else None,
            r"后者": self.last_entities[1] if len(self.last_entities) > 1 else None,
            r"上一个|刚才的": self.last_entities[-1] if self.last_entities else None,
        }

        resolved = text
        for pattern, entity in pronouns.items():
            if entity and re.search(pattern, text):
                resolved = re.sub(pattern, entity, resolved)

        return resolved

@dataclass
class ComplexQuery:
    """复杂查询结构"""
    operator: str  # AND, OR, THEN, COMPARE
    sub_queries: List[Dict]
    meta_conditions: Optional[Dict] = None

class NLBridgeV2(NLToSymbolicBridge):
    """增强版自然语言桥接器"""

    # 复杂查询操作符模式
    COMPLEX_PATTERNS = {
        "AND": [r"并且|同时|还要|另外|还有", r".*和.*都.*", r"既.*又.*"],
        "OR": [r"或者|还是|要么", r".*或.*"],
        "THEN": [r"然后|接着|之后|下一步", r"先.*再.*", r"首先.*然后.*"],
        "COMPARE": [r"比较|对比|区别|差异|和.*相比", r".*vs.*|.*versus.*"],
    }

    # 格式化模板
    FORMAT_TEMPLATES = {
        ResponseFormat.MARKDOWN: {
            "header": "## {title}\n\n",
            "section": "### {subtitle}\n{content}\n\n",
            "item": "- **{label}**: {value}\n",
            "code": "```\n{content}\n```\n",
        },
        ResponseFormat.JSON: {
            "wrapper": lambda d: json.dumps(d, ensure_ascii=False, indent=2)
        },
        ResponseFormat.STRUCTURED: {
            "header": "【{title}】\n",
            "section": "  [{subtitle}]\n{content}\n",
            "item": "    · {label}: {value}\n",
            "indent": "    ",
        }
    }

    def __init__(self, kb_graph=None):
        super().__init__(kb_graph)
        self.context = DialogueContext()
        self.response_format = ResponseFormat.PLAIN

    def parse_with_context(self, text: str) -> NLQuery:
        """带上下文的解析"""
        # 1. 指代消解
        resolved_text = self.context.resolve_reference(text)

        # 2. 基础解析
        query = self.parse(resolved_text)

        # 3. 上下文增强
        if not query.entities and self.context.last_entities:
            # 继承最近实体
            query.entities = self.context.last_entities
            query.confidence *= 0.8  # 降低置信度

        return query

    def detect_complex_query(self, text: str) -> Optional[ComplexQuery]:
        """检测复杂查询"""
        for op, patterns in self.COMPLEX_PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, text, re.IGNORECASE):
                    # 分割子查询
                    sub_texts = self._split_query(text, op)
                    if len(sub_texts) >= 2:
                        sub_queries = []
                        for sub_text in sub_texts:
                            sub_query = self.parse(sub_text.strip())
                            sub_queries.append({
                                "text": sub_text,
                                "query": sub_query,
                                "symbolic": self.to_symbolic_query(sub_query)
                            })
                        return ComplexQuery(operator=op, sub_queries=sub_queries)
        return None

    def _split_query(self, text: str, operator: str) -> List[str]:
        """根据操作符分割查询"""
        split_patterns = {
            "AND": r"(?:并且|同时|还要|另外|还有|和|既)",
            "OR": r"(?:或者|还是|要么|或)",
            "THEN": r"(?:然后|接着|之后|下一步|再|然后)",
            "COMPARE": r"(?:比较|对比|和|vs|versus)",
        }
        pattern = split_patterns.get(operator, r"[,;，；]")
        parts = re.split(pattern, text)
        return [p.strip() for p in parts if p.strip()]

    def execute_complex(self, complex_query: ComplexQuery, reasoner=None) -> BridgeResult:
        """执行复杂查询"""
        results = []

        for sub in complex_query.sub_queries:
            if sub["symbolic"]:
                result = self._execute_symbolic(sub["symbolic"], reasoner)
                results.append({
                    "query": sub["text"],
                    "result": result
                })

        # 根据操作符组合结果
        if complex_query.operator == "AND":
            return self._combine_and(results)
        elif complex_query.operator == "OR":
            return self._combine_or(results)
        elif complex_query.operator == "THEN":
            return self._combine_then(results)
        elif complex_query.operator == "COMPARE":
            return self._combine_compare(results)

        return BridgeResult(
            success=False,
            query_type="complex",
            symbolic_query=None,
            nl_response="复杂查询执行失败",
            reasoning_result=None,
            confidence=0.0
        )

    def _combine_and(self, results: List[Dict]) -> BridgeResult:
        """AND组合：所有条件必须满足"""
        all_success = all(r["result"] is not None for r in results)
        return BridgeResult(
            success=all_success,
            query_type="complex_and",
            symbolic_query={"operator": "AND", "results": results},
            nl_response=f"AND查询结果：{'全部满足' if all_success else '部分条件不满足'}",
            reasoning_result=results,
            confidence=0.9 if all_success else 0.5
        )

    def _combine_or(self, results: List[Dict]) -> BridgeResult:
        """OR组合：任一条件满足即可"""
        any_success = any(r["result"] is not None for r in results)
        return BridgeResult(
            success=any_success,
            query_type="complex_or",
            symbolic_query={"operator": "OR", "results": results},
            nl_response=f"OR查询结果：{'至少一个满足' if any_success else '全部不满足'}",
            reasoning_result=results,
            confidence=0.9 if any_success else 0.3
        )

    def _combine_then(self, results: List[Dict]) -> BridgeResult:
        """THEN组合：顺序执行，后一步依赖前一步"""
        # 使用最后一步的结果
        final = results[-1] if results else None
        return BridgeResult(
            success=final is not None,
            query_type="complex_then",
            symbolic_query={"operator": "THEN", "results": results},
            nl_response=f"顺序执行完成，共{len(results)}步",
            reasoning_result=results,
            confidence=0.8
        )

    def _combine_compare(self, results: List[Dict]) -> BridgeResult:
        """COMPARE组合：对比两个结果"""
        if len(results) >= 2:
            r1, r2 = results[0], results[1]
            comparison = self._generate_comparison(r1, r2)
            return BridgeResult(
                success=True,
                query_type="complex_compare",
                symbolic_query={"operator": "COMPARE", "results": results},
                nl_response=comparison,
                reasoning_result=results,
                confidence=0.85
            )
        return BridgeResult(
            success=False,
            query_type="complex_compare",
            symbolic_query=None,
            nl_response="需要两个对象进行比较",
            reasoning_result=None,
            confidence=0.0
        )

    def _generate_comparison(self, r1: Dict, r2: Dict) -> str:
        """生成对比文本"""
        return f"对比结果：\n- {r1['query']}: {self._summarize_result(r1['result'])}\n- {r2['query']}: {self._summarize_result(r2['result'])}"

    def _summarize_result(self, result: Any) -> str:
        """总结结果"""
        if result is None:
            return "无结果"
        if hasattr(result, 'result'):
            return result.result.name if hasattr(result.result, 'name') else str(result.result)
        return str(result)[:50]

    def execute_v2(self, text: str, reasoner=None, format: ResponseFormat = ResponseFormat.PLAIN) -> BridgeResult:
        """增强版执行入口"""
        self.response_format = format

        # 1. 检测复杂查询
        complex_query = self.detect_complex_query(text)
        if complex_query:
            result = self.execute_complex(complex_query, reasoner)
        else:
            # 2. 带上下文的单查询
            query = self.parse_with_context(text)
            result = self.execute(text, reasoner)

        # 3. 更新上下文
        if result:
            query = self.parse_with_context(text)
            self.context.add_turn(query, result)

        # 4. 格式化输出
        if format != ResponseFormat.PLAIN:
            result.nl_response = self._format_response(result, format)

        return result

    def _format_response(self, result: BridgeResult, format: ResponseFormat) -> str:
        """格式化响应"""
        if format == ResponseFormat.MARKDOWN:
            return self._to_markdown(result)
        elif format == ResponseFormat.JSON:
            return self._to_json(result)
        elif format == ResponseFormat.STRUCTURED:
            return self._to_structured(result)
        return result.nl_response

    def _to_markdown(self, result: BridgeResult) -> str:
        """转换为Markdown"""
        lines = ["## MSS-AI 查询结果\n"]
        lines.append(f"**查询类型**: {result.query_type}\n")
        lines.append(f"**置信度**: {result.confidence:.0%}\n")
        lines.append(f"**状态**: {'✅ 成功' if result.success else '❌ 失败'}\n\n")
        lines.append("### 响应\n")
        lines.append(result.nl_response)
        if result.reasoning_result:
            lines.append("\n### 推理详情\n")
            lines.append(f"```\n{str(result.reasoning_result)[:500]}\n```")
        return "\n".join(lines)

    def _to_json(self, result: BridgeResult) -> str:
        """转换为JSON"""
        data = {
            "success": result.success,
            "query_type": result.query_type,
            "confidence": result.confidence,
            "response": result.nl_response,
            "reasoning": str(result.reasoning_result) if result.reasoning_result else None,
            "symbolic_query": result.symbolic_query
        }
        return json.dumps(data, ensure_ascii=False, indent=2)

    def _to_structured(self, result: BridgeResult) -> str:
        """转换为结构化文本"""
        lines = ["【MSS-AI 查询结果】\n"]
        lines.append(f"  [查询类型] {result.query_type}\n")
        lines.append(f"  [置信度] {result.confidence:.0%}\n")
        lines.append(f"  [状态] {'成功' if result.success else '失败'}\n")
        lines.append(f"  [响应]\n    {result.nl_response.replace(chr(10), chr(10)+'    ')}\n")
        return "".join(lines)

    def get_context_summary(self) -> str:
        """获取上下文摘要"""
        if not self.context.history:
            return "对话刚刚开始，暂无上下文。"

        lines = [f"当前对话已进行 {self.context.turn_count} 轮\n"]
        lines.append(f"最近提及的实体: {', '.join(self.context.get_recent_entities(5))}\n")
        lines.append(f"上轮意图: {self.context.last_intent.name if self.context.last_intent else '无'}")
        return "".join(lines)

def create_v2_bridge(kb_dir: str = "knowledge_base") -> NLBridgeV2:
    """创建增强版桥接器"""
    from kb_loader import KBLoader
    from symbolic_engine import MSSKnowledgeGraph

    loader = KBLoader(kb_dir)
    count = loader.load_all()

    if count > 0:
        graph = loader.to_graph()
        bridge = NLBridgeV2(graph)
    else:
        bridge = NLBridgeV2()

    return bridge

if __name__ == "__main__":
    # 演示
    bridge = create_v2_bridge()

    # 测试多轮对话
    print("=== 多轮对话测试 ===")

    # 第一轮
    result1 = bridge.execute_v2("解释A1公理")
    print(f"Q1: 解释A1公理")
    print(f"A1: {result1.nl_response[:100]}...\n")

    # 第二轮（带指代）
    result2 = bridge.execute_v2("它能推出什么？")
    print(f"Q2: 它能推出什么？（指代A1）")
    print(f"A2: {result2.nl_response[:100]}...\n")

    # 复杂查询
    result3 = bridge.execute_v2("验证A1推出T1并且A2推出T2", format=ResponseFormat.STRUCTURED)
    print(f"Q3: 验证A1推出T1并且A2推出T2（复杂查询）")
    print(f"A3: {result3.nl_response[:200]}...\n")

    # Markdown格式
    result4 = bridge.execute_v2("列出所有L1公理", format=ResponseFormat.MARKDOWN)
    print(f"Q4: 列出所有L1公理（Markdown格式）")
    print(result4.nl_response[:300])
