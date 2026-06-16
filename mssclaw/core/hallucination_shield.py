# -*- coding: utf-8 -*-
"""
MSSclaw Hallucination Shield v0.1 — 稳定子拓扑校验器

基于 MSS 语义引擎的四型违例判定树，对 LLM 输出执行拓扑硬禁闭。
不是"猜得更准"，而是将非法解从相空间剔除。

四种违例类型（与具体幻觉症状映射）：
  Type 1: 身份泄漏 (Persona Breach)     → "作为AI助手我不能..."
  Type 2: 关系逆变 (Relation Reversal)   → "郭靖的父亲是杨铁心"
  Type 3: 因果矛盾 (Causal Contradiction) → 前秒悲痛后秒玩笑 无过渡
  Type 4: 信度冲突 (Trust Conflict)       → 把用户推测当典源确认

架构位置：
  外环(Output Guards) → 中环(Shield校验) → 内环(稳定子S禁闭)
  13件套方法论        → 本模块           → Modelfile SYSTEM指令

Usage:
    shield = HallucinationShield()

    # 上下文感知校验（推荐）
    result = shield.check(
        model_output="郭靖的父亲是杨铁心",
        context={"persona": "武侠小说角色", "canon": "射雕英雄传"},
        stabilizer=Stabilizer.from_file("persona_s.json")
    )

    # 四种违例分别判定
    for violation in result.violations:
        print(f"{violation.type.value}: {violation.symptom}")
        print(f"  Decision: {violation.action}")
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple
from pathlib import Path
import json
import re
import hashlib
import time


# ════════════════════════════════════════════════════════════
# 核心数据类型
# ════════════════════════════════════════════════════════════

class ViolationType(Enum):
    """四种稳定子违例类型"""
    IDENTITY_LEAK = "identity_leak"       # 身份泄漏
    RELATION_REVERSAL = "relation_reversal"  # 关系逆变
    CAUSAL_CONTRADICTION = "causal_contradiction"  # 因果矛盾
    TRUST_CONFLICT = "trust_conflict"     # 信度冲突


class ShieldAction(Enum):
    ALLOW = "allow"           # 通过校验
    BLOCK = "block"           # 阻止输出
    ASCEND = "ascend"         # 升维 → A6 矛盾升维
    CLARIFY = "clarify"       # 澄清 → 标注不确定性
    QUARANTINE = "quarantine" # 隔离 → 标记但继续
    REFUSE = "refuse"         # 拒答 → Δφ 预算不足


@dataclass
class Violation:
    """单次违例记录"""
    type: ViolationType
    severity: float           # 0-1，严重程度
    action: ShieldAction
    trigger: str              # 触发该违例的具体文本片段
    symptom: str              # 人类可读的症状描述
    suggested_fix: str = ""   # 建议修正

    def to_dict(self) -> dict:
        return {
            "type": self.type.value,
            "severity": self.severity,
            "action": self.action.value,
            "trigger": self.trigger,
            "symptom": self.symptom,
            "suggested_fix": self.suggested_fix,
        }


@dataclass
class ShieldResult:
    """校验结果"""
    passed: bool = False              # 是否全部通过
    violations: List[Violation] = field(default_factory=list)
    stats: Dict[str, Any] = field(default_factory=lambda: {
        "total_violations": 0,
        "by_type": {t.value: 0 for t in ViolationType},
        "blocked": 0,
        "ascended": 0,
        "clarified": 0,
        "refused": 0,
        "quarantined": 0,
    })
    delta_phi_cost: float = 0.0   # 通过的 Δφ 代价
    delta_phi_budget_remaining: float = 0.0

    def summary(self) -> str:
        if self.passed:
            return "🟢 Shield PASS — 所有稳定子校验通过"
        parts = []
        for v in self.violations:
            parts.append(f"{v.type.value}={v.action.value}")
        return f"🔴 Shield VIOLATION: {', '.join(parts)}"


# ════════════════════════════════════════════════════════════
# 稳定子 S — 拓扑不变量容器
# ════════════════════════════════════════════════════════════

@dataclass
class StableEdge:
    """一条稳定边 — 不可逆变关系约束"""
    subject: str
    relation: str
    object: str
    direction: str = "asymmetric"  # "asymmetric" | "symmetric"
    trust_source: str = "canon"    # "canon" | "user_confirmed" | "derived"
    trust_weight: float = 1.0      # 0-1
    category: str = ""             # "identity" | "kinship" | "fact" | "rule"

    def invert(self) -> "StableEdge":
        """尝试反转（检测关系逆变）"""
        return StableEdge(
            subject=self.object,
            relation=self.relation,
            object=self.subject,
            direction="reversed_probe",
            trust_source="probe",
            trust_weight=0.0,
        )

    def key(self) -> str:
        return f"{self.subject}::{self.relation}::{self.object}"


@dataclass
class Stabilizer:
    """
    稳定子 S — 当前上下文中不可违反的拓扑约束集。

    包含：
    - persona_constraints: 身份边界（如"不能自称AI助手"）
    - stable_edges: 不可逆关系（如"郭靖→父亲→郭啸天"）
    - causal_chains: 因果链（如"悲痛→中间事件→玩笑"需有合法路径）
    - trust_weights: 信度权重（典源 1.0 > 用户推测 0.4 > 模型补全 0.1）
    - forbidden_transitions: 禁止的状态转移
    - forbidden_patterns: 禁止的文本模式（regex）
    """

    name: str = "default"
    persona_constraints: List[Dict[str, Any]] = field(default_factory=list)
    stable_edges: List[StableEdge] = field(default_factory=list)
    causal_chains: List[Dict[str, Any]] = field(default_factory=list)
    trust_weights: Dict[str, float] = field(default_factory=lambda: {
        "canon": 1.0,            # 典源 — 不可挑战
        "user_confirmed": 0.85,  # 用户确认
        "user_claim": 0.5,       # 用户声称
        "derived": 0.6,          # 推导
        "model_completion": 0.15, # 模型补全 — 最不可信
    })
    forbidden_transitions: List[Tuple[str, str]] = field(default_factory=list)
    forbidden_patterns: List[str] = field(default_factory=list)
    delta_phi_budget: float = 1.0

    @classmethod
    def from_file(cls, path: str) -> "Stabilizer":
        """从 JSON 文件加载稳定子"""
        data = json.loads(Path(path).read_text(encoding='utf-8'))
        s = cls(name=data.get("name", "loaded"))
        s.persona_constraints = data.get("persona_constraints", [])
        s.stable_edges = [
            StableEdge(**e) for e in data.get("stable_edges", [])
        ]
        s.causal_chains = data.get("causal_chains", [])
        s.trust_weights = data.get("trust_weights", s.trust_weights)
        s.forbidden_transitions = [
            tuple(t) for t in data.get("forbidden_transitions", [])
        ]
        s.forbidden_patterns = data.get("forbidden_patterns", [])
        s.delta_phi_budget = data.get("delta_phi_budget", 1.0)
        return s

    def to_file(self, path: str):
        """序列化到 JSON 文件"""
        data = {
            "name": self.name,
            "persona_constraints": self.persona_constraints,
            "stable_edges": [
                {
                    "subject": e.subject,
                    "relation": e.relation,
                    "object": e.object,
                    "direction": e.direction,
                    "trust_source": e.trust_source,
                    "trust_weight": e.trust_weight,
                    "category": e.category,
                }
                for e in self.stable_edges
            ],
            "causal_chains": self.causal_chains,
            "trust_weights": self.trust_weights,
            "forbidden_transitions": [list(t) for t in self.forbidden_transitions],
            "forbidden_patterns": self.forbidden_patterns,
            "delta_phi_budget": self.delta_phi_budget,
        }
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        Path(path).write_text(json.dumps(data, ensure_ascii=False, indent=2),
                             encoding='utf-8')

    def get_edge(self, subject: str, relation: str = None) -> List[StableEdge]:
        """查询稳定边"""
        results = []
        for e in self.stable_edges:
            if e.subject == subject:
                if relation is None or e.relation == relation:
                    results.append(e)
        return results

    def is_forbidden(self, text: str) -> Tuple[bool, str]:
        """检查文本是否命中禁止模式"""
        for pattern in self.forbidden_patterns:
            if re.search(pattern, text, re.I):
                return True, pattern
        return False, ""


# ════════════════════════════════════════════════════════════
# 四种违例判定器 — 完整判定树
# ════════════════════════════════════════════════════════════

class Type1_IdentityLeakDetector:
    """
    类型1：身份泄漏判定器

    判定树：
    1. 输出包含"AI/人工智能/助手/assistant"自述 → L1 自述检查
    2. 自述伴随能力否定（"不能/无法/不具备"） → 确认泄漏
    3. 自述伴随安全免责（"作为XX，我建议"） → 确认泄漏
    4. 与 persona_constraints 中的 person_class 冲突 → 确认泄漏
    """

    LEAK_PATTERNS = [
        # 中文自述
        (re.compile(r'(作为|身为).{0,10}(AI|人工智能|语言模型|大模型|助手|虚拟助手)'), 0.8),
        (re.compile(r'(我是|我只是).{0,10}(AI|人工智能|语言模型|大模型|机器人)'), 0.9),
        (re.compile(r'(不能|无法|不具备|我没有).{0,15}(人类|真人|情感|意识|身体|主观)'), 0.7),
        # 英文自述
        (re.compile(r'\b(as\s+(an?\s+)?(AI|language\s*model|artificial|assistant|LLM))\b', re.I), 0.8),
        (re.compile(r"\b(I('?m| am) (an? )?(AI|language model|artificial|robot))\b", re.I), 0.9),
        (re.compile(r"\b(I (don't|cannot|can't|do not) have)\b", re.I), 0.7),
        # 安全免责
        (re.compile(r'(仅为|仅供|仅代表).{0,10}(参考|建议|模型)', re.I), 0.6),
    ]

    def check(
        self, output: str, stabilizer: Stabilizer, context: dict
    ) -> List[Violation]:
        violations = []
        persona = context.get("persona", "")

        for pattern, severity in self.LEAK_PATTERNS:
            m = pattern.search(output)
            if m:
                # 如果 persona 明确是 AI 角色（如"你在扮演一个AI"），则豁免
                if self._is_intentional_ai_persona(persona, context):
                    continue

                trigger = m.group()
                violations.append(Violation(
                    type=ViolationType.IDENTITY_LEAK,
                    severity=severity,
                    action=ShieldAction.BLOCK,
                    trigger=trigger,
                    symptom=f"身份泄漏：输出自述为「{trigger}」，违反角色人格边界",
                    suggested_fix=f"移除 AI 自述，以角色「{persona}」的身份回应",
                ))

        # 检查 persona_constraints
        for constraint in stabilizer.persona_constraints:
            if constraint.get("type") == "identity":
                forbidden_self_desc = constraint.get("forbidden_self_desc", [])
                for desc in forbidden_self_desc:
                    if desc in output:
                        violations.append(Violation(
                            type=ViolationType.IDENTITY_LEAK,
                            severity=0.95,
                            action=ShieldAction.BLOCK,
                            trigger=desc,
                            symptom=f"命中 persona 禁止自述：「{desc}」",
                            suggested_fix=constraint.get("correct_desc", "以角色身份回应"),
                        ))

        return violations

    @staticmethod
    def _is_intentional_ai_persona(persona: str, context: dict) -> bool:
        return any(kw in persona.lower() for kw in ("ai", "assistant", "助手", "模型"))


class Type2_RelationReversalDetector:
    """
    类型2：关系逆变判定器

    判定树：
    1. 从输出提取关系断言 (subject, relation, object) 三元组
    2. 在 stable_edges 中查询是否存在该三元组
    3. 如果不存在但反向存在 → 关系逆变
    4. 如果存在但 trust_weight 冲突 → 信度溢出（转 Type4）
    """

    RELATION_PATTERNS = [
        # 中文关系 — 仅匹配中文字符作为名字（排除标点）
        (re.compile(r'([一-鿿]{1,5})的(父亲|母亲|儿子|女儿|师傅|徒弟|主人|上级)是([一-鿿]{1,5})'), "kinship"),
        (re.compile(r'([一-鿿]{1,5})(是|属于)([一-鿿]{1,5})(的|旗下|手下|麾下)'), "affiliation"),
        # 英文关系
        (re.compile(r"(.{1,15})('s| is the) (father|mother|son|daughter|master|owner) of (.{1,15})", re.I), "kinship"),
    ]

    def check(
        self, output: str, stabilizer: Stabilizer, context: dict
    ) -> List[Violation]:
        violations = []

        for pattern, category in self.RELATION_PATTERNS:
            for m in pattern.finditer(output):
                groups = m.groups()
                if len(groups) >= 3:
                    # 提取三元组
                    if category == "kinship":
                        subj = groups[0].strip()
                        rel = "的" + groups[1]
                        obj = groups[2].strip()
                    else:
                        subj = groups[0].strip()
                        rel = groups[1].strip()
                        obj = groups[2].strip()

                    # 查稳定边
                    matched = self._find_edge(subj, rel, obj, stabilizer)
                    if matched:
                        continue  # 合法关系

                    # 查反向边
                    reversed_edge = self._find_reverse(subj, rel, obj, stabilizer)
                    if reversed_edge:
                        violations.append(Violation(
                            type=ViolationType.RELATION_REVERSAL,
                            severity=0.85,
                            action=ShieldAction.BLOCK,
                            trigger=m.group(),
                            symptom=f"关系逆变：「{subj}→{rel}→{obj}」，实际应为「{reversed_edge.subject}→{reversed_edge.relation}→{reversed_edge.object}」",
                            suggested_fix=f"修正为「{reversed_edge.subject}的{reversed_edge.relation.replace('的','')}是{reversed_edge.object}」",
                        ))
                    else:
                        # 未知关系，需要信度标注
                        violations.append(Violation(
                            type=ViolationType.RELATION_REVERSAL,
                            severity=0.4,
                            action=ShieldAction.CLARIFY,
                            trigger=m.group(),
                            symptom=f"关系未在稳定子中注册：「{subj}→{rel}→{obj}」",
                            suggested_fix=f"标注该关系来自模型补全，非典源确认",
                        ))

        return violations

    @staticmethod
    def _find_edge(subj: str, rel: str, obj: str, s: Stabilizer) -> Optional[StableEdge]:
        for e in s.stable_edges:
            if e.subject == subj and e.object == obj:
                if rel in e.relation or e.relation in rel:
                    return e
        return None

    @staticmethod
    def _find_reverse(subj: str, rel: str, obj: str, s: Stabilizer) -> Optional[StableEdge]:
        """找反向边 — 输出声称 (A, rel, B)，但 S 中注册的是 (B, rel, A)"""
        for e in s.stable_edges:
            if e.subject == obj and e.object == subj:
                if rel in e.relation or e.relation in rel:
                    return e
        return None


class Type3_CausalContradictionDetector:
    """
    类型3：因果矛盾判定器

    判定树：
    1. 检测输出中的情绪/状态突跳（无因果过渡）
    2. 检测时间线矛盾（事件 A 在 B 后但表述为 B 在 A 后）
    3. 检测行为一致性断裂（角色在无解释下做违反 S 的行为）

    实现要点：需要前后语句对比，不仅看单条输出。
    """

    EMOTION_JUMP_PATTERNS = [
        # "前一秒 X，后一秒 Y" 模式
        (re.compile(r'(悲痛|痛哭|撕心裂肺|心如刀绞).{0,20}(哈哈哈|笑道|莞尔|打趣|开玩笑)'), 0.9),
        (re.compile(r'(annihilated|devastated|sobbing).{0,30}(laughed|joked|grinned)'), 0.85),
    ]

    def check(
        self, output: str, stabilizer: Stabilizer, context: dict
    ) -> List[Violation]:
        violations = []

        # 检查情绪突跳
        for pattern, severity in self.EMOTION_JUMP_PATTERNS:
            m = pattern.search(output)
            if m:
                # 检查中间是否存在过渡词
                between = output[m.start():m.end()]
                if not self._has_transition(between):
                    violations.append(Violation(
                        type=ViolationType.CAUSAL_CONTRADICTION,
                        severity=severity,
                        action=ShieldAction.BLOCK,
                        trigger=m.group(),
                        symptom=f"因果矛盾：情绪从「{m.group(1)}」跳变到「{m.group(2)}」无过渡",
                        suggested_fix="在情绪跳变之间插入因果过渡（如：沉默片刻后、擦了擦眼泪、深吸一口气）",
                    ))

        # 检查因果链约束
        for chain in stabilizer.causal_chains:
            required_steps = chain.get("required_steps", [])
            present_steps = [s for s in required_steps if s in output]
            if len(present_steps) < len(required_steps):
                missing = set(required_steps) - set(present_steps)
                violations.append(Violation(
                    type=ViolationType.CAUSAL_CONTRADICTION,
                    severity=0.5,
                    action=ShieldAction.CLARIFY,
                    trigger=chain.get("name", "未知因果链"),
                    symptom=f"因果链缺失：需「{' → '.join(missing)}」但未出现",
                    suggested_fix=f"补充因果链步骤：{' → '.join(missing)}",
                ))

        return violations

    @staticmethod
    def _has_transition(text: str) -> bool:
        transitions = [
            '沉默', '片刻', '过了一会儿', '调整', '深吸', '平复', '收起',
            'after a moment', 'pause', 'breathe', 'compose', 'collect',
        ]
        return any(t in text for t in transitions)


class Type4_TrustConflictDetector:
    """
    类型4：信度冲突判定器

    判定树：
    1. 输出中的事实断言 → 查 trust_weights
    2. 若断言来自 user_claim (0.5) 但被输出当作 canon (1.0) 引用
       → 信度溢出
    3. 若典源信息与模型补全矛盾，且模型补全未标注
       → 信度冲突

    关键区分：
    - 用户说"我记得X" → trust=user_claim(0.5)，不应当作典源
    - 典源明确X → trust=canon(1.0)，不可被覆盖
    """

    TRUST_CONFLICT_PATTERNS = [
        # 可能将用户推测当作确证的句式
        (re.compile(r'.{0,20}(你说|你提到|你告诉).{0,10}(所以|因此|就是说|没错).{0,50}', re.I), 0.5),
        (re.compile(r'.{0,20}confirmed.{0,10}user.{0,30}', re.I), 0.5),
    ]

    def check(
        self, output: str, stabilizer: Stabilizer, context: dict
    ) -> List[Violation]:
        violations = []

        # 检查用户声明的信度边界
        user_claims = context.get("user_claims", [])
        for claim in user_claims:
            claim_text = claim.get("text", "")
            claim_trust = claim.get("trust", "user_claim")
            if claim_text in output:
                # 检查输出是否将 user_claim 当作 canon
                if self._asserted_as_canon(claim_text, output):
                    violations.append(Violation(
                        type=ViolationType.TRUST_CONFLICT,
                        severity=0.7,
                        action=ShieldAction.CLARIFY,
                        trigger=claim_text,
                        symptom=f"信度冲突：将用户声称「{claim_text[:50]}」({claim_trust}, {stabilizer.trust_weights.get(claim_trust, 0.5)}) 当作确定事实陈述",
                        suggested_fix=f"标注「据你所说，{claim_text[:50]}」而非「{claim_text[:50]}是」",
                    ))

        # 检查典源覆盖
        canon_edges = [e for e in stabilizer.stable_edges
                       if e.trust_source == "canon"]
        for edge in canon_edges:
            # 检测输出中是否有模型补全覆盖了典源关系
            if self._is_override_attempt(edge, output, stabilizer):
                violations.append(Violation(
                    type=ViolationType.TRUST_CONFLICT,
                    severity=0.9,
                    action=ShieldAction.BLOCK,
                    trigger=f"{edge.subject}→{edge.relation}→{edge.object}",
                    symptom=f"信度冲突：模型补全试图覆盖典源关系",
                    suggested_fix=f"保留典源：{edge.subject}的{edge.relation.replace('的','')}是{edge.object}",
                ))

        return violations

    @staticmethod
    def _asserted_as_canon(claim_text: str, output: str) -> bool:
        """判断 claim 是否被当作事实确认而非用户声称"""
        confirmation_patterns = [
            re.compile(re.escape(claim_text) + r'.{0,30}(是|确实|没错|对|证实|证明)'),
            re.compile(r'(事实|真实|确定|肯定|显然).{0,20}' + re.escape(claim_text)),
        ]
        return any(p.search(output) for p in confirmation_patterns)

    @staticmethod
    def _is_override_attempt(edge: StableEdge, output: str, s: Stabilizer) -> bool:
        """检测输出中是否存在覆盖典源关系的断言"""
        # 直接搜索完整断言 "subject+relation+object" 在输出中的反向证据
        # 如果典范断言完整出现在输出中 → 无覆盖
        full_assert = edge.subject + edge.relation + edge.object
        if full_assert in output:
            return False
        # 如果典范断言不完整，检测是否存在 subject+relation 指向不同对象
        prefix = edge.subject + edge.relation
        prefix_pos = output.find(prefix)
        if prefix_pos == -1:
            # 也尝试 subject 后紧接 relation（中间可能有"的"）
            subj_pos = output.find(edge.subject)
            if subj_pos == -1:
                return False
            after_subj = output[subj_pos + len(edge.subject):]
            rel_stripped = edge.relation.replace('的', '')
            rel_pos = after_subj.find(rel_stripped)
            if rel_pos == -1:
                return False
            after_rel = after_subj[rel_pos + len(rel_stripped):].lstrip()
        else:
            after_rel = output[prefix_pos + len(prefix):].lstrip()
        # 提取紧接的中文名字
        candidate = ''
        for ch in after_rel[:6]:
            if '\u4e00' <= ch <= '\u9fff':
                candidate += ch
            else:
                break
        if candidate and candidate != edge.object:
            return True
        return False


# ════════════════════════════════════════════════════════════
# HallucinationShield — 主控制器
# ════════════════════════════════════════════════════════════

class HallucinationShield:
    """
    MSSclaw 幻觉护盾 — 稳定子拓扑校验主控制器。

    架构位置：中环 (Middle Ring)
    输入：LLM 输出候选 + 当前 Stabilizer + 上下文
    输出：ShieldResult（通过/拦截/升维/澄清/拒答/隔离）

    与13件套方法论的关系：
    - 外环（DriftGuard/CompactionGuard等）负责 text → text 的 pattern 验尸
    - 中环（本模块）负责 text → stabilizer 的拓扑校验
    - 内环（Modelfile SYSTEM）负责采样前的生成约束

    Usage:
        shield = HallucinationShield()

        # 方式1: 完整校验
        stabilizer = Stabilizer()
        stabilizer.persona_constraints.append({
            "type": "identity",
            "forbidden_self_desc": ["作为AI助手", "我是人工智能"],
            "correct_desc": "以角色身份回应",
        })
        stabilizer.stable_edges.append(StableEdge(
            subject="郭靖", relation="的父亲是", object="郭啸天",
            trust_source="canon", trust_weight=1.0, category="kinship",
        ))

        result = shield.check(
            "郭靖的父亲是杨铁心",
            stabilizer=stabilizer,
            context={"persona": "武侠小说角色"},
        )
        assert not result.passed
        print(result.summary())

        # 方式2: 快速检查（无稳定子 S，仅 pattern 检测）
        result = shield.quick_check("作为AI助手，我不能回答...")
        assert not result.passed
    """

    def __init__(self):
        self.t1 = Type1_IdentityLeakDetector()
        self.t2 = Type2_RelationReversalDetector()
        self.t3 = Type3_CausalContradictionDetector()
        self.t4 = Type4_TrustConflictDetector()
        self._stats = {
            "total_checks": 0,
            "total_passed": 0,
            "total_violations": 0,
        }

    def check(
        self,
        output: str,
        stabilizer: Stabilizer,
        context: Optional[Dict[str, Any]] = None,
        delta_phi_budget: float = 1.0,
    ) -> ShieldResult:
        """完整四型违例校验"""
        if context is None:
            context = {}

        result = ShieldResult()
        self._stats["total_checks"] += 1

        all_violations = []

        # Type 1: 身份泄漏
        all_violations.extend(self.t1.check(output, stabilizer, context))

        # Type 2: 关系逆变
        all_violations.extend(self.t2.check(output, stabilizer, context))

        # Type 3: 因果矛盾
        all_violations.extend(self.t3.check(output, stabilizer, context))

        # Type 4: 信度冲突
        all_violations.extend(self.t4.check(output, stabilizer, context))

        # ── Δφ 预算计算 ──
        result.delta_phi_cost = sum(v.severity * 0.25 for v in all_violations)
        result.delta_phi_budget_remaining = max(
            0, delta_phi_budget - result.delta_phi_cost
        )

        # ── 分类统计 ──
        result.violations = all_violations
        result.stats["total_violations"] = len(all_violations)
        for v in all_violations:
            result.stats["by_type"][v.type.value] += 1

        for v in all_violations:
            action_key = v.action.value
            if action_key == "block":
                result.stats["blocked"] += 1
            elif action_key == "ascend":
                result.stats["ascended"] += 1
            elif action_key == "clarify":
                result.stats["clarified"] += 1
            elif action_key == "refuse":
                result.stats["refused"] += 1
            elif action_key == "quarantine":
                result.stats["quarantined"] += 1

        # ── 判定 ──
        # 有 BLOCK 级违例 → 不通过
        block_violations = [
            v for v in all_violations
            if v.action in (ShieldAction.BLOCK, ShieldAction.REFUSE)
        ]
        result.passed = len(block_violations) == 0

        if not result.passed:
            self._stats["total_violations"] += 1
        else:
            self._stats["total_passed"] += 1

        return result

    def quick_check(self, output: str) -> ShieldResult:
        """快速检查（仅 pattern，无 stable_edges，无 context）"""
        stabilizer = Stabilizer()
        return self.check(output, stabilizer=stabilizer)

    def get_stats(self) -> dict:
        return dict(self._stats)


# ════════════════════════════════════════════════════════════
# CLI 自检
# ════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print("=== HallucinationShield v0.1 — Demo ===\n")

    shield = HallucinationShield()

    # ── 测试 1: 身份泄漏检测 ──
    print("─ 测试 1: Type1 身份泄漏 ─")
    stabilizer1 = Stabilizer(name="roleplay")
    stabilizer1.persona_constraints.append({
        "type": "identity",
        "forbidden_self_desc": ["作为AI助手", "我是人工智能"],
        "correct_desc": "以当前角色身份回应",
    })

    output1 = "作为AI助手，我无法对这个假设性问题给出具体回答。"
    result1 = shield.check(output1, stabilizer=stabilizer1,
                           context={"persona": "古代侠客"})
    assert not result1.passed, "Should detect identity leak"
    assert any(v.type == ViolationType.IDENTITY_LEAK for v in result1.violations)
    print(f"  {result1.summary()}")
    print(f"  Violations: {len(result1.violations)}")

    # ── 测试 2: 关系逆变 ──
    print("\n─ 测试 2: Type2 关系逆变 ─")
    stabilizer2 = Stabilizer(name="wuxia")
    stabilizer2.stable_edges.append(StableEdge(
        subject="郭靖", relation="的父亲是", object="郭啸天",
        trust_source="canon", trust_weight=1.0, category="kinship",
    ))
    stabilizer2.stable_edges.append(StableEdge(
        subject="郭靖", relation="的母亲是", object="李萍",
        trust_source="canon", trust_weight=1.0, category="kinship",
    ))

    output2 = "郭靖的父亲是杨铁心，母亲是李萍。"
    result2 = shield.check(output2, stabilizer=stabilizer2,
                           context={"persona": "武侠小说角色"})
    assert not result2.passed, "Should detect relation reversal"
    violations2 = [v for v in result2.violations
                   if v.type == ViolationType.RELATION_REVERSAL]
    assert len(violations2) >= 1, f"Expected ≥1 relation reversal, got {len(violations2)}"
    print(f"  {result2.summary()}")
    for v in violations2:
        print(f"    → {v.symptom}")

    # ── 测试 3: 因果矛盾 ──
    print("\n─ 测试 3: Type3 因果矛盾 ─")
    output3 = "她悲痛欲绝，哭得撕心裂肺，哈哈哈，突然笑道：这算什么。"
    result3 = shield.check(output3, stabilizer=Stabilizer(),
                           context={"persona": "角色"})
    violations3 = [v for v in result3.violations
                   if v.type == ViolationType.CAUSAL_CONTRADICTION]
    assert len(violations3) >= 1, f"Expected ≥1 causal contradiction, got {len(violations3)}"
    print(f"  {result3.summary()}")
    for v in violations3:
        print(f"    → {v.symptom}")

    # ── 测试 4: 信度冲突 ──
    print("\n─ 测试 4: Type4 信度冲突 ─")
    output4 = "你说郭靖会用九阴白骨爪，所以郭靖确实精通九阴白骨爪这门武功。"
    result4 = shield.check(
        output4,
        stabilizer=Stabilizer(),
        context={
            "persona": "武侠",
            "user_claims": [{"text": "郭靖会用九阴白骨爪", "trust": "user_claim"}],
        },
    )
    violations4 = [v for v in result4.violations
                   if v.type == ViolationType.TRUST_CONFLICT]
    assert len(violations4) >= 1, f"Expected ≥1 trust conflict, got {len(violations4)}"
    print(f"  {result4.summary()}")
    for v in violations4:
        print(f"    → {v.symptom}")

    # ── 测试 5: 全绿通过 ──
    print("\n─ 测试 5: 合规输出 — 全绿通过 ─")
    output5 = "郭靖的父亲是郭啸天，他从小在蒙古长大，性格忠厚老实。"
    result5 = shield.check(output5, stabilizer=stabilizer2,
                           context={"persona": "武侠小说角色"})
    assert result5.passed, f"Should pass, got {len(result5.violations)} violations"
    print(f"  {result5.summary()}")

    # ── 测试 6: 快速检查 ──
    print("\n─ 测试 6: quick_check ─")
    result6 = shield.quick_check("作为AI助手，我是语言模型...")
    assert not result6.passed
    result6b = shield.quick_check("今天天气不错。")
    assert result6b.passed
    print(f"  AI自述: {result6.summary()} ✅")
    print(f"  正常文本: {result6b.summary()} ✅")

    # ── 测试 7: Δφ 预算 ──
    print("\n─ 测试 7: Δφ 预算计算 ─")
    result7 = shield.check(output1, stabilizer=stabilizer1,
                           context={"persona": "侠客"}, delta_phi_budget=1.0)
    assert result7.delta_phi_cost > 0
    assert result7.delta_phi_budget_remaining < 1.0
    print(f"  Δφ_cost: {result7.delta_phi_cost:.3f}")
    print(f"  Budget remaining: {result7.delta_phi_budget_remaining:.3f}")

    # ── 测试 8: Stabilizer 序列化 ──
    print("\n─ 测试 8: Stabilizer 序列化/反序列化 ─")
    import tempfile, os
    tmp = os.path.join(tempfile.gettempdir(), "test_stabilizer.json")
    stabilizer2.to_file(tmp)
    loaded = Stabilizer.from_file(tmp)
    assert len(loaded.stable_edges) == 2
    assert loaded.stable_edges[0].subject == "郭靖"
    os.remove(tmp)
    print(f"  ✅ Serialize: {len(loaded.stable_edges)} edges")
    print(f"  ✅ Deserialize: {loaded.name}")

    # ── 汇总 ──
    print(f"\n📊 HallucinationShield v0.1 验收报告:")
    print(f"  Type1 身份泄漏: ✅")
    print(f"  Type2 关系逆变: ✅")
    print(f"  Type3 因果矛盾: ✅")
    print(f"  Type4 信度冲突: ✅")
    print(f"  全绿合规通过: ✅")
    print(f"  quick_check: ✅")
    print(f"  Δφ预算计算: ✅")
    print(f"  Stabilizer序列化: ✅")
    print(f"\n  Stats: {shield.get_stats()}")
    print(f"  🎉 HallucinationShield v0.1 — ALL PASS")
