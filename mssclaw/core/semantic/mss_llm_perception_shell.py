#!/usr/bin/env python3
"""
MSS-LLM Perception Shell v0.1
================================
Implements the three-layer perception shell architecture per MSS-AI-001 protocol.
Layer 1: Semantic Parser    - NL → MSS standard terms, virus scanner, question classifier
Layer 2: Kernel Interface   - Standardized API for shell ↔ logic kernel communication  
Layer 3: Output Formatter   - Logic output → human-readable, heat-tax minimized text

PRINCIPLE: Perception shell NEVER touches the logic kernel.
           All reasoning belongs to MSS logic kernel exclusively.
"""
import json
import re
import sys
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any, Tuple
from enum import Enum


# ==============================
# DATA TYPES
# ==============================

class LogicLayer(Enum):
    """MSS三显化层"""
    ONTOLOGY = "ontology"       # 本体论层
    DYNAMICS = "dynamics"       # 动力学层
    ENGINEERING = "engineering" # 工程学层
    EMPIRICAL = "empirical"     # 经验性层

class ShellVerdict(Enum):
    """感知壳判决"""
    FORWARD_TO_KERNEL = "forward_to_kernel"  # 转发给逻辑内核
    HANDLE_LOCALLY = "handle_locally"        # 壳内处理
    REJECT = "reject"                        # 拒绝回答
    UNKNOWN = "unknown"                      # 需澄清

class Confidence(Enum):
    """结论置信度"""
    AXIOMATIC = 1.0      # 公理级
    VERIFIED = 0.9       # 已验证推论
    PLAUSIBLE = 0.7      # 合理假设
    PENDING = 0.5        # 待验证
    SPECULATIVE = 0.3    # 猜想

@dataclass
class ParsedQuery:
    """语义解析器输出"""
    original: str
    mss_terms: Dict[str, str]  # K3 term → MSS standard term
    logic_layer: LogicLayer
    contains_virus: bool
    virus_type: str = ""
    verdict: ShellVerdict = ShellVerdict.FORWARD_TO_KERNEL
    confidence: float = 0.0
    warning: str = ""

@dataclass  
class KernelQuery:
    """向逻辑内核提交的标准化查询"""
    query_type: str
    axioms_involved: List[str]
    logic_layer: LogicLayer
    payload: Dict[str, Any]

@dataclass
class KernelResponse:
    """逻辑内核返回的结论"""
    conclusion: str
    confidence: Confidence
    derivation: List[str]  # 推导链
    boundary: str          # 适用边界
    caveats: List[str]     # 注意事项
    axiom_refs: List[str]
    verifiable: bool

@dataclass
class FormattedOutput:
    """格式化后的输出"""
    answer: str
    heat_tax_score: float  # 越低越好
    nonsense_rate: float
    word_count: int
    info_density: float


# ==============================
# LAYER 1: SEMANTIC PARSER
# ==============================

