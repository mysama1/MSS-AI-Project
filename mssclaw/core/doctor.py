"""
mssclaw doctor — 环境自检命令

检查运行mssclaw所需的全部依赖:
  - Python版本
  - pip包状态
  - Ollama服务 + 模型
  - Julia + Catlab
  - 路径映射
  - 磁盘空间

H649 Quick Win #3
"""
import sys
import os
import subprocess
import platform
import shutil
from pathlib import Path


def check_python() -> dict:
    """Python环境检查."""
    return {
        "version": sys.version,
        "executable": sys.executable,
        "platform": platform.platform(),
        "arch": platform.machine(),
    }


def check_pip_packages() -> dict:
    """关键pip包检查 (通过实际import测试)."""
    modules = {
        "pytest": "测试框架",
        "requests": "HTTP客户端",
        "flask": "Web服务 (skill_api)",
        "fastapi": "D2预警服务",
    }
    optional = {"fastapi"}

    result = {"ok": {}, "missing": {}, "mss_agent": False}

    # Check MSS agent
    try:
        import mssclaw
        result["mss_agent"] = True
        result["ok"]["mssclaw"] = {"version": getattr(mssclaw, '__version__', 'dev'), "description": "MSS核心包"}
    except ImportError:
        result["missing"]["mssclaw"] = "MSS核心包 (not importable)"

    for mod_name, desc in modules.items():
        try:
            mod = __import__(mod_name)
            version = getattr(mod, '__version__', 'installed')
            result["ok"][mod_name] = {"version": str(version), "description": desc}
        except ImportError:
            if mod_name not in optional:
                result["missing"][mod_name] = desc

    return result


def check_ollama() -> dict:
    """Ollama服务+模型检查."""
    result = {"service": False, "models": [], "mss_models": [], "error": None}
    try:
        r = subprocess.run(["ollama", "list"], capture_output=True, text=True, timeout=10)
        if r.returncode == 0:
            result["service"] = True
            for line in r.stdout.strip().split('\n')[1:]:  # skip header
                parts = line.split()
                if parts:
                    name = parts[0]
                    result["models"].append(name)
                    if "mss" in name.lower():
                        result["mss_models"].append(name)
        else:
            result["error"] = r.stderr.strip()
    except FileNotFoundError:
        result["error"] = "ollama not found in PATH"
    except subprocess.TimeoutExpired:
        result["error"] = "ollama list timed out"
    except Exception as e:
        result["error"] = str(e)
    return result


def check_julia() -> dict:
    """Julia + Catlab检查."""
    result = {"installed": False, "version": None, "catlab": False}

    # Check common Julia paths
    candidates = [
        r"E:\AI_Workspace\Tools\Julia-1.11.5\bin\julia.exe",
        r"C:\Julia-1.11\bin\julia.exe",
    ]
    julia_exe = None
    for c in candidates:
        if os.path.exists(c):
            julia_exe = c
            break

    if not julia_exe:
        julia_exe = shutil.which("julia")

    if julia_exe:
        result["installed"] = True
        result["path"] = julia_exe
        try:
            r = subprocess.run([julia_exe, "--version"], capture_output=True, text=True, timeout=10)
            result["version"] = r.stdout.strip()
            # Check Catlab
            r2 = subprocess.run(
                [julia_exe, "-e", 'using Catlab; println("Catlab v$(pkgversion(Catlab))")'],
                capture_output=True, text=True, timeout=30
            )
            if "Catlab v" in r2.stdout:
                result["catlab"] = True
                result["catlab_version"] = r2.stdout.strip()
        except Exception as e:
            result["error"] = str(e)

    return result


def check_disk() -> dict:
    """磁盘空间检查."""
    result = {}
    for drive_letter in ['E:', 'C:']:
        try:
            usage = shutil.disk_usage(drive_letter + '\\')
            result[drive_letter] = {
                "total_gb": round(usage.total / (1024**3), 1),
                "used_gb": round(usage.used / (1024**3), 1),
                "free_gb": round(usage.free / (1024**3), 1),
                "pct_free": round(usage.free / usage.total * 100, 1),
            }
        except:
            pass
    return result


def check_paths() -> dict:
    """关键路径检查."""
    checks = {
        "project_root": r"E:\AI_Workspace\MSS-AI\project",
        "kb_dir": r"E:\AI_Workspace\MSS-AI\project\kb",
        "data_skills": r"E:\QClaw-Data\skills",
        "mssclaw_core": r"E:\AI_Workspace\MSS-AI\project\mssclaw\core",
    }
    result = {}
    for name, path in checks.items():
        result[name] = {
            "path": path,
            "exists": os.path.exists(path),
        }
        if result[name]["exists"]:
            # count items
            try:
                items = len(os.listdir(path))
                result[name]["items"] = items
            except:
                pass
    return result


