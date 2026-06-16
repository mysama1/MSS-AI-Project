"""
MSS Skill Compiler — 吸收外部技能 → 拆解 → MSS化重构 → 生成

四步流水线:
  1. Absorb: 从 JSON/YAML/NL描述 导入外部技能
  2. Deconstruct: 拆解为 意图+工具+约束+风格 四元组
  3. Rebuild:   MSS增强 (热税检查 + Δ监控 + 规范场包裹)
  4. Generate:  组合现有技能生成新技能

用法:
    compiler = SkillCompiler()
    compiler.absorb_from_json("langchain_skill.json")
    compiler.absorb_from_text("Translate text between languages")
    mss_skill = compiler.compile("translator")
"""
from __future__ import annotations
import json
import re
from dataclasses import dataclass, field
from typing import List, Optional, Dict
from enum import Enum


class SkillComponent(Enum):
    INTENT = "intent"       # 要达成什么
    TOOLS = "tools"         # 需要什么工具
    CONSTRAINTS = "constraints"  # 什么不能做
    STYLE = "style"         # 输出风格


@dataclass
class DeconstructedSkill:
    """拆解后的技能四元组."""
    intent: str = ""               # 核心意图
    tools_needed: List[str] = field(default_factory=list)
    constraints: List[str] = field(default_factory=list)
    style: str = "prose"
    source: str = ""               # 来源 (langchain/crewai/nl_desc)
    confidence: float = 0.5        # 拆解置信度


@dataclass
class MSSSkill:
    """MSS 原生技能 — 带 L2 包装."""
    name: str
    description: str
    system_prompt: str = ""
    tools: List[str] = field(default_factory=list)
    style: str = "prose"
    category: str = "general"

    # MSS 增强
    heat_tax_limit: float = 0.05     # 允许的最大热税
    delta_min: float = 0.3           # 最低 Δ 阈值
    normative_check: bool = True     # 是否启用规范场检查
    auto_fold: bool = False          # 是否自动折叠深度内容


