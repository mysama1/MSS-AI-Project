"""
heat_tax_self_scan v1.0 — MSS自反式热税扫描

对mssclaw自身代码库做三层热税审计:
  L0: 物理浪费 (文件大小、冗余import、孤儿模块)
  L1: 逻辑浪费 (死代码、未使用函数、重复代码)
  L2: 意义浪费 (TODO积压、注释掉的代码、假模式)

H649 Quick Win #1
"""
import os
import ast
import json
from collections import defaultdict
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent


def scan_l0_physical(root: Path) -> dict:
    """L0: 物理热税 — 文件大小分布、import冗余、孤儿模块."""
    files = []
    total_size = 0
    ext_counts = defaultdict(int)
    ext_sizes = defaultdict(int)

    for f in root.rglob("*"):
        if f.is_file() and not any(p in f.parts for p in ['.git', '__pycache__', '.egg-info', 'node_modules', '.next', 'dist', 'build']):
            size = f.stat().st_size
            ext = f.suffix or 'no_ext'
            ext_counts[ext] += 1
            ext_sizes[ext] += size
            total_size += size
            files.append({"path": str(f.relative_to(root)), "size": size})

    # 找出最大的文件(top 10)
    files.sort(key=lambda x: x["size"], reverse=True)

    # 检查孤儿模块 — 没有被import过的core模块
    core_dir = root / "mssclaw" / "core"
    if core_dir.exists():
        all_core = {f.stem for f in core_dir.glob("*.py") if not f.name.startswith("_")}
        imported = set()
        for py_file in root.rglob("*.py"):
            if '.git' in str(py_file):
                continue
            try:
                content = py_file.read_text(encoding='utf-8', errors='ignore')
                for name in all_core:
                    if name in content and py_file.stem != name:
                        imported.add(name)
            except:
                pass
        orphans = all_core - imported - {'cli', '__init__'}
    else:
        orphans = set()

    return {
        "total_size_kb": round(total_size / 1024, 1),
        "total_files": len(files),
        "ext_distribution": {k: {"count": v, "size_kb": round(ext_sizes[k]/1024, 1)}
                            for k, v in sorted(ext_counts.items(), key=lambda x: -x[1])},
        "top10_largest": [{"path": f["path"], "size_kb": round(f["size"]/1024, 1)}
                         for f in files[:10]],
        "orphan_core_modules": sorted(orphans),
        "orphan_count": len(orphans)
    }


def scan_l1_logical(root: Path) -> dict:
    """L1: 逻辑热税 — 死代码、注释掉的代码块、重复模式."""
    py_files = list(root.rglob("*.py"))
    py_files = [f for f in py_files if not any(p in f.parts for p in ['.git', '__pycache__', '.egg-info'])]

    total_lines = 0
    comment_lines = 0
    blank_lines = 0
    code_lines = 0
    todo_count = 0
    fixme_count = 0
    commented_code_lines = 0  # 被注释掉的代码行 (heuristic)

    for f in py_files:
        try:
            lines = f.read_text(encoding='utf-8', errors='ignore').split('\n')
        except:
            continue
        total_lines += len(lines)

        in_docstring = False
        for line in lines:
            stripped = line.strip()

            if not stripped:
                blank_lines += 1
                continue

            # 注释
            if stripped.startswith('#'):
                comment_lines += 1
                # 检测被注释掉的代码
                if any(kw in stripped.lower() for kw in ['def ', 'class ', 'import ', 'return ', 'if ', 'for ']):
                    commented_code_lines += 1
                if 'todo' in stripped.lower():
                    todo_count += 1
                if 'fixme' in stripped.lower():
                    fixme_count += 1
                continue

            # 文档字符串
            if stripped.startswith('"""') or stripped.startswith("'''"):
                in_docstring = not in_docstring
                comment_lines += 1
                continue

            if in_docstring:
                comment_lines += 1
                continue

            code_lines += 1

            # 代码行中的TODO
            if 'todo' in stripped.lower() and stripped.startswith('#'):
                pass  # already counted
            elif '# todo' in stripped.lower():
                todo_count += 1

    return {
        "total_lines": total_lines,
        "code_lines": code_lines,
        "comment_lines": comment_lines,
        "blank_lines": blank_lines,
        "comment_ratio": round(comment_lines / max(total_lines, 1), 3),
        "commented_out_code": commented_code_lines,
        "todo_count": todo_count,
        "fixme_count": fixme_count,
        "code_to_comment_ratio": round(code_lines / max(comment_lines, 1), 1),
    }


