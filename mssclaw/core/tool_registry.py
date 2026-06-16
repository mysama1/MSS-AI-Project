"""
MSS Tool Calling — L2 过滤的函数调用

与其他框架的关键区别: 每个工具调用都经过 L2 安检.
  A3 热税: 检查调用是否有意义
  Δ: 检查是否在循环调用
  规范场: 检查调用是否安全

用法:
    tools = ToolRegistry()
    tools.register("get_weather", get_weather_fn, "Get weather for a city")
    
    agent = MSSAgent("tool-agent", llm=be)
    result = agent.run_with_tools("What's the weather in Beijing?", tools)
"""
from __future__ import annotations
import json
import time
from dataclasses import dataclass, field
from typing import Callable, Optional, Dict, List, Any


@dataclass
class ToolDef:
    """工具定义."""
    name: str
    description: str
    func: Callable
    parameters: Dict[str, Any] = field(default_factory=dict)
    category: str = "general"  # "safe" | "network" | "file" | "system"
    max_calls_per_task: int = 5
    call_count: int = 0
    total_time_ms: float = 0.0
    heat_tax_per_call: float = 0.01  # A3 基础成本

    def to_openai_schema(self) -> dict:
        """转为 OpenAI function calling 格式."""
        return {
            "name": self.name,
            "description": self.description,
            "parameters": self.parameters or {
                "type": "object",
                "properties": {},
            },
        }


class ToolRegistry:
    """
    工具注册表 + L2 安检.

    每个工具调用都会:
      1. A3 热税检查 → 是否浪费推理成本
      2. Δ 检查 → 是否循环调用
      3. 规范场 → 是否安全 (category-based)
    """

    MAX_TOTAL_CALLS_PER_TASK = 20

    def __init__(self):
        self._tools: Dict[str, ToolDef] = {}
        self._call_history: List[dict] = []
        self._total_calls = 0

    def register(self, name: str, func: Callable, description: str,
                 parameters: dict = None, category: str = "general"):
        """注册工具."""
        self._tools[name] = ToolDef(
            name=name, func=func, description=description,
            parameters=parameters or {}, category=category,
        )

    def get_schemas(self) -> List[dict]:
        """获取所有工具的 OpenAI function schema."""
        return [t.to_openai_schema() for t in self._tools.values()]

    def get_descriptions(self) -> str:
        """文本描述 (给不持 function calling 的模型)."""
        lines = []
        for t in self._tools.values():
            lines.append(f"- {t.name}: {t.description}")
        return "\n".join(lines)

    def call(self, name: str, params: dict = None, tax=None, delta=None) -> dict:
        """
        执行工具调用 (带 L2 过滤).

        返回: {"success": bool, "result": Any, "l2": {...}}
        """
        params = params or {}

        # Tool exists?
        tool = self._tools.get(name)
        if not tool:
            return {"success": False, "error": f"Unknown tool: {name}", "l2": {}}

        # L2 Gate 1: A3 Heat Tax
        if tax:
            tax.charge_by_name("L2_MEANING", tool.heat_tax_per_call, f"tool:{name}")
            if tax.exceeded():
                return {
                    "success": False,
                    "error": f"Tool '{name}' blocked: heat tax budget exceeded",
                    "l2": {"tax_blocked": True, "tax_total": tax.total()},
                }

        # L2 Gate 2: Δ circular check
        if delta:
            recent = [h["tool"] for h in self._call_history[-5:] if h["tool"] == name]
            if len(recent) >= 3:
                return {
                    "success": False,
                    "error": f"Tool '{name}' blocked: circular call detected (Δ protection)",
                    "l2": {"delta_blocked": True, "recent_calls": len(recent)},
                }

        # L2 Gate 3: Category safety
        if tool.category == "system" and not self._call_history:
            return {
                "success": False,
                "error": f"Tool '{name}' blocked: system tool requires prior safe calls",
                "l2": {"norm_blocked": True},
            }

        # Rate limit per tool
        if tool.call_count >= tool.max_calls_per_task:
            return {
                "success": False,
                "error": f"Tool '{name}' blocked: max calls ({tool.max_calls_per_task}) reached",
                "l2": {"rate_limited": True},
            }

        # Global rate limit
        if self._total_calls >= self.MAX_TOTAL_CALLS_PER_TASK:
            return {
                "success": False,
                "error": "Max total tool calls reached",
                "l2": {"global_limit": True},
            }

        # Execute
        try:
            t0 = time.time()
            result = tool.func(**params)
            elapsed = (time.time() - t0) * 1000
        except Exception as e:
            return {"success": False, "error": str(e), "l2": {}}

        # Update stats
        tool.call_count += 1
        tool.total_time_ms += elapsed
        self._total_calls += 1
        self._call_history.append({
            "tool": name, "params": str(params)[:100],
            "elapsed_ms": round(elapsed, 1), "ts": time.time(),
        })
        self._call_history = self._call_history[-50:]

        return {
            "success": True,
            "result": result,
            "l2": {
                "tax_charged": tool.heat_tax_per_call,
                "elapsed_ms": round(elapsed, 1),
                "tool_calls": tool.call_count,
            },
        }

    def stats(self) -> dict:
        return {
            "tools": len(self._tools),
            "total_calls": self._total_calls,
            "calls": [
                {"name": t.name, "count": t.call_count, "time_ms": round(t.total_time_ms, 1)}
                for t in self._tools.values() if t.call_count > 0
            ],
            "history_len": len(self._call_history),
        }

    def reset(self):
        for t in self._tools.values():
            t.call_count = 0
            t.total_time_ms = 0.0
        self._total_calls = 0
        self._call_history.clear()


