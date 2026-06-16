"""
Agent Absorber — 吸收外部Agent → MSS化

输入: 外部Agent定义 (JSON/描述/框架specific)
输出: MSSAgent配置 + 技能包 + 可插拔工具

三路径吸收:
  1. Agent→Agent: 整Agent转化 (配置+技能+工具)
  2. Agent→Skills: 拆Agent为独立技能包
  3. Agent→Tools: 核心能力沉淀为可复用工具

用法:
    absorber = AgentAbsorber()
    
    # 从自然语言描述吸收
    config = absorber.absorb_from_text(
        "A code review agent that checks Python for bugs and security"
    )
    # → MSSAgent配置 + review_code技能 + security_check工具
    
    # 批量吸收并生成
    absorber.absorb_from_text("A poet that writes haiku")
    ecosystem = absorber.export_ecosystem()
    # → {agents: [...], skills: [...], tools: [...]}
"""
from __future__ import annotations
import json
import re
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Callable


@dataclass
class AbsorbedAgent:
    """吸收后的 MSS Agent 配置."""
    name: str
    description: str
    role: str = ""                 # writer/reviewer/analyst/assistant
    capabilities: List[str] = field(default_factory=list)
    skills: List[str] = field(default_factory=list)
    tools: List[str] = field(default_factory=list)
    style: str = "prose"
    heat_tax: float = 0.05
    delta_min: float = 0.3

    def to_config(self) -> dict:
        return {
            "name": self.name, "description": self.description,
            "role": self.role, "capabilities": self.capabilities,
            "skills": self.skills, "tools": self.tools,
            "style": self.style, "heat_tax": self.heat_tax,
            "delta_min": self.delta_min,
        }


@dataclass
class AgentEcosystem:
    """吸收后生成的完整生态系统."""
    agents: List[AbsorbedAgent] = field(default_factory=list)
    skills: List[dict] = field(default_factory=list)
    tools: List[dict] = field(default_factory=list)