def run_diagnosis() -> dict:
    """完整诊断."""
    results = {
        "python": check_python(),
        "packages": check_pip_packages(),
        "ollama": check_ollama(),
        "julia": check_julia(),
        "disk": check_disk(),
        "paths": check_paths(),
    }

    # 计算健康分数
    ok_count = 0
    total_checks = 0

    total_checks += 1; ok_count += 1  # python always ok (we're running)
    pkgs = results["packages"]
    total_checks += len(pkgs["ok"]) + len(pkgs["missing"])
    ok_count += len(pkgs["ok"])
    total_checks += 1; ok_count += int(results["ollama"]["service"])
    total_checks += 1; ok_count += int(results["ollama"]["mss_models"] != [])
    total_checks += 1; ok_count += int(results["julia"]["installed"])
    total_checks += 1; ok_count += int(results["julia"]["catlab"])
    for p in results["paths"].values():
        total_checks += 1; ok_count += int(p["exists"])
    for d in results["disk"].values():
        total_checks += 1; ok_count += int(d["free_gb"] > 5)

    results["health"] = {
        "score": round(ok_count / max(total_checks, 1), 3),
        "passed": ok_count,
        "total": total_checks,
        "verdict": "🟢 all clear" if ok_count == total_checks else
                   "🟡 some issues" if ok_count / total_checks > 0.7 else
                   "🔴 needs attention",
    }

    return results


def format_diagnosis(results: dict) -> str:
    """格式化为人类可读输出."""
    lines = ["=== mssclaw doctor ===", ""]

    # Python
    py = results["python"]
    lines.append(f"Python: {py['version'].split()[0]} ({py['arch']})")
    lines.append(f"  Path: {py['executable']}")
    lines.append("")

    # Packages
    pkgs = results["packages"]
    lines.append("Packages:")
    for name, info in sorted(pkgs["ok"].items()):
        lines.append(f"  ✅ {name} {info['version']} — {info['description']}")
    for name, desc in sorted(pkgs["missing"].items()):
        lines.append(f"  ❌ {name} MISSING — {desc} (pip install {name})")
    lines.append("")

    # Ollama
    oll = results["ollama"]
    if oll["service"]:
        lines.append(f"Ollama: ✅ running ({len(oll['models'])} models)")
        if oll["mss_models"]:
            for m in oll["mss_models"]:
                lines.append(f"  ✅ {m}")
        else:
            lines.append(f"  ⚠️  No MSS models found")
        other = [m for m in oll["models"] if "mss" not in m.lower()]
        if other:
            lines.append(f"  Other: {', '.join(other[:5])}" + ("..." if len(other) > 5 else ""))
    else:
        lines.append(f"Ollama: ❌ {oll.get('error', 'not running')}")
    lines.append("")

    # Julia
    jul = results["julia"]
    if jul["installed"]:
        lines.append(f"Julia: ✅ {jul.get('version', '')}")
        lines.append(f"  Path: {jul.get('path', '')}")
        lines.append(f"  Catlab: {'✅ ' + jul.get('catlab_version', '') if jul['catlab'] else '❌ not installed'}")
    else:
        lines.append(f"Julia: ❌ not found")
    lines.append("")

    # Disk
    lines.append("Disk:")
    for drive, info in results["disk"].items():
        status = "✅" if info["free_gb"] > 10 else "⚠️" if info["free_gb"] > 5 else "🔴"
        lines.append(f"  {status} {drive} {info['free_gb']}GB free / {info['total_gb']}GB total ({info['pct_free']}%)")
    lines.append("")

    # Paths
    lines.append("Paths:")
    for name, info in results["paths"].items():
        status = "✅" if info["exists"] else "❌"
        extra = f" ({info.get('items', '?')} items)" if info["exists"] else ""
        lines.append(f"  {status} {name}: {info['path']}{extra}")
    lines.append("")

    # Health
    h = results["health"]
    lines.append(f"Health: {h['verdict']} ({h['passed']}/{h['total']} checks passed, score={h['score']})")

    return '\n'.join(lines)


if __name__ == "__main__":
    results = run_diagnosis()
    print(format_diagnosis(results))