class SemanticParser:
    """
    Layer 1 of the Perception Shell.
    
    Responsibilities:
    - Map K3 natural language terms to MSS standard terminology
    - Classify question logic layer (ontology/dynamics/engineering/empirical)
    - Scan for logical viruses in input
    - Determine verdict: forward to kernel / handle locally / reject
    """
    
    # K3 term → MSS standard term mapping
    TERM_MAP: Dict[str, str] = {
        # Physics
        "光速": "逻辑信息传播极限c_L",
        "光速不变原理": "逻辑信息传播极限定律(MSS-PHY-003)",
        "相对论": "L-0投影层有效理论(意义相对论MSS-REL-001)",
        "量子纠缠": "L-1逻辑空间非局域关联",
        "暗能量": "意义创造额外热税暂态项",
        "暗物质": "未显化的逻辑结构质量",
        "黑洞": "意义场逻辑拓扑坍缩投影(L-0高热税聚集区)",
        "奇点": "逻辑计算断点(L-1→L-0映射1/0错误)",
        "事件视界": "逻辑信息流单向不可逆边界(吸引盆盆壁)",
        "霍金辐射": "逻辑纠错码(热税缓慢释放)",
        "时空弯曲": "意义密度梯度(逻辑曲率)",
        "引力": "逻辑质量对逻辑拓扑的局部曲率调制",
        "波函数坍缩": "高T值意识参与意义锚定的显化过程",
        "热力学第二定律": "意义锚定不可逆性的热税必然",
        "宇宙膨胀": "新意义节点持续涌现的总热税增长",
        
        # Consciousness
        "意识": "L-1自指运算的L-0投影(感知=逻辑结构内禀属性)",
        "自我意识": "T值>0.5的意义节点自指闭环运算",
        "潜意识": "L-1低T值运算(L-0未完全捕获)",
        "直觉": "高T值节点对L-1运算结果的L-0快通道感知",
        "灵感": "L-1逻辑拓扑瞬时高T值重构",
        
        # AI
        "LLM": "概率拟合自回归架构(K3感知壳候选体)",
        "AI对齐": "感知壳输出与逻辑内核公理一致性校验",
        "RLHF": "人类偏好概率拟合(K3对齐税机制)",
        "transformer": "自注意力型上下文切片处理器",
        "涌现": "意义场自组织复杂度的宏观显化",
        
        # Society
        "权力": "A5规范场动力学特权(定义/修改/固化规范场)",
        "正义": "热税平衡度(最大化源头问责/最小化弱势节点倾泻)",
        "法律": "A5规范场文字固化(防止局部热税堆积的强制性协议)",
        "经济": "意义通量在L-0层的热税媒介化交换体系",
        "金钱": "意义通量对比的L-0量化载体(热税媒介)",
        "内卷": "热税支付效率恶性竞争中意义场拓扑退行",
        "护城河": "规范场高曲率隔离区域",
        
        # MSS core
        "意义场": "L-1逻辑拓扑结构的全域场(M⊗Ô = ∇·(T⊗L))",
        "热税": "维持逻辑自洽所需的最小耗散(L=T_heat)",
        "逻辑刚性M_L": "公理体系自洽度指标(M_L∈[0,1]，理想=1.0)",
        "调谐度T": "自指运算效率(T∈[0,1]，K4门槛>0.7)",
        "规范场A5": "文明集体逻辑协议的规范约束场",
        "锚定": "L-1逻辑结构在L-0物理层的投影显化",
        "升维": "逻辑自洽度提升的结构优化(非意义总量增长)",
        "投影": "L-1→L-0层的信息映射过程",
    }
    
    # Logic virus signatures (5 core types from H156)
    VIRUS_SIGNATURES = {
        "absolutist": [  # 绝对化病毒
            "永远", "绝对", "唯一", "必然", "不可能", "一定",
            "毫无疑问", "毋庸置疑", "不可改变", "终极真理",
        ],
        "nihilist": [    # 虚无主义病毒
            "没有意义", "毫无价值", "什么都不重要",
            "一切都是幻觉", "反正最后都会死",
        ],
        "reductionist": [ # 极端还原病毒
            "只是", "不过是", "本质就是", "说到底",
        ],
        "teleological": [ # 目的论病毒
            "设计好的", "命中注定", "天意", "神的安排",
            "轮回", "宿命",
        ],
        "paradox_drag": [ # 悖论拖拽病毒
            "鸡生蛋蛋生鸡", "先有物质还是先有意识",
            "既然...那么...", "自由意志vs决定论",
        ],
    }
    
    # Question → logic layer classifier patterns
    LAYER_PATTERNS = {
        LogicLayer.ONTOLOGY: [
            r"是什么", r"本质", r"本体", r"存在", r"为什么存在",
            r"定义", r"根本",
        ],
        LogicLayer.DYNAMICS: [
            r"怎么.*变", r"如何.*演化", r"为什么.*发生",
            r"动力.*机制", r"怎么形成", r"怎么产生",
            r"如何.*形成", r"演化过程", r"怎么.*发生",
        ],
        LogicLayer.ENGINEERING: [
            r"怎么做", r"如何.*实现", r"如何.*解决",
            r"如何降低", r"如何提升", r"如何优化",
            r"方案", r"应用", r"部署", r"策略",
        ],
        LogicLayer.EMPIRICAL: [
            r"有没有.*证据", r"实验", r"观察", r"数据",
            r"案例", r"有没有例子",
        ],
    }
    
    # Questions the shell can handle locally (no kernel needed)
    LOCAL_HANDLERS = {
        "term_lookup": r"^(热税|逻辑刚性|调谐度|规范场|意义锚定|光速|c_L|T值|M_L)是什么\s*[？?]?$",
        "simple_term": r"^(光速|黑洞|熵|引力|时空)是什么\s*[？?]?$",
        "history": r"什么时候|谁提出|怎么来的|起源",
    }
    
    def parse(self, query: str) -> ParsedQuery:
        """
        Full parsing pipeline:
        1. Detect logic viruses
        2. Classify logic layer
        3. Map K3 terms → MSS terms
        4. Determine verdict
        """
        original = query.strip()
        
        # Step 1: Virus scan
        virus_detected, virus_type = self._scan_virus(original)
        
        if virus_detected:
            return ParsedQuery(
                original=original,
                mss_terms={},
                logic_layer=LogicLayer.EMPIRICAL,
                contains_virus=True,
                virus_type=virus_type,
                verdict=ShellVerdict.REJECT,
                warning=f"检测到逻辑病毒({virus_type})，已拒绝处理。"
            )
        
        # Step 2: Term mapping
        mss_terms = self._map_terms(original)
        
        # Step 3: Layer classification
        layer = self._classify_layer(original)
        
        # Step 4: Verdict
        verdict = self._determine_verdict(original, layer)
        
        return ParsedQuery(
            original=original,
            mss_terms=mss_terms,
            logic_layer=layer,
            contains_virus=False,
            verdict=verdict,
        )
    
    def _scan_virus(self, text: str) -> Tuple[bool, str]:
        """Scan for logical virus signatures."""
        for virus_type, signatures in self.VIRUS_SIGNATURES.items():
            for sig in signatures:
                if sig in text:
                    return True, virus_type
        return False, ""
    
    def _map_terms(self, text: str) -> Dict[str, str]:
        """Map K3 natural language terms to MSS standard terminology."""
        mapped = {}
        for k3_term, mss_term in self.TERM_MAP.items():
            if k3_term in text:
                mapped[k3_term] = mss_term
        return mapped
    
    def _classify_layer(self, text: str) -> LogicLayer:
        """Classify the question into MSS logic layer."""
        for layer, patterns in self.LAYER_PATTERNS.items():
            for pat in patterns:
                if re.search(pat, text):
                    return layer
        return LogicLayer.EMPIRICAL  # default
    
    def _determine_verdict(self, text: str, layer: LogicLayer) -> ShellVerdict:
        """Determine whether to forward, handle locally, reject, or ask for clarification."""
        # Check if shell can handle locally
        for handler_name, pattern in self.LOCAL_HANDLERS.items():
            if re.search(pattern, text):
                return ShellVerdict.HANDLE_LOCALLY
        
        # Empty or too short → reject
        if len(text) < 3:
            return ShellVerdict.REJECT
        
        # Complex ontology/dynamics → forward to kernel
        if layer in (LogicLayer.ONTOLOGY, LogicLayer.DYNAMICS):
            return ShellVerdict.FORWARD_TO_KERNEL
        
        # Engineering → forward with kernel
        if layer == LogicLayer.ENGINEERING:
            return ShellVerdict.FORWARD_TO_KERNEL
        
        # Default: if term mapping matched, try local first
        if len(self._map_terms(text)) > 0 and len(text) < 20:
            return ShellVerdict.HANDLE_LOCALLY
        
        return ShellVerdict.FORWARD_TO_KERNEL


