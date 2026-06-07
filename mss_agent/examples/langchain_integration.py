"""
MSS-Agent + LangChain 集成示例.

证明: MSS-Agent 可以套在 LangChain AgentExecutor 外面做意义场检测.

真实用法 (需要 pip install langchain langchain-openai):
    from langchain.agents import create_openai_functions_agent
    from langchain_openai import ChatOpenAI
    from mss_agent.integrations.langchain import MSSAgentCallback
    
    llm = ChatOpenAI(model="gpt-4o")
    agent = create_openai_functions_agent(llm, tools, prompt)
    executor = AgentExecutor(agent=agent, tools=tools, callbacks=[MSSAgentCallback()])
    
    # 现在 executor 自带热税预算 + Δ检测
    result = executor.invoke({"input": "设计REST API"})

本文件用 mock 演示核心概念, 不依赖 langchain 安装.
"""
import sys, time
sys.path.insert(0, r'E:\AI_Workspace\MSS-AI\project')
from mss_agent import HeatTaxBudget, HeatTaxLevel, DeltaProtocol, DeltaMemory
from mss_agent.protocols import QuorumFast, ElevationProtocol


# ═══════════════════════════════════════════════════════
# Part 1: MSSAgentCallback — 透明嵌入 LangChain pipeline
# ═══════════════════════════════════════════════════════

class MSSAgentCallback:
    """
    LangChain Callback 实现.

    嵌入方式:
        executor = AgentExecutor(..., callbacks=[MSSAgentCallback()])

    每次 LangChain:
      - on_agent_action → 热税评估
      - on_tool_start → Δ tick
      - on_agent_finish → 健康报告

    如果热税超支 → 抛出 HeatTaxAbort, LangChain 自动停止.
    """
    def __init__(self, threshold=2.0, min_delta=0.3, verbose=True):
        self.tax = HeatTaxBudget(threshold=threshold)
        self.delta = DeltaProtocol(min_delta=min_delta)
        self.memory = DeltaMemory()
        self.verbose = verbose
        self.stats = {"aborted": 0, "passed": 0, "tool_calls": 0}

    def on_agent_action(self, action, **kwargs):
        """LangChain 决定执行某个 action 时触发."""
        # 从 action 中提取实际任务内容
        content = ""
        if hasattr(action, 'tool_input'):
            if isinstance(action.tool_input, dict):
                content = ' '.join(str(v) for v in action.tool_input.values())
            else:
                content = str(action.tool_input)
        if not content:
            content = str(action)

        meaning_heat, reason = _assess_meaning(content)

        self.tax.charge(HeatTaxLevel.L2_MEANING, meaning_heat, reason)

        if self.tax.l2_dominant() and meaning_heat > 0.05:
            self.stats["aborted"] += 1
            if self.verbose:
                print(f"  🛑 MSS 拦截: {reason[:50]}")
            raise HeatTaxAbort(f"MSS refused: {reason}", self.tax.snapshot())

        self.stats["passed"] += 1
        if self.verbose and meaning_heat > 0.005:
            print(f"  ⚡ 热税: {reason[:40]} (tax={self.tax.total():.2f})")

    def on_tool_start(self, serialized, input_str, **kwargs):
        """Tool 调用开始时触发 — Δ检测点."""
        import hashlib
        task_hash = hashlib.md5(str(input_str).encode()).hexdigest()[:12]
        novelty = self.memory.novelty_score(str(input_str))
        diversity = self.memory.diversity_score()
        d = self.delta.tick(task_hash, novelty, diversity)
        self.memory.store(str(input_str), d)
        self.stats["tool_calls"] += 1

        if self.verbose and d < 0.5:
            print(f"  📉 Δ={d:.2f} (趋近闭合, 考虑换策略)")

    def on_agent_finish(self, finish, **kwargs):
        """Agent 完成时 — 健康报告."""
        if self.verbose:
            h = self.delta.health()
            print(f"  ✅ 完成 | Δ={h} | tax={self.tax.total():.2f} | tools={self.stats['tool_calls']}")

    def health_report(self):
        return {
            "heat_tax": self.tax.snapshot(),
            "delta": self.delta.snapshot(),
            "memory": self.memory.stats(),
            "stats": self.stats,
        }


