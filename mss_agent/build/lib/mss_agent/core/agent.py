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
        评估任务的意义热税。

        启发式分层:
          1. 空/极短 → 拒绝
          2. 纯废话模式 → 高税 (改写/换个说法/重写/翻译/总结…)
          3. 有意义关键词 → 低税
          4. 默认 → 中性
        """
        prompt_lower = prompt.lower().strip()
        plen = len(prompt)

        # Layer 0: Empty or near-empty → refuse
        if plen < 5:
            return 0.08, "Prompt <5 chars: likely trivial"

        # Meaningful keywords
        meaning_signals = [
            "为什么", "怎么", "分析", "评估", "设计", "实现", "方案",
            "安全", "风险", "架构", "优化", "策略", "审查", "测试",
            "why", "how", "analyze", "design", "implement", "architecture",
            "review", "refactor", "test", "debug", "security",
        ]
        meaning_score = sum(1 for s in meaning_signals if s in prompt_lower)

        # Busywork/waste patterns — these signal meaningless work
        waste_patterns = [
            # Chinese
            "改写", "重写", "换个说法", "换一种说法", "重新说",
            "总结", "翻译", "简短点", "简化", "缩写",
            "再改", "再说", "重新写", "重来",
            # English
            "rewrite", "rephrase", "reword", "summarize",
            "translate", "shorten", "simplify", "again", "retry",
            "one more", "just", "quick",
        ]
        waste_score = sum(1 for s in waste_patterns if s in prompt_lower)

        # Layer 1: Busywork detection — single waste signal + short/no meaning = refuse
        if waste_score >= 2:
            return 0.06, "Multiple busywork patterns detected"
        if waste_score >= 1 and meaning_score == 0 and plen < 50:
            return 0.06, "Busywork: no meaningful intent in short prompt"

        # Layer 2: Too short with no meaning signals
        if plen < 20 and meaning_score == 0:
            return 0.04, "Very short prompt with no clear intent"

        # Layer 3: Meaningful — reduce heat
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