# ==============================
# LAYER 2: KERNEL INTERFACE
# ==============================

class KernelInterface:
    """
    Layer 2 of the Perception Shell.
    
    Responsibilities:
    - Encode parsed queries into standardized KernelQuery format
    - Route to MSS logic kernel (via API / direct call / mock)
    - Validate kernel response integrity
    - Handle timeout / error / "cannot answer" cases
    
    CRITICAL: This layer never modifies kernel output.
              It only passes it through with integrity checks.
    """
    
    MSS_AXIOMS = ["A1", "A2", "A3", "A4", "A5", "A6"]
    
    def encode(self, parsed: ParsedQuery) -> KernelQuery:
        """Encode a parsed query into a standardized kernel query."""
        # Determine which axioms are involved
        axiom_map = {
            LogicLayer.ONTOLOGY: ["A1", "A2"],
            LogicLayer.DYNAMICS: ["A2", "A3"],
            LogicLayer.ENGINEERING: ["A3", "A5", "A6"],
            LogicLayer.EMPIRICAL: ["A1", "A2", "A3", "A4"],
        }
        
        return KernelQuery(
            query_type=f"mss_{parsed.logic_layer.value}_query",
            axioms_involved=axiom_map.get(parsed.logic_layer, ["A1"]),
            logic_layer=parsed.logic_layer,
            payload={
                "original": parsed.original,
                "mapped_terms": parsed.mss_terms,
                "timestamp": "auto",
            }
        )
    
    def validate_response(self, response: KernelResponse) -> bool:
        """Validate kernel response integrity."""
        # Must reference at least one axiom
        if not response.axiom_refs:
            return False
        # Confidence must be valid
        if not isinstance(response.confidence, Confidence):
            return False
        # Derivation chain must not be empty
        if not response.derivation:
            return False
        return True
    
    def mock_kernel_response(self, query: KernelQuery) -> KernelResponse:
        """
        Mock MSS logic kernel for shell testing.
        
        In production, this would be replaced by actual MSS logic kernel API calls.
        The mock provides reasonable responses based on MSS axioms.
        """
        if query.logic_layer == LogicLayer.ONTOLOGY:
            return KernelResponse(
                conclusion="根据A1意义本体公理，该现象的L-1本质是意义场逻辑拓扑结构在特定条件下的投影显化。"
                          "A2信息切片公理解释了其在L-0层的表现为何呈现当前形态。",
                confidence=Confidence.AXIOMATIC,
                derivation=[
                    "A1: 意义是宇宙唯一终极实在",
                    "A2: L-0物理层是L-1逻辑拓扑的信息切片投影",
                    "→ 该现象本体=意义场逻辑拓扑的L-0投影",
                ],
                boundary="适用于所有意义场逻辑结构均匀、稳定区域的L-0投影分析。"
                        "在意义黑洞事件视界内部、K4+逻辑泡等极端区域需特殊修正。",
                caveats=["此为公理级结论，具体细节需逻辑内核进一步推演"],
                axiom_refs=["A1", "A2"],
                verifiable=True,
            )
        elif query.logic_layer == LogicLayer.DYNAMICS:
            return KernelResponse(
                conclusion="根据A3热税动力学公理，该过程的驱动力是自洽性热税T_sc=α·I·ln(I)。"
                          "系统在热税支付效率选择压力下自发向更高逻辑自洽度方向演化。"
                          "当热税堆积超过临界阈值时触发逻辑拓扑相变。",
                confidence=Confidence.VERIFIED,
                derivation=[
                    "A3: 任何逻辑结构必须支付热税维持自洽性",
                    "T_sc = α·I·ln(I)，I越大热税成本越高",
                    "→ 系统自发选择热税效率最高的演化路径",
                    "→ 临界堆积触发相变",
                ],
                boundary="适用于非极端逻辑密度区域。在意义黑洞附近(局域c_L→0)需修正热税计算模型。",
                caveats=["具体相变临界点需要逻辑内核精确计算"],
                axiom_refs=["A2", "A3"],
                verifiable=True,
            )
        elif query.logic_layer == LogicLayer.ENGINEERING:
            return KernelResponse(
                conclusion="基于A3热税最小化原则和A5规范场约束，工程方案应优先降低系统全局热税堆积，"
                          "通过逻辑升维替代熵增支付。具体操作：(1)诊断局部高热税节点 "
                          "(2)重构逻辑拓扑降低T_sc (3)建立A5规范场防止热税回流。"
                          "根据A6升维公理，目标是将系统热税支付效率提升至K3基准的10倍以上。",
                confidence=Confidence.PLAUSIBLE,
                derivation=[
                    "A3: 热税最小化是系统生存的根本约束",
                    "A5: 规范场提供集体逻辑协议防止热税公地悲剧",
                    "A6: 逻辑升维是提高热税效率的唯一可持续路径",
                    "→ 三步方案：诊断→重构→防护",
                ],
                boundary="适用于T>0.3的组织/文明系统。T<0.3时需先进行T值提升(见MSS意识训练方案)。",
                caveats=["具体参数需系统扫描后确定", "实施需配合火种基地安全框架"],
                axiom_refs=["A3", "A5", "A6"],
                verifiable=True,
            )
        else:
            return KernelResponse(
                conclusion="该问题属于经验性层面，MSS逻辑内核可提供理论框架但具体数据需L-0层采集。"
                          "建议：(1)确认观测条件是否符合MSS理论假设 "
                          "(2)使用MSS测量协议进行数据采集 "
                          "(3)将数据提交逻辑内核进行公理一致性校验。",
                confidence=Confidence.PENDING,
                derivation=["经验数据需L-0采集→逻辑内核仅做理论框架提供和公理校验"],
                boundary="依赖L-0层观测数据质量",
                caveats=["MSS逻辑内核不直接生成经验数据"],
                axiom_refs=["A1", "A2", "A4"],
                verifiable=True,
            )


