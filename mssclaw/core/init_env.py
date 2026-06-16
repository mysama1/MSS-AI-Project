"""mssclaw init - 一键环境初始化."""
import sys, os, subprocess, shutil, time
from pathlib import Path


def init_environment():
    """一键初始化 mssclaw 环境."""
    C = {"green": "\033[32m", "cyan": "\033[36m", "yellow": "\033[33m", "red": "\033[31m", "dim": "\033[2m", "reset": "\033[0m"}
    def ok(msg): print(f"  {C['green']}✅{C['reset']} {msg}")
    def warn(msg): print(f"  {C['yellow']}⚠️{C['reset']} {msg}")
    def fail(msg): print(f"  {C['red']}❌{C['reset']} {msg}")
    def step(n, label): print(f"{C['cyan']}Step {n}: {label}{C['reset']}")

    print(f"{C['cyan']}mssclaw v0.3.0 — 环境初始化{C['reset']}")

    # Step 1: Check Python
    step(1, "Python version")
    py_ver = sys.version_info
    if py_ver >= (3, 10):
        ok(f"Python {py_ver.major}.{py_ver.minor}.{py_ver.micro}")
    else:
        fail(f"Python {py_ver.major}.{py_ver.minor} (< 3.10 required)")
        return

    # Step 2: Check Ollama
    step(2, "Ollama")
    ollama_ok = False
    try:
        import requests
        r = requests.get("http://localhost:11434/api/tags", timeout=5)
        if r.status_code == 200:
            models = r.json().get("models", [])
            ok(f"Ollama running ({len(models)} models)")
            ollama_ok = True
        else:
            fail(f"Ollama returned {r.status_code}")
    except Exception:
        fail("Ollama not running. Install from https://ollama.com")
        print(f"    {C['yellow']}Ollama 不是必须的，但推荐安装。跳过模型下载。{C['reset']}")

    # Step 3: Pull recommended models
    if ollama_ok:
        step(3, "Model check")
        recommended = ["qwen2.5:7b", "phi3:mini"]
        missing = []
        for model in recommended:
            found = any(m.get("name", "") == model for m in models)
            if found:
                ok(f"{model} ready")
            else:
                missing.append(model)

        for model in missing:
            print(f"  Pulling {model}...", end=" ", flush=True)
            try:
                subprocess.run(["ollama", "pull", model], check=True, capture_output=True, timeout=120)
                ok(f"{model} installed")
            except Exception:
                warn(f"Cannot pull {model} (skip)")

    # Step 4: Create vault
    step(4, "Vault")
    vault_dir = Path.home() / ".mssclaw"
    vault_dir.mkdir(exist_ok=True)
    vault_db = vault_dir / "vault.db"
    if vault_db.exists():
        ok("Vault exists")
    else:
        try:
            sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
            from mssclaw.core.credential_vault import CredentialVault
            v = CredentialVault()
            ok("Vault created")
        except Exception as e:
            warn(f"Vault init: {e}")

    # Step 5: Create config
    step(5, "Config")
    config_dir = vault_dir
    config_file = config_dir / "config.yaml"
    if not config_file.exists():
        config = {
            "version": "0.3.0",
            "ollama": {"host": "http://localhost:11434"},
            "default_model": "qwen2.5:7b",
            "vault": {"db_path": str(vault_db)},
            "logging": {"level": "INFO"},
        }
        config_file.write_text(
            "# mssclaw configuration\n" +
            "\n".join(f"{k}: {v}" for k, v in config.items()) +
            "\n"
        )
        ok("config.yaml created")
    else:
        ok("Config exists")

    # Step 6: Quick health check
    step(6, "Health check")
    issues = 0
    try:
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
        from mssclaw.core.agent import MSSAgent
        from mssclaw.core.llm_backend import create_backend
        if ollama_ok:
            agent = MSSAgent("health_check", llm=create_backend("auto"))
            ok("Agent backend OK")
        else:
            warn("Agent: Ollama not available")
            issues += 1

        from mssclaw.core.credential_vault import CredentialVault
        v = CredentialVault()
        ok("Vault OK")
    except Exception as e:
        warn(f"Health: {e}")
        issues += 1

    # Summary
    print(f"\n{C['green']}{'='*40}{C['reset']}")
    if issues == 0:
        print(f"{C['green']}✅ mssclaw ready!{C['reset']}")
        print(f"  Try: mssclaw chat")
        print(f"  Try: mssclaw demo")
    else:
        print(f"{C['yellow']}⚠️  mssclaw initialized with {issues} warnings{C['reset']}")
        print(f"  Run: mssclaw status for details")

    return issues == 0


if __name__ == "__main__":
    init_environment()
