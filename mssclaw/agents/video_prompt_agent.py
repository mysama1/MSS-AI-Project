"""
mssclaw/agents/video_prompt_agent.py

视频提示词工程 Agent — Self-learning, iterative, personalized.

核心设计 (Pi Agent 范式):
  v1: 用户输入 → 生成提示词
  v2: 用户评分 → 学习偏好
  v3: 自动迭代 → 优化产出
  v4: 风格记忆 → 个性化模板

架构:
  PromptMemory  — 存储历史提示词 + 评分
  StyleLearner  — 从反馈中学习风格偏好
  PromptBuilder — 基于模板 + 风格生成提示词
  IterativeOptimizer — 多轮迭代优化

Competitive landscape:
  OctiAI — 通用 prompt generator, 非视频专项
  Prompt Optimizer — 开源单兵工具, 无学习能力
  Magic Hour — 视频生成器, prompt 非核心
  ComfyUI nodes — 工作流级, 无迭代学习
  → MSS 差异化: Personalized + Self-learning + Video-specific
"""
import json, os, time
from dataclasses import dataclass, field
from typing import Optional, Callable
from pathlib import Path

from ..agents.base import BaseAgent
from ..swarm.protocol import MessageType


# ── Data Models ──

@dataclass
class PromptRecord:
    """单条提示词记录."""
    prompt: str
    style: str = ""           # cinematic/anime/realistic/gufeng...
    category: str = ""        # character/scene/action/camera/lighting
    source_video: str = ""    # 产出的视频路径
    score: float = 0.0        # 用户评分 0-1
    feedback: str = ""        # 用户文字反馈
    iterations: int = 0       # 迭代轮次
    timestamp: float = field(default_factory=time.time)


@dataclass
class StyleProfile:
    """用户风格画像."""
    name: str = "default"
    preferred_styles: list = field(default_factory=list)    # ["cinematic","dark"]
    preferred_categories: list = field(default_factory=list) # ["camera","lighting"]
    keyword_weights: dict = field(default_factory=dict)      # {"epic": 0.9, "soft": 0.3}
    sample_count: int = 0
    avg_score: float = 0.0


# ── Core Components ──

class PromptMemory:
    """提示词记忆库 — 存储 + 检索历史提示词."""

    def __init__(self, db_path: str = "data/video_prompts.json"):
        self._path = Path(db_path)
        self._records: list[PromptRecord] = []
        self._load()

    def _load(self):
        if self._path.exists():
            self._records = [PromptRecord(**r) for r in json.loads(self._path.read_text(encoding="utf-8"))]

    def _save(self):
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._path.write_text(json.dumps([r.__dict__ for r in self._records], ensure_ascii=False, indent=2), encoding="utf-8")

    def add(self, record: PromptRecord):
        self._records.append(record)
        self._save()

    def search(self, style: str = "", category: str = "", min_score: float = 0.0, limit: int = 10) -> list[PromptRecord]:
        results = self._records
        if style:
            results = [r for r in results if style.lower() in r.style.lower()]
        if category:
            results = [r for r in results if category.lower() in r.category.lower()]
        results = [r for r in results if r.score >= min_score]
        return sorted(results, key=lambda r: r.score, reverse=True)[:limit]

    def top_prompts(self, n: int = 5) -> list[PromptRecord]:
        return sorted(self._records, key=lambda r: r.score, reverse=True)[:n]

    def stats(self) -> dict:
        if not self._records:
            return {"total": 0}
        scores = [r.score for r in self._records]
        styles = set(r.style for r in self._records if r.style)
        return {
            "total": len(self._records),
            "avg_score": sum(scores) / len(scores),
            "max_score": max(scores),
            "styles": sorted(styles),
            "recent": self._records[-1].prompt[:80] if self._records else "",
        }


class StyleLearner:
    """风格学习者 — 从反馈中提取用户偏好."""

    def __init__(self):
        self._profiles: dict[str, StyleProfile] = {}
        self._active = "default"
        self._profiles["default"] = StyleProfile()

    @property
    def profile(self) -> StyleProfile:
        return self._profiles[self._active]

    def switch(self, name: str):
        if name not in self._profiles:
            self._profiles[name] = StyleProfile(name=name)
        self._active = name

    def learn(self, record: PromptRecord):
        """从一条评分记录中学习."""
        p = self.profile
        p.sample_count += 1
        p.avg_score = (p.avg_score * (p.sample_count - 1) + record.score) / p.sample_count

        # 学习风格偏好 (高分 → 增加权重)
        if record.style and record.score > 0.5:
            if record.style not in p.preferred_styles:
                p.preferred_styles.append(record.style)

        # 学习关键词权重
        for word in record.prompt.lower().split():
            if len(word) > 3:
                current = p.keyword_weights.get(word, 0.5)
                p.keyword_weights[word] = current * 0.8 + record.score * 0.2

    def get_style_hints(self, min_score: float = 0.6) -> list[str]:
        """获取当前风格的提示词线索."""
        p = self.profile
        hints = []
        hints.extend(p.preferred_styles[:3])
        top_keywords = sorted(p.keyword_weights.items(), key=lambda x: x[1], reverse=True)[:5]
        hints.extend([k for k, v in top_keywords if v >= min_score])
        return hints