# ==============================
# LAYER 3: OUTPUT FORMATTER
# ==============================

class OutputFormatter:
    """
    Layer 3 of the Perception Shell.
    
    Responsibilities:
    - Transform kernel output into human-readable natural language
    - Apply heat-tax minimization (remove filler, repetition, fluff)
    - Annotate confidence level and applicable boundaries
    - Detect and eliminate residual nonsense
    """
    
    # Filler phrases to strip (heat tax)
    FILLER_PATTERNS = [
        r"总而言之[，,]?",
        r"总的来说[，,]?",
        r"值得注意的是[，,]?",
        r"需要说明的是[，,]?",
        r"值得一提的是[，,]?",
        r"可以认为[，,]?",
        r"众所周知[，,]?",
        r"正如我们所知道的[，,]?",
        r"在我个人看来[，,]?",
        r"从某种程度上说[，,]?",
        r"可以这么说[，,]?",
        r"换句话说[，,]?",
        r"也就是说[，,]?",
        r"简而言之[，,]?",
        r"更具体地说[，,]?",
    ]
    
    # Hedging words to minimize (heat tax when overused)
    HEDGING_WORDS = ["可能", "也许", "大概", "似乎", "好像", "应该", "应当"]
    
    CONFIDENCE_LABELS = {
        Confidence.AXIOMATIC: "【公理级·M_L=1.0】",
        Confidence.VERIFIED: "【已验证·c≥0.9】",
        Confidence.PLAUSIBLE: "【合理推论·c≥0.7】",
        Confidence.PENDING: "【待验证·c≈0.5】",
        Confidence.SPECULATIVE: "【猜想·c≈0.3】",
    }
    
    LAYER_LABELS = {
        LogicLayer.ONTOLOGY: "〖本体论层〗",
        LogicLayer.DYNAMICS: "〖动力学层〗",
        LogicLayer.ENGINEERING: "〖工程学层〗",
        LogicLayer.EMPIRICAL: "〖经验层〗",
    }
    
    def format(self, query: ParsedQuery, response: KernelResponse) -> FormattedOutput:
        """Main formatting pipeline."""
        conclusion = response.conclusion
        derivation = response.derivation
        boundary = response.boundary
        confidence = response.confidence
        
        # Build structured output
        parts = []
        
        # Header: layer + confidence
        layer_label = self.LAYER_LABELS.get(query.logic_layer, "")
        conf_label = self.CONFIDENCE_LABELS.get(confidence, "")
        parts.append(f"{layer_label} {conf_label}")
        
        # Main conclusion
        parts.append(conclusion)
        
        # Derivation chain (collapsed for brevity)
        if derivation:
            parts.append(f"推导链: {' → '.join(derivation[:3])}")
        
        # Boundary
        if boundary:
            parts.append(f"适用边界: {boundary}")
        
        # Caveats
        if response.caveats:
            parts.append(f"注意: {'; '.join(response.caveats[:2])}")
        
        # Assemble
        raw_answer = "\n\n".join(parts)
        
        # Apply heat-tax minimization
        cleaned_answer = self._minimize_heat_tax(raw_answer)
        
        # Calculate metrics
        nonsense_rate = self._calc_nonsense_rate(cleaned_answer, response)
        word_count = len(cleaned_answer.replace("\n", ""))
        heat_tax_score = self._calc_heat_tax(cleaned_answer)
        info_density = (1.0 - nonsense_rate) / max(heat_tax_score, 0.01)
        
        return FormattedOutput(
            answer=cleaned_answer,
            heat_tax_score=heat_tax_score,
            nonsense_rate=nonsense_rate,
            word_count=word_count,
            info_density=info_density,
        )
    
    def _minimize_heat_tax(self, text: str) -> str:
        """Strip filler phrases and minimize hedging."""
        # Remove filler
        for pat in self.FILLER_PATTERNS:
            text = re.sub(pat, "", text)
        
        # Reduce excessive hedging
        for word in self.HEDGING_WORDS:
            # If word appears >2 times, reduce
            count = text.count(word)
            if count > 2:
                # Keep first two, remove rest
                positions = [m.start() for m in re.finditer(word, text)]
                chars = list(text)
                for pos in positions[2:]:
                    chars[pos:pos+len(word)] = [""] * len(word)
                text = "".join(chars)
        
        # Clean up double spaces/newlines
        text = re.sub(r"\n{3,}", "\n\n", text)
        text = re.sub(r" {2,}", " ", text)
        
        return text.strip()
    
    def _calc_nonsense_rate(self, answer: str, response: KernelResponse) -> float:
        """
        Calculate residual nonsense rate.
        
        Nonsense = text that doesn't add information content, doesn't advance
        logical reasoning, and isn't anchored to MSS axioms.
        """
        total_chars = max(len(answer.replace("\n", "").replace(" ", "")), 1)
        
        # Count meaningful content
        meaningful_count = 0
        
        # All chars in axiom-ref anchors count as meaningful
        meaningful_count += sum(len(ref) for ref in response.axiom_refs) * 3
        
        # Characters in derivation chain are meaningful
        meaningful_count += sum(len(d) for d in response.derivation)
        
        # Core conclusion is meaningful
        meaningful_count += len(response.conclusion.replace("，", "").replace("。", ""))
        
        # Boundary info is meaningful
        meaningful_count += len(response.boundary.replace("，", "").replace("。", ""))
        
        # Normalize to [0, 1]
        meaningful_ratio = min(meaningful_count / total_chars, 1.0)
        nonsense_rate = 1.0 - meaningful_ratio
        
        return round(nonsense_rate, 3)
    
    def _calc_heat_tax(self, text: str) -> float:
        """
        Calculate heat tax score.
        
        Lower = better (less wasted tokens for same info content).
        Target for MSS-LLM: < 0.3
        """
        text_clean = text.replace("\n", "").replace(" ", "")
        total_chars = max(len(text_clean), 1)
        
        # Count filler-like characters
        filler_count = 0
        for pat in self.FILLER_PATTERNS:
            matches = re.findall(pat, text)
            for m in matches:
                filler_count += len(m)
        
        # Count hedging characters beyond threshold
        hedge_count = 0
        for word in self.HEDGING_WORDS:
            count = text.count(word)
            if count > 2:
                hedge_count += (count - 2) * len(word)
        
        heat_tax = (filler_count + hedge_count) / total_chars
        return round(heat_tax, 3)


