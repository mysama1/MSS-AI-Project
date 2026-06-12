"""
Code-Agent — 编程执行者.

职责：
  - Python/JS/Go 编码
  - pip 包发布、CI/CD 维护
  - 代码审计（安全+性能）
  - 自动化测试运行
"""
import json
from .base import BaseAgent
from ..swarm.protocol import Message, MessageType


class CodeAgent(BaseAgent):
    role = "Code-Agent"
    capabilities = ["coding", "python", "debugging", "ci_cd", "audit"]

    def __init__(self, name: str = "CODE", workspace: str = "", **kwargs):
        super().__init__(name=name, **kwargs)
        self._workspace = workspace

    def _register_handlers(self) -> None:
        self.swarm.on(MessageType.TASK_ASSIGN.value)(self._on_task)

    def _on_task(self, msg: Message) -> None:
        task_id = msg.payload.get("task_id", "")
        spec = msg.payload.get("spec", {})

        action = spec.get("action", "audit")
        if action == "audit":
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