# ═══════════════════════════════════════════
# Built-in Tools
# ═══════════════════════════════════════════

def builtin_calculator(expression: str) -> str:
    """安全计算器 (仅算术)."""
    # Only allow safe operations
    allowed = set("0123456789+-*/().% ")
    if not all(c in allowed for c in expression):
        return "Error: unsafe expression"
    try:
        result = eval(expression, {"__builtins__": {}}, {})
        return str(result)
    except Exception as e:
        return f"Error: {e}"


def builtin_datetime(format_str: str = "%Y-%m-%d %H:%M:%S") -> str:
    """当前时间."""
    return time.strftime(format_str)


def builtin_length(text: str) -> int:
    """文本长度."""
    return len(text)


def builtin_read_file(path: str) -> str:
    """读取文本文件 (前 5KB)."""
    from pathlib import Path
    p = Path(path)
    if not p.exists():
        return f"Error: file not found: {path}"
    if p.stat().st_size > 100 * 1024:
        return f"Error: file too large ({p.stat().st_size} bytes)"
    try:
        return p.read_text(encoding="utf-8", errors="replace")[:5000]
    except Exception as e:
        return f"Error: {e}"


def builtin_list_dir(path: str = ".") -> str:
    """列出目录文件."""
    from pathlib import Path
    p = Path(path)
    if not p.exists():
        return f"Error: directory not found: {path}"
    if not p.is_dir():
        return f"Error: not a directory: {path}"
    try:
        items = []
        for item in sorted(p.iterdir()):
            suffix = "/" if item.is_dir() else ""
            size = item.stat().st_size if item.is_file() else 0
            items.append(f"  {item.name}{suffix} ({size}B)")
        return "\n".join(items[:50])
    except Exception as e:
        return f"Error: {e}"


def builtin_run_command(command: str) -> str:
    """执行安全命令 (白名单)."""
    import subprocess
    # Whitelist: only safe commands
    safe_commands = ["dir", "echo", "date", "time", "whoami", "hostname",
                     "ls", "pwd", "cat", "head", "wc", "uname"]
    cmd_parts = command.strip().split()
    if not cmd_parts or cmd_parts[0].lower() not in safe_commands:
        return f"Error: command '{cmd_parts[0]}' not in safe list"
    try:
        result = subprocess.run(
            command, shell=True, capture_output=True, text=True,
            timeout=10, cwd="."
        )
        output = (result.stdout + result.stderr)[:2000]
        return output if output.strip() else "(no output)"
    except subprocess.TimeoutExpired:
        return "Error: command timed out"
    except Exception as e:
        return f"Error: {e}"


def register_builtin_tools(registry: ToolRegistry):
    """注册内置工具."""
    registry.register("calculator", builtin_calculator,
        "Evaluate a mathematical expression (safe, arithmetic only)",
        {"type": "object", "properties": {"expression": {"type": "string"}}},
        category="safe")
    registry.register("datetime", builtin_datetime,
        "Get the current date and time",
        {"type": "object", "properties": {"format_str": {"type": "string"}}},
        category="safe")
    registry.register("length", builtin_length,
        "Count the number of characters in a text",
        {"type": "object", "properties": {"text": {"type": "string"}}},
        category="safe")
    registry.register("read_file", builtin_read_file,
        "Read the contents of a text file",
        {"type": "object", "properties": {"path": {"type": "string"}}},
        category="file")
    registry.register("list_dir", builtin_list_dir,
        "List files in a directory",
        {"type": "object", "properties": {"path": {"type": "string"}}},
        category="file")
    registry.register("run_command", builtin_run_command,
        "Run a safe shell command (dir/ls/echo/date only)",
        {"type": "object", "properties": {"command": {"type": "string"}}},
        category="system")