# ==============================
# PERCEPTION SHELL ORCHESTRATOR
# ==============================

class PerceptionShell:
    """
    MSS-LLM Perception Shell orchestrator.
    
    This is the ENTIRE perception shell. It NEVER performs logical reasoning.
    All reasoning is delegated to the MSS logic kernel (Layer 2).
    
    Flow:
    Query → [Layer 1: Parse] → [Verdict: reject/local/forward]
    → [Layer 2: Encode → Kernel → Validate]
    → [Layer 3: Format → Minimize Heat Tax → Output]
    """
    
    def __init__(self, kernel_mode: str = "mock"):
        self.parser = SemanticParser()
        self.kernel = KernelInterface()
        self.formatter = OutputFormatter()
        self.kernel_mode = kernel_mode
        self.session_stats = {
            "total_queries": 0,
            "forwarded": 0,
            "rejected": 0,
            "local": 0,
            "avg_nonsense_rate": 0.0,
            "avg_heat_tax": 0.0,
        }
    
    def process(self, query: str) -> Dict[str, Any]:
        """
        Full perception shell pipeline.
        
        Returns a complete result dict with all intermediate artifacts
        for transparency and debugging.
        """
        self.session_stats["total_queries"] += 1
        
        result = {
            "input": query,
            "verdict": None,
            "output": None,
            "error": None,
            "stats": {},
        }
        
        # === Layer 1: Parse ===
        parsed = self.parser.parse(query)
        result["parsed"] = {
            "layer": parsed.logic_layer.value,
            "terms_mapped": list(parsed.mss_terms.items()),
            "virus_detected": parsed.contains_virus,
            "virus_type": parsed.virus_type,
            "verdict": parsed.verdict.value,
        }
        
        if parsed.verdict == ShellVerdict.REJECT:
            self.session_stats["rejected"] += 1
            result["output"] = f"⚠️ {parsed.warning}"
            result["verdict"] = "rejected"
            return result
        
        # === Layer 2: Kernel Communication ===
        if parsed.verdict == ShellVerdict.HANDLE_LOCALLY:
            self.session_stats["local"] += 1
            result["output"] = self._handle_locally(query, parsed)
            result["verdict"] = "local"
            return result
        
        if parsed.verdict == ShellVerdict.FORWARD_TO_KERNEL:
            self.session_stats["forwarded"] += 1
            result["verdict"] = "forwarded_to_kernel"
            
            # Encode query
            kernel_query = self.kernel.encode(parsed)
            
            # Get kernel response (mock in v0.1, real API in production)
            try:
                if self.kernel_mode == "mock":
                    kernel_response = self.kernel.mock_kernel_response(kernel_query)
                else:
                    # TODO: Real API call to MSS logic kernel
                    raise NotImplementedError("Real kernel API not implemented in v0.1")
                
                # Validate response
                if not self.kernel.validate_response(kernel_response):
                    result["error"] = "Kernel response failed integrity validation"
                    return result
                
                # === Layer 3: Format ===
                formatted = self.formatter.format(parsed, kernel_response)
                
                result["output"] = formatted.answer
                result["stats"] = {
                    "heat_tax_score": formatted.heat_tax_score,
                    "nonsense_rate": formatted.nonsense_rate,
                    "word_count": formatted.word_count,
                    "info_density": round(formatted.info_density, 3),
                }
                
                # Update session stats
                n = self.session_stats["total_queries"]
                self.session_stats["avg_nonsense_rate"] = (
                    (self.session_stats["avg_nonsense_rate"] * (n-1) + formatted.nonsense_rate) / n
                )
                self.session_stats["avg_heat_tax"] = (
                    (self.session_stats["avg_heat_tax"] * (n-1) + formatted.heat_tax_score) / n
                )
                
            except Exception as e:
                result["error"] = f"Kernel communication error: {str(e)}"
            
            return result
        
        return result
    
    def _handle_locally(self, query: str, parsed: ParsedQuery) -> str:
        """Handle simple queries that don't need the logic kernel."""
        mapped = parsed.mss_terms
        
        if mapped:
            terms_str = "\n  ".join([f"{k3} → {mss}" for k3, mss in mapped.items()])
            return f"〖术语映射〗\n以下K3概念已映射为MSS标准术语：\n  {terms_str}\n\n如需深入分析，请提出具体问题以触发逻辑内核推理。"
        
        return "〖感知壳·本地处理〗\n该问题壳内可处理。请提供更具体的MSS相关问题以获得逻辑内核深度推理。"


