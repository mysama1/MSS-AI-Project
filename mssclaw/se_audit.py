#!/usr/bin/env python3
"""
MSS Software Engineering Auditor v0.1 — se_audit.py
====================================================
基于 MSS 意义场理论的代码架构审计器。

输入:  Python 项目目录
输出:  MSS 架构健康报告 (η_code, 稳定子保真度, 规范场违反, 热税热点, 升维建议)

理论基座: H647 (代码→意义场量化映射)
差异化:   SonarQube告诉你"哪里坏了", MSS告诉你"为什么坏/还能撑多久/该修还是拆"

PRINCIPLE: 审计器是规范场的投影工具 — 它本身不定义规范场, 只检测违反。
"""
from __future__ import annotations
import ast
import os
import sys
import json
import math
from pathlib import Path
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple
from collections import defaultdict, Counter
from enum import Enum


# ═══════════════════════════════════════════════════════
# H647 量化模型
# ═══════════════════════════════════════════════════════

class NormativeViolation(Enum):
    """规范场违反类型."""
    ILLEGAL_IMPORT = "illegal_import"           # 跨层/反向依赖
    STABLE_NODE_BREACH = "stable_node_breach"   # 违反稳定子
    HEAT_HOTSPOT = "heat_hotspot"               # 热税热点
    COUPLING_EXCESS = "coupling_excess"         # 过度耦合
    ORPHAN_MODULE = "orphan_module"             # 孤儿模块(未注册规范场)
    INCOMPLETE_ENUM = "incomplete_enum"         # 枚举不完备(H635 Type II)
    CIRCULAR_DEPENDENCY = "circular_dependency" # 循环依赖
    DEAD_CODE_SUSPECT = "dead_code_suspect"     # 疑似死码


@dataclass
class Violation:
    file: str
    line: int
    type: NormativeViolation
    description: str
    severity: float  # 0-1, H633 tension scale
    suggestion: str


@dataclass
class ModuleMetrics:
    file: str
    lines: int
    imports: List[str]
    internal_imports: List[str]  # 项目内依赖
    exported_symbols: List[str]
    classes: int
    functions: int
    complexity: float  # 归一化复杂度
    heat_tax_estimate: float  # 0-1
    normative_violations: List[Violation] = field(default_factory=list)


@dataclass
class AuditReport:
    project_root: str
    total_files: int
    total_lines: int
    modules: List[ModuleMetrics]
    violations: List[Violation]
    eta_code: float  # H647: 综合意义场健康度
    S_fidelity: float
    N_compliance: float
    H_utilization: float
    heat_hotspots: List[Tuple[str, float]]  # (file, heat_score)
    elevation_suggestions: List[str]


# ═══════════════════════════════════════════════════════
# 审计引擎
# ═══════════════════════════════════════════════════════