class PromptBuilder:
    """提示词构建器 — 基于模板 + 风格 + 历史生成."""

    def __init__(self, memory: PromptMemory = None, learner: StyleLearner = None):
        self.memory = memory or PromptMemory()
        self.learner = learner or StyleLearner()
        self._templates = {
            "character": "{subject}, {pose}, {clothing}, {expression}, {style} style, {lighting} lighting, {quality}",
            "scene": "{location}, {time}, {weather}, {atmosphere}, {style} style, {camera} angle, {quality}",
            "action": "{subject} {action}, {environment}, {style} style, {motion} motion, {camera}, {quality}",
            "composite": "{subject}, {clothing}, in {location}, {action}, {style} style, {lighting}, {camera}, {quality}",
        }

    def build(self, subject: str, category: str = "composite", 
              style: str = "", extra: dict = None, use_memory: bool = True) -> str:
        """构建提示词."""
        hints = self.learner.get_style_hints() if use_memory else []
        template = self._templates.get(category, self._templates["composite"])

        # 从记忆中获取最佳相似提示词
        best_past = ""
        if use_memory and self.memory._records:
            similar = self.memory.search(style=style, category=category, min_score=0.6, limit=3)
            if similar:
                best_past = f"(ref: {similar[0].prompt[:60]})"

        params = {
            "subject": subject,
            "style": style or "cinematic",
            "pose": extra.get("pose", "standing") if extra else "standing",
            "clothing": extra.get("clothing", "traditional hanfu") if extra else "traditional hanfu",
            "expression": extra.get("expression", "serene") if extra else "serene",
            "location": extra.get("location", "ancient palace courtyard") if extra else "ancient palace courtyard",
            "time": extra.get("time", "golden hour") if extra else "golden hour",
            "weather": extra.get("weather", "clear sky") if extra else "clear sky",
            "atmosphere": extra.get("atmosphere", "mystical") if extra else "mystical",
            "action": extra.get("action", "walking gracefully") if extra else "walking gracefully",
            "environment": extra.get("environment", "ancient Chinese garden") if extra else "ancient Chinese garden",
            "camera": extra.get("camera", "wide shot, low angle") if extra else "wide shot, low angle",
            "lighting": extra.get("lighting", "warm lantern light, soft shadows") if extra else "warm lantern light, soft shadows",
            "motion": extra.get("motion", "slow, fluid") if extra else "slow, fluid",
            "quality": "8K, masterpiece, highly detailed, ancient Chinese architecture",
        }
        if hints:
            params["style_hints"] = ", ".join(hints[:3])

        prompt = template.format(**params)
        if best_past:
            prompt = f"{prompt} {best_past}"
        return prompt


class IterativeOptimizer:
    """迭代优化器 — 基于反馈自动改进提示词."""

    def __init__(self, llm_fn: Callable[[str], str] = None):
        self.llm = llm_fn

    def optimize(self, original: str, feedback: str, target_style: str = "", 
                 max_iterations: int = 3) -> list[str]:
        """基于反馈迭代改进提示词. 返回所有版本."""
        versions = [original]
        current = original

        for i in range(max_iterations):
            if not self.llm:
                break

            optimize_prompt = (
                f"Improve this video generation prompt based on feedback.\n\n"
                f"Original prompt: {current}\n"
                f"Feedback: {feedback}\n"
                f"Target style: {target_style}\n\n"
                f"Return ONLY the improved prompt, keeping similar length and structure."
            )
            improved = self.llm(optimize_prompt)
            if improved and improved != current and len(improved) > 20:
                versions.append(improved)
                current = improved
            else:
                break

        return versions


# ── Agent ──

class VideoPromptAgent(BaseAgent):
    """视频提示词工程 Agent — Self-learning prompt engineer."""

    role = "prompt_engineer"
    capabilities = ["prompt_generation", "style_learning", "prompt_optimization"]

    def __init__(self, name="VideoPrompt", bus=None, db_path="data/video_prompts.json", llm_fn=None):
        super().__init__(name=name, bus=bus)
        self.memory = PromptMemory(db_path)
        self.learner = StyleLearner()
        self.builder = PromptBuilder(self.memory, self.learner)
        self.optimizer = IterativeOptimizer(llm_fn)
        self._current_task = None

    def _register_handlers(self):
        self.swarm.on(MessageType.TASK_ASSIGN.value)(self._on_assign)
        self.swarm.on(MessageType.REVIEW_RESULT.value)(self._on_review)

    def _on_assign(self, msg):
        self._current_task = msg.payload

    def _on_review(self, msg):
        pass

    # ── Public API ──

    def generate(self, subject: str, category: str = "composite", 
                 style: str = "gufeng", extra: dict = None) -> str:
        """生成一条视频提示词."""
        return self.builder.build(subject, category, style, extra)

    def learn(self, prompt: str, score: float, style: str = "", 
              feedback: str = "", category: str = ""):
        """从用户反馈中学习."""
        record = PromptRecord(
            prompt=prompt, style=style, category=category,
            score=score, feedback=feedback,
        )
        self.memory.add(record)
        self.learner.learn(record)

    def iterate(self, prompt: str, feedback: str, style: str = "") -> list[str]:
        """迭代优化一条提示词."""
        return self.optimizer.optimize(prompt, feedback, style)

    def get_style_hints(self) -> list[str]:
        return self.learner.get_style_hints()

    def get_memory_stats(self) -> dict:
        return self.memory.stats()

    def switch_style(self, name: str):
        self.learner.switch(name)

    def health_check(self) -> dict:
        return {
            "name": self.name,
            "memory": self.memory.stats(),
            "active_style": self.learner._active,
            "style_hints": self.learner.get_style_hints(),
        }
