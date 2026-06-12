"""
Code-Agent — 编程执行者.

职责：
  - LLM 驱动的代码生成 (P1: wired to Ollama/DeepSeek)
  - Python/JS/Go 编码
  - pip 包发布、CI/CD 维护
  - 代码审计（安全+性能）
  - 自动化测试运行
"""
import json
from .base import BaseAgent
from ..swarm.protocol import Message, MessageType
from ..llm.providers import get_provider


class CodeAgent(BaseAgent):
    role = "Code-Agent"
    capabilities = ["coding", "python", "debugging", "ci_cd", "audit", "llm_generate"]

    def __init__(self, name: str = "CODE", workspace: str = "",
                 llm_model: str = "mss-ai-v3.4.3-balanced",
                 llm_provider: str = "ollama",
                 **kwargs):
        super().__init__(name=name, **kwargs)
        self._workspace = workspace
        self._llm = None
        self._llm_model = llm_model
        self._llm_provider = llm_provider

    def _register_handlers(self) -> None:
        self.swarm.on(MessageType.TASK_ASSIGN.value)(self._on_task)

    def _on_task(self, msg: Message) -> None:
        task_id = msg.payload.get("task_id", "")
        spec = msg.payload.get("spec", {})

        action = spec.get("action", "generate")  # 默认: LLM生成
        if action == "generate":
            result = self.generate_code(
                task_spec=spec,
                prompt=spec.get("prompt", spec.get("description", ""))
            )
            self.report(task_id, result, result.get("success", False))
        elif action == "audit":
            result = self.audit_code(spec.get("path", ""))
            self.report(task_id, result, result.get("ok", False))
        elif action == "run_tests":
            result = self.run_tests(spec.get("path", ""))
            self.report(task_id, result, result.get("passed", 0) == result.get("total", 0))
        elif action == "check_deps":
            result = self.check_dependencies()
            self.report(task_id, result, True)
        elif action == "build":
            result = {"built": True, "info": "Build placeholder"}
            self.report(task_id, result, True)
        else:
            self.report(task_id, {"error": f"Unknown action: {action}"}, False)

    def generate_code(self, task_spec: dict, prompt: str = "") -> dict:
        """LLM 驱动的代码生成 — 生产纪律层.

        CodeAgent 职责 (生产纪律):
          A3 热税   — 预算管理, 超额拒绝
          A6 Δ    — 趋势监测, 闭合预警
          Syntax  — 快速语法检查 (非审查)

        AuditAgent 职责 (质量审查):
          五维评分 — security/pollution/logic/code/style
          安全检测 — eval/exec/硬编码密钥
          上诉仲裁 — appeal 流程

        架构: CodeAgent 产出 → SwarmBus → AuditAgent 审查
        """
        # A3: 热税检查
        if self.heat.exceeded():
            return {
                "success": False,
                "error": f"Heat budget exceeded ({self.heat.total():.0%})",
                "mss_checks": {"heat_tax": round(self.heat.total(), 3)},
            }

        from ..core.heat_tax import HeatTaxLevel
        self.heat.charge(
            HeatTaxLevel.L1_LOGICAL,
            task_spec.get("estimated_tokens", 1000) * 0.01,
            f"generate: {task_spec.get('title', 'unknown')}"
        )

        # 懒初始化 LLM
        if self._llm is None:
            try:
                self._llm = get_provider(self._llm_provider, model=self._llm_model)
            except Exception as e:
                return {"success": False, "error": f"LLM init failed: {e}"}

        title = task_spec.get("title", "unnamed task")
        description = task_spec.get("description", prompt)
        language = task_spec.get("language", "Python")

        code_prompt = (
            f"Write {language} code for this task. Return ONLY the code, no explanation.\n\n"
            f"Task: {title}\n"
            f"Description: {description}\n"
        )
        if prompt:
            code_prompt += f"\nAdditional requirements: {prompt}"

        try:
            code = self._llm(code_prompt)
        except Exception as e:
            return {"success": False, "error": f"LLM generation failed: {e}"}

        # 快速语法检查 (效率优先 — 完整审查交给 AuditAgent)
        syntax_ok = self._quick_syntax_check(code, language)

        # A6 Δ: 趋势监测
        self.delta.tick(task_hash=f"gen:{title}", novelty_score=0.5, diversity_score=0.5)

        return {
            "success": len(code) > 20,
            "code": code,
            "chars": len(code),
            "language": language,
            "model": self._llm_model,
            "mss_checks": {
                "heat_tax": round(self.heat.total(), 3),
                "exceeded": self.heat.exceeded(),
                "delta_health": str(self.delta.health()),
                "syntax_ok": syntax_ok,
                "ready_for_audit": syntax_ok and not self.heat.exceeded(),
            },
        }

    def _quick_syntax_check(self, code: str, language: str) -> bool:
        """快速语法检查 (非深度审查 — 审查交给 AuditAgent)."""
        if not code or len(code) < 10:
            return False
        if language == "Python":
            try:
                compile(code, "<generated>", "exec")
                return True
            except SyntaxError:
                return False
        return True  # 非 Python 跳过语法检查

    def audit_code(self, path: str) -> dict:
        """代码审计 — 安全 + 规范 + 性能"""
        import os
        issues = []
        if path and os.path.exists(path):
            with open(path, encoding="utf-8") as f:
                lines = f.readlines()

            for i, line in enumerate(lines, 1):
                # 安全检查
                if "os.system(" in line or "subprocess.call(" in line:
                    issues.append({"line": i, "type": "SECURITY", "msg": "System call detected"})
                if "eval(" in line or "exec(" in line:
                    issues.append({"line": i, "type": "SECURITY", "msg": "Dynamic execution"})
                # 规范检查
                if len(line.rstrip()) > 120:
                    issues.append({"line": i, "type": "STYLE", "msg": f"Line too long ({len(line.rstrip())})"})

        return {
            "path": path,
            "ok": len([i for i in issues if i["type"] == "SECURITY"]) == 0,
            "issues": issues,
            "total_issues": len(issues),
        }

    def run_tests(self, path: str) -> dict:
        """运行测试（placeholder — 需要实际环境）"""
        return {"path": path, "passed": 0, "total": 0, "note": "Test runner placeholder"}

    def check_dependencies(self) -> dict:
        """检查依赖"""
        import importlib
        deps = {
            "torch": False, "transformers": False,
            "pydantic": False, "unsloth": False,
        }
        for dep in deps:
            try:
                importlib.import_module(dep.replace("-", "_"))
                deps[dep] = True
            except ImportError:
                pass
        return {"dependencies": deps, "all_ok": all(deps.values())}
