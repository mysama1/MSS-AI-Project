"""
Video-Agent — 视频管线管理员.

职责：
  - ComfyUI 工作流管理
  - SFT 训练调度
  - 提示词质检
  - 模型版本追踪
"""
import json
import os
from .base import BaseAgent
from ..swarm.protocol import Message, MessageType


class VideoAgent(BaseAgent):
    role = "Video-Agent"
    capabilities = ["video", "comfyui", "sft_training", "prompt_qa", "model_tracking"]

    def __init__(self, name: str = "VIDEO",
                 comfyui_path: str = "E:\\ComfyUI",
                 models_path: str = "E:\\ComfyUI\\data\\models\\",
                 **kwargs):
        super().__init__(name=name, **kwargs)
        self._comfyui = comfyui_path
        self._models = models_path
        self._model_cache: dict[str, dict] = {}

    def _register_handlers(self) -> None:
        self.swarm.on(MessageType.TASK_ASSIGN.value)(self._on_task)

    def _on_task(self, msg: Message) -> None:
        task_id = msg.payload.get("task_id", "")
        spec = msg.payload.get("spec", {})

        action = spec.get("action", "status")
        if action == "status":
            result = self.get_status()
            self.report(task_id, result, True)
        elif action == "list_models":
            result = self.list_models(spec.get("model_type", "all"))
            self.report(task_id, result, True)
        elif action == "qa_prompt":
            result = self.qa_prompt(spec.get("prompt", ""))
            self.report(task_id, result, result.get("score", 0) >= 0.5)
        elif action == "track_sft":
            result = self.track_sft_runs()
            self.report(task_id, result, True)
        elif action == "check_workflow":
            result = self.check_workflow(spec.get("workflow", ""))
            self.report(task_id, result, result.get("valid", False))
        else:
            self.report(task_id, {"error": f"Unknown action: {action}"}, False)

    def get_status(self) -> dict:
        """获取 ComfyUI 状态"""
        return {
            "comfyui_path": self._comfyui,
            "models_path": self._models,
            "comfyui_exists": os.path.exists(self._comfyui),
            "models_exists": os.path.exists(self._models),
        }

    def list_models(self, model_type: str = "all") -> dict:
        """列出可用模型"""
        models = {"checkpoints": [], "loras": [], "vaes": []}
        mapping = {
            "checkpoints": ["checkpoints", "unet", "diffusion_models"],
            "loras": ["loras", "controlnet"],
            "vaes": ["vae"],
        }

        for key, dirs in mapping.items():
            if model_type not in ("all", key):
                continue
            for d in dirs:
                full_path = os.path.join(self._models, d)
                if os.path.isdir(full_path):
                    for f in os.listdir(full_path):
                        if f.endswith((".safetensors", ".ckpt", ".pt")):
                            models[key].append({"name": f, "dir": d})

        models["total"] = sum(len(v) for v in models.values())
        return models

    def qa_prompt(self, prompt: str) -> dict:
        """提示词质检 — 基于 MCP 检测规则"""
        checks = {
            "has_subject": bool(prompt),
            "sufficient_length": len(prompt) >= 10,
            "has_action": any(w in prompt for w in ["走", "跑", "站", "坐", "拿", "打", "看", "说"]),
            "has_detail": any(w in prompt for w in ["光", "色", "风", "雾", "影", "纹理"]),
            "has_camera": any(w in prompt for w in ["镜头", "视角", "特写", "远景", "中景"]),
        }
        score = sum(1 for v in checks.values() if v) / len(checks)
        suggestions = []
        if not checks["has_action"]:
            suggestions.append("建议添加动作描述")
        if not checks["has_detail"]:
            suggestions.append("建议添加环境/光影细节")
        if not checks["has_camera"]:
            suggestions.append("建议添加镜头指示")

        return {"prompt": prompt[:100], "score": round(score, 2), "checks": checks,
                "suggestions": suggestions}

    def track_sft_runs(self) -> dict:
        """追踪 SFT 训练运行"""
        runs = []
        sft_dir = os.path.join(os.path.dirname(self._comfyui), "..", "AI_Workspace",
                                "prompt-rewrite", "models")
        if os.path.exists(sft_dir):
            for d in os.listdir(sft_dir):
                full = os.path.join(sft_dir, d, "adapter_model.safetensors")
                if os.path.exists(full):
                    size_mb = os.path.getsize(full) / (1024 * 1024)
                    runs.append({"name": d, "adapter_mb": round(size_mb, 1),
                                 "path": full})
        return {"runs": runs, "total": len(runs)}

    def check_workflow(self, workflow_json: str) -> dict:
        """检查 ComfyUI 工作流有效性"""
        try:
            wf = json.loads(workflow_json) if isinstance(workflow_json, str) else workflow_json
            nodes = wf.get("nodes", []) if isinstance(wf, dict) else wf
            return {"valid": True, "node_count": len(nodes) if isinstance(nodes, list) else 0}
        except json.JSONDecodeError:
            return {"valid": False, "error": "Invalid JSON"}