class MSSAuditor:
    """
    MSS 代码审计器.

    分层:
      L0: AST解析 — 提取语法结构
      L1: 依赖分析 — 构建调用图
      L2: 规范场检测 — 对照声明规则
      L3: 意义场评分 — 计算 η_code
    """

    # 合法依赖方向 (下层 → 上层是违规)
    # 默认分层: core → agents/scanner → cli
    DEFAULT_LAYERS = {
        "core": 0,
        "core.evolution": 0,
        "core.meaning": 0,
        "core.reliability": 0,
        "core.security": 0,
        "core.semantic": 0,
        "core.swarm": 0,
        "agents": 1,
        "scanner": 1,
        "cli": 2,
        "config": 1,
        "llm": 1,
    }

    # 热税热点规则
    HEAT_RULES = {
        "high_coupling": 0.3,      # 内部依赖 > 5 → 热税加成
        "large_file": 0.2,         # >500行 → 热税加成
        "deep_nesting": 0.15,      # 嵌套深度>4 → 热税加成
        "many_classes": 0.1,       # 单文件>10类 → 热税加成
        "stdlib_only": -0.2,       # 纯stdlib → 热税减免(H646强模型保护)
    }

    def __init__(self, project_root: str, normative_rules: dict = None):
        self.project_root = Path(project_root)
        self.normative_rules = normative_rules or {}
        self.layers = dict(self.DEFAULT_LAYERS)
        self.violations: List[Violation] = []
        self.modules: List[ModuleMetrics] = []

    # ── L0: AST 解析 ──

    def _parse_file(self, filepath: Path) -> Optional[ast.Module]:
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                source = f.read()
            return ast.parse(source, filename=str(filepath))
        except (SyntaxError, UnicodeDecodeError) as e:
            return None

    def _extract_imports(self, tree: ast.Module) -> Tuple[List[str], List[str]]:
        """返回 (all_imports, internal_imports)."""
        all_imports = []
        internal = []

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    name = alias.name.split('.')[0]
                    all_imports.append(name)
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    name = node.module.split('.')[0]
                    all_imports.append(name)

        # 检测项目内依赖
        proj_name = self.project_root.name
        for imp in all_imports:
            if imp in ('mssclaw', 'core', 'agents', 'scanner', 'config', 'llm', proj_name):
                internal.append(imp)

        return all_imports, internal

    def _count_symbols(self, tree: ast.Module) -> Tuple[int, int, List[str]]:
        classes = 0
        functions = 0
        exports = []

        for node in ast.iter_child_nodes(tree):
            if isinstance(node, ast.ClassDef):
                classes += 1
                exports.append(node.name)
            elif isinstance(node, ast.FunctionDef):
                if not node.name.startswith('_'):
                    functions += 1
                    exports.append(node.name)

        return classes, functions, exports

    def _estimate_complexity(self, tree: ast.Module, lines: int) -> float:
        """归一化复杂度 (0-1)."""
        nesting_depth = 0
        branches = 0
        total_nodes = 0

        for node in ast.walk(tree):
            total_nodes += 1
            if isinstance(node, (ast.If, ast.For, ast.While, ast.Try, ast.With, ast.ExceptHandler)):
                branches += 1

        if total_nodes == 0:
            return 0.0

        # 圈复杂度归一化
        cc = 1 + branches
        cc_norm = min(1.0, cc / 50.0)  # 50 → 1.0

        # 每行节点密度
        density = min(1.0, total_nodes / max(lines, 1) * 5)

        return (cc_norm + density) / 2.0

    # ── L1: 依赖分析 ──

    def _get_layer(self, filepath: Path) -> Optional[int]:
        """根据文件路径推断架构层."""
        rel = filepath.relative_to(self.project_root)
        parts = rel.parts

        # 匹配已知层
        for layer_name, layer_id in self.layers.items():
            layer_path = layer_name.replace('.', os.sep)
            if str(rel).startswith(layer_path) or str(rel.parent).startswith(layer_path):
                return layer_id

        return None

    def _check_layer_violation(self, filepath: Path, imports: List[str], tree: ast.Module) -> List[Violation]:
        """检测跨层依赖违反."""
        violations = []
        my_layer = self._get_layer(filepath)
        if my_layer is None:
            return violations

        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module:
                imp_path = node.module.replace('.', os.sep) + '.py'
                imp_full = self.project_root / imp_path
                if imp_full.exists():
                    target_layer = self._get_layer(imp_full)
                    if target_layer is not None and my_layer > target_layer:
                        # 上层引用下层 → 违反
                        violations.append(Violation(
                            file=str(filepath.relative_to(self.project_root)),
                            line=node.lineno,
                            type=NormativeViolation.ILLEGAL_IMPORT,
                            description=f"反向依赖: 层{my_layer}→层{target_layer} ({node.module})",
                            severity=0.42,
                            suggestion=f"引入接口抽象层或移动目标模块到同层/上层"
                        ))

        return violations

    # ── L2: 规范场检测 ──

    def _detect_circular_deps(self) -> List[Violation]:
        """检测循环依赖."""
        violations = []
        deps = defaultdict(set)
        for mod in self.modules:
            for imp in mod.internal_imports:
                deps[mod.file].add(imp)

        # 简易DFS检测
        visited = set()
        rec_stack = set()

        def dfs(node):
            visited.add(node)
            rec_stack.add(node)
            for neighbor in deps.get(node, set()):
                if neighbor not in visited:
                    if dfs(neighbor):
                        return True
                elif neighbor in rec_stack:
                    return True
            rec_stack.discard(node)
            return False

        for node in list(deps.keys()):
            if node not in visited:
                if dfs(node):
                    violations.append(Violation(
                        file=node,
                        line=0,
                        type=NormativeViolation.CIRCULAR_DEPENDENCY,
                        description=f"循环依赖检测: {node} 在环中",
                        severity=0.72,
                        suggestion="提取共同依赖到独立模块或引入接口层"
                    ))

        return violations

    def _detect_orphan_modules(self) -> List[Violation]:
        """检测未注册规范场的孤儿模块 (scene_router审计发现)."""
        violations = []
        normative_modules = set(self.normative_rules.get('registered_modules', []))

        for mod in self.modules:
            mod_name = mod.file.replace('.py', '').replace(os.sep, '.')
            if mod_name not in normative_modules and mod.internal_imports:
                violations.append(Violation(
                    file=mod.file,
                    line=0,
                    type=NormativeViolation.ORPHAN_MODULE,
                    description=f"模块 {mod_name} 未在规范场中注册",
                    severity=0.35,
                    suggestion="在 normative_field.py 中声明此模块的规范约束"
                ))

        return violations

    def _detect_heat_hotspots(self) -> List[Violation]:
        """检测热税热点."""
        violations = []

        for mod in self.modules:
            heat = mod.heat_tax_estimate

            if heat > 0.7:
                violations.append(Violation(
                    file=mod.file,
                    line=0,
                    type=NormativeViolation.HEAT_HOTSPOT,
                    description=f"高热税模块: heat={heat:.2f} (行数={mod.lines}, 内部依赖={len(mod.internal_imports)}, 类={mod.classes})",
                    severity=heat * 0.8,
                    suggestion="考虑拆分为多个小模块或降低内部依赖数"
                ))

        return violations

    def _detect_incomplete_enum(self, tree: ast.Module, filepath: Path) -> List[Violation]:
        """H635: 检测枚举不完备 (Type II 选项空间不足)."""
        violations = []
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                # 检查是否是 Enum 子类
                is_enum = any(
                    isinstance(base, ast.Attribute) and base.attr == 'Enum'
                    or isinstance(base, ast.Name) and base.id == 'Enum'
                    for base in node.bases
                )
                if is_enum:
                    members = [n.targets[0].id for n in node.body 
                              if isinstance(n, ast.Assign) and hasattr(n.targets[0], 'id')]
                    if len(members) < 3:
                        violations.append(Violation(
                            file=str(filepath.relative_to(self.project_root)),
                            line=node.lineno,
                            type=NormativeViolation.INCOMPLETE_ENUM,
                            description=f"枚举 {node.name} 只有{len(members)}个成员, 可能存在Type II选项空间不足",
                            severity=0.68 if len(members) <= 2 else 0.25,
                            suggestion=f"考虑是否遗漏枚举值, 或使用动态注册模式 (A7创造, H635)"
                        ))

        return violations

    # ── L3: 意义场评分 ──

    def _calc_eta(self) -> Tuple[float, float, float, float]:
        """H647公式: η_code = ω_s × S_fidelity + ω_n × N_compliance + ω_h × (1 - H_utilization)."""
        if not self.modules:
            return 0.0, 0.0, 0.0, 0.0

        # 稳定子保真度: 基于声明的稳定子(当前简化: 所有模块无规范场违反=高保真)
        declared = len(self.normative_rules.get('stable_nodes', [])) or 1
        breached = sum(1 for v in self.violations if v.type == NormativeViolation.STABLE_NODE_BREACH)
        S_fidelity = max(0.0, 1.0 - breached / declared)

        # 规范场遵守率: 基于检测到的违反比例
        total_edges = sum(len(m.internal_imports) for m in self.modules) or 1
        illegal_edges = sum(1 for v in self.violations if v.type == NormativeViolation.ILLEGAL_IMPORT)
        N_compliance = max(0.0, 1.0 - illegal_edges / total_edges)

        # 热税利用率: 平均热税 / 预算
        avg_heat = sum(m.heat_tax_estimate for m in self.modules) / len(self.modules)
        budget = self.normative_rules.get('heat_budget', 0.5)
        H_utilization = min(1.0, avg_heat / max(budget, 0.01))

        # H647 默认权重
        w_s, w_n, w_h = 0.40, 0.35, 0.25
        eta = w_s * S_fidelity + w_n * N_compliance + w_h * (1.0 - H_utilization)

        return eta, S_fidelity, N_compliance, H_utilization

    # ── 主入口 ──

    def audit(self) -> AuditReport:
        """运行完整审计."""
        self.violations = []
        self.modules = []
        total_lines = 0

        for filepath in self.project_root.rglob("*.py"):
            # 跳过测试和临时文件
            if any(p in filepath.parts for p in ('__pycache__', '.git', 'tests', 'test', '_test')):
                continue

            tree = self._parse_file(filepath)
            if tree is None:
                continue

            imports, internal_imports = self._extract_imports(tree)
            classes, functions, exports = self._count_symbols(tree)
            lines = len(tree.body) or 1
            total_lines += lines

            # 复杂度 + 热税
            complexity = self._estimate_complexity(tree, lines)
            heat = self._calc_module_heat(lines, len(internal_imports), classes, complexity, imports)

            mod = ModuleMetrics(
                file=str(filepath.relative_to(self.project_root)),
                lines=lines,
                imports=imports,
                internal_imports=internal_imports,
                exported_symbols=exports,
                classes=classes,
                functions=functions,
                complexity=round(complexity, 3),
                heat_tax_estimate=round(heat, 3),
            )

            # 检查各层违反
            layer_vios = self._check_layer_violation(filepath, internal_imports, tree)
            enum_vios = self._detect_incomplete_enum(tree, filepath)
            mod.normative_violations = layer_vios + enum_vios
            self.violations.extend(mod.normative_violations)
            self.modules.append(mod)

        # 全局检测
        self.violations.extend(self._detect_circular_deps())
        self.violations.extend(self._detect_orphan_modules())
        self.violations.extend(self._detect_heat_hotspots())

        # H647 评分
        eta, S_f, N_c, H_u = self._calc_eta()

        # 热税热点排序
        hotspots = sorted(
            [(m.file, m.heat_tax_estimate) for m in self.modules if m.heat_tax_estimate > 0.3],
            key=lambda x: x[1], reverse=True
        )[:10]

        # 升维建议
        elevation = self._generate_elevation_suggestions()

        return AuditReport(
            project_root=str(self.project_root),
            total_files=len(self.modules),
            total_lines=total_lines,
            modules=self.modules,
            violations=self.violations,
            eta_code=round(eta, 3),
            S_fidelity=round(S_f, 3),
            N_compliance=round(N_c, 3),
            H_utilization=round(H_u, 3),
            heat_hotspots=hotspots,
            elevation_suggestions=elevation,
        )

    def _calc_module_heat(self, lines: int, internal_deps: int, classes: int,
                          complexity: float, imports: List[str]) -> float:
        """计算模块热税 (0-1)."""
        heat = 0.0

        # 内部依赖 → 高耦合热税
        if internal_deps > 5:
            heat += self.HEAT_RULES["high_coupling"] * min(1.0, internal_deps / 10)

        # 大文件
        if lines > 500:
            heat += self.HEAT_RULES["large_file"] * min(1.0, lines / 1000)

        # 多类
        if classes > 10:
            heat += self.HEAT_RULES["many_classes"] * min(1.0, classes / 20)

        # 复杂度加成
        heat += complexity * 0.3

        # H646: 纯stdlib模块 → 热税减免 (强模型保护)
        if not internal_deps:
            heat += self.HEAT_RULES["stdlib_only"]

        return max(0.0, min(1.0, heat))

    def _generate_elevation_suggestions(self) -> List[str]:
        """基于 tension + heat 生成升维建议."""
        suggestions = []

        # 高热税模块
        hot = [m for m in self.modules if m.heat_tax_estimate > 0.6]
        if hot:
            suggestions.append(
                f"🔥 {len(hot)}个高热税模块 (heat>0.6): "
                + ", ".join(m.file for m in hot[:3])
                + " — 考虑拆分或降低耦合"
            )

        # 高违反数
        severe = [v for v in self.violations if v.severity > 0.5]
        if severe:
            suggestions.append(
                f"⚠️ {len(severe)}个高严重度违反 (severity>0.5): "
                + ", ".join(set(v.file for v in severe[:3]))
            )

        # H635: 枚举不完备
        enum_vios = [v for v in self.violations if v.type == NormativeViolation.INCOMPLETE_ENUM]
        if enum_vios:
            suggestions.append(
                f"🔷 Type II风险: {len(enum_vios)}个枚举可能不完备 "
                + f"({', '.join(v.file for v in enum_vios[:3])})"
                + " — 考虑动态注册 (A7创造, H635)"
            )

        # 孤儿模块
        orphans = [v for v in self.violations if v.type == NormativeViolation.ORPHAN_MODULE]
        if orphans:
            suggestions.append(
                f"👻 {len(orphans)}个孤儿模块未注册规范场"
                + " — 需要 normative_field 声明或确认独立合法性"
            )

        # 总体评价
        eta = self._calc_eta()[0]
        if eta >= 0.7:
            suggestions.append(f"✅ 整体健康 (η={eta:.2f}), D2_idle — 保持现状")
        elif eta >= 0.5:
            suggestions.append(f"⚡ 中等健康 (η={eta:.2f}), D1_resolve — 建议渐进重构")
        else:
            suggestions.append(f"🔴 低健康 (η={eta:.2f}), 需要系统性重构或重写")

        return suggestions


