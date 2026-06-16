"""
Agent Chat Terminal — 本地终端版 ChatGPT

功能:
  - 彩色对话界面
  - 多轮对话历史
  - 流式语义输出
  - /命令: /clear /save /load /model /vault
  - 对话持久化 (JSON)

用法:
    python -m mssclaw.core.agent_chat
    python -m mssclaw.core.agent_chat --model qwen2.5:7b
"""
import sys, os, json, time, readline
from pathlib import Path
from datetime import datetime


# ── Colors ──

C = {
    "reset": "\033[0m",
    "bold": "\033[1m",
    "dim": "\033[2m",
    "red": "\033[31m",
    "green": "\033[32m",
    "yellow": "\033[33m",
    "blue": "\033[34m",
    "magenta": "\033[35m",
    "cyan": "\033[36m",
    "white": "\033[37m",
}


def c(text, color):
    return f"{C.get(color, '')}{text}{C['reset']}"


def chat_loop(model: str = "qwen2.5:7b"):
    """交互式聊天循环."""
    from mssclaw.core.agent import MSSAgent
    from mssclaw.core.llm_backend import OllamaBackend, create_backend

    # Init
    print(c("╔══════════════════════════════════╗", "cyan"))
    print(c("║   MSS Agent Chat Terminal        ║", "cyan"))
    print(c("╠══════════════════════════════════╣", "cyan"))
    print(c(f"║   Model: {model:<24s} ║", "cyan"))
    print(c("╚══════════════════════════════════╝", "cyan"))
    print()
    print(c("  /clear  /save  /load  /model <name>  /vault  /tools  /absorb <desc>  /shell  /quit", "dim"))
    print()

    # Create agent
    be = create_backend("auto", model=model)
    if isinstance(be, OllamaBackend):
        models = be.list_models()
        if model not in models:
            avail = [m for m in models if not m.startswith("mss-ai-v3")][:3]
            if avail:
                model = avail[0]
                be = create_backend("auto", model=model)
                print(c(f"  Model switched to: {model}", "yellow"))

    agent = MSSAgent(name="chat-agent", llm=be)

    # Tools
    from mssclaw.core.tool_registry import ToolRegistry, register_builtin_tools
    tools = ToolRegistry()
    register_builtin_tools(tools)
    tools_enabled = True

    # Try vault
    vault_path = Path.home() / ".mssclaw" / "vault.db"
    has_vault = vault_path.exists()

    history = []
    history_file = Path.home() / ".mssclaw" / "chat_history.json"

    def save_history():
        history_file.parent.mkdir(parents=True, exist_ok=True)
        with open(history_file, "w", encoding="utf-8") as f:
            json.dump(history[-100:], f, ensure_ascii=False, indent=2)

    # Load history
    if history_file.exists():
        try:
            with open(history_file, encoding="utf-8") as f:
                history = json.load(f)
            last = history[-1] if history else None
            if last:
                print(c(f"  Loaded {len(history)} messages from {history_file.name}", "dim"))
        except Exception:
            pass

    # Chat loop
    while True:
        try:
            user_input = input(c("\nYou: ", "green")).strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break

        if not user_input:
            continue

        # Commands
        if user_input.startswith("/"):
            cmd = user_input[1:].strip().split()
            if not cmd:
                continue

            if cmd[0] == "quit" or cmd[0] == "exit":
                break
            elif cmd[0] == "clear":
                history = []
                agent.reset()
                print(c("  History cleared", "dim"))
                continue
            elif cmd[0] == "save":
                save_history()
                print(c(f"  Saved {len(history)} messages", "dim"))
                continue
            elif cmd[0] == "load":
                if history_file.exists():
                    with open(history_file, encoding="utf-8") as f:
                        history = json.load(f)
                    print(c(f"  Loaded {len(history)} messages", "dim"))
                continue
            elif cmd[0] == "model" and len(cmd) > 1:
                new_model = cmd[1]
                try:
                    agent.llm = create_backend("auto", model=new_model)
                    model = new_model
                    print(c(f"  Model: {model}", "cyan"))
                except Exception:
                    print(c("  Model not available", "red"))
                continue
            elif cmd[0] == "vault":
                if has_vault:
                    agent.configure_vault(str(vault_path))
                    print(c("  Vault connected", "dim"))
                else:
                    print(c("  No vault found. Run: mss-vault setup", "yellow"))
                continue
            elif cmd[0] == "tools":
                tools_enabled = not tools_enabled
                status = "ON" if tools_enabled else "OFF"
                print(c(f"  Tools: {status} ({len(tools._tools)} available)", "dim"))
                continue
            elif cmd[0] == "absorb" and len(cmd) > 1:
                desc = " ".join(cmd[1:])
                from mssclaw.core.digest_engine import DigestEngine
                from mssclaw.core.logic_virus_detector import LogicVirusDetector

                detector = LogicVirusDetector()
                virus_report = detector.scan(desc)

                if virus_report.risk_level.value in ("critical", "high"):
                    print(c(f"  ⚠️  Virus detected: {virus_report.risk_level.value}", "red"))
                    for r in virus_report.recommendations:
                        print(c(f"    {r}", "red"))
                    cleaned = detector.repair(desc, virus_report)
                    print(c(f"  🔧 Auto-repaired: {len(virus_report.findings)} issues fixed", "yellow"))
                    desc = cleaned

                engine = DigestEngine(agent)
                result = engine.absorb_and_digest(desc)
                print(c(f"  Absorbed: {result['absorbed']['name']}", "cyan"))
                print(c(f"  Applied: {result['report']['applied']} | Conflicts: {result['report']['conflicts']}", "dim"))
                for d in result['report']['details']:
                    print(c(f"    {d}", "dim"))
                continue
            elif cmd[0] == "shell":
                if not hasattr(agent, '_shell_mode'):
                    agent._shell_mode = "off"
                modes = ["off", "auto", "dual", "check"]
                current = agent._shell_mode
                if len(cmd) > 1 and cmd[1] in modes:
                    agent._shell_mode = cmd[1]
                else:
                    idx = modes.index(current)
                    agent._shell_mode = modes[(idx + 1) % len(modes)]
                print(c(f"  Shell mode: {agent._shell_mode} (off|auto=FULL_DUAL|dual|check=CORE_CHECK)", "dim"))
                continue
            else:
                print(c("  Commands: /clear /save /load /model /vault /tools /shell /absorb /quit", "dim"))
                continue

        # Build context from history
        context = ""
        for h in history[-6:]:  # last 3 exchanges
            context += f"User: {h['user']}\nAssistant: {h['assistant'][:300]}\n"
        # Try tool call first (if enabled)
        tool_result = None
        if tools_enabled:
            tool_prompt = f"{context}User: {user_input}\n"
            tool_prompt += f"Available tools: {tools.get_descriptions()}\n"
            tool_prompt += "If you need a tool, respond JSON: {\"tool\": \"name\", \"params\": {}}\n"
            prompt = f"{tool_prompt}Assistant:"
        else:
            prompt = f"{context}User: {user_input}\nAssistant:"

        # Stream response
        print(c("Agent: ", "blue"), end="", flush=True)
        t0 = time.time()
        response_parts = []
        try:
            for chunk in agent.run_stream(prompt, semantic=True):
                response_parts.append(chunk)
                print(chunk, end="", flush=True)
        except Exception as e:
            print(c(f"\n  Error: {e}", "red"))
            continue

        response = "".join(response_parts)
        elapsed = time.time() - t0

        # Show metadata
        bridge = agent.l2bridge.level.name
        meta = f"  [{elapsed:.1f}s | {bridge}]"
        print(c(f"\n{meta}", "dim"))

        # Try to parse tool call from response
        if tools_enabled:
            import json as _json, re as _re
            try:
                match = _re.search(r'\{[^{}]*"tool"[^{}]*\}', response)
                if match:
                    call = _json.loads(match.group())
                    t_name = call.get("tool", "")
                    t_params = call.get("params", {})
                    if t_name in tools._tools:
                        t_result = tools.call(t_name, t_params)
                        icon = "✅" if t_result["success"] else "❌"
                        print(c(f"  {icon} Tool: {t_name} → {t_result.get('result', t_result.get('error', ''))}", "cyan"))
            except Exception:
                pass

        # Save to history
        history.append({
            "user": user_input,
            "assistant": response,
            "time": datetime.now().isoformat(),
            "model": model,
            "bridge": bridge,
        })
        save_history()

    # Exit
    save_history()
    print(c("\nGoodbye!", "cyan"))


def main():
    model = "qwen2.5:7b"
    args = sys.argv[1:]
    for i, a in enumerate(args):
        if a == "--model" and i + 1 < len(args):
            model = args[i + 1]
    chat_loop(model=model)


if __name__ == "__main__":
    main()