def scan_l2_meaning(root: Path) -> dict:
    """L2: 意义热税 — 未闭合的TODO、假模式、废弃但未删除的代码."""
    suspicious_patterns = []

    # 检测常见反模式
    anti_patterns = {
        "except: pass": "bare except pass — 吞掉错误",
        "except Exception: pass": "broad except pass — 静默失败",
        "# TODO": "未闭合的TODO",
        "# FIXME": "未修复的FIXME",
        "# HACK": "临时方案未清理",
        "print(": "调试print未移除 (生产代码中)",
    }

    for py_file in root.rglob("*.py"):
        if any(p in py_file.parts for p in ['.git', '__pycache__', '.egg-info']):
            continue
        try:
            content = py_file.read_text(encoding='utf-8', errors='ignore')
            lines = content.split('\n')
        except:
            continue

        for i, line in enumerate(lines, 1):
            for pattern, desc in anti_patterns.items():
                if pattern in line and not line.strip().startswith('#'):
                    # skip docstrings and known good cases
                    if pattern == "print(" and ("logging" in str(py_file).lower() or "demo" in str(py_file).lower()):
                        continue
                    suspicious_patterns.append({
                        "file": str(py_file.relative_to(root)),
                        "line": i,
                        "pattern": pattern,
                        "issue": desc
                    })

    # 非关键模式只保留摘要
    pattern_counts = defaultdict(int)
    file_hits = defaultdict(int)
    for sp in suspicious_patterns:
        pattern_counts[sp["pattern"]] += 1
        file_hits[sp["file"]] += 1

    # 只返回需要关注的 (print排除, 只留实质性的)
    substantive = [sp for sp in suspicious_patterns
                   if sp["pattern"] != "print("]

    return {
        "total_suspicious": len(substantive),
        "by_pattern": dict(pattern_counts),
        "top_files_by_hits": sorted(file_hits.items(), key=lambda x: -x[1])[:10],
        "high_priority": [sp for sp in substantive
                         if sp["pattern"] in ["except: pass", "except Exception: pass"]][:20],
        "todo_backlog": pattern_counts.get("# TODO", 0) + pattern_counts.get("# FIXME", 0) + pattern_counts.get("# HACK", 0),
    }


def run_self_scan(root: Path = None) -> dict:
    """执行完整自反式热税扫描."""
    root = root or PROJECT_ROOT

    l0 = scan_l0_physical(root)
    l1 = scan_l1_logical(root)
    l2 = scan_l2_meaning(root)

    # 计算综合热税分数 (0=最优, 1=最差)
    heat_scores = {
        "L0_physical": round(
            0.3 * (l0["orphan_count"] / max(len(list((root/"mssclaw"/"core").glob("*.py"))), 1)) +
            0.3 * (l0["top10_largest"][0]["size_kb"] / 1000 if l0["top10_largest"] else 0) +
            0.4 * min(l0["total_size_kb"] / 10000, 1.0), 3
        ),
        "L1_logical": round(
            0.4 * (l1["commented_out_code"] / max(l1["total_lines"], 1) * 100) +
            0.3 * (1 - min(l1["code_to_comment_ratio"] / 5, 1.0)) +
            0.3 * min((l1["todo_count"] + l1["fixme_count"]) / 100, 1.0), 3
        ),
        "L2_meaning": round(
            0.5 * min(l2["total_suspicious"] / 50, 1.0) +
            0.3 * min(l2["todo_backlog"] / 30, 1.0) +
            0.2 * min(l2["high_priority_silent_failures"] / 10 if "high_priority_silent_failures" in l2 else 0, 1.0), 3
        ),
    }
    heat_scores["overall"] = round(
        heat_scores["L0_physical"] * 0.15 +
        heat_scores["L1_logical"] * 0.25 +
        heat_scores["L2_meaning"] * 0.60, 3
    )

    return {
        "project": str(root),
        "timestamp": __import__('datetime').datetime.now().isoformat(),
        "L0_physical": l0,
        "L1_logical": l1,
        "L2_meaning": l2,
        "heat_scores": heat_scores,
        "verdict": "🟢 healthy" if heat_scores["overall"] < 0.2 else
                   "🟡 moderate" if heat_scores["overall"] < 0.5 else
                   "🔴 critical",
    }


if __name__ == "__main__":
    result = run_self_scan()
    print(json.dumps(result, indent=2, ensure_ascii=False))