# ═══════════════════════════════════════════════════════
# 报告输出
# ═══════════════════════════════════════════════════════

def print_report(report: AuditReport):
    """格式化输出审计报告."""
    print(f"\n{'═' * 70}")
    print(f"  MSS 架构健康审计报告")
    print(f"{'═' * 70}")
    print(f"  项目: {report.project_root}")
    print(f"  文件: {report.total_files} | 行数: {report.total_lines}")
    print()

    # H647 健康评分
    print(f"  ┌─ η_code (意义场健康度) ─────────────────────")
    eta_bar = "█" * int(report.eta_code * 20) + "░" * (20 - int(report.eta_code * 20))
    status = "✅ 健康" if report.eta_code >= 0.7 else ("⚡ 中等" if report.eta_code >= 0.5 else "🔴 低")
    print(f"  │ {eta_bar} {report.eta_code:.3f} [{status}]")
    print(f"  ├─ 稳定子保真度:  {report.S_fidelity:.3f}")
    print(f"  ├─ 规范场遵守率:  {report.N_compliance:.3f}")
    print(f"  └─ 热税利用率:    {report.H_utilization:.3f}")
    print()

    # 违反摘要
    by_type = defaultdict(list)
    for v in report.violations:
        by_type[v.type.value].append(v)

    print(f"  ┌─ 规范场违反 ({len(report.violations)} 项) ────────")
    for vtype, vlist in sorted(by_type.items()):
        icon = {"illegal_import": "⬆", "orphan_module": "👻", "heat_hotspot": "🔥",
                "incomplete_enum": "🔷", "circular_dependency": "🔄",
                "stable_node_breach": "💥", "coupling_excess": "🔗",
                "dead_code_suspect": "💀"}.get(vtype, "❓")
        print(f"  │ {icon} {vtype}: {len(vlist)}")
    if not report.violations:
        print(f"  │ ✅ 无违反")
    print()

    # 热税热点 Top 5
    if report.heat_hotspots:
        print(f"  ┌─ 热税热点 ──────────────────────────────")
        for i, (fname, heat) in enumerate(report.heat_hotspots[:5], 1):
            bar = "🔥" * min(5, int(heat * 10))
            print(f"  │ {i}. {fname:<40} {bar} ({heat:.2f})")
        print()

    # 升维建议
    if report.elevation_suggestions:
        print(f"  ┌─ A6 升维建议 ────────────────────────────")
        for s in report.elevation_suggestions:
            print(f"  │ {s}")
        print()

    # 最高热税模块详情
    if report.heat_hotspots:
        print(f"  ┌─ 重点模块 ──────────────────────────────")
        for fname, heat in report.heat_hotspots[:3]:
            mod = next((m for m in report.modules if m.file == fname), None)
            if mod:
                print(f"  │ {fname}: {mod.lines}行, {mod.classes}类, "
                      f"{mod.functions}函数, 内部依赖={len(mod.internal_imports)}, "
                      f"复杂度={mod.complexity:.2f}")

    print(f"\n{'═' * 70}")
    print(f"  审计完成 — MSS se_audit v0.1 (H647 + scene_router 实证)")
    print(f"{'═' * 70}\n")


