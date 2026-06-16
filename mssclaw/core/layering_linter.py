"""
MSS Layering Linter — Theorem L1 Computable Check.

从mssclaw源码自动建耦合图→计算三层条件→输出违规报告。

Theorem L1 (H626): 合法分层需满足
  C1: S-closure (稳定子不裂)
  C2: Στ(E_ij) < Θ (跨层热税可偿)
  C3: 每层Si非空 (子场闭合, 非K3抽屉)

用法:
    mssclaw lint --layering
"""
from __future__ import annotations
import ast, os, json
from pathlib import Path
from collections import defaultdict
from typing import Dict, List, Set, Tuple


class LayeringLinter:
    """Theorem L1 可计算检查器."""

    # 已知的稳定子(不可违反的硬约束) — 来自H593三层范畴
    KNOWN_STABLES = {
        "L3_KB": ["典源信誉不可篡改", "H-ID唯一性", "引用完整性"],
        "L2_CORE": ["六公理锚定(A1-A6)", "热税预算(A3)", "Δ>0开放度(A6)", "规范场(A5)"],
        "L1_AGENT": ["对话梯度连续性", "工作记忆一致性", "投影保真度η"],
        "L0_SHELL": [],  # ← 如果为空, C3判定: 不是层, 是K3抽屉
    }

    # 跨层热税预算 (A3分配) — 未列出的层对默认budget=0.5
    CROSS_LAYER_BUDGET = {
        ("L3_KB", "L2_CORE"): 0.05,
        ("L2_CORE", "L1_AGENT"): 0.30,  # 推理投影 — medium tau, 提高预算
        ("L1_AGENT", "L0_SHELL"): 0.10,
    }

    def __init__(self, project_root: str = None):
        self.root = Path(project_root or os.getcwd())
        self.core_dir = self.root / "mssclaw" / "core"
        self.graph: Dict[str, Set[Tuple[str, float]]] = defaultdict(set)  # 耦合图
        self.layer_map: Dict[str, str] = {}  # 节点→层
        self.violations: List[dict] = []

    def build_graph(self):
        """从源码建耦合图."""
        if not self.core_dir.exists():
            return

        for py_file in self.core_dir.glob("*.py"):
            if py_file.name.startswith("_"):
                continue
            try:
                tree = ast.parse(py_file.read_text(encoding="utf-8"))
            except Exception:
                continue

            module_name = py_file.stem
            imports = set()
            calls = set()

            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        imports.add(alias.name.split(".")[-1])
                elif isinstance(node, ast.ImportFrom):
                    if node.module:
                        mod = node.module.split(".")[-1]
                        imports.add(mod)
                elif isinstance(node, ast.Call):
                    if isinstance(node.func, ast.Attribute):
                        calls.add(node.func.attr)
                    elif isinstance(node.func, ast.Name):
                        calls.add(node.func.id)

            # 导入边: weight=0.5 (module依赖)
            for imp in imports:
                self.graph[module_name].add((imp, 0.5))
                self.graph[imp].add((module_name, 0.5))

            # 稳定子边: 检测公理引用
            content = py_file.read_text(encoding="utf-8").lower()
            if any(kw in content for kw in ["heat_tax", "热税", "a3"]):
                self.graph[module_name].add(("A3_heat_tax", 0.9))
            if any(kw in content for kw in ["delta", "意义开放", "Δ"]):
                self.graph[module_name].add(("A6_delta", 0.8))
            if any(kw in content for kw in ["normative_field", "规范场", "stable_edge", "稳定子"]):
                self.graph[module_name].add(("A5_norm_field", 0.9))

        # 手动标注已知层
        self._classify_layers()

    def _classify_layers(self):
        """标注模块到MSS层的映射."""
        # L2 Core: 公理实现
        l2_modules = {"heat_tax", "heat_tax_system", "heat_tax_fuse", "delta", "delta_monitor",
                       "delta_quick_audit", "normative_field", "norm_shield_bridge",
                       "hallucination_shield", "mss_evaluator", "cognitive_framework",
                       "l2_bridge", "agent", "guardian_engine", "molting_engine"}
        # L1 Agent: 运行时
        l1_modules = {"agent_server", "agent_chat", "agent_pipeline", "agent_orchestrator",
                       "semantic_styler", "stream_styler", "smart_router", "deep_fold",
                       "mss_shell", "mss_swarm"}
        # L3 KB: 知识
        l3_modules = {"library_manager", "model_catalog", "model_library"}
        # L0 Shell: 纯投影 (应无状态)
        l0_modules = {"dashboard", "live_demo", "demo"}

        for node in self.graph:
            if node in l2_modules:
                self.layer_map[node] = "L2_CORE"
            elif node in l1_modules:
                self.layer_map[node] = "L1_AGENT"
            elif node in l3_modules:
                self.layer_map[node] = "L3_KB"
            elif node in l0_modules:
                self.layer_map[node] = "L0_SHELL"
            else:
                self.layer_map[node] = "unclassified"

    def check_C1(self) -> List[dict]:
        """C1: S-closure — 稳定子是否被切层? """
        violations = []
        for layer, stables in self.KNOWN_STABLES.items():
            if not stables:
                continue
            layer_nodes = {n for n, l in self.layer_map.items() if l == layer}
            if not layer_nodes:
                continue
            for stable in stables:
                stable_key = stable.split("(")[0].replace(" ", "_")
                # 检查引用此稳定子的节点是否全部在对应层内
                ref_nodes = {n for n in self.graph if f"A{stable_key[-1] if stable_key else ''}" in str(self.graph[n]) or stable_key in str(self.graph[n])}
                ref_nodes &= set(self.graph.keys())
                if not ref_nodes:
                    continue
                outside = ref_nodes - layer_nodes
                if outside:
                    violations.append({
                        "condition": "C1",
                        "severity": "critical",
                        "stable": stable,
                        "layer": layer,
                        "outside_nodes": list(outside),
                        "message": f"稳定子'{stable}'被切层: 引用节点{outside}不在{layer}内"
                    })
        return violations

    def check_C2(self) -> List[dict]:
        """C2: 跨层热税可偿."""
        violations = []
        cross_edges: Dict[Tuple[str, str], float] = defaultdict(float)

        for src, edges in self.graph.items():
            src_layer = self.layer_map.get(src, "unclassified")
            for dst, weight in edges:
                dst_layer = self.layer_map.get(dst, "unclassified")
                if src_layer != dst_layer and src_layer != "unclassified" and dst_layer != "unclassified":
                    key = tuple(sorted([src_layer, dst_layer]))
                    cross_edges[key] += 0.1 * weight  # τ ≈ weight/10 per edge

        for (l1, l2), total_tau in cross_edges.items():
            budget = self.CROSS_LAYER_BUDGET.get((l1, l2), 0.5)  # 未列出的层对默认0.5
            if total_tau > budget:
                violations.append({
                    "condition": "C2",
                    "severity": "warning",
                    "layers": f"{l1}↔{l2}",
                    "total_tau": round(total_tau, 3),
                    "budget": budget,
                    "message": f"跨层热税超预算: {l1}↔{l2} τ={total_tau:.3f} > Θ={budget}"
                })

        return violations

    def check_C3(self) -> List[dict]:
        """C3: 子场闭合 — 每层必携自己的S_i."""
        violations = []
        for layer, stables in self.KNOWN_STABLES.items():
            layer_nodes = {n for n, l in self.layer_map.items() if l == layer}
            if not stables and layer_nodes:
                violations.append({
                    "condition": "C3",
                    "severity": "critical",
                    "layer": layer,
                    "node_count": len(layer_nodes),
                    "message": f"层'{layer}'无稳定子(S_i=∅) — 按L1定理C3, 这不是MSS合法层, 是K3抽屉"
                })
        return violations

    def lint(self) -> dict:
        """运行完整L1检查."""
        self.build_graph()

        report = {
            "theorem": "L1 (H626 v0.2)",
            "graph": {
                "nodes": len(self.graph),
                "edges": sum(len(v) for v in self.graph.values()),
                "layers": {k: len(v) for k, v in self._layer_distribution().items()},
            },
            "C1_violations": self.check_C1(),
            "C2_violations": self.check_C2(),
            "C3_violations": self.check_C3(),
            "verdict": "PASS" if not (self.check_C1() or self.check_C3()) else "VIOLATIONS FOUND",
        }

        # Also check the HTML frontend
        webui = self.root / "mssclaw" / "webui" / "index.html"
        if webui.exists():
            try:
                content = webui.read_text(encoding="utf-8")
            except UnicodeDecodeError:
                content = webui.read_text(encoding="utf-8", errors="ignore")
            has_local_storage = "localStorage.setItem" in content or "localStorage.getItem" in content
            if has_local_storage:
                report.setdefault("Shell_audit", {})
                report["Shell_audit"]["localStorage"] = "VIOLATION — Shell持有独立状态(双源真值)"

        return report

    def _layer_distribution(self) -> Dict[str, List[str]]:
        """每层的节点列表."""
        dist = defaultdict(list)
        for node, layer in self.layer_map.items():
            dist[layer].append(node)
        return dict(dist)

    def report(self) -> str:
        """生成可读报告."""
        r = self.lint()
        lines = ["=" * 60, "Theorem L1 — Layering Legitimacy Report", "=" * 60]
        lines.append(f"Graph: {r['graph']['nodes']} nodes, {r['graph']['edges']} edges")
        lines.append(f"Layers: {r['graph']['layers']}")
        lines.append("")

        for cond in ["C1", "C2", "C3"]:
            viols = r.get(f"{cond}_violations", [])
            if viols:
                lines.append(f"❌ {cond} Violations ({len(viols)}):")
                for v in viols:
                    lines.append(f"  [{v['severity']}] {v['message']}")
            else:
                lines.append(f"✅ {cond}: PASS")

        if "Shell_audit" in r:
            lines.append(f"\n🔍 Shell Audit:")
            for k, v in r["Shell_audit"].items():
                lines.append(f"  {k}: {v}")

        lines.append(f"\n📋 Verdict: {r['verdict']}")
        return "\n".join(lines)


# ═══ CLI ═══
def cmd_lint(args_rest):
    """CLI入口: mssclaw lint --layering"""
    if not args_rest or "--layering" not in args_rest:
        print("mssclaw lint --layering  (Theorem L1 check)")
        return

    linter = LayeringLinter()
    print(linter.report())