class AgentAbsorber:
    """
    Agent 吸收器 — 外部Agent → MSS原生.

    核心: 一个被吸收的Agent同时产生:
      - 完整的MSS Agent配置
      - 可复用的技能包
      - 可插拔的工具
    """

    # 角色识别模式
    ROLE_PATTERNS = {
        "writer": r'\b(write|create|generate|compose|draft|author|写|创作|生成|编写)\b',
        "reviewer": r'\b(review|check|audit|inspect|examine|verify|审查|检查|审计)\b',
        "analyst": r'\b(analyze|research|investigate|study|explore|分析|研究|调查)\b',
        "translator": r'\b(translate|convert|localize|翻译|转换|本地化)\b',
        "assistant": r'\b(assist|help|support|guide|answer|帮助|协助|引导|回答)\b',
    }

    # 能力模式
    CAPABILITY_PATTERNS = {
        "code_generation": r'\b(code|program|function|class|script|implement)\b',
        "code_review": r'\b(review code|audit code|code quality|bug|vulnerability)\b',
        "security_audit": r'\b(security|vulnerability|exploit|injection|XSS|CSRF)\b',
        "data_analysis": r'\b(data|analyze|statistics|visualize|chart|graph)\b',
        "translation": r'\b(translate|language|Chinese|English|Japanese)\b',
        "writing": r'\b(write|compose|poem|story|article|blog|essay)\b',
        "research": r'\b(research|knowledge base|search|find|lookup)\b',
    }

    def __init__(self):
        self._absorbed: List[AbsorbedAgent] = []
        self._generated_skills: List[dict] = []
        self._generated_tools: List[dict] = []

    # ── Absorption ──

    def absorb_from_text(self, description: str) -> AbsorbedAgent:
        """从自然语言描述吸收 Agent."""
        name = self._extract_name(description)
        role = self._extract_role(description)
        capabilities = self._extract_capabilities(description)
        tools = self._extract_tools(description)
        style = self._infer_style(description)

        agent = AbsorbedAgent(
            name=name, description=description, role=role,
            capabilities=capabilities, tools=tools, style=style,
            heat_tax=0.03 + len(tools) * 0.01,
            delta_min=0.4 if style == "poetry" else 0.3,
        )

        # Auto-generate skills
        self._generate_skills_from(agent)

        # Auto-generate tools
        self._generate_tools_from(agent)

        self._absorbed.append(agent)
        return agent

    def absorb_from_dict(self, data: dict) -> AbsorbedAgent:
        """从字典吸收 Agent."""
        agent = AbsorbedAgent(
            name=data.get("name", "absorbed_agent"),
            description=data.get("description", ""),
            role=data.get("role", "assistant"),
            capabilities=data.get("capabilities", []),
            skills=data.get("skills", []),
            tools=data.get("tools", []),
            style=data.get("style", "prose"),
            heat_tax=data.get("heat_tax", 0.05),
            delta_min=data.get("delta_min", 0.3),
        )
        self._absorbed.append(agent)
        return agent

    # ── Extraction ──

    def _extract_name(self, desc: str) -> str:
        """从描述提取 Agent 名称."""
        desc_lower = desc.lower()
        # Try to find "X agent" or "X bot" pattern
        match = re.search(r'(\w+)\s+(agent|bot|assistant|expert)', desc_lower)
        if match:
            return match.group(1).replace("_", "-")
        # Use first distinctive word
        words = [w for w in desc_lower.split() if len(w) > 3][:2]
        return "_".join(words) if words else "agent"

    def _extract_role(self, desc: str) -> str:
        for role, pattern in self.ROLE_PATTERNS.items():
            if re.search(pattern, desc.lower()):
                return role
        return "assistant"

    def _extract_capabilities(self, desc: str) -> list:
        caps = []
        for cap, pattern in self.CAPABILITY_PATTERNS.items():
            if re.search(pattern, desc.lower()):
                caps.append(cap)
        return caps or ["general"]

    def _extract_tools(self, desc: str) -> list:
        tools = []
        patterns = {
            "read_file": r'\b(read|file|document|source code)\b',
            "kb_search": r'\b(search|find|research|knowledge)\b',
            "calculator": r'\b(calc|compute|math|calculate)\b',
            "list_dir": r'\b(list|directory|folder|project)\b',
        }
        for tool, pattern in patterns.items():
            if re.search(pattern, desc.lower()):
                tools.append(tool)
        return tools

    def _infer_style(self, desc: str) -> str:
        if re.search(r'\b(poem|poetry|诗|verse)\b', desc.lower()):
            return "poetry"
        if re.search(r'\b(code|program|debug|algorithm)\b', desc.lower()):
            return "code"
        if re.search(r'\b(explain|tutorial|guide|analyze)\b', desc.lower()):
            return "explain"
        return "prose"

    # ── Skill Generation ──

    def _generate_skills_from(self, agent: AbsorbedAgent):
        """从被吸收的Agent自动生成技能包."""
        # Core skill: the agent's primary function
        core_skill = {
            "name": agent.name,
            "description": agent.description,
            "system_prompt": f"You are a {agent.role} named {agent.name}. {agent.description}",
            "tools": agent.tools,
            "style": agent.style,
            "source": "absorbed_agent",
        }
        self._generated_skills.append(core_skill)

        # Sub-skills from capabilities
        for cap in agent.capabilities:
            sub_skill = {
                "name": f"{agent.name}_{cap}",
                "description": f"{cap.replace('_', ' ')} capability of {agent.name}",
                "system_prompt": f"Focus on {cap.replace('_', ' ')}. {agent.description}",
                "tools": agent.tools[:2],
                "style": agent.style,
                "source": f"absorbed_agent.{agent.name}",
            }
            self._generated_skills.append(sub_skill)

    # ── Tool Generation ──

    def _generate_tools_from(self, agent: AbsorbedAgent):
        """从被吸收Agent生成可插拔工具."""
        # Each capability becomes a potential tool wrapper
        for cap in agent.capabilities:
            tool_def = {
                "name": f"{agent.name}_{cap}",
                "description": f"Use {agent.name}'s {cap} capability",
                "agent_ref": agent.name,
                "capability": cap,
                "style": agent.style,
            }
            self._generated_tools.append(tool_def)

    # ── Export ──

    def export_ecosystem(self) -> dict:
        """导出完整生态系统."""
        return {
            "agents": [a.to_config() for a in self._absorbed],
            "skills": self._generated_skills,
            "tools": self._generated_tools,
            "stats": {
                "agents": len(self._absorbed),
                "skills": len(self._generated_skills),
                "tools": len(self._generated_tools),
            },
        }

    def export_agent_config(self, name: str) -> Optional[dict]:
        """导出单个 Agent 的完整配置."""
        for a in self._absorbed:
            if a.name == name:
                config = a.to_config()
                # Find associated skills
                config["skills"] = [
                    s for s in self._generated_skills
                    if s.get("source", "").startswith(f"absorbed_agent.{name}")
                    or s["name"] == name
                ]
                config["tools"] = [
                    t for t in self._generated_tools
                    if t["agent_ref"] == name
                ]
                return config
        return None


def demo_absorption():
    """演示吸收流程."""
    absorber = AgentAbsorber()

    # Absorb 3 agents
    absorber.absorb_from_text(
        "A code review agent that checks Python code for bugs, security vulnerabilities, and style issues"
    )
    absorber.absorb_from_text(
        "A poet agent that writes haiku and classical Chinese poetry about nature"
    )
    absorber.absorb_from_text(
        "A research agent that searches the knowledge base for MSS theory concepts"
    )

    eco = absorber.export_ecosystem()
    print(f"Absorbed: {eco['stats']['agents']} agents → "
          f"{eco['stats']['skills']} skills + {eco['stats']['tools']} tools")

    for agent in eco["agents"]:
        print(f"\n  [{agent['name']}] role={agent['role']} style={agent['style']}")
        print(f"    caps: {agent['capabilities']}")
        print(f"    tools: {agent['tools']}")
        print(f"    heat_tax={agent['heat_tax']} delta_min={agent['delta_min']}")


if __name__ == "__main__":
    demo_absorption()
