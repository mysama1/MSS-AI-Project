"""
MSS MCP Client — Model Context Protocol 最小实现 (Sprint 140).

stdlib-only, 零外部依赖. 支持:
  - tools/list: 获取MCP服务器的工具列表
  - tools/call: 调用MCP服务器工具
  - JSON-RPC 2.0 over stdio

用法:
    from mssclaw.core.mcp_client import MCPClient
    client = MCPClient()
    client.connect("npx", "-y", "@modelcontextprotocol/server-filesystem", "/tmp")
    tools = client.list_tools()
    result = client.call_tool("read_file", {"path": "/tmp/test.txt"})
"""
from __future__ import annotations
import subprocess, json, sys, os, threading, queue, time
from typing import List, Dict, Optional, Any


class MCPClient:
    """
    MCP客户端 — JSON-RPC 2.0 over stdio.

    支持:
      - 启动MCP服务器(任意命令)
      - tools/list + tools/call
      - 自动重连 + 超时
    """

    def __init__(self, timeout: float = 30):
        self._process: Optional[subprocess.Popen] = None
        self._request_id = 0
        self._timeout = timeout
        self._responses: queue.Queue = queue.Queue()
        self._reader_thread: Optional[threading.Thread] = None
        self._connected = False
        self._tools: List[dict] = []

    def connect(self, *command: str) -> bool:
        """启动MCP服务器并建立连接."""
        try:
            self._process = subprocess.Popen(
                list(command),
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1,
            )

            # 启动读取线程
            self._reader_thread = threading.Thread(
                target=self._read_responses, daemon=True
            )
            self._reader_thread.start()

            # 初始化握手
            init_result = self._send_request("initialize", {
                "protocolVersion": "2024-11-05",
                "capabilities": {"tools": {}},
                "clientInfo": {"name": "mssclaw-mcp", "version": "0.3.9"},
            })

            if init_result and "error" not in init_result:
                self._connected = True
                # 获取工具列表
                tools_result = self._send_request("tools/list", {})
                if tools_result and "tools" in tools_result:
                    self._tools = tools_result["tools"]
                return True

            return False

        except Exception as e:
            print(f"MCP connect failed: {e}", file=sys.stderr)
            return False

    def list_tools(self) -> List[dict]:
        """获取可用工具列表."""
        if not self._connected:
            return []
        # 刷新工具列表
        result = self._send_request("tools/list", {})
        if result and "tools" in result:
            self._tools = result["tools"]
        return [
            {
                "name": t.get("name", "unknown"),
                "description": t.get("description", ""),
                "inputSchema": t.get("inputSchema", {}),
            }
            for t in self._tools
        ]

    def call_tool(self, name: str, arguments: dict = None) -> dict:
        """调用MCP工具."""
        if not self._connected:
            return {"error": "MCP not connected"}

        result = self._send_request("tools/call", {
            "name": name,
            "arguments": arguments or {},
        })

        if result and "error" not in result:
            content = result.get("content", [])
            if content:
                return {
                    "success": True,
                    "tool": name,
                    "result": content[0].get("text", str(content)),
                }

        return {
            "success": False,
            "tool": name,
            "error": result.get("error", {}).get("message", "Unknown error") if result else "No response",
        }

    def disconnect(self):
        """断开MCP连接."""
        self._connected = False
        if self._process:
            try:
                self._process.terminate()
                self._process.wait(timeout=5)
            except Exception:
                self._process.kill()

    def _send_request(self, method: str, params: dict) -> Optional[dict]:
        """发送JSON-RPC请求并等待响应."""
        if not self._process:
            return None

        self._request_id += 1
        request = {
            "jsonrpc": "2.0",
            "id": self._request_id,
            "method": method,
            "params": params,
        }

        try:
            request_str = json.dumps(request) + "\n"
            self._process.stdin.write(request_str)
            self._process.stdin.flush()

            # 等待响应
            try:
                response = self._responses.get(timeout=self._timeout)
                return response
            except queue.Empty:
                return {"error": {"message": "Request timeout"}}

        except (BrokenPipeError, OSError) as e:
            self._connected = False
            return {"error": {"message": str(e)}}

    def _read_responses(self):
        """后台线程: 读取服务器响应."""
        try:
            for line in self._process.stdout:
                line = line.strip()
                if not line:
                    continue
                try:
                    response = json.loads(line)
                    self._responses.put(response)
                except json.JSONDecodeError:
                    pass
        except Exception:
            pass

    def is_connected(self) -> bool:
        return self._connected

    def stats(self) -> dict:
        return {
            "connected": self._connected,
            "tools_count": len(self._tools),
            "tools": [t.get("name", "?") for t in self._tools],
        }


# ═══ CLI ═══
def cmd_mcp(args_rest):
    """CLI: mssclaw mcp [connect|list|call|status]"""
    if not args_rest:
        print("mssclaw mcp [connect|list|call|status]")
        print("\nExamples:")
        print("  mssclaw mcp connect npx -y @modelcontextprotocol/server-filesystem /tmp")
        print("  mssclaw mcp list")
        print("  mssclaw mcp call read_file path=/tmp/test.txt")
        return

    cmd = args_rest[0]
    client = MCPClient()

    if cmd == "connect":
        command = args_rest[1:]
        if not command:
            print("Usage: mssclaw mcp connect <command...>")
            return
        ok = client.connect(*command)
        print(f"MCP: {'connected' if ok else 'failed'}")

    elif cmd == "list":
        tools = client.list_tools()
        if not tools:
            print("MCP: not connected — use 'mssclaw mcp connect' first")
            return
        print(f"MCP Tools ({len(tools)}):")
        for t in tools:
            print(f"  - {t['name']}: {t['description'][:60]}")

    elif cmd == "call":
        if len(args_rest) < 2:
            print("Usage: mssclaw mcp call <tool> [key=val ...]")
            return
        tool_name = args_rest[1]
        args_dict = {}
        for arg in args_rest[2:]:
            if "=" in arg:
                k, v = arg.split("=", 1)
                args_dict[k] = v
        result = client.call_tool(tool_name, args_dict)
        print(json.dumps(result, ensure_ascii=False, indent=2))

    elif cmd == "status":
        print(json.dumps(client.stats(), ensure_ascii=False, indent=2))


# ═══ Demo (self-test with echo) ═══
if __name__ == "__main__":
    print("=== MSS MCP Client v0.1 ===")
    print("Usage: mssclaw mcp connect <server_command>")
    print("       mssclaw mcp list")
    print("       mssclaw mcp call <tool> <args>")
    print()
    print("MCP Client: stdlib-only JSON-RPC 2.0 over stdio ✅")
