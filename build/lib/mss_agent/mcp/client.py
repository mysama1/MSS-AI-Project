"""MSS-Agent MCP (Model Context Protocol) Integration.

MCP lets MSS-Agent use external tools — file system, databases, web APIs.
Implements a lightweight MCP client (stdlib only) so agents can:

  1. List available tools from an MCP server
  2. Call tools with structured input/output
  3. Apply heat tax to MCP tool calls (expensive tools get higher tax)

Architecture:
  Agent.run(prompt)
    → _estimate_meaning_heat(prompt)
    → [if meaningful] → call MCP tools as needed
    → delta.tick() + memory.store()

Usage:
    agent = MSSAgent(name="tool-agent",
                     llm=DeepSeekLLM(),
                     mcp_servers=[MCPServerConfig("filesystem", ["npx", "-y", "@modelcontextprotocol/server-filesystem", "/tmp"])])
"""
import json
import subprocess
import threading
import time
import os
from dataclasses import dataclass, field
from typing import Optional, Callable


@dataclass
class MCPServerConfig:
    """MCP 服务器配置。"""

    name: str
    command: list  # e.g. ["npx", "-y", "@modelcontextprotocol/server-filesystem", "/tmp"]
    env: dict = field(default_factory=lambda: os.environ.copy())
    timeout_ms: int = 30000


class MCPClient:
    """轻量 MCP 客户端 (stdlib only)。

    通过 subprocess 启动 MCP server (stdio), JSON-RPC 通信。
    支持 tools/list, tools/call, resources/list。
    """

    def __init__(self, config: MCPServerConfig):
        self.config = config
        self.process: Optional[subprocess.Popen] = None
        self._lock = threading.Lock()
        self._tools: list[dict] = []
        self._request_id = 0
        self._initialized = False

    def start(self):
        """启动 MCP server 进程并执行初始化握手。"""
        if self.process:
            return

        self.process = subprocess.Popen(
            self.config.command,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=self.config.env,
            text=True,
            bufsize=1,
        )
        self._send_request("initialize", {
            "protocolVersion": "2024-11-05",
            "capabilities": {"tools": {}},
            "clientInfo": {"name": "mss-agent", "version": "0.2.0"},
        })
        self._initialized = True
        self._tools = self.list_tools()

    def stop(self):
        if self.process:
            try:
                self.process.stdin.close()
                self.process.wait(timeout=3)
            except Exception:
                self.process.kill()
            self.process = None
            self._initialized = False

    def _send_request(self, method: str, params: dict = None) -> dict:
        """发送 JSON-RPC 请求到 MCP server。"""
        self._request_id += 1
        request = {
            "jsonrpc": "2.0",
            "id": self._request_id,
            "method": method,
            "params": params or {},
        }
        payload = json.dumps(request)
        self.process.stdin.write(payload + "\n")
        self.process.stdin.flush()

        # Read response line
        response_line = self.process.stdout.readline()
        if not response_line:
            raise ConnectionError(f"MCP server {self.config.name} closed connection")

        return json.loads(response_line)

    def list_tools(self) -> list[dict]:
        """获取可用工具列表。"""
        result = self._send_request("tools/list")
        return result.get("result", {}).get("tools", [])

    def call_tool(self, tool_name: str, arguments: dict) -> dict:
        """调用 MCP 工具。"""
        result = self._send_request("tools/call", {
            "name": tool_name,
            "arguments": arguments,
        })
        return result.get("result", {})

    def call_tool_string(self, tool_name: str, arguments: dict) -> str:
        """调用工具并返回字符串结果。"""
        result = self.call_tool(tool_name, arguments)
        content = result.get("content", [])
        if isinstance(content, list):
            return "\n".join(
                item.get("text", str(item))
                for item in content
            )
        return str(content)

    @property
    def available_tools(self) -> list[str]:
        """可用工具名称列表。"""
        if not self._tools:
            try:
                self._tools = self.list_tools()
            except Exception:
                pass
        return [t.get("name", "?") for t in self._tools]


class MCPAgentMixin:
    """Mixin: 为 MSSAgent 添加 MCP 工具调用能力。

    用法:
        class ToolAgent(MCPAgentMixin, MSSAgent):
            pass
    """

    def __init__(self, *args, mcp_servers: list[MCPServerConfig] = None, **kwargs):
        super().__init__(*args, **kwargs)
        self._mcp_clients: dict[str, MCPClient] = {}
        self._mcp_configs = mcp_servers or []

    def _ensure_mcp(self):
        """懒启动所有 MCP server。"""
        for cfg in self._mcp_configs:
            if cfg.name not in self._mcp_clients:
                client = MCPClient(cfg)
                client.start()
                self._mcp_clients[cfg.name] = client

    def list_mcp_tools(self) -> dict[str, list[str]]:
        """列出所有 MCP server 提供的工具。"""
        self._ensure_mcp()
        return {
            name: client.available_tools
            for name, client in self._mcp_clients.items()
        }

    def call_mcp_tool(self, server: str, tool: str, args: dict) -> str:
        """调用指定 MCP server 的工具。"""
        self._ensure_mcp()
        if server not in self._mcp_clients:
            raise ValueError(f"Unknown MCP server: {server}")
        return self._mcp_clients[server].call_tool_string(tool, args)

    def shutdown_mcp(self):
        """关闭所有 MCP server。"""
        for client in self._mcp_clients.values():
            client.stop()
        self._mcp_clients.clear()
