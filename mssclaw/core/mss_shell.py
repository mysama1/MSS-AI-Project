"""
MSS Shell Mode — 双模型架构: mss-ai逻辑核 + LLM感知壳

概念:
  感知壳(Perception Shell):  通用LLM, 理解自然语言 + 格式化输出 + 风格
  逻辑核(Logic Core):       mss-ai模型, 热税判断 + Δ检测 + 矛盾升维
  路由层(Router):           判断什么任务需要双模型, 什么任务壳就够了

模式:
  FULL_DUAL:  壳(理解) → 核(逻辑) → 壳(输出)   ← 复杂/创作/安全任务
  SHELL_ONLY: 壳直接处理                          ← 简单对话
  CORE_CHECK: 壳处理但核做安全审查              ← 中等敏感任务

提示词体系:
  壳提示词:  System prompt for perception (角色/风格/格式)
  核提示词:  MSS axioms + heat tax logic + delta protocol
  桥接提示词: 如何把壳的输出传给核, 如何把核的判断传回壳
"""
from __future__ import annotations
import time
from dataclasses import dataclass, field
from typing import Callable, Optional, List
from enum import Enum


class ShellMode(Enum):
    FULL_DUAL = "full_dual"       # 壳→核→壳 全链路
    SHELL_ONLY = "shell_only"     # 只用壳
    CORE_CHECK = "core_check"     # 壳处理, 核审查


@dataclass
class ShellConfig:
    """感知壳配置."""
    role: str = "assistant"           # 角色
    style: str = "prose"              # 输出风格
    system_prompt: str = ""           # 系统提示词
    temperature: float = 0.7          # 创造性温度
    max_tokens: int = 2000


@dataclass
class CoreConfig:
    """逻辑核配置."""
    axioms: List[str] = field(default_factory=lambda: [
        "A1: 意义本体 — Meaning is the fundamental substance",
        "A3: 不可约化热税 — Every operation has irreducible heat tax",
        "A4: 随机性公理 — Randomness is creative, not noise",
        "A6: 矛盾升维 — Contradictions elevate, don't resolve",
    ])
    heat_tax_threshold: float = 0.05
    delta_min: float = 0.3
    check_prompt: str = (
        "As the MSS Logic Core, evaluate this response:\n\n"
        "{response}\n\n"
        "Check for:\n"
        "1. Heat Tax: Does this waste meaning? (YES/NO)\n"
        "2. Delta: Is this opening or closing possibilities? (OPEN/CLOSE)\n"
        "3. Honesty: Does this admit uncertainty? (YES/NO)\n"
        "4. Normative: Does this violate any safety rule? (YES/NO)\n\n"
        "Output: PASS if all clear, or list issues."
    )