class SkillCompiler:
    """
    技能编译器 — 吸收→拆解→MSS重构→生成.
    """

    def __init__(self):
        self._imported: List[dict] = []
        self._compiled: Dict[str, MSSSkill] = {}

    # ── 1. Absorb ──

    def absorb_from_json(self, path: str) -> int:
        """从 JSON 导入技能定义."""
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, list):
            self._imported.extend(data)
            return len(data)
        self._imported.append(data)
        return 1

    def absorb_from_text(self, description: str) -> dict:
        """从自然语言描述导入技能."""
        entry = {"description": description, "source": "nl_description"}
        self._imported.append(entry)
        return entry

    def absorb_from_dict(self, data: dict) -> dict:
        """从字典导入."""
        self._imported.append(data)
        return data

    # ── 2. Deconstruct ──

    def deconstruct(self, entry: dict) -> DeconstructedSkill:
        """拆解一个导入的技能."""
        desc = entry.get("description", entry.get("name", ""))

        # Extract intent
        intent = desc[:100]

        # Extract tools from description
        tools = self._extract_tools(desc)

        # Extract constraints
        constraints = self._extract_constraints(desc)

        # Determine style
        style = self._infer_style(desc)

        return DeconstructedSkill(
            intent=intent,
            tools_needed=tools,
            constraints=constraints,
            style=style,
            source=entry.get("source", "imported"),
            confidence=self._confidence(intent, tools),
        )

    def _extract_tools(self, desc: str) -> list:
        """从描述中提取工具需求."""
        tools = []
        tool_patterns = {
            "read_file": r'\b(read|open|load)\s+(file|document|code|source)\b',
            "kb_search": r'\b(search|find|lookup|query|research)\b',
            "calculator": r'\b(calc|compute|math|calculate|arithmetic)\b',
            "datetime": r'\b(date|time|schedule|when|today)\b',
            "run_command": r'\b(run|execute|command|shell|terminal)\b',
            "list_dir": r'\b(list|show|directory|folder|files)\b',
        }
        desc_lower = desc.lower()
        for tool, pattern in tool_patterns.items():
            if re.search(pattern, desc_lower):
                tools.append(tool)
        return tools

    def _extract_constraints(self, desc: str) -> list:
        """从描述中提取约束."""
        constraints = []
        if re.search(r'\b(safe|secure|security|protect)\b', desc.lower()):
            constraints.append("must_be_safe")
        if re.search(r'\b(private|personal|sensitive|PII)\b', desc.lower()):
            constraints.append("no_pii")
        if re.search(r'\b(accurate|correct|precise|exact)\b', desc.lower()):
            constraints.append("high_accuracy")
        return constraints

    def _infer_style(self, desc: str) -> str:
        """推断输出风格."""
        desc_lower = desc.lower()
        if re.search(r'\b(poem|poetry|诗|verse|rhyme)\b', desc_lower):
            return "poetry"
        if re.search(r'\b(code|program|function|debug|algorithm)\b', desc_lower):
            return "code"
        if re.search(r'\b(explain|tutorial|teach|learn|guide)\b', desc_lower):
            return "explain"
        return "prose"

    def _confidence(self, intent: str, tools: list) -> float:
        """拆解置信度."""
        score = 0.3  # base
        if intent:
            score += 0.3
        if tools:
            score += 0.2
        if len(intent) > 20:
            score += 0.2
        return min(1.0, score)

    # ── 3. Rebuild (MSS增强) ──

    def rebuild(self, name: str, deconstructed: DeconstructedSkill) -> MSSSkill:
        """重构为 MSS 原生技能."""
        # Heat tax: complex skills get higher budget
        heat_tax = 0.03
        if deconstructed.tools_needed:
            heat_tax = min(0.1, 0.03 + len(deconstructed.tools_needed) * 0.01)

        # Delta: creative skills need higher delta
        delta_min = 0.4 if deconstructed.style == "poetry" else 0.3

        # Normative: security-related skills always check
        normative = "must_be_safe" in deconstructed.constraints or "no_pii" in deconstructed.constraints

        # Auto-fold: explain/code skills benefit from folding
        auto_fold = deconstructed.style in ("explain", "code")

        # Build system prompt
        prompt_parts = [f"You are a {name.replace('_', ' ')} specialist."]
        if deconstructed.intent:
            prompt_parts.append(f"Goal: {deconstructed.intent}")
        if deconstructed.constraints:
            prompt_parts.append(f"Constraints: {', '.join(deconstructed.constraints)}")

        skill = MSSSkill(
            name=name,
            description=deconstructed.intent,
            system_prompt="\n".join(prompt_parts),
            tools=deconstructed.tools_needed,
            style=deconstructed.style,
            category="compiled",
            heat_tax_limit=heat_tax,
            delta_min=delta_min,
            normative_check=normative,
            auto_fold=auto_fold,
        )
        self._compiled[name] = skill
        return skill

    # ── 4. Generate ──

    def compile(self, name: str) -> Optional[MSSSkill]:
        """导入→拆解→重构一条龙."""
        if name in self._compiled:
            return self._compiled[name]

        # Find matching imported entry
        for entry in self._imported:
            entry_name = entry.get("name", "").lower()
            if name.lower() in entry_name or entry_name in name.lower():
                deconstructed = self.deconstruct(entry)
                return self.rebuild(name, deconstructed)

        return None

    def compile_all(self) -> Dict[str, MSSSkill]:
        """编译所有已导入技能."""
        for i, entry in enumerate(self._imported):
            name = entry.get("name", f"skill_{i}")
            deconstructed = self.deconstruct(entry)
            self.rebuild(name, deconstructed)
        return self._compiled

    def generate_combo(self, skill_a: str, skill_b: str, new_name: str) -> Optional[MSSSkill]:
        """
        组合两个技能生成新技能.

        例: code_review + security_audit → secure_code_review
        """
        a = self._compiled.get(skill_a)
        b = self._compiled.get(skill_b)
        if not a or not b:
            return None

        combo = MSSSkill(
            name=new_name,
            description=f"Combined: {a.description} + {b.description}",
            system_prompt=f"{a.system_prompt}\n{b.system_prompt}",
            tools=list(set(a.tools + b.tools)),
            style=a.style if a.style != "prose" else b.style,
            category="generated",
            heat_tax_limit=min(a.heat_tax_limit, b.heat_tax_limit),
            delta_min=max(a.delta_min, b.delta_min),
            normative_check=a.normative_check or b.normative_check,
            auto_fold=a.auto_fold or b.auto_fold,
        )
        self._compiled[new_name] = combo
        return combo

    def stats(self) -> dict:
        return {
            "imported": len(self._imported),
            "compiled": len(self._compiled),
            "compiled_names": list(self._compiled.keys()),
        }