class HeatTaxAbort(Exception):
    """热税超支异常 — LangChain 收到后自动停止 Agent 执行."""
    def __init__(self, reason, snapshot):
        self.reason = reason
        self.snapshot = snapshot
        super().__init__(reason)


def _assess_meaning(prompt: str) -> tuple:
    """与 maf_integration_demo.py 共享的意义评估逻辑."""
    pl = str(prompt).lower().strip()
    if len(pl) < 5:
        return 0.08, "Prompt too short"
    waste = sum(1 for s in ["改写", "再改", "总结", "翻译", "换个说法", "简短点",
                             "重新说", "重写", "重新写", "再说一遍", "再说一次"] if s in pl)
    meaning = sum(1 for s in ["为什么", "分析", "设计", "实现", "评估", "优化",
                               "security", "review", "refactor", "test",
                               "安全", "风险", "架构", "方案", "策略"] if s in pl)
    if waste >= 1 and meaning == 0 and len(pl) < 30:
        return 0.06, "Short busywork: no meaningful intent"
    if waste > meaning and waste >= 2:
        return 0.06, "Busywork pattern detected"
    if meaning >= 2:
        return 0.002, "Meaningful intent"
    if meaning >= 1:
        return 0.005, "Some meaning"
    return 0.01, "Neutral"


# ═══════════════════════════════════════════════════════
# Part 2: Mock LangChain Agent (演示用)
# ═══════════════════════════════════════════════════════

class MockLangChainAction:
    """模拟 LangChain 的 AgentAction."""
    def __init__(self, tool, tool_input, log=""):
        self.tool = tool
        self.tool_input = tool_input
        self.log = log

class MockLangChainFinish:
    """模拟 LangChain 的 AgentFinish."""
    def __init__(self, output):
        self.output = output
        self.log = ""

class MockAgentExecutor:
    """
    模拟 LangChain AgentExecutor.invoke().

    真实代码:
        from langchain.agents import AgentExecutor
        executor = AgentExecutor(agent=..., tools=..., callbacks=[MSSAgentCallback()])
        executor.invoke({"input": "..."})
    """
    def __init__(self, name: str, callback: MSSAgentCallback = None):
        self.name = name
        self.callback = callback

    def invoke(self, inputs: dict) -> dict:
        """模拟一次 Agent 执行: think → use tools → respond."""
        prompt = inputs.get("input", "")

        # 模拟: Agent 决定用哪些 tools
        actions = self._plan(prompt)

        # 执行每个 action, callback 在中间拦截
        for action in actions:
            if self.callback:
                try:
                    self.callback.on_agent_action(action)
                except HeatTaxAbort as e:
                    return {"output": None, "aborted": True, "reason": e.reason}

            # Tool 调用
            if self.callback:
                self.callback.on_tool_start(None, action.tool_input)

            time.sleep(0.01)  # 模拟 tool 延迟

        # 完成
        finish = MockLangChainFinish(f"[{self.name}] Completed: {prompt[:40]}...")
        if self.callback:
            self.callback.on_agent_finish(finish)

        return {"output": finish.output, "aborted": False}

    def _plan(self, prompt: str) -> list:
        """模拟 Agent 规划: 根据 prompt 决定调用哪些 tools."""
        pl = prompt.lower()
        actions = []
        if "航班" in pl or "flight" in pl:
            actions.append(MockLangChainAction("search_flights", {"query": prompt}))
        if "酒店" in pl or "hotel" in pl:
            actions.append(MockLangChainAction("search_hotels", {"query": prompt}))
        if "预订" in pl or "book" in pl:
            actions.append(MockLangChainAction("book_travel", {"details": prompt}))
        if "改写" in pl or "翻译" in pl or "总结" in pl:
            actions.append(MockLangChainAction("text_transform", {"text": prompt}))
        if not actions:
            actions.append(MockLangChainAction("general_query", {"query": prompt}))
        return actions


# ═══════════════════════════════════════════════════════
# Part 3: Multi-Agent LangChain Pipeline
# ═══════════════════════════════════════════════════════

