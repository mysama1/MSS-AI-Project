"""MCP 文件系统集成 Demo — MSS-Agent 工具调用能力演示.

演示:
  1. 启动 MCP filesystem server
  2. Agent 列出文件
  3. Agent 读取文件并应用热税判断
  4. Agent 写文件（仅通过热税检测的有意义操作）

用法:
  pip install mss-agent
  npx @modelcontextprotocol/server-filesystem /tmp/mss-agent-demo

  py -3.11 demo_mcp_filesystem.py
"""
import os, sys, tempfile, json
sys.path.insert(0, r'E:\AI_Workspace\MSS-AI\project')

from mss_agent import MSSAgent
from mss_agent.mcp.client import MCPClient, MCPServerConfig


def create_demo_files(root: str):
    """创建演示用的文件结构。"""
    os.makedirs(root, exist_ok=True)

    # 有价值的文件
    with open(os.path.join(root, "security_policy.md"), "w", encoding="utf-8") as f:
        f.write("# Security Policy\n\n- Use TLS 1.3\n- Rotate keys every 90 days\n- MFA required\n")

    with open(os.path.join(root, "api_readme.md"), "w", encoding="utf-8") as f:
        f.write("# API Documentation\n\nEndpoint: POST /api/v1/auth\nAuth: Bearer token\nRate limit: 100/min\n")

    # 无意义的文件
    with open(os.path.join(root, "log_tmp.txt"), "w", encoding="utf-8") as f:
        f.write("temp log\ntemp log\ntemp log\n" * 100)

    print(f"Demo files created in {root}")
    return root


def demo():
    """Run the MCP filesystem demo."""
    print("=" * 60)
    print("MSS-Agent + MCP Filesystem Demo")
    print("=" * 60)

    # 1. Create demo files
    root = os.path.join(tempfile.gettempdir(), "mss-agent-demo")
    create_demo_files(root)

    # 2. Start MCP filesystem server
    mcp_config = MCPServerConfig(
        name="filesystem",
        command=["npx", "-y", "@modelcontextprotocol/server-filesystem", root],
    )
    client = MCPClient(mcp_config)

    try:
        client.start()
        tools = client.available_tools
        print(f"\nMCP tools available: {tools}")
    except Exception as e:
        print(f"\n⚠️  MCP server not available (npx/npm required): {e}")
        print("Falling back to file listing simulation...")
        client = None

    # 3. Create Agent with MCP tool
    def llm_with_tools(prompt: str) -> str:
        """LLM that can use MCP tools."""
        if client and "list files" in prompt.lower():
            try:
                result = client.call_tool_string("list_directory", {"path": root})
                return f"Files found:\n{result}"
            except Exception:
                pass

        if client and "read" in prompt.lower():
            # Extract filename from prompt
            for f in os.listdir(root):
                if f.lower().replace("_", " ") in prompt.lower():
                    try:
                        result = client.call_tool_string(
                            "read_file", {"path": os.path.join(root, f)}
                        )
                        return f"Content of {f}:\n{result}"
                    except Exception:
                        pass

        # Fallback: simple analysis
        return f"[Agent analysis] Task analyzed: {len(prompt)} chars, intent=meaningful"

    agent = MSSAgent(name="mcp-demo", llm=llm_with_tools)

    # 4. Test meaningful tasks
    print("\n" + "-" * 40)
    print("Task 1: Read security policy (meaningful)")
    result = agent.run("Read the security_policy.md file and list requirements")
    print(f"  Status: {'PASS' if not result.aborted else 'ABORT'}")
    print(f"  HeatTax: {agent.tax.total():.4f}")
    if hasattr(result, 'output') and result.output:
        preview = result.output[:200]
        print(f"  Output: {preview}")

    print("\nTask 2: List all files in the project")
    result = agent.run("List all files in the project root directory")
    print(f"  Status: {'PASS' if not result.aborted else 'ABORT'}")
    print(f"  HeatTax: {agent.tax.total():.4f}")

    # 5. Test busywork rejection
    print("\n" + "-" * 40)
    print("Task 3: Rewrite (busywork — should be rejected)")
    result = agent.run("Rewrite the file again")
    print(f"  Status: {'PASS' if not result.aborted else 'ABORT'}")
    print(f"  Reason: {getattr(result, 'reason', 'N/A')}")

    # 6. Show health report
    print("\n" + "-" * 40)
    print("Agent Health Report:")
    report = agent.health_report()
    print(f"  Runs: {report['runs']} | Aborts: {report['aborts']} | Rate: {report['abort_rate']}")
    print(f"  Delta: {report['delta']['health']}")
    print(f"  Memory: items={report['memory']['total']} diversity={report['memory']['diversity']}")

    # 7. Cleanup
    if client:
        client.stop()

    # Clean temp files
    for f in os.listdir(root):
        os.remove(os.path.join(root, f))
    os.rmdir(root)

    print("\n" + "=" * 60)
    print("Demo complete!")
    print("=" * 60)


if __name__ == "__main__":
    demo()
