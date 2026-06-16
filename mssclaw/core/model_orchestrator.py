"""
Multi-Model Orchestrator — 多模型协同工作

用法:
    orch = ModelOrchestrator()
    orch.add_worker("writer", model="qwen2.5:7b", role="writer")
    orch.add_worker("reviewer", model="mss-ai-v3.4.3-balanced", role="reviewer")
    
    result = orch.run_pipeline("Write a security audit report")

模型分配策略:
  - auto: 根据任务类型自动选模型 (creative→大模型, simple→小模型)
  - manual: 手动指定每个角色的模型
  - pool: 从模型池中智能分配
"""
from __future__ import annotations
import time
import threading
from dataclasses import dataclass, field
from typing import Callable, Optional, List, Dict
from enum import Enum


class WorkerRole(Enum):
    WRITER = "writer"
    REVIEWER = "reviewer"
    REFINER = "refiner"
    RESEARCHER = "researcher"
    TRANSLATOR = "translator"
    CUSTOM = "custom"


@dataclass
class ModelWorker:
    """模型工人."""
    name: str
    model: str
    role: WorkerRole
    backend: object = None
    agent: object = None
    stats: dict = field(default_factory=lambda: {"tasks": 0, "total_ms": 0, "errors": 0})


@dataclass
class OrchestrationResult:
    success: bool
    steps: List[dict] = field(default_factory=list)
    final_output: str = ""
    total_time_ms: float = 0.0
    workers_used: List[str] = field(default_factory=list)


class ModelOrchestrator:
    """
    多模型编排器.

    支持:
      - 不同角色用不同模型
      - 模型池智能分配
      - 并行/串行执行
    """

    def __init__(self):
        self._workers: Dict[str, ModelWorker] = {}
        self._pool: List[str] = []

    def add_worker(self, name: str, model: str, role: str = "writer",
                   backend: object = None) -> ModelWorker:
        """注册一个模型工人."""
        from mssclaw.core.llm_backend import create_backend

        if backend is None:
            backend = create_backend("auto", model=model)

        worker = ModelWorker(
            name=name, model=model,
            role=WorkerRole(role) if role in [r.value for r in WorkerRole] else WorkerRole.CUSTOM,
            backend=backend,
        )

        # Create agent for this worker
        from mssclaw.core.agent import MSSAgent
        worker.agent = MSSAgent(name=name, llm=backend)

        self._workers[name] = worker
        if model not in self._pool:
            self._pool.append(model)

        return worker

    def remove_worker(self, name: str):
        self._workers.pop(name, None)

    def list_workers(self) -> List[dict]:
        return [
            {"name": w.name, "model": w.model, "role": w.role.value, "tasks": w.stats["tasks"]}
            for w in self._workers.values()
        ]

    def get_worker(self, role: str) -> Optional[ModelWorker]:
        """按角色获取工人."""
        for w in self._workers.values():
            if w.role.value == role:
                return w
        # Fallback: any available
        for w in self._workers.values():
            return w
        return None

    def auto_assign(self, task: str) -> ModelWorker:
        """
        智能分配: 根据任务类型选最优模型.

        规则:
          - 创意任务(写诗/故事) → poetry capable model
          - 技术任务(代码/审查) → largest available model
          - 简单任务 → smallest/fastest model
        """
        creative_keywords = ["诗", "故事", "创作", "写", "poem", "story", "create", "write"]
        tech_keywords = ["代码", "审查", "审计", "安全", "code", "review", "audit", "security"]

        task_lower = task.lower()
        is_creative = any(k in task_lower for k in creative_keywords)
        is_tech = any(k in task_lower for k in tech_keywords)

        if is_creative:
            # Prefer: mss model > 大模型 > any
            for w in self._workers.values():
                if "mss" in w.model.lower():
                    return w
            return max(self._workers.values(), key=lambda w: len(w.model))

        if is_tech:
            # Prefer: largest model
            return max(self._workers.values(), key=lambda w: len(w.model))

        # Default: smallest/fastest
        return min(self._workers.values(), key=lambda w: len(w.model))

    # ── Pipeline Execution ──

    def run_pipeline(self, prompt: str, roles: List[str] = None) -> OrchestrationResult:
        """
        执行多模型流水线.

        默认: writer → reviewer → refiner
        """
        t0 = time.time()
        roles = roles or ["writer", "reviewer", "refiner"]
        steps = []
        context = {"prompt": prompt, "input": prompt, "review": ""}
        used_workers = []

        for i, role in enumerate(roles):
            worker = self.get_worker(role)
            if not worker:
                # Auto-assign
                worker = self.auto_assign(prompt)
            if not worker:
                continue

            used_workers.append(worker.name)
            step_start = time.time()

            # Build instruction based on role
            if role == "writer":
                instruction = f"Write a thorough response to: {prompt}"
            elif role == "reviewer":
                instruction = (
                    f"Review the following for accuracy, safety, clarity:\n\n"
                    f"{context.get('input', prompt)}\n\n"
                    f"Output [PASS] or list specific issues."
                )
            elif role == "refiner":
                instruction = (
                    f"Refine based on review:\n\n"
                    f"Original: {context.get('input', prompt)}\n"
                    f"Review: {context.get('review', '')}\n\n"
                    f"Output improved version."
                )
            else:
                instruction = prompt

            # Execute
            result = worker.agent.run(instruction)
            elapsed = (time.time() - step_start) * 1000

            worker.stats["tasks"] += 1
            worker.stats["total_ms"] += elapsed
            if result.aborted:
                worker.stats["errors"] += 1

            step = {
                "role": role,
                "worker": worker.name,
                "model": worker.model,
                "output": result.output[:200],
                "elapsed_ms": round(elapsed, 1),
                "aborted": result.aborted,
                "delta": result.delta,
            }
            steps.append(step)

            # Update context
            if role == "writer":
                context["input"] = result.output
            elif role == "reviewer":
                context["review"] = result.output
                if "PASS" in result.output[:50]:
                    break  # Skip refiner

        final_output = steps[-1]["output"] if steps else ""
        total_ms = (time.time() - t0) * 1000

        return OrchestrationResult(
            success=True,
            steps=steps,
            final_output=final_output,
            total_time_ms=round(total_ms, 1),
            workers_used=list(set(used_workers)),
        )

    # ── Parallel Execution ──

    def run_parallel(self, tasks: List[str]) -> Dict[str, str]:
        """
        并行执行多个任务 (每个任务自动分配模型).

        tasks: ["task1", "task2", "task3"]
        返回: {task: output}
        """
        results = {}
        threads = []

        def _execute(task):
            worker = self.auto_assign(task)
            if worker:
                result = worker.agent.run(task)
                results[task] = result.output[:500]
            else:
                results[task] = "(no worker available)"

        for task in tasks:
            t = threading.Thread(target=_execute, args=(task,))
            t.start()
            threads.append(t)

        for t in threads:
            t.join(timeout=30)

        return results

    def stats(self) -> dict:
        return {
            "workers": len(self._workers),
            "models": len(self._pool),
            "pool": self._pool,
            "workers_detail": [
                {"name": w.name, "model": w.model, "role": w.role.value,
                 "tasks": w.stats["tasks"], "errors": w.stats["errors"]}
                for w in self._workers.values()
            ],
        }
