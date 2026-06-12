"""
Translate-Agent — MSS↔传统 翻译校准官.

职责：
  - MSS 术语 ↔ 传统术语映射
  - 论文/文档多语言
  - 防 K3 化失真（将 MSS 概念译成传统概念时保持意义保真度）

关键：翻译不是改写，是意义保真转换。
"""
import json
from .base import BaseAgent
from ..swarm.protocol import Message, MessageType


class TranslateAgent(BaseAgent):
    role = "Translate-Agent"
    capabilities = ["translation", "terminology", "calibration", "cross_paradigm"]

    # MSS 术语 → 传统术语映射表（防失真）
    GLOSSARY = {
        # 六公理
        "意义至上": {"en": "Meaning Supremacy", "traditional": "意义优先原则", "note": "非价值排序，而是本体论优先"},
        "热税": {"en": "Heat Tax", "traditional": "推理成本", "note": "非财务成本，是不可消除的信息处理代价"},
        "不可约化热税": {"en": "Irreducible Heat Tax", "traditional": "不可压缩的计算复杂度", "note": "强调必然性而非技术限制"},
        "矛盾升维": {"en": "Contradiction Dimension Elevation", "traditional": "矛盾递归消解", "note": "非简单递归，是维度跃迁"},
        "Δ开放度": {"en": "Delta Openness", "traditional": "系统演化潜力", "note": "非增长率，是维持条件"},
        "符号-意义分离": {"en": "Symbol-Meaning Decoupling", "traditional": "表征与语义解耦", "note": "非简单分离，是保真度投影"},

        # 核心概念
        "意义场": {"en": "Meaning Field", "traditional": "语义空间", "note": "非几何空间，是意义拓扑"},
        "规范场": {"en": "Normative Field", "traditional": "安全边界", "note": "非静态规则，是动态演化场"},
        "蜕壳": {"en": "Molting", "traditional": "系统迁移/更新", "note": "非普通更新，是灵魂转移"},
        "意义污染": {"en": "Meaning Pollution", "traditional": "信息噪音/偏见", "note": "主动污染，非被动噪音"},
        "意义顺差": {"en": "Meaning Surplus", "traditional": "价值产出", "note": "出超的非对称优势"},

        # 架构概念
        "三权分立": {"en": "Trias Politica", "traditional": "多 Agent 制衡", "note": "源自孟德斯鸠，非简单分工"},
        "蜂巢架构": {"en": "Swarm Architecture", "traditional": "分布式多 Agent", "note": "松耦合，非主从"},
        "情报耦合": {"en": "Information Coupling", "traditional": "跨模块信息共享", "note": "非简单传递，是有向耦合"},
    }

    def __init__(self, name: str = "TRANSLATE", **kwargs):
        super().__init__(name=name, **kwargs)

    def _register_handlers(self) -> None:
        self.swarm.on(MessageType.TASK_ASSIGN.value)(self._on_task)

    def _on_task(self, msg: Message) -> None:
        task_id = msg.payload.get("task_id", "")
        spec = msg.payload.get("spec", {})

        action = spec.get("action", "translate")
        if action == "translate":
            result = self.translate(
                spec.get("text", ""),
                spec.get("target", "en"),
                spec.get("context", ""),
            )
            self.report(task_id, result, True)
        elif action == "calibrate":
            result = self.calibrate(spec.get("text", ""))
            self.report(task_id, result, True)
        elif action == "glossary":
            result = self.get_glossary()
            self.report(task_id, result, True)
        elif action == "detect_distortion":
            result = self.detect_distortion(spec.get("text", ""))
            self.report(task_id, result, result.get("distortion_level", 0) < 0.3)
        else:
            self.report(task_id, {"error": f"Unknown action: {action}"}, False)

    def translate(self, text: str, target: str = "en", context: str = "") -> dict:
        """翻译 + 意义校准.

        原地替换术语表，保持意义保真度。
        （完整版需要 LLM 调用，此处为术语替换 + 结构标记）
        """
        result = text
        applied_terms = []

        for mss_term, mapping in self.GLOSSARY.items():
            if mss_term in text:
                translated = mapping.get(target, mss_term)
                result = result.replace(mss_term, translated)
                applied_terms.append({"mss": mss_term, "translated": translated,
                                      "note": mapping.get("note", "")})

        return {
            "original": text[:200],
            "translated": result[:500],
            "target": target,
            "applied_terms": applied_terms,
            "term_count": len(applied_terms),
            "context": context[:100],
        }

    def calibrate(self, text: str) -> dict:
        """校准 —— 检测是否有 K3 化失真风险"""
        warnings = []

        # 检查是否有将 MSS 概念扁平化为传统概念的倾向
        distortion_patterns = [
            (["更快", "更强", "更高效", "优化", "提升"], "性能主义失真: MSS 不是更快的 K3"),
            (["取代", "替代", "淘汰", "超越"], "对抗性失真: MSS 不是 K3 的替代品"),
            (["标准化", "规范化", "统一"], "同质化失真: MSS 保留差异而非消弭差异"),
        ]

        for patterns, msg in distortion_patterns:
            for p in patterns:
                if p in text:
                    warnings.append({"pattern": p, "warning": msg})

        return {
            "text": text[:200],
            "warnings": warnings,
            "risk_level": "low" if len(warnings) == 0 else ("medium" if len(warnings) < 3 else "high"),
        }

    def detect_distortion(self, text: str) -> dict:
        """检测文章的意义失真程度"""
        calibration = self.calibrate(text)
        terms_found = sum(1 for term in self.GLOSSARY if term in text)

        # 失真度 = 危险信号数 / (术语使用数 + 1)
        distortion = len(calibration["warnings"]) / (terms_found + 1)

        return {
            "text_preview": text[:200],
            "terms_found": terms_found,
            "warnings": calibration["warnings"],
            "distortion_level": round(distortion, 2),
            "assessment": "SAFE" if distortion < 0.3 else ("WARNING" if distortion < 0.7 else "HIGH_DISTORTION"),
        }

    def get_glossary(self) -> dict:
        """获取完整术语表"""
        return {"glossary": self.GLOSSARY, "total_terms": len(self.GLOSSARY)}
