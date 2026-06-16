"""
Agent Skill Registry — 可加载技能模版

用法:
    skills = SkillRegistry()
    skills.register("code_review", "Review code for bugs and security issues", tools=["read_file"])
    skills.register("poet", "Write poetry in classical Chinese style", style="poetry")
    
    agent.load_skill("code_review")  # 自动配置提示词+工具+风格
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Optional, Dict


@dataclass
class Skill:
    name: str
    description: str
    system_prompt: str = ""
    tools: List[str] = field(default_factory=list)
    style: str = "prose"
    examples: List[str] = field(default_factory=list)
    category: str = "general"


class SkillRegistry:
    """技能注册表."""

    DEFAULT_SKILLS = {
        "code_review": Skill(
            name="code_review",
            description="Review code for bugs, security issues, and style",
            system_prompt="You are a senior code reviewer. Check for: 1) bugs 2) security 3) readability 4) performance. Be specific.",
            tools=["read_file", "list_dir"],
            style="explain",
        ),
        "poet": Skill(
            name="poet",
            description="Write poetry in various styles",
            system_prompt="You are a classical poet. Write elegant, meaningful poetry.",
            style="poetry",
        ),
        "security_audit": Skill(
            name="security_audit",
            description="Audit system for security vulnerabilities",
            system_prompt="You are a security auditor. Check for vulnerabilities and compliance issues.",
            tools=["read_file", "list_dir", "run_command"],
            style="explain",
        ),
        "researcher": Skill(
            name="researcher",
            description="Research topics using the knowledge base",
            system_prompt="You are a research assistant. Use the knowledge base to find relevant information.",
            tools=["kb_search"],
            style="explain",
        ),
        "translator": Skill(
            name="translator",
            description="Translate between Chinese and English",
            system_prompt="You are a professional translator. Translate accurately and naturally.",
            style="prose",
        ),
    }

    def __init__(self):
        self._skills: Dict[str, Skill] = dict(self.DEFAULT_SKILLS)

    def register(self, name: str, description: str, system_prompt: str = "",
                 tools: list = None, style: str = "prose"):
        self._skills[name] = Skill(
            name=name, description=description,
            system_prompt=system_prompt, tools=tools or [],
            style=style,
        )

    def get(self, name: str) -> Optional[Skill]:
        return self._skills.get(name)

    def list_skills(self) -> list:
        return [
            {"name": s.name, "description": s.description, "tools": s.tools, "style": s.style}
            for s in self._skills.values()
        ]

    def apply(self, agent, skill_name: str) -> bool:
        """
        应用技能到 Agent.

        设置: 提示词 + 风格 + 工具
        """
        skill = self._skills.get(skill_name)
        if not skill:
            return False

        # Store skill context on agent
        agent._skill = skill

        # Set style preference
        agent._skill_style = skill.style

        return True

    def build_prompt(self, skill_name: str, user_prompt: str) -> str:
        """构建技能增强提示词."""
        skill = self._skills.get(skill_name)
        if not skill:
            return user_prompt

        parts = []
        if skill.system_prompt:
            parts.append(skill.system_prompt)
        parts.append(f"\nTask: {user_prompt}")

        if skill.tools:
            parts.append(f"\nAvailable tools: {', '.join(skill.tools)}")

        return "\n".join(parts)
