"""
Product-Agent — 产品落地运营.

职责：
  - GitHub Pages/Wiki 维护
  - PyPI/npm 发布
  - 社区运营（Discussions/Issues）
  - 版本发布管理
"""
import json
import os
from .base import BaseAgent
from ..swarm.protocol import Message, MessageType


class ProductAgent(BaseAgent):
    role = "Product-Agent"
    capabilities = ["product", "publishing", "community", "release_management"]

    def __init__(self, name: str = "PRODUCT",
                 repo_path: str = "E:\\AI_Workspace\\MSS-AI",
                 **kwargs):
        super().__init__(name=name, **kwargs)
        self._repo = repo_path

    def _register_handlers(self) -> None:
        self.swarm.on(MessageType.TASK_ASSIGN.value)(self._on_task)

    def _on_task(self, msg: Message) -> None:
        task_id = msg.payload.get("task_id", "")
        spec = msg.payload.get("spec", {})

        action = spec.get("action", "status")
        if action == "status":
            result = self.check_status()
            self.report(task_id, result, True)
        elif action == "prepare_release":
            result = self.prepare_release(spec.get("version", "0.1.0"))
            self.report(task_id, result, result.get("ready", False))
        elif action == "check_docs":
            result = self.check_docs()
            self.report(task_id, result, True)
        elif action == "generate_changelog":
            result = self.generate_changelog()
            self.report(task_id, result, True)
        elif action == "sync_community":
            result = self.sync_community()
            self.report(task_id, result, True)
        else:
            self.report(task_id, {"error": f"Unknown action: {action}"}, False)

    def check_status(self) -> dict:
        """检查产品状态"""
        return {
            "repo": self._repo,
            "repo_exists": os.path.exists(self._repo),
            "docs": {
                "architecture": os.path.exists(os.path.join(self._repo, "..", "docs", "MSSCLAW_ARCHITECTURE_v02.md")),
                "reference": os.path.exists(os.path.join(self._repo, "..", "docs", "MSSCLAW_REFERENCE_REPORT.md")),
                "task_plan": os.path.exists(os.path.join(self._repo, "..", "docs", "MSSCLAW_TASK_PLAN.md")),
            },
        }

    def prepare_release(self, version: str) -> dict:
        """准备发布"""
        checklist = []
        project_dir = os.path.join(self._repo, "project", "mss_agent")

        # 检查 __init__.py
        init_file = os.path.join(project_dir, "__init__.py")
        checklist.append({"item": "__init__.py exists", "ok": os.path.exists(init_file)})

        # 检查核心模块
        modules = ["swarm/protocol.py", "swarm/swarm.py", "swarm/meeting_room.py",
                   "core/normative_field.py", "core/molting.py",
                   "agents/base.py", "agents/plan_agent.py",
                   "agents/kb_agent.py", "agents/code_agent.py",
                   "agents/video_agent.py", "agents/translate_agent.py",
                   "agents/product_agent.py"]
        for mod in modules:
            path = os.path.join(project_dir, mod)
            checklist.append({"item": mod, "ok": os.path.exists(path)})

        all_ok = all(c["ok"] for c in checklist)
        return {
            "version": version,
            "ready": all_ok,
            "checklist": checklist,
            "missing": [c["item"] for c in checklist if not c["ok"]],
        }

    def check_docs(self) -> dict:
        """检查文档完整性"""
        docs_dir = os.path.join(os.path.dirname(self._repo), "docs")
        expected = [
            "MSSCLAW_ARCHITECTURE_v02.md",
            "MSSCLAW_REFERENCE_REPORT.md",
            "MSSCLAW_TASK_PLAN.md",
            "ACTION_LANG_DECOUPLING.md",
            "PAPER_DRAFT_CCL2026_v2.md",
        ]
        present = []
        missing = []
        for doc in expected:
            path = os.path.join(docs_dir, doc)
            if os.path.exists(path):
                size = os.path.getsize(path)
                present.append({"name": doc, "size_kb": round(size / 1024, 1)})
            else:
                missing.append(doc)

        return {
            "docs_present": len(present),
            "docs_missing": len(missing),
            "present": present,
            "missing": missing,
            "coverage": round(len(present) / len(expected), 2),
        }

    def generate_changelog(self) -> dict:
        """生成变更日志"""
        return {
            "version": "0.2.0-dev",
            "date": "2026-06-11",
            "sections": [
                {"title": "新增", "items": [
                    "MSSclaw Swarm 蜂巢架构 (S-002)",
                    "NormativeField 自演化安全引擎 (S-003)",
                    "MeetingRoom 公共会议室 (S-004)",
                    "Molt Protocol 四种蜕壳模式 (S-005)",
                    "Plan-Agent 全局规划官 (S-006)",
                    "5 个专项 Agent: KB/Code/Video/Translate/Product (S-007)",
                ]},
                {"title": "文档", "items": [
                    "MSSCLAW_ARCHITECTURE_v02.md",
                    "MSSCLAW_REFERENCE_REPORT.md",
                    "MSSCLAW_TASK_PLAN.md",
                    "ACTION_LANG_DECOUPLING.md",
                ]},
            ],
        }

    def sync_community(self) -> dict:
        """同步社区状态（placeholder）"""
        return {
            "platforms": {
                "github": "mysama1/MSS-AI-Project",
                "pypi": "mss-agent / mss-vdp",
                "zenodo": "10.5281/zenodo.20602976",
                "miraheze": "mssai.miraheze.org",
            },
            "note": "Community sync requires manual API tokens",
        }
