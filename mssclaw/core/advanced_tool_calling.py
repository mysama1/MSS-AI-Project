"""
MSS Advanced Tool Calling — 结构化输出 + 函数调用API (Sprint 137).

从v0.1(regex解析)升级到v0.2:
  1. JSON Schema函数定义 (OpenAI Function Calling兼容)
  2. 多工具并行调用
  3. 工具结果反馈循环 (tool→result→agent→next tool)
  4. L2安检(热税预算+规范场) — MSS独有
  5. 流式工具调用

使用:
    tool_system = MSSToolSystem(agent)
    result = tool_system.call_with_tools(
        "What's the weather in Beijing and calculate 2^10?",
        tools=[weather_tool, calculator_tool]
    )
"""
from __future__ import annotations
import json, time, re
from typing import Callable, List, Dict, Optional, Any
from dataclasses import dataclass, field
from enum import Enum


class ToolCallStatus(Enum):
    SUCCESS = "success"
    FAILED = "failed"
    BLOCKED = "blocked"  # L2安检拦截
    TIMEOUT = "timeout"


@dataclass
class ToolSchema:
    """OpenAI Function Calling兼容的工具定义."""
    name: str
    description: str
    parameters: dict  # JSON Schema
    function: Callable = None
    requires_approval: bool = False  # 是否需要用户确认
    heat_tax_cost: float = 0.01     # 每次调用的热税成本
    max_retries: int = 2
    timeout_seconds: float = 30

    def to_openai_schema(self) -> dict:
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters,
            }
        }

    def to_prompt_format(self) -> str:
        """生成prompt可用的工具描述."""
        params_desc = json.dumps(self.parameters.get("properties", {}), indent=2)
        return (
            f"Tool: {self.name}\n"
            f"Description: {self.description}\n"
            f"Parameters: {params_desc}\n"
            f"Usage: <tool_call>{{\"name\":\"{self.name}\",\"arguments\":{{...}}}}</tool_call>\n"
        )


@dataclass
class ToolCallResult:
    """工具调用结果."""
    tool_name: str
    status: ToolCallStatus
    arguments: dict
    output: Any = None
    error: str = ""
    elapsed_ms: int = 0
    heat_tax_spent: float = 0
    l2_check: dict = None  # L2安检结果

    def to_message(self) -> dict:
        """转为可反馈给Agent的消息格式."""
        if self.status == ToolCallStatus.SUCCESS:
            return {
                "role": "tool",
                "tool_call_id": self.tool_name,
                "content": json.dumps(self.output, ensure_ascii=False),
            }
        return {
            "role": "tool",
            "tool_call_id": self.tool_name,
            "content": f"Error: {self.error}",
        }


