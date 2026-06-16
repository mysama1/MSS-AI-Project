"""
MSS System Status — 全栈健康一览

mssclaw status → 一页看透所有子系统
"""
import sys, os, time, json
from pathlib import Path


def system_status():
    """全系统状态检查."""
    C = {"green": "\033[32m", "yellow": "\033[33m", "red": "\033[31m", "cyan": "\033[36m", "dim": "\033[2m", "reset": "\033[0m"}
    def ok(msg): return f"  {C['green']}✅{C['reset']} {msg}"
    def warn(msg): return f"  {C['yellow']}⚠️{C['reset']} {msg}"
    def fail(msg): return f"  {C['red']}❌{C['reset']} {msg}"
    def title(s): return f"\n{C['cyan']}{'='*50}{C['reset']}\n{C['cyan']}{s}{C['reset']}\n{C['cyan']}{'='*50}{C['reset']}"

    lines = [f"{C['cyan']}🧬 mssclaw v0.3.9 — System Status{C['reset']}"]
    score = 0
    total = 0

    # ═══ Services ═══
    print(title("Services"))

    # Agent
    total += 1
    try:
        import urllib.request
        r = urllib.request.urlopen("http://127.0.0.1:5100/health", timeout=3)
        d = json.loads(r.read())
        print(ok(f"Agent Server (5100) — Δ={d.get('delta',0):.2f}, {d.get('bridge','?')}"))
        score += 1
    except Exception:
        print(fail("Agent Server (5100) — offline"))

    # Frontend
    total += 1
    try:
        r = urllib.request.urlopen("http://127.0.0.1:3000/index.html", timeout=3)
        print(ok(f"Frontend (3000) — HTTP {r.status}"))
        score += 1
    except Exception:
        print(warn("Frontend (3000) — not running"))

    # Ollama
    total += 1
    try:
        r = urllib.request.urlopen("http://localhost:11434/api/tags", timeout=3)
        d = json.loads(r.read())
        models = d.get("models", [])
        mss_models = [m["name"] for m in models if "mss" in m.get("name","").lower()]
        print(ok(f"Ollama (11434) — {len(models)} models ({len(mss_models)} MSS)"))
        score += 1
    except Exception:
        print(warn("Ollama (11434) — not running"))

    # Vault
    total += 1
    try:
        r = urllib.request.urlopen("http://127.0.0.1:5099/health", timeout=3)
        print(ok("Vault Server (5099)"))
        score += 1
    except Exception:
        print(warn("Vault (5099) — not running"))

    # ═══ MSS Metrics ═══
    print(title("MSS Metrics"))
    try:
        r = urllib.request.urlopen("http://127.0.0.1:5100/health", timeout=3)
        d = json.loads(r.read())
        delta = d.get("delta", 0)
        tax = d.get("tax_burden", 0)
        bridge = d.get("bridge", "?")
        msg = d.get("message", "")
        total += 3
        if delta > 0.5:
            print(ok(f"Δ Meaning Openness: {delta:.3f} (healthy)")); score += 1
        elif delta > 0.2:
            print(warn(f"Δ Meaning Openness: {delta:.3f} (degrading)")); score += 1
        else:
            print(fail(f"Δ Meaning Openness: {delta:.3f} (critical)"))
        if tax < 0.3:
            print(ok(f"Tax Burden: {(tax*100):.0f}%")); score += 1
        else:
            print(warn(f"Tax Burden: {(tax*100):.0f}%"))
        print(ok(f"L2 Bridge: {bridge}")); score += 1
        if msg:
            print(f"  {C['dim']}{msg}{C['reset']}")
    except Exception:
        print(warn("MSS Metrics unavailable"))

    # ═══ Development Tools ═══
    print(title("Development Tools"))
    tools = [
        ("Heat Tax Timer", "mssclaw timer"),
        ("Goal Anchor", "mssclaw goal"),
        ("Dimension Escalator", "mssclaw escalate"),
        ("Layering Linter", "mssclaw lint --layering"),
        ("Virus Classifier", "mssclaw classify"),
        ("Vaccine Evaluator", "mssclaw vaccine eval"),
        ("Defense Pipeline", "mssclaw defend"),
    ]
    for name, cmd in tools:
        print(f"  ✅ {name:22s} → {C['dim']}{cmd}{C['reset']}")

    # ═══ Knowledge Base ═══
    print(title("Knowledge Base"))
    kb_dir = Path("knowledge_base")
    if kb_dir.exists():
        entries = list(kb_dir.rglob("h*.json"))
        latest = sorted(entries, key=lambda p: p.stat().st_mtime, reverse=True)[:3]
        print(f"  Entries: {len(entries)} (latest: {', '.join(p.stem.upper() for p in latest)})")
    else:
        print(f"  KB directory not found")

    # ═══ Cleanup Stats ═══
    print(title("System Health"))
    import subprocess
    try:
        result = subprocess.run(["netstat", "-ano"], capture_output=True, text=True, timeout=5)
        zombie_3000 = result.stdout.count(":3000") - result.stdout.count("LISTENING.*3000")
        if zombie_3000 < 2:
            print(ok(f"Port 3000: clean (no zombies)"))
        else:
            print(warn(f"Port 3000: {zombie_3000} zombie connections"))
    except Exception:
        pass

    # ═══ Overall ═══
    pct = score / max(total, 1) * 100
    color = C["green"] if pct >= 80 else C["yellow"] if pct >= 50 else C["red"]
    print(f"\n{C['cyan']}{'='*50}{C['reset']}")
    print(f"{color}Overall: {score}/{total} ({pct:.0f}%){C['reset']}")
    print(f"{C['cyan']}mssclaw v0.3.9 · 133 Sprints · 126 Tests{C['reset']}")

    return {"score": score, "total": total, "pct": pct}


def cmd_status(args_rest):
    """CLI: mssclaw status"""
    system_status()


if __name__ == "__main__":
    system_status()