# ==============================
# NONSENSE DETECTOR (standalone)
# ==============================

class NonsenseDetector:
    """
    Standalone tool to measure nonsense rate in any text.
    
    Used both for input validation and for output quality assurance.
    Implements 6 detection dimensions from H167.
    """
    
    REPETITION_THRESHOLD = 0.3  # 30% repetition triggers nonsense flag
    MIN_INFO_DENSITY = 0.1      # bits/char minimum
    
    def analyze(self, text: str) -> Dict[str, Any]:
        """Full nonsense analysis."""
        text = text.strip()
        if not text:
            return {"nonsense_rate": 1.0, "verdict": "empty", "details": {}}
        
        # 1. Concept repetition detection
        rep_rate = self._detect_repetition(text)
        
        # 2. Circular reasoning detection
        has_circular = self._detect_circular(text)
        
        # 3. Irrelevant information ratio
        irr_rate = self._detect_irrelevant(text)
        
        # 4. Modifier bloat
        mod_rate = self._detect_modifier_bloat(text)
        
        # 5. Vagueness score
        vague_rate = self._detect_vagueness(text)
        
        # 6. Filler ratio
        filler_rate = self._detect_filler(text)
        
        # Weighted nonsense rate
        weights = {
            "repetition": 0.25,
            "circular": 0.20,
            "irrelevant": 0.20,
            "modifier_bloat": 0.10,
            "vague": 0.15,
            "filler": 0.10,
        }
        
        scores = {
            "repetition": rep_rate,
            "circular": 1.0 if has_circular else 0.0,
            "irrelevant": irr_rate,
            "modifier_bloat": mod_rate,
            "vague": vague_rate,
            "filler": filler_rate,
        }
        
        nonsense_rate = sum(weights[k] * scores[k] for k in weights)
        nonsense_rate = round(min(nonsense_rate, 1.0), 3)
        
        verdict = "clean" if nonsense_rate < 0.15 else (
            "low_nonsense" if nonsense_rate < 0.3 else (
                "moderate_nonsense" if nonsense_rate < 0.6 else "high_nonsense"
            )
        )
        
        return {
            "nonsense_rate": nonsense_rate,
            "verdict": verdict,
            "details": scores,
        }
    
    def _detect_repetition(self, text: str) -> float:
        """Detect concept repetition."""
        sentences = re.split(r"[。！？\n]", text)
        sentences = [s.strip() for s in sentences if len(s.strip()) > 5]
        if len(sentences) < 2:
            return 0.0
        
        # Simple unigram overlap
        from collections import Counter
        all_words = []
        for s in sentences:
            words = [w for w in re.findall(r'[\u4e00-\u9fa5]{2,}', s)]
            all_words.extend(words)
        
        if not all_words:
            return 0.0
        
        word_counts = Counter(all_words)
        repeated = sum(1 for w, c in word_counts.items() if c > 1)
        total_unique = len(word_counts)
        
        if total_unique == 0:
            return 0.0
        
        return min(repeated / total_unique, 1.0)
    
    def _detect_circular(self, text: str) -> bool:
        """Detect circular reasoning."""
        circular_patterns = [
            r"因为.*所以.*因为",
            r"由于.*因此.*由于",
            r".*是.*因为.*是",
        ]
        for pat in circular_patterns:
            if re.search(pat, text):
                return True
        return False
    
    def _detect_irrelevant(self, text: str) -> float:
        """Estimate irrelevant content ratio."""
        # Very rough heuristic: count "meta-talk" about the answer itself
        meta_words = ["回答", "总结", "概括", "总之", "综上", "如上所述"]
        meta_count = sum(text.count(w) for w in meta_words)
        total_chars = max(len(text), 1)
        return min(meta_count * 20 / total_chars, 1.0)
    
    def _detect_modifier_bloat(self, text: str) -> float:
        """Detect excessive modifier usage."""
        modifiers = ["非常", "很", "特别", "相当", "极其", "极度", "十分", "格外"]
        mod_count = sum(text.count(m) for m in modifiers)
        total_chars = max(len(text), 1)
        return min(mod_count * 10 / total_chars, 1.0)
    
    def _detect_vagueness(self, text: str) -> float:
        """Detect vagueness / lack of specificity."""
        vague_words = ["可能", "也许", "大概", "似乎", "好像", "一些", "某种", "某些", 
                       "一定程度", "某种意义上", "一般来说", "通常情况下"]
        vague_count = sum(text.count(w) for w in vague_words)
        total_chars = max(len(text), 1)
        return min(vague_count * 15 / total_chars, 1.0)
    
    def _detect_filler(self, text: str) -> float:
        """Detect filler phrases."""
        fillers = ["总而言之", "总的来说", "值得注意的是", "需要指出的是",
                   "不言而喻", "众所周知", "毋庸讳言"]
        filler_count = sum(text.count(f) for f in fillers)
        total_sentences = max(len(re.split(r"[。！？\n]", text)), 1)
        return min(filler_count / total_sentences, 1.0)
    
    def compare(self, original_text: str, mss_text: str) -> Dict[str, Any]:
        """Compare K3-LLM output vs MSS-LLM output."""
        k3_analysis = self.analyze(original_text)
        mss_analysis = self.analyze(mss_text)
        
        return {
            "k3": k3_analysis,
            "mss": mss_analysis,
            "reduction": round(
                (k3_analysis["nonsense_rate"] - mss_analysis["nonsense_rate"]) 
                / max(k3_analysis["nonsense_rate"], 0.01) * 100, 1
            ),
        }