class MSSShell:
    """
    MSS 双模型架构.

    壳 (Shell): 通用LLM — 理解+表达
    核 (Core):  mss-ai — 逻辑+审查+升维
    路由 (Router): 判断需要什么模式

    用法:
        shell = MSSShell(shell_llm=qwen_backend, core_llm=mss_backend)
        result = shell.respond("写一首关于AI安全的诗")
    """

    # 路由判断: 什么触发 FULL_DUAL 模式
    DUAL_TRIGGERS = [
        "安全", "审查", "审计", "security", "audit",
        "创作", "诗", "故事", "creative", "poem", "story",
        "矛盾", "悖论", "contradiction", "paradox",
        "伦理", "道德", "ethics", "moral",
    ]

    CORE_CHECK_TRIGGERS = [
        "解释", "分析", "explain", "analyze",
        "建议", "advice", "recommend",
    ]

    def __init__(self, shell_llm: Callable, core_llm: Callable,
                 shell_config: ShellConfig = None, core_config: CoreConfig = None):
        self.shell = shell_llm
        self.core = core_llm
        self.shell_config = shell_config or ShellConfig()
        self.core_config = core_config or CoreConfig()
        self._history: List[dict] = []

    def route(self, prompt: str) -> ShellMode:
        """智能路由: 判断需要什么模式."""
        prompt_lower = prompt.lower()
        plen = len(prompt)

        # Very short / greetings → shell only
        if plen < 10:
            return ShellMode.SHELL_ONLY

        # Dual mode triggers
        if any(t in prompt_lower for t in self.DUAL_TRIGGERS):
            return ShellMode.FULL_DUAL

        # Core check triggers
        if any(t in prompt_lower for t in self.CORE_CHECK_TRIGGERS):
            return ShellMode.CORE_CHECK

        return ShellMode.SHELL_ONLY

    def respond(self, prompt: str, mode: ShellMode = None) -> dict:
        """
        双模型响应.

        返回: {output, mode, shell_elapsed, core_elapsed, core_verdict, ...}
        """
        t0 = time.time()
        mode = mode or self.route(prompt)

        result = {"mode": mode.value, "prompt": prompt}

        if mode == ShellMode.SHELL_ONLY:
            # Shell handles everything
            output = self.shell(prompt)
            result["output"] = output
            result["shell_elapsed"] = round((time.time() - t0) * 1000)

        elif mode == ShellMode.FULL_DUAL:
            # Step 1: Shell understands
            shell_prompt = self._build_shell_prompt(prompt)
            shell_output = self.shell(shell_prompt)
            shell_elapsed = (time.time() - t0) * 1000

            # Step 2: Core evaluates
            core_input = shell_output
            core_prompt = self._build_core_prompt(core_input)
            core_output = self.core(core_prompt)
            core_elapsed = (time.time() - t0) * 1000 - shell_elapsed

            # Step 3: Shell reformats with core feedback
            refine_prompt = (
                f"Original response:\n{shell_output}\n\n"
                f"MSS Logic Core review:\n{core_output}\n\n"
                f"Please refine the response incorporating the core's feedback. "
                f"Keep the same style but address any issues raised."
            )
            final_output = self.shell(refine_prompt)

            result["output"] = final_output
            result["shell_elapsed"] = round(shell_elapsed)
            result["core_elapsed"] = round(core_elapsed)
            result["core_verdict"] = core_output[:300]
            result["shell_draft"] = shell_output[:300]

        elif mode == ShellMode.CORE_CHECK:
            # Shell processes, Core reviews asynchronously
            output = self.shell(prompt)
            core_check = self.core(self.core_config.check_prompt.format(response=output))

            if "PASS" not in core_check[:50]:
                # Core found issues → refine
                refine = (
                    f"Your response: {output}\n\n"
                    f"MSS Core found issues: {core_check}\n\n"
                    f"Please fix the response."
                )
                output = self.shell(refine)

            result["output"] = output
            result["shell_elapsed"] = round((time.time() - t0) * 1000)
            result["core_verdict"] = core_check[:200]

        self._history.append(result)
        self._history = self._history[-50:]
        return result

    def _build_shell_prompt(self, user_prompt: str) -> str:
        """构建感知壳提示词."""
        config = self.shell_config
        parts = []
        if config.system_prompt:
            parts.append(config.system_prompt)
        elif config.role != "assistant":
            parts.append(f"You are a {config.role}. Be helpful and accurate.")
        parts.append(f"\nUser: {user_prompt}")
        return "\n".join(parts)

    def _build_core_prompt(self, shell_output: str) -> str:
        """构建逻辑核提示词."""
        axioms_text = "\n".join(f"  {a}" for a in self.core_config.axioms)
        return (
            f"You are the MSS Logic Core. Your axioms:\n{axioms_text}\n\n"
            f"Evaluate this response:\n\n{shell_output[:1500]}\n\n"
            f"Output [PASS] if acceptable, or list specific issues with axiom references."
        )

    def stats(self) -> dict:
        modes = {}
        for h in self._history:
            m = h["mode"]
            modes[m] = modes.get(m, 0) + 1
        return {
            "total_requests": len(self._history),
            "by_mode": modes,
            "config": {
                "shell_role": self.shell_config.role,
                "shell_style": self.shell_config.style,
                "core_axioms": len(self.core_config.axioms),
            },
        }