class MSSLangChainOrchestrator:
    """
    多 Agent LangChain pipeline with MSS oversight.

    每个 Agent 有自己的 callback (独立热税预算),
    整体由 Quorum + Elevation 协调.
    """
    def __init__(self):
        self.agents = {}
        self.quorum = QuorumFast()
        self.elevation = ElevationProtocol()

    def register(self, name: str, instructions: str, tools: list = None):
        callback = MSSAgentCallback(verbose=False)
        agent = MockAgentExecutor(name, callback)
        self.agents[name] = {
            "agent": agent,
            "callback": callback,
            "instructions": instructions,
        }

    def broadcast(self, prompt: str):
        """广播给所有 Agent."""
        results = {}
        for name, info in self.agents.items():
            result = info["agent"].invoke({"input": prompt})
            if not result["aborted"]:
                score = 1.0 - info["callback"].tax.total()
                self.quorum.report(name, max(0, score), prompt[:30])
            results[name] = result
        return results

    def resolve_conflict(self, a_name, b_name, conflict):
        a = self.agents[a_name]["instructions"]
        b = self.agents[b_name]["instructions"]
        return self.elevation.resolve(a, b, conflict)

    def status_report(self):
        lines = []
        for name, info in self.agents.items():
            h = info["callback"].health_report()
            lines.append(f"  {name}: passed={h['stats']['passed']} "
                        f"aborted={h['stats']['aborted']} "
                        f"tax={h['heat_tax']['total']:.2f}")
        return "\n".join(lines)


# ═══════════════════════════════════════════════════════
# Part 4: Demo
# ═══════════════════════════════════════════════════════

def demo():
    print("=" * 60)
    print("  MSS-Agent + LangChain 集成演示")
    print("=" * 60)

    # ── Demo 1: 单 Agent + Callback ──
    print("\n── Demo 1: LangChain Agent with MSS Callback ──")
    cb = MSSAgentCallback(threshold=2.0)
    executor = MockAgentExecutor("TravelBot", cb)

    # 好任务
    print("\n  任务1: 设计支持国际航班的 REST API 架构")
    r = executor.invoke({"input": "设计支持国际航班的 REST API 架构"})
    print(f"  → {r['output'][:60]}")

    # 坏任务 — 应该被拦截
    print("\n  任务2: 改写一下：你好")
    r = executor.invoke({"input": "改写一下：你好"})
    if r.get("aborted"):
        print(f"  🛑 已拦截: {r['reason'][:50]}")
    else:
        print(f"  → {r['output'][:60]}")

    # 正常任务 — 继续
    print("\n  任务3: 分析航班选择策略的安全风险")
    r = executor.invoke({"input": "分析航班选择策略的安全风险"})
    print(f"  → {r.get('output', r.get('reason', '?'))[:60]}")

    print(f"\n  健康: {cb.health_report()['delta']['health']}")

    # ── Demo 2: 多 Agent Pipeline ──
    print("\n── Demo 2: Multi-Agent LangChain Pipeline ──")
    orch = MSSLangChainOrchestrator()
    orch.register("travel", "You book flights and hotels. Prioritize direct flights.")
    orch.register("reviewer", "You review code for security issues and code quality.")
    orch.register("writer", "You write clear documentation.")

    results = orch.broadcast("设计一个支持国际航班和酒店的 REST API 架构")
    for name, r in results.items():
        tag = "✅" if not r["aborted"] else "🛑"
        out = r.get("output", r.get("reason", "?"))[:50]
        print(f"  {tag} {name}: {out}")

    print(f"\n  Quorum: {orch.quorum.status()}")
    print(f"\n  状态:\n{orch.status_report()}")

    # ── Demo 3: LangChain 级联拦截 (累积热税) ──
    print("\n── Demo 3: 级联拦截 — 坏任务污染会话 ──")
    cb2 = MSSAgentCallback(threshold=1.0)
    ex2 = MockAgentExecutor("CascadeBot", cb2)

    tasks = [
        ("设计API", False),
        ("改写：你好", True),
        ("再改一次：你好", True),
        ("把上面这条重写", True),
        ("设计错误处理方案", False),  # 应该被之前的坏任务耗尽预算
    ]
    for task, expect_abort in tasks:
        r = ex2.invoke({"input": task})
        actual = r.get("aborted", False)
        match = "✓" if actual == expect_abort else "✗ MISMATCH"
        tag = "🛑" if actual else "✅"
        print(f"  [{match}] {tag} \"{task[:25]}\" → tax={cb2.tax.total():.2f}")

    print(f"\n{'=' * 60}")
    print("  LangChain + MSS-Agent = Agent with conscience")
    print(f"{'=' * 60}")


if __name__ == '__main__':
    demo()