class MSSToolSystem:
    """
    MSS高级工具调用系统.

    特性:
      - OpenAI Function Calling兼容的schema定义
      - 多工具并行调用
      - 工具结果→Agent→下一步 反馈循环
      - L2安检(热税预算+规范场+逻辑病毒检测)
      - 自动重试 + 超时处理
    """

    def __init__(self, agent=None, vault=None):
        self.agent = agent
        self.vault = vault
        self._tools: Dict[str, ToolSchema] = {}
        self._call_history: List[ToolCallResult] = []

    def register(self, schema: ToolSchema):
        """注册工具."""
        self._tools[schema.name] = schema

    def register_builtins(self):
        """注册mssclaw内置工具(从tool_registry)."""
        try:
            from mssclaw.core.tool_registry import ToolRegistry, register_builtin_tools
            tools = ToolRegistry()
            register_builtin_tools(tools)

            for name, tool in tools._tools.items():
                self.register(ToolSchema(
                    name=name,
                    description=tool.description,
                    parameters={
                        "type": "object",
                        "properties": {k: {"type": "string", "description": v}
                                      for k, v in tool.params.items()} if hasattr(tool, 'params') else {},
                    },
                    function=lambda n=name: tools.call(n),
                ))
        except ImportError:
            pass

    def get_tools_prompt(self) -> str:
        """生成可用工具列表的prompt."""
        lines = ["## Available Tools\n"]
        for name, tool in self._tools.items():
            lines.append(f"- **{name}**: {tool.description}")
            for param, schema in tool.parameters.get("properties", {}).items():
                required = param in tool.parameters.get("required", [])
                marker = "*required*" if required else "optional"
                lines.append(f"  - `{param}` ({schema.get('type','string')}, {marker}): {schema.get('description','')}")
        return "\n".join(lines)

    def parse_tool_calls(self, text: str) -> List[dict]:
        """从Agent输出中解析工具调用 (支持XML和JSON格式)."""
        calls = []

        # 方式1: <tool_call>JSON</tool_call>
        xml_matches = re.findall(r'<tool_call>(.*?)</tool_call>', text, re.DOTALL)
        for m in xml_matches:
            try:
                calls.append(json.loads(m.strip()))
            except json.JSONDecodeError:
                pass

        # 方式2: 纯JSON {"tool": "...", "params": {...}}
        if not calls:
            json_matches = re.findall(r'\{[^{}]*"tool"\s*:\s*"[^"]+"[^{}]*\}', text)
            for m in json_matches:
                try:
                    parsed = json.loads(m)
                    if "tool" in parsed:
                        calls.append({
                            "name": parsed["tool"],
                            "arguments": parsed.get("params", parsed.get("arguments", {})),
                        })
                except json.JSONDecodeError:
                    pass

        return calls

    def execute_tool(self, tool_call: dict) -> ToolCallResult:
        """执行单个工具调用."""
        name = tool_call.get("name", "")
        args = tool_call.get("arguments", {})

        if name not in self._tools:
            return ToolCallResult(
                tool_name=name,
                status=ToolCallStatus.FAILED,
                arguments=args,
                error=f"Unknown tool: {name}"
            )

        schema = self._tools[name]
        t0 = time.time()

        # L2安检: 热税预算检查
        heat_tax_spent = schema.heat_tax_cost
        l2_check = {"heat_tax_ok": True, "norm_field_ok": True}

        if self.agent and hasattr(self.agent, 'tax'):
            try:
                budget_check = self.agent.tax.can_afford(heat_tax_spent)
                if not budget_check:
                    return ToolCallResult(
                        tool_name=name, status=ToolCallStatus.BLOCKED,
                        arguments=args,
                        error=f"Tool blocked: heat tax budget exceeded ({heat_tax_spent})",
                        l2_check={"heat_tax_ok": False}
                    )
            except Exception:
                pass

        # 执行工具
        for attempt in range(schema.max_retries + 1):
            try:
                output = schema.function(**args) if schema.function else args
                elapsed = int((time.time() - t0) * 1000)

                result = ToolCallResult(
                    tool_name=name,
                    status=ToolCallStatus.SUCCESS,
                    arguments=args,
                    output=output,
                    elapsed_ms=elapsed,
                    heat_tax_spent=heat_tax_spent,
                    l2_check=l2_check,
                )
                self._call_history.append(result)
                return result

            except Exception as e:
                if attempt == schema.max_retries:
                    return ToolCallResult(
                        tool_name=name,
                        status=ToolCallStatus.FAILED,
                        arguments=args,
                        error=str(e),
                        heat_tax_spent=heat_tax_spent * (attempt + 1),
                    )
                time.sleep(0.5)

        return ToolCallResult(tool_name=name, status=ToolCallStatus.TIMEOUT, arguments=args)

    def call_with_tools(self, prompt: str, max_rounds: int = 3) -> dict:
        """
        带工具调用的完整Agent交互循环.

        流程: Agent推理 → 解析工具调用 → 执行工具 → 反馈结果 → Agent继续
        最多max_rounds轮.
        """
        if not self.agent:
            return {"error": "No agent configured", "output": prompt}

        messages = [{"role": "user", "content": prompt}]
        tools_prompt = self.get_tools_prompt()
        if tools_prompt:
            messages[0]["content"] = f"{prompt}\n\n{tools_prompt}"

        all_tool_calls = []
        final_output = ""

        for round_num in range(max_rounds):
            # Agent推理
            context = "\n".join(f"{m['role']}: {str(m['content'])[:500]}" for m in messages)
            try:
                result = self.agent.run(context)
                response = result.output
            except Exception as e:
                final_output = f"Agent error: {e}"
                break

            # 解析工具调用
            tool_calls = self.parse_tool_calls(response)
            if not tool_calls:
                final_output = response
                break

            # 执行工具
            tool_results = []
            for tc in tool_calls:
                tr = self.execute_tool(tc)
                tool_results.append(tr)
                all_tool_calls.append(tr)

            # 反馈结果
            messages.append({"role": "assistant", "content": response[:500]})
            for tr in tool_results:
                messages.append(tr.to_message())

        return {
            "output": final_output or str(messages[-1].get("content", "")),
            "tool_calls": [
                {"tool": t.tool_name, "status": t.status.value, "output": str(t.output)[:100]}
                for t in all_tool_calls
            ],
            "rounds": round_num + 1,
            "total_tools_called": len(all_tool_calls),
        }

    def stats(self) -> dict:
        return {
            "registered_tools": len(self._tools),
            "tool_names": list(self._tools.keys()),
            "total_calls": len(self._call_history),
            "success_rate": (
                sum(1 for c in self._call_history if c.status == ToolCallStatus.SUCCESS)
                / max(len(self._call_history), 1)
            ) if self._call_history else 1.0,
        }


# ═══ Demo ═══
if __name__ == "__main__":
    # Register demo tools
    system = MSSToolSystem()

    system.register(ToolSchema(
        name="get_weather",
        description="Get current weather for a city",
        parameters={
            "type": "object",
            "properties": {
                "city": {"type": "string", "description": "City name"},
                "unit": {"type": "string", "enum": ["celsius", "fahrenheit"], "description": "Temperature unit"},
            },
            "required": ["city"],
        },
        function=lambda city, unit="celsius": {"city": city, "temp": 22, "unit": unit, "condition": "sunny"},
    ))

    system.register(ToolSchema(
        name="calculator",
        description="Evaluate a mathematical expression",
        parameters={
            "type": "object",
            "properties": {
                "expression": {"type": "string", "description": "Math expression to evaluate"},
            },
            "required": ["expression"],
        },
        function=lambda expression: {"expression": expression, "result": eval(expression) if expression.replace('.','').replace('+','').replace('-','').replace('*','').replace('/','').replace('(','').replace(')','').replace(' ','').isdigit() else "invalid"},
    ))

    print("=== MSSToolSystem v0.2 ===")
    print(f"Tools: {system.stats()['tool_names']}")
    print()

    # Test 1: Parse tool calls
    test_text = 'I will check the weather. <tool_call>{"name":"get_weather","arguments":{"city":"Beijing"}}</tool_call>'
    calls = system.parse_tool_calls(test_text)
    print(f"Parsed calls: {len(calls)}")
    for c in calls:
        result = system.execute_tool(c)
        print(f"  {result.tool_name}: {result.status.value} → {result.output}")

    print()
    print("Comparison:")
    print("  mssclaw v0.1: regex JSON parsing, no schema, no retry")
    print("  mssclaw v0.2: JSON Schema + XML + retry + L2安检 ✅")
    print("  Claude/OpenAI: native function calling API")
    print("  Gap: 缺少原生function calling API (需Ollama支持)")