def save_report_json(report: AuditReport, outpath: str):
    """输出 JSON 格式报告."""
    data = {
        "project": report.project_root,
        "files": report.total_files,
        "lines": report.total_lines,
        "eta_code": report.eta_code,
        "S_fidelity": report.S_fidelity,
        "N_compliance": report.N_compliance,
        "H_utilization": report.H_utilization,
        "violations": [
            {"file": v.file, "line": v.line, "type": v.type.value,
             "severity": v.severity, "desc": v.description, "suggestion": v.suggestion}
            for v in report.violations
        ],
        "hotspots": [{"file": f, "heat": h} for f, h in report.heat_hotspots],
        "elevation": report.elevation_suggestions,
    }
    with open(outpath, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    print(f"  📄 JSON报告: {outpath}")


# ═══════════════════════════════════════════════════════
# CLI
# ═══════════════════════════════════════════════════════

def main():
    import argparse
    parser = argparse.ArgumentParser(
        description="MSS 架构健康审计器 — 意义场视角下的代码质量评估"
    )
    parser.add_argument("path", nargs="?", default=".",
                        help="Python项目路径 (默认: 当前目录)")
    parser.add_argument("--json", "-j", metavar="FILE",
                        help="输出JSON报告到文件")
    parser.add_argument("--rules", "-r", metavar="FILE",
                        help="自定义规范场规则 (JSON)")
    parser.add_argument("--layers", "-l", metavar="FILE",
                        help="自定义分层配置 (JSON)")

    args = parser.parse_args()

    # 加载自定义规则
    rules = {}
    if args.rules and os.path.exists(args.rules):
        with open(args.rules, 'r', encoding='utf-8') as f:
            rules = json.load(f)

    # 加载自定义分层
    if args.layers and os.path.exists(args.layers):
        with open(args.layers, 'r', encoding='utf-8') as f:
            custom_layers = json.load(f)
            auditor = MSSAuditor(args.path, rules)
            auditor.layers.update(custom_layers)
    else:
        auditor = MSSAuditor(args.path, rules)

    report = auditor.audit()
    print_report(report)

    if args.json:
        save_report_json(report, args.json)


if __name__ == "__main__":
    main()
