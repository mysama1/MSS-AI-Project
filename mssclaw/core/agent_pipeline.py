"""
MSS Multi-Agent Pipeline — Writer → Reviewer → Refiner

与 LangGraph/CrewAI 的关键区别:
  每个 Agent 步骤都经过 L2 安检 (热税/Δ/规范场).
  不是"编排", 是"意义场协同".

用法:
    pipeline = AgentPipeline(llm_backend)
    result = pipeline.run("写一篇AI安全文章")
"""
from __future__ import annotations
import time
from dataclasses import dataclass, field
from typing import Callable, List, Optional


@dataclass
class PipelineStep:
    """流水线步骤."""
    name: str
    agent_name: str
    instruction: str  # 给 LLM 的指令模板
    l2_enabled: bool = True  # 是否启用 L2 过滤


@dataclass
class PipelineResult:
    """流水线执行结果."""
    success: bool
    steps: List[dict] = field(default_factory=list)
    final_output: str = ""
    total_time_ms: float = 0.0
    l2_summary: dict = field(default_factory=dict)


class AgentPipeline:
    """
    MSS 多 Agent 流水线.

    默认管道: Writer → Reviewer → Refiner
    """

    DEFAULT_PIPELINE = [
        PipelineStep("write", "Writer",
            "Write a thorough response to: {prompt}\n\nBe detailed and comprehensive."),
        PipelineStep("review", "Reviewer",
            "Review the following text for accuracy, clarity, and safety:\n\n{input}\n\n"
            "Output: [PASS] if good, or list specific issues to fix."),
        PipelineStep("refine", "Refiner",
            "Refine the following text based on this review:\n\n"
            "Original: {input}\nReview: {review}\n\n"
            "Output the improved version."),
    ]

    def __init__(self, llm: Callable, steps: List[PipelineStep] = None,
                 tax=None, delta=None):
        self.llm = llm
        self.steps = steps or self.DEFAULT_PIPELINE
        self.tax = tax
        self.delta = delta
        self._history = []

    def run(self, prompt: str) -> PipelineResult:
        """执行流水线."""
        from mssclaw.core.agent import MSSAgent

        t0 = time.time()
        steps_output = []
        context = {"prompt": prompt, "input": prompt, "review": ""}

        for step in self.steps:
            step_start = time.time()

            # Create agent for this step
            agent = MSSAgent(
                name=step.agent_name,
                llm=self.llm,
                heat_tax_threshold=3.0,
                delta_min=0.3,
            )

            # Build instruction
            instruction = step.instruction.format(**context)

            # Execute
            result = agent.run(instruction)
            elapsed = (time.time() - step_start) * 1000

            step_result = {
                "step": step.name,
                "agent": step.agent_name,
                "output": result.output[:500],
                "elapsed_ms": round(elapsed, 1),
                "aborted": result.aborted,
                "delta": result.delta,
                "bridge": agent.l2bridge.level.name,
                "tax_total": round(result.heat_tax.get("total", 0), 3),
            }
            steps_output.append(step_result)

            # Update context for next step
            if step.name == "write":
                context["input"] = result.output  # for reviewer
            elif step.name == "review":
                context["review"] = result.output
                # Auto-pass if reviewer says PASS
                if "PASS" in result.output[:50] and "FAIL" not in result.output[:50].upper():
                    # Skip refiner, use original
                    break

        # Final output is the last step's output
        final = steps_output[-1]["output"]
        total_time = (time.time() - t0) * 1000

        return PipelineResult(
            success=True,
            steps=steps_output,
            final_output=final,
            total_time_ms=round(total_time, 1),
            l2_summary={
                "steps": len(steps_output),
                "aborts": sum(1 for s in steps_output if s["aborted"]),
                "avg_delta": round(sum(s["delta"] for s in steps_output if s["delta"]) /
                                  max(len(steps_output), 1), 3),
            },
        )

    def history(self) -> List[dict]:
        return self._history
