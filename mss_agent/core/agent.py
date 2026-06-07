"""
MSS-Agent 核心基类 — 三层防御的自主 Agent.

每个 MSSAgent 实例携带:
  L0 热税预算 (A3) — 拒绝无意义任务
  L1 Δ检测协议 (A6) — 检测闭合, 触发蜕壳
  L2 记忆系统     — 不记住一切, 遗忘旧模式

Usage:
    agent = MSSAgent(name="Writer", llm=my_llm_fn)
    result = agent.run("写一篇关于 AI 安全的文章")
    if result.aborted:
        print(f"Agent 拒绝: {result.reason}")
    agent.health_report()
"""
from dataclasses import dataclass, field
from typing import Optional, Callable, Any
import hashlib
import time

from .heat_tax import HeatTaxBudget, HeatTaxLevel, HeatTaxAbort
from .delta import DeltaProtocol
from .memory import DeltaMemory


@dataclass
class AgentResult:
    """Agent 执行结果."""
    success: bool
    output: Any = None
    aborted: bool = False
    reason: str = ""
    heat_tax: dict = field(default_factory=dict)
    delta: float = 0.0
    elapsed_ms: float = 0.0


class MSSAgent:
    """
    MSS-Agent 基类.

    所有 Agent (Writer/Reviewer/Analyst) 继承此类.
    核心循环: think → heat_tax_check → act → delta_tick → remember

    Args:
        name: Agent 名称
        llm: LLM 调用函数 (prompt) -> str
        heat_tax_threshold: 热税预算上限 (default 0.5)
        delta_min: Δ 最低阈值 (default 0.3)
    """

    def __init__(
        self,
        name: str,
        llm: Optional[Callable[[str], str]] = None,
        heat_tax_threshold: float = 2.0,
        delta_min: float = 0.3,
    ):
        self.name = name
        self.llm = llm or (lambda p: f"[{name}] LLM not configured. Prompt: {p[:80]}...")
        self.tax = HeatTaxBudget(threshold=heat_tax_threshold)
        self.delta = DeltaProtocol(min_delta=delta_min)
        self.memory = DeltaMemory()
        self.run_count = 0
        self.abort_count = 0

    def _task_hash(self, prompt: str) -> str:
        return hashlib.md5(prompt.encode()).hexdigest()[:12]

    def _estimate_meaning_heat(self, prompt: str) -> tuple[float, str]:
        """
        评估任务的意义热税. 基于 LLM 自省.

        高意义热税 = 任务可能在浪费生命.
        启发式:
          - 空 prompt / 纯废话 → high heat
          - 含 '为什么' / '怎么' / '分析' → low heat (有意义)
          - <=20 chars → suspicious

        Returns (heat_value, reason). heat_value: 0.0=very meaningful, 1.0=meaningless.
        Note: L2 weight is 1000x, so even 0.001 matters. Calibrate carefully.
        """
        prompt_lower = prompt.lower().strip()

        # Heuristic: meaningful keywords reduce heat tax
        meaning_signals = ["为什么", "怎么", "分析", "评估", "设计", "实现",
                           "why", "how", "analyze", "design", "implement",
                           "review", "refactor", "test", "debug"]
        meaning_score = sum(1 for s in meaning_signals if s in prompt_lower)

        # Wasted-life signals increase heat tax
        waste_signals = ["帮我写", "改写一下", "翻译成", "总结一下", "简短点"]
        waste_score = sum(1 for s in waste_signals if s in prompt_lower)

        if len(prompt) < 5:
            return 0.08, "Prompt <5 chars: likely trivial"

        if waste_score > meaning_score and waste_score >= 2:
            return 0.05, "Task smells like busywork (high waste signals)"

        if meaning_score >= 2:
            return 0.002, "Task has clear meaningful intent"

        if meaning_score >= 1:
            return 0.005, "Task has some meaningful intent"

        return 0.01, "Task assessed as neutral"

    def run(self, prompt: str) -> AgentResult:
        """
        运行 Agent 的核心循环.

        1. 评估意义热税 → 如果过高 → 拒绝
        2. 执行 LLM 调用
        3. 记录热税
        4. Δ tick + memory store
        """
        t0 = time.time()
        self.run_count += 1
        task_hash = self._task_hash(prompt)

        # L2: 意义热税评估
        meaning_heat, meaning_reason = self._estimate_meaning_heat(prompt)
        self.tax.charge(HeatTaxLevel.L2_MEANING, meaning_heat, meaning_reason)

        if self.tax.l2_dominant() and meaning_heat > 0.05:
            self.abort_count += 1
            return AgentResult(
                success=False, aborted=True,
                reason=f"Task has LOW meaning: {meaning_reason}",
                heat_tax=self.tax.snapshot(),
                elapsed_ms=(time.time() - t0) * 1000,
            )

        # L1: Check total budget
        if self.tax.exceeded():
            self.abort_count += 1
            return AgentResult(
                success=False, aborted=True,
                reason=f"Heat tax budget exceeded: {self.tax.total():.3f}",
                heat_tax=self.tax.snapshot(),
                elapsed_ms=(time.time() - t0) * 1000,
            )

        # Execute
        try:
            output = self.llm(prompt)
        except Exception as e:
            self.tax.charge(HeatTaxLevel.L1_LOGICAL, 0.05, f"LLM error: {str(e)[:60]}")
            return AgentResult(
                success=False, aborted=True, reason=str(e),
                heat_tax=self.tax.snapshot(),
                elapsed_ms=(time.time() - t0) * 1000,
            )

        # L1: Charge logical heat (token count proxy)
        token_estimate = len(output) / 4  # ~4 chars per token
        self.tax.charge(HeatTaxLevel.L1_LOGICAL, token_estimate * 0.0001, f"{int(token_estimate)} tokens")

        # L0: Physical heat (always tiny)
        elapsed = (time.time() - t0) * 1000
        self.tax.charge(HeatTaxLevel.L0_PHYSICAL, elapsed * 0.00001, f"{elapsed:.0f}ms")

        # Δ tick: novelty + diversity → delta
        novelty = self.memory.novelty_score(prompt)
        diversity = self.memory.diversity_score()
        current_delta = self.delta.tick(task_hash, novelty, diversity)

        # Store in memory
        self.memory.store(prompt, current_delta)

        return AgentResult(
            success=True,
            output=output,
            aborted=False,
            heat_tax=self.tax.snapshot(),
            delta=current_delta,
            elapsed_ms=elapsed,
        )

    def health_report(self) -> dict:
        """输出 Agent 健康报告."""
        return {
            "agent": self.name,
            "runs": self.run_count,
            "aborts": self.abort_count,
            "abort_rate": round(self.abort_count / max(self.run_count, 1), 3),
            "heat_tax": self.tax.snapshot(),
            "delta": self.delta.snapshot(),
            "memory": self.memory.stats(),
        }

    def reset(self):
        """重置 Agent (保留 memory)."""
        self.tax = HeatTaxBudget(threshold=self.tax.threshold)
        self.delta = DeltaProtocol(min_delta=self.delta.min_delta)
        self.run_count = 0
        self.abort_count = 0
