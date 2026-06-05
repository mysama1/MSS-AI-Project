#!/usr/bin/env python3
"""
D5-046: MSS 热税剖析器 v1.0
量化代码中的实际热税 — CPU/内存/IO/复杂度 → γ系数
"""
import os, ast, json, time, math
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Dict

@dataclass
class HeatTaxProfile:
    filepath: str
    lines: int = 0
    functions: int = 0
    classes: int = 0
    ast_nodes: int = 0           # AST节点数（复杂度代理）
    max_indent: int = 0          # 最大缩进深度
    nested_loops: int = 0        # 嵌套循环数
    branches: int = 0            # 条件分支数
    imports: int = 0               # 导入数
    string_literals: int = 0     # 字符串字面量（重复信息）
    comments: int = 0            # 注释行

    # 派生指标
    gamma: float = 0.0           # 热税系数 γ
    complexity_per_line: float = 0.0
    nesting_density: float = 0.0
    import_burden: float = 0.0

    def compute_gamma(self):
        """计算热税系数 γ = (nodes × branches × (1+nesting)) / lines"""
        if self.lines == 0:
            return
        # Base complexity
        base = (self.ast_nodes + self.branches * 2) / max(self.lines, 1)
        # Nesting penalty: exp(nesting_density)
        self.nesting_density = self.max_indent / 4
        nest_penalty = math.exp(self.nesting_density * 0.5) if self.max_indent > 4 else 1.0
        # Import burden
        self.import_burden = self.imports / max(self.functions, 1)
        # Duplicate information tax
        dup_tax = 1.0 + (self.string_literals / max(self.lines, 1)) * 0.5
        # Comment efficiency (too many comments = low meaning density)
        comment_ratio = self.comments / max(self.lines, 1)
        comment_tax = 1.0 if comment_ratio < 0.3 else 1.0 + (comment_ratio - 0.3) * 2

        self.complexity_per_line = base
        self.gamma = round(base * nest_penalty * self.import_burden * dup_tax * comment_tax, 3)


class HeatTaxProfiler:
    """热税剖析器 — 静态分析Python代码的γ系数"""

    def profile_file(self, filepath: str) -> HeatTaxProfile:
        profile = HeatTaxProfile(filepath=filepath)
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            source = f.read()

        lines = source.split('\n')
        profile.lines = len(lines)
        profile.comments = sum(1 for l in lines if l.strip().startswith('#'))

        # Count string literals (simplified)
        profile.string_literals = source.count('"') // 2 + source.count("'") // 2

        try:
            tree = ast.parse(source)
            profile.ast_nodes = sum(1 for _ in ast.walk(tree))
            profile.functions = sum(1 for n in ast.walk(tree) if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)))
            profile.classes = sum(1 for n in ast.walk(tree) if isinstance(n, ast.ClassDef))
            profile.imports = sum(1 for n in ast.walk(tree) if isinstance(n, (ast.Import, ast.ImportFrom)))
            profile.branches = sum(1 for n in ast.walk(tree) if isinstance(n, (ast.If, ast.While, ast.For, ast.Try, ast.ExceptHandler)))

            # Max indent
            profile.max_indent = max(
                (len(l) - len(l.lstrip()) for l in lines if l.strip()), default=0
            )

            # Nested loops
            profile.nested_loops = self._count_nested_loops(tree)
        except SyntaxError:
            pass

        profile.compute_gamma()
        return profile

    def _count_nested_loops(self, tree: ast.AST) -> int:
        count = 0
        for node in ast.walk(tree):
            if isinstance(node, (ast.For, ast.While)):
                for child in ast.walk(node):
                    if child is not node and isinstance(child, (ast.For, ast.While)):
                        count += 1
                        break
        return count

    def profile_directory(self, root: str) -> List[HeatTaxProfile]:
        profiles = []
        for dirpath, dirs, files in os.walk(root):
            dirs[:] = [d for d in dirs if d not in ('__pycache__','.git','node_modules','unsloth_compiled_cache')]
            for f in files:
                if not f.endswith('.py'): continue
                fp = os.path.join(dirpath, f)
                try:
                    p = self.profile_file(fp)
                    profiles.append(p)
                except: pass
        return profiles


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser(description="MSS Heat Tax Profiler (D5-046)")
    ap.add_argument("target")
    ap.add_argument("--dir", "-d", action="store_true")
    args = ap.parse_args()

    profiler = HeatTaxProfiler()

    if args.dir:
        profiles = profiler.profile_directory(args.target)
        profiles.sort(key=lambda p: -p.gamma)

        # Summary
        avg_gamma = sum(p.gamma for p in profiles) / max(len(profiles), 1)
        total_lines = sum(p.lines for p in profiles)
        total_functions = sum(p.functions for p in profiles)

        print(f"Project: {args.target}")
        print(f"Files: {len(profiles)} | Lines: {total_lines} | Functions: {total_functions}")
        print(f"Avg γ: {avg_gamma:.3f}")
        print(f"\nGamma rating: ", end="")
        if avg_gamma < 0.5: print("OPTIMAL ✅")
        elif avg_gamma < 1.0: print("GOOD 👍")
        elif avg_gamma < 2.0: print("ELEVATED ⚠️")
        elif avg_gamma < 5.0: print("HIGH 🔴")
        else: print("CRITICAL 💀")

        print(f"\nTop 10 Heat Tax Contributors:")
        for p in profiles[:10]:
            print(f"  γ={p.gamma:.3f} | L{p.lines} F{p.functions} N{p.ast_nodes} B{p.branches} I{p.max_indent//4}Lv | {os.path.basename(p.filepath)}")

        print(f"\nBottom 5 (Most Efficient):")
        for p in sorted(profiles, key=lambda x: x.gamma)[:5]:
            print(f"  γ={p.gamma:.3f} | L{p.lines} F{p.functions} | {os.path.basename(p.filepath)}")
    else:
        p = profiler.profile_file(args.target)
        print(f"File: {os.path.basename(args.target)}")
        print(f"Lines: {p.lines} | Functions: {p.functions} | Classes: {p.classes}")
        print(f"AST nodes: {p.ast_nodes} | Branches: {p.branches}")
        print(f"Max indent: {p.max_indent} ({p.max_indent//4} levels)")
        print(f"Nested loops: {p.nested_loops}")
        print(f"Complexity/line: {p.complexity_per_line:.3f}")
        print(f"Nesting density: {p.nesting_density:.3f}")
        print(f"Import burden: {p.import_burden:.3f}")
        print(f"\n🔥 γ = {p.gamma:.3f} | ", end="")
        if p.gamma < 1: print("LOW HEAT TAX ✅")
        elif p.gamma < 3: print("MODERATE ⚠️")
        elif p.gamma < 10: print("HIGH 🔴")
        else: print("THERMAL RUNAWAY 💀")