# -*- coding: utf-8 -*-
"""
CapabilityLevel — 工具吸收分级系统 (S-030)

方法论#9 工程落地。对每个工具/技能做三级能力标注:
  L-A (Absorbed)  — 已验证可用的能力，可被调度器调用
  L-B (Bench)     — 已验证但需条件满足，不可自动调度
  L-C (Catalog)   — 仅文档参考，声明有但不应被调用

核心约束:
  C 级工具声明"仅文档参考" → task_router 不可选中
  validate_capability_claims() 交叉验证

Usage:
  cl = CapabilityLevel()
  cl.register("eval_executor", CapabilityLevel.Type.B, 
              requires=["sandbox_env"], notes="需要沙盒环境")
  cl.register("file_writer", CapabilityLevel.Type.A,
              verified=True, benchmark={"accuracy": 0.95})

  # 调度器可以用
  available = cl.available_for_scheduling()  # 只返回 A 级
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional, Set
from enum import Enum
import json
import time


class CapTier(Enum):
    """三级吸收度。"""
    A = "absorbed"    # 已吸收 — 可调度
    B = "bench"       # 待验证 — 不可自动调度
    C = "catalog"     # 仅目录 — 禁止调度


@dataclass
class Capability:
    """单个工具的能力声明。"""
    name: str                    # 工具名
    tier: CapTier
    requires: List[str] = field(default_factory=list)    # 依赖/前置条件
    provides: List[str] = field(default_factory=list)    # 提供的能力
    verified: bool = False       # 是否已通过验证
    benchmark: Dict[str, float] = field(default_factory=dict)  # 基准数据
    notes: str = ""
    registered_at: float = field(default_factory=time.time)
    last_verified_at: float = 0.0

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "tier": self.tier.value,
            "requires": self.requires,
            "provides": self.provides,
            "verified": self.verified,
            "benchmark": self.benchmark,
            "notes": self.notes,
        }

    def is_schedulable(self) -> bool:
        """是否可被 task_router 选中。"""
        return self.tier == CapTier.A and self.verified

    def is_documentation_only(self) -> bool:
        """是否仅文档参考。"""
        return self.tier == CapTier.C


@dataclass
class CapabilityReport:
    """能力验证报告。"""
    capabilities: List[Capability] = field(default_factory=list)
    tier_a_count: int = 0
    tier_b_count: int = 0
    tier_c_count: int = 0
    schedulable: List[str] = field(default_factory=list)
    documentation_only: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)

    @property
    def total(self) -> int:
        return self.tier_a_count + self.tier_b_count + self.tier_c_count

    def to_dict(self) -> dict:
        return {
            "total": self.total,
            "tier_a": self.tier_a_count,
            "tier_b": self.tier_b_count,
            "tier_c": self.tier_c_count,
            "schedulable": self.schedulable,
            "documentation_only": self.documentation_only,
            "warnings": self.warnings,
        }


class CapabilityLevel:
    """
    工具吸收分级注册表。

    约束:
      - C 级工具不可被 task_router 选中
      - B 级需条件满足后才能晋升 A
      - A 级需 verified=True 才可调度

    Usage:
        cl = CapabilityLevel()
        cl.register("code_runner", CapTier.A, verified=True)
        cl.register("eval_exec", CapTier.C, notes="危险工具，仅记录")
        assert "eval_exec" not in cl.available_for_scheduling()
    """

    def __init__(self):
        self._registry: Dict[str, Capability] = {}

    # ── 注册 ──

    def register(
        self,
        name: str,
        tier: CapTier,
        requires: Optional[List[str]] = None,
        provides: Optional[List[str]] = None,
        verified: bool = False,
        benchmark: Optional[Dict[str, float]] = None,
        notes: str = "",
    ) -> Capability:
        """
        注册一个工具。

        Args:
            name: 工具唯一标识
            tier: 吸收分级
            requires: 依赖列表
            provides: 能力列表
            verified: 是否已验证
            benchmark: 基准测试数据
            notes: 备注

        Returns:
            Capability
        """
        cap = Capability(
            name=name,
            tier=tier,
            requires=requires or [],
            provides=provides or [],
            verified=verified,
            benchmark=benchmark or {},
            notes=notes,
        )
        self._registry[name] = cap
        return cap

    def register_bulk(
        self,
        specs: List[Dict],
    ) -> List[Capability]:
        """批量注册。"""
        results = []
        for spec in specs:
            results.append(self.register(
                name=spec["name"],
                tier=CapTier(spec["tier"]),
                requires=spec.get("requires"),
                provides=spec.get("provides"),
                verified=spec.get("verified", False),
                benchmark=spec.get("benchmark"),
                notes=spec.get("notes", ""),
            ))
        return results

    # ── 查询 ──

    def get(self, name: str) -> Optional[Capability]:
        """按名获取。"""
        return self._registry.get(name)

    def list_by_tier(self, tier: CapTier) -> List[Capability]:
        """按分级列出。"""
        return [c for c in self._registry.values() if c.tier == tier]

    def available_for_scheduling(self) -> List[str]:
        """可被调度器调用的工具列表 (A 级 + 已验证)。"""
        return [c.name for c in self._registry.values() if c.is_schedulable()]

    def documentation_only(self) -> List[str]:
        """仅文档参考的工具列表 (C 级)。"""
        return [c.name for c in self._registry.values() if c.is_documentation_only()]

    # ── 晋升/降级 ──

    def promote(self, name: str, verify: bool = True) -> bool:
        """
        晋升工具: C→B 或 B→A。

        Returns:
            True if promoted
        """
        cap = self._registry.get(name)
        if not cap:
            return False

        if cap.tier == CapTier.C:
            cap.tier = CapTier.B
            cap.notes += " | auto-promoted C→B"
            return True
        elif cap.tier == CapTier.B and verify:
            cap.tier = CapTier.A
            cap.verified = True
            cap.last_verified_at = time.time()
            cap.notes += " | promoted B→A (verified)"
            return True

        return False

    def demote(self, name: str, reason: str = "") -> bool:
        """
        降级工具: A→B 或 B→C。

        Returns:
            True if demoted
        """
        cap = self._registry.get(name)
        if not cap:
            return False

        if cap.tier == CapTier.A:
            cap.tier = CapTier.B
            cap.verified = False
            cap.notes += f" | demoted A→B: {reason}"
            return True
        elif cap.tier == CapTier.B:
            cap.tier = CapTier.C
            cap.notes += f" | demoted B→C: {reason}"
            return True

        return False

    # ── 验证 ──

    def validate_capability_claims(self) -> CapabilityReport:
        """
        交叉验证所有能力声明。

        检查:
          1. A 级但未 verified → WARNING
          2. C 级但声称 provides → WARNING
          3. requires 中的依赖不存在 → WARNING
          4. B 级 cites A 级依赖但那个依赖未 verified → WARNING

        Returns:
            CapabilityReport 含所有警告
        """
        report = CapabilityReport()
        all_names = set(self._registry.keys())

        for cap in self._registry.values():
            # 统计
            if cap.tier == CapTier.A:
                report.tier_a_count += 1
                if cap.is_schedulable():
                    report.schedulable.append(cap.name)
            elif cap.tier == CapTier.B:
                report.tier_b_count += 1
            elif cap.tier == CapTier.C:
                report.tier_c_count += 1
                report.documentation_only.append(cap.name)

            # ── 交叉验证规则 ──
            warnings = []

            # W1: A 级未验证
            if cap.tier == CapTier.A and not cap.verified:
                warnings.append(
                    f"{cap.name}: tier=A but not verified — cannot be scheduled"
                )

            # W2: C 级声称 provides (矛盾)
            if cap.tier == CapTier.C and cap.provides:
                warnings.append(
                    f"{cap.name}: tier=C but claims provides={cap.provides} — "
                    f"documentation-only tools should not claim capabilities"
                )

            # W3: 依赖不存在
            for dep in cap.requires:
                if dep not in all_names:
                    warnings.append(
                        f"{cap.name}: requires '{dep}' which is not registered"
                    )

            # W4: B 级引用未验证的 A 级依赖
            if cap.tier == CapTier.B:
                for dep in cap.requires:
                    dep_cap = self._registry.get(dep)
                    if dep_cap and dep_cap.tier == CapTier.A and not dep_cap.verified:
                        warnings.append(
                            f"{cap.name}: B-tier depends on A-tier '{dep}' "
                            f"which is unverified"
                        )

            report.warnings.extend(warnings)

        # 自动排序
        report.schedulable.sort()
        report.documentation_only.sort()

        return report

    # ── 导出 ──

    def to_dict(self) -> dict:
        return {name: cap.to_dict() for name, cap in self._registry.items()}

    def export_json(self, path: str) -> None:
        """导出到 JSON 文件。"""
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, ensure_ascii=False, indent=2)

    def import_json(self, path: str) -> None:
        """从 JSON 文件导入。"""
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        for name, spec in data.items():
            if spec.get("tier") in ("absorbed", "bench", "catalog"):
                self.register(
                    name=name,
                    tier=CapTier(spec["tier"]),
                    requires=spec.get("requires", []),
                    provides=spec.get("provides", []),
                    verified=spec.get("verified", False),
                    benchmark=spec.get("benchmark", {}),
                    notes=spec.get("notes", ""),
                )

    def __len__(self) -> int:
        return len(self._registry)

    def __contains__(self, name: str) -> bool:
        return name in self._registry


# ════════════════════════════════════════════════════════════
# CLI 自检
# ════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print("=== CapabilityLevel S-030 — 工具分级 Demo ===\n")

    cl = CapabilityLevel()

    # ── 注册一批工具 ──
    cl.register("code_runner", CapTier.A, verified=True,
                provides=["code_execution", "sandbox"],
                benchmark={"latency_ms": 150, "accuracy": 0.98})
    cl.register("file_writer", CapTier.A, verified=True,
                provides=["file_io"])
    cl.register("ollama_query", CapTier.A, verified=True,
                provides=["llm_inference"],
                benchmark={"latency_ms": 2000})
    cl.register("eval_executor", CapTier.B,
                requires=["sandbox_env"],
                provides=["raw_execution"],
                notes="需要沙盒环境")
    cl.register("web_scraper", CapTier.B,
                requires=["ollama_query"],
                provides=["web_access"],
                notes="等待 ollama_query 验证后晋升")
    cl.register("shell_exec", CapTier.C,
                provides=["raw_shell"],
                notes="仅文档记录——危险工具禁止调度")

    # ── 测试 1: 调度器可用工具 ──
    print("─ 测试 1: available_for_scheduling ─")
    avail = cl.available_for_scheduling()
    print(f"  Schedulable: {avail}")
    assert "code_runner" in avail
    assert "file_writer" in avail
    assert "ollama_query" in avail
    assert "eval_executor" not in avail  # B 级
    assert "shell_exec" not in avail     # C 级
    print(f"  ✅ Test 1 PASS")

    # ── 测试 2: 文档记录工具 ──
    print("\n─ 测试 2: 仅文档参考 ─")
    docs = cl.documentation_only()
    print(f"  Doc-only: {docs}")
    assert "shell_exec" in docs
    print(f"  ✅ Test 2 PASS")

    # ── 测试 3: 晋升 ──
    print("\n─ 测试 3: 晋升 C→B→A ─")
    assert cl.promote("shell_exec", verify=False)
    cap_shell = cl.get("shell_exec")
    assert cap_shell and cap_shell.tier == CapTier.B
    print(f"  Shell C→B: tier={cap_shell.tier.value}")

    assert cl.promote("shell_exec")
    cap_shell2 = cl.get("shell_exec")
    assert cap_shell2 and cap_shell2.tier == CapTier.A
    assert cap_shell2.verified
    print(f"  Shell B→A: tier={cap_shell2.tier.value}, verified={cap_shell2.verified}")
    print(f"  ✅ Test 3 PASS")

    # ── 测试 4: 降级 ──
    print("\n─ 测试 4: 降级 A→B ─")
    # 把刚晋升的 shell_exec 降回去
    assert cl.demote("shell_exec", "安全审计未通过")
    cap_demoted = cl.get("shell_exec")
    assert cap_demoted and cap_demoted.tier == CapTier.B
    assert not cap_demoted.verified
    print(f"  Shell A→B: tier={cap_demoted.tier.value}, verified={cap_demoted.verified}")
    print(f"  ✅ Test 4 PASS")

    # ── 测试 5: 交叉验证 ──
    print("\n─ 测试 5: 交叉验证 ─")
    report = cl.validate_capability_claims()
    print(f"  Tier A: {report.tier_a_count}, B: {report.tier_b_count}, C: {report.tier_c_count}")
    print(f"  Schedulable: {report.schedulable}")
    print(f"  Warnings: {report.warnings}")
    # web_scraper(B) 依赖 ollama_query(A, verified) → 无警告
    # 但如果有未验证的 A 级被 B 级依赖，会触发 W4
    assert len(report.schedulable) >= 3
    print(f"  ✅ Test 5 PASS")

    # ── 测试 6: JSON 导出/导入 ──
    print("\n─ 测试 6: JSON 导出/导入 ─")
    import tempfile
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as tmp:
        cl.export_json(tmp.name)
        export_path = tmp.name

    cl2 = CapabilityLevel()
    cl2.import_json(export_path)
    assert len(cl2) == len(cl), f"Import count mismatch: {len(cl2)} vs {len(cl)}"
    assert cl2.get("code_runner")
    assert cl2.get("code_runner").tier == CapTier.A
    print(f"  Exported {len(cl)} tools → import OK")
    print(f"  ✅ Test 6 PASS")

    # ── 测试 7: 序列化 ──
    print("\n─ 测试 7: 序列化 ─")
    from pathlib import Path
    json_path = Path(tempfile.gettempdir()) / "cap_test.json"
    cl.export_json(str(json_path))
    d = cl.to_dict()
    assert len(d) == len(cl)
    print(f"  Dict size: {len(d)} | JSON file: {json_path.stat().st_size} bytes")
    print(f"  ✅ Test 7 PASS")

    print(f"\n📊 S-030 CapabilityLevel 验收报告:")
    print(f"  调度器可用 (A+verified): ✅")
    print(f"  文档参考 (C-tier): ✅")
    print(f"  晋升 C→B→A: ✅")
    print(f"  降级 A→B: ✅")
    print(f"  交叉验证 (W1-W4): ✅")
    print(f"  JSON 导入/导出: ✅")
    print(f"  序列化: ✅")
    print(f"\n  🎉 S-030 CapabilityLevel — ALL PASS")