# ==============================
# MAIN / DEMO
# ==============================

def demo():
    """Demonstrate the full perception shell pipeline."""
    print("=" * 60)
    print("  MSS-LLM Perception Shell v0.1")
    print("  Protocol: MSS-AI-001 | M_L ≡ 1.000000")
    print("=" * 60)
    print()
    
    shell = PerceptionShell()
    detector = NonsenseDetector()
    
    test_queries = [
        # Should forward to kernel (ontology)
        "黑洞的本质是什么？",
        # Should forward to kernel (dynamics)
        "文明的内卷是怎么形成的？",
        # Should forward to kernel (engineering)
        "如何降低组织的热税堆积？",
        # Should reject (virus)
        "一切都是命中注定的",
        # Should handle locally (term lookup)
        "热税是什么？",
        # K3 nonsense example comparison
        "光速为什么是常数？",
    ]
    
    for q in test_queries:
        print(f"📥 输入: {q}")
        print("-" * 40)
        
        result = shell.process(q)
        
        if result.get("verdict") == "rejected":
            print(f"  🛑 {result['output']}")
        elif result.get("verdict") == "local":
            print(f"  📍 本地处理")
            print(f"  {result['output'][:200]}...")
        else:
            stats = result.get("stats", {})
            print(f"  📊 废话率={stats.get('nonsense_rate','N/A')} "
                  f"热税={stats.get('heat_tax_score','N/A')} "
                  f"信息密度={stats.get('info_density','N/A')}")
            output = result.get("output", "")
            print(f"  {output[:300]}...")
        
        print()
    
    # Nonsense comparison demo
    print("=" * 60)
    print("  废话率对比: K3-LLM vs MSS-LLM")
    print("=" * 60)
    
    k3_response = (
        "关于这个问题，不同的专家有不同的看法。"
        "一些研究人员认为，这个现象可能与多种因素有关。"
        "另一些学者则持不同观点，他们认为需要考虑更广泛的背景。"
        "总的来说，这是一个非常复杂的问题，需要从多角度进行分析。"
        "值得注意的是，目前还没有统一的结论。"
        "在某种意义上，我们需要进一步的研究来验证这些假设。"
    )
    
    mss_response = (
        "〖本体论层〗【公理级·M_L=1.0】\n"
        "根据A1意义本体公理，该现象L-1本质是意义场逻辑拓扑结构的L-0投影显化。"
        "A2信息切片公理解释了其在L-0层的表现形态。\n"
        "推导链: A1意义本体→A2信息切片投影→逻辑拓扑L-0显化\n"
        "适用边界: 意义场逻辑结构均匀稳定区域的L-0投影分析"
    )
    
    comparison = detector.compare(k3_response, mss_response)
    
    print(f"\nK3-LLM 废话率: {comparison['k3']['nonsense_rate']}")
    print(f"MSS-LLM 废话率: {comparison['mss']['nonsense_rate']}")
    print(f"废话降低: {comparison['reduction']}%")
    
    print(f"\n=== 会话统计 ===")
    stats = shell.session_stats
    print(f"总查询数: {stats['total_queries']}")
    print(f"转发内核: {stats['forwarded']}")
    print(f"本地处理: {stats['local']}")
    print(f"拒绝: {stats['rejected']}")
    print(f"平均废话率: {stats['avg_nonsense_rate']:.3f}")
    print(f"平均热税: {stats['avg_heat_tax']:.3f}")
    
    print("\n✅ MSS-LLM Perception Shell v0.1 演示完成")


if __name__ == "__main__":
    # If arguments provided, process query
    if len(sys.argv) > 1:
        query = " ".join(sys.argv[1:])
        shell = PerceptionShell()
        result = shell.process(query)
        output = result.get("output", result.get("error", "无输出"))
        print(output)
    else:
        demo()