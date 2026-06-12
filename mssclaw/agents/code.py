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
        """LLM 驱动的代码生成 (P1).
        
        Args:
            task_spec: {title, description, language, ...}
            prompt: 额外的提示词
        
        Returns:
            {success, code, language, chars, model}
        """
        # 懒初始化 LLM (延迟加载, 省资源)
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
            return {
                "success": len(code) > 20,
                "code": code,
                "chars": len(code),
                "language": language,
                "model": self._llm_model,
            }
        except Exception as e:
            return {"success": False, "error": f"LLM generation failed: {e}"}

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
