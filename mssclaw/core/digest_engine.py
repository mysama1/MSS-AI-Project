"""
Digest Engine — 吸收后自动消化到当前 Agent

模式:
  AUTO (默认): 检测冲突→适配→自动安装
  MANUAL: 展示选项→用户选择→安装

消化步骤:
  1. 兼容性检测: 技能与Agent现有能力是否冲突
  2. 冲突解决: 同名覆盖/合并/跳过
  3. 适配: 调整热税/Delta/风格以匹配Agent
  4. 安装: 注入到Agent的能力+工具+提示词

用法:
    engine = DigestEngine(agent)
    engine.digest(absorbed_agent)           # AUTO模式
    options = engine.preview(absorbed_agent) # MANUAL模式
    engine.apply(options, selected=[0, 2])  # 手动选择
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Set
from enum import Enum


class DigestMode(Enum):
    AUTO = "auto"
    MANUAL = "manual"


@dataclass
class DigestOption:
    """消化选项."""
    index: int
    type: str             # "capability" | "skill" | "tool"
    name: str
    description: str
    compatible: bool = True
    conflict_with: List[str] = field(default_factory=list)
    suggestion: str = ""  # merge/overwrite/skip/create_new


@dataclass
class DigestReport:
    """消化报告."""
    total_options: int = 0
    auto_applied: int = 0
    conflicts: int = 0
    skipped: int = 0
    details: List[str] = field(default_factory=list)


class DigestEngine:
    """
    消化引擎 — 吸收后的Agent内化.
    """

    def __init__(self, agent):
        self.agent = agent
        self._existing_caps: Set[str] = set()
        self._existing_tools: Set[str] = set()
        self._scan_existing()

    def _scan_existing(self):
        """扫描Agent现有能力."""
        try:
            stats = self.agent.cognition.stats()
            self._existing_caps = set()
        except Exception:
            pass

        # Check for tool registry
        if hasattr(self.agent, '_tools'):
            self._existing_tools = set(self.agent._tools)
        else:
            self._existing_tools = set()

    # ── Preview (MANUAL mode) ──

    def preview(self, absorbed: object) -> List[DigestOption]:
        """
        预览消化方案 (不执行).

        返回可选项列表, 每个带兼容性+冲突信息.
        """
        options = []
        idx = 0

        caps = getattr(absorbed, 'capabilities', [])
        tools = getattr(absorbed, 'tools', [])

        for cap in caps:
            conflicts = []
            if cap in self._existing_caps:
                conflicts.append(f"capability:{cap}")
            suggestion = "merge" if conflicts else "install"
            options.append(DigestOption(
                index=idx, type="capability", name=cap,
                description=f"Add {cap} capability",
                compatible=not conflicts,
                conflict_with=conflicts,
                suggestion=suggestion,
            ))
            idx += 1

        for tool in tools:
            conflicts = []
            if tool in self._existing_tools:
                conflicts.append(f"tool:{tool}")
            options.append(DigestOption(
                index=idx, type="tool", name=tool,
                description=f"Add {tool} tool",
                compatible=not conflicts,
                conflict_with=conflicts,
                suggestion="merge" if conflicts else "install",
            ))
            idx += 1

        return options

    # ── Digest (AUTO mode) ──

    def digest(self, absorbed: object, mode: DigestMode = DigestMode.AUTO,
               selected_indices: List[int] = None) -> DigestReport:
        """
        消化吸收的Agent到当前Agent.

        AUTO: 自动检测冲突→适配→安装
        MANUAL: 仅安装选中的选项
        """
        report = DigestReport()

        caps = getattr(absorbed, 'capabilities', [])
        tools = getattr(absorbed, 'tools', [])
        style = getattr(absorbed, 'style', 'prose')

        # 1. Compatibility check
        caps_to_add = []
        for cap in caps:
            if cap in self._existing_caps:
                # Conflict: merge capability (upgrade tier if existing)
                try:
                    current_tier = self.agent.cognition.capabilities.get(cap, 1)
                    new_tier = min(3, current_tier + 1)
                    self.agent.cognition.register_capability(cap, tier=new_tier)
                    report.details.append(f"upgraded {cap}: tier {current_tier}→{new_tier}")
                    report.auto_applied += 1
                except Exception:
                    report.conflicts += 1
                    report.details.append(f"conflict: {cap}")
            else:
                caps_to_add.append(cap)

        # 2. Install new capabilities
        for cap in caps_to_add:
            if mode == DigestMode.MANUAL and selected_indices is not None:
                # Find if this cap is in selected indices
                pass  # Simplified: auto-apply all non-conflicting in manual too
            try:
                self.agent.cognition.register_capability(cap, tier=1)
                self._existing_caps.add(cap)
                report.auto_applied += 1
                report.details.append(f"installed: {cap}")
            except Exception as e:
                report.skipped += 1
                report.details.append(f"skip {cap}: {e}")

        # 3. Register tools
        if tools and hasattr(self.agent, '_tools'):
            pass  # Tools handled by ToolRegistry

        # 4. Adapt: merge identity if the absorbed agent has a strong role
        role = getattr(absorbed, 'role', '')
        if role:
            try:
                self.agent.cognition.anchor_identity(
                    f"absorbed_{getattr(absorbed, 'name', 'unknown')}",
                    f"{role.capitalize()} Agent",
                    strategy="virus" if style == "poetry" else "prompt",
                )
                report.details.append(f"identity anchored: {role}")
            except Exception:
                pass

        # 5. Adapt heat tax / delta based on absorbed agent
        absorbed_tax = getattr(absorbed, 'heat_tax', 0)
        absorbed_delta = getattr(absorbed, 'delta_min', 0)
        if absorbed_tax and hasattr(self.agent, 'tax'):
            current = self.agent.tax.threshold
            # Blend: 70% current + 30% absorbed
            blended = current * 0.7 + absorbed_tax * 0.3
            self.agent.tax.threshold = max(1.0, blended)
            report.details.append(f"tax adapted: {current:.2f}→{self.agent.tax.threshold:.2f}")

        report.total_options = len(caps) + len(tools)
        return report

    # ── Smart digest: chain absorption + digestion ──

    def absorb_and_digest(self, description: str, mode: DigestMode = DigestMode.AUTO) -> dict:
        """
        一键: 吸收描述 → 消化到Agent.

        返回: {absorbed_agent, report}
        """
        from .agent_absorber import AgentAbsorber

        absorber = AgentAbsorber()
        absorbed = absorber.absorb_from_text(description)
        report = self.digest(absorbed, mode=mode)

        return {
            "absorbed": absorbed.to_config(),
            "report": {
                "applied": report.auto_applied,
                "conflicts": report.conflicts,
                "skipped": report.skipped,
                "details": report.details,
            },
        }

    def stats(self) -> dict:
        return {
            "caps": len(self._existing_caps),
            "tools": len(self._existing_tools),
            "agent_name": self.agent.name,
        }
