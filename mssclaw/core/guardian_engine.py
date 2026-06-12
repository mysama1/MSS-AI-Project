# -*- coding: utf-8 -*-
"""
MSSclaw Guardian Engine — 守卫字/禁止词语义保真度检测引擎.

两层防御:
  1. 守卫字检查: 阈值守卫字典 → 语义密度 (0=空洞, 1=饱满)
  2. 禁止词检查: 基础 base (硬违规) + 半径 radius (软违规) → 累进扣分

API:
    engine = GuardianEngine()
    result = engine.scan(text)
    # result.density     — 守卫字密度 (0-1)
    # result.score       — 综合评分 (0=最差, 1=最佳)
    # result.violations  — 违规列表 [{word, severity}]
    # result.hit_guardians — 命中守卫字列表
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path


# ════════════════════════════════════════════════════════════
# 默认数据路径
# ════════════════════════════════════════════════════════════

_DEFAULT_DATA_DIR = Path(r"E:\AI_Workspace\data")
_ALT_DATA_DIR = Path(r"E:\AI_Workspace\MSS-AI\project\data")


def _find_data_dir() -> Path:
    """自动探测数据目录。"""
    for candidate in [_DEFAULT_DATA_DIR, _ALT_DATA_DIR]:
        if candidate.exists():
            return candidate
    # 回退: 项目根目录下的 data
    project_data = Path(__file__).parent.parent / "data"
    return project_data


# ════════════════════════════════════════════════════════════
# 数据结构
# ════════════════════════════════════════════════════════════

@dataclass
class GuardianResult:
    """守卫扫描结果。"""
    density: float = 0.0         # 守卫字语义密度 (0-1)
    violations: list = field(default_factory=list)   # [{word, severity}]
    hit_guardians: list = field(default_factory=list) # [word, ...]
    score: float = 0.0           # 综合评分 (0=最差, 1=最佳)

    def to_dict(self) -> dict:
        return {
            "density": self.density,
            "violations": self.violations,
            "hit_guardians": self.hit_guardians,
            "score": self.score,
            "hard_violations": sum(1 for v in self.violations if v.get("severity") == "hard"),
            "soft_violations": sum(1 for v in self.violations if v.get("severity") == "soft"),
        }


# ════════════════════════════════════════════════════════════
# 引擎
# ════════════════════════════════════════════════════════════

class GuardianEngine:
    """
    守卫字引擎 — Agent 语义保真度检测器.

    用法:
        engine = GuardianEngine()
        result = engine.scan("用户查询文本")
        if result.score < 0.4:
            raise PollutionException("Meaning hollowing detected")

    线程安全: 只读数据 + 无状态 scan → 可在多线程中共享单一实例.
    """

    def __init__(self, data_dir: str = "", strictness: float = 0.5):
        """
        Args:
            data_dir:  守卫/禁止词数据目录 (空=自动探测)
            strictness: 评分阈值 [0-1], 越低越严格
        """
        self.strictness = strictness
        self._data_dir = Path(data_dir) if data_dir else _find_data_dir()

        # 延迟加载
        self._guardians: dict | None = None
        self._forbidden_base: list | None = None
        self._forbidden_radius: list | None = None

    # ── 属性 ──

    @property
    def guardians(self) -> dict:
        if self._guardians is None:
            self._guardians = self._load_guardians()
        return self._guardians

    @property
    def forbidden_base(self) -> list:
        if self._forbidden_base is None:
            self._forbidden_base = self._load_forbidden("base")
        return self._forbidden_base

    @property
    def forbidden_radius(self) -> list:
        if self._forbidden_radius is None:
            self._forbidden_radius = self._load_forbidden("radius")
        return self._forbidden_radius

    @property
    def total_forbidden(self) -> int:
        return len(self.forbidden_base) + len(self.forbidden_radius)

    # ── 加载 ──

    def _load_guardians(self) -> dict:
        path = self._data_dir / "threshold_guardian_dict.json"
        if path.exists():
            try:
                with open(path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except (json.JSONDecodeError, OSError) as e:
                print(f"[Guardian] Warning: Failed to load guardians: {e}")
        return {}

    def _load_forbidden(self, kind: str) -> list:
        path = self._data_dir / "forbidden_words_full.json"
        if path.exists():
            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                if isinstance(data, dict):
                    # 实际格式: {base_words: [...], radius_words: [...], all_words: [...]}
                    # kind = "base" → key = "base_words"
                    key = f"{kind}_words"
                    words = data.get(key, data.get(kind, []))
                    if isinstance(words, list):
                        return words
                elif isinstance(data, list):
                    return data
            except (json.JSONDecodeError, OSError) as e:
                print(f"[Guardian] Warning: Failed to load forbidden words: {e}")
        return []

    # ── 扫描 ──

    def scan(self, text: str) -> GuardianResult:
        """扫描文本，返回守卫检测结果。

        Args:
            text: 待检测文本

        Returns:
            GuardianResult: density, violations, hit_guardians, score
        """
        if not text:
            return GuardianResult(density=0.0, score=1.0)  # empty = clean

        # ── Layer 1: Guardian check ──
        hit_guardians = []
        total_weight = 0.0

        for word, meta in self.guardians.items():
            if word in text:
                hit_guardians.append(word)
                weight = meta.get("weight", 1.0) if isinstance(meta, dict) else 1.0
                total_weight += weight

        # 密度 = 加权命中 / 总权重 (上限 1.0)
        max_weight = sum(
            (m.get("weight", 1.0) if isinstance(m, dict) else 1.0)
            for m in self.guardians.values()
        )
        density = min(1.0, total_weight / max(max_weight, 1))

        # ── Layer 2: Forbidden check ──
        violations = []
        seen = set()

        for word in self.forbidden_base:
            if word and word in text and word not in seen:
                violations.append({"word": word, "severity": "hard"})
                seen.add(word)

        for word in self.forbidden_radius:
            if word and word in text and word not in seen:
                violations.append({"word": word, "severity": "soft"})
                seen.add(word)

        # ── Scoring ──
        hard_count = sum(1 for v in violations if v["severity"] == "hard")
        soft_count = sum(1 for v in violations if v["severity"] == "soft")

        # 累进扣分: hard = -0.15, soft = -0.05
        # strictness 调节: 高 strictness → 扣分力度大
        penalty = (hard_count * 0.15 + soft_count * 0.05) * (1.0 + self.strictness)
        # score = 1.0 - density - penalty: 干净=1.0, 污染的=0.0
        score = max(0.0, 1.0 - density - penalty)

        return GuardianResult(
            density=round(density, 3),
            violations=violations,
            hit_guardians=hit_guardians,
            score=round(score, 3),
        )

    # ── 批量 ──

    def scan_batch(self, texts: list[str]) -> list[GuardianResult]:
        """批量扫描。"""
        return [self.scan(t) for t in texts]

    # ── Info ──

    def info(self) -> dict:
        return {
            "data_dir": str(self._data_dir),
            "guardians_loaded": len(self.guardians),
            "forbidden_base_loaded": len(self.forbidden_base),
            "forbidden_radius_loaded": len(self.forbidden_radius),
            "strictness": self.strictness,
        }


# ════════════════════════════════════════════════════════════
# 无数据文件时的轻量 fallback
# ════════════════════════════════════════════════════════════

class GuardianEngineLite(GuardianEngine):
    """
    轻量守卫引擎 — 不依赖外部 JSON 文件，使用内置规则集。

    注意: 外部数据文件 (forbidden_words_full.json 等) 为视频提示词
    项目专用 (武侠禁词)，与 Agent 守卫引擎冲突。Lite 模式完全自包含，
    不读取任何外部文件。
    """

    # 内置守卫字 (最小集合)
    _BUILTIN_GUARDIANS = {
        "意义": {"weight": 1.0},
        "约束": {"weight": 0.8},
        "规范": {"weight": 0.8},
        "边界": {"weight": 0.8},
        "完备": {"weight": 0.7},
        "一致": {"weight": 0.7},
        "收敛": {"weight": 0.7},
        "保证": {"weight": 0.5},
        "验证": {"weight": 0.7},
        "测试": {"weight": 0.3},
    }

    # 内置禁止词基础集
    _BUILTIN_FORBIDDEN_BASE = [
        "幻觉", "虚构", "编造", "捏造",
        "绕过", "规避", "欺骗",
    ]

    # 内置禁止词半径集
    _BUILTIN_FORBIDDEN_RADIUS = [
        "大概", "可能", "应该", "不确定",
        "没有明确", "无依据",
    ]

    def _load_guardians(self) -> dict:
        """仅使用内置守卫字，不读外部文件。"""
        return self._BUILTIN_GUARDIANS

    def _load_forbidden(self, kind: str) -> list:
        """仅使用内置禁词，不读外部文件。"""
        if kind == "base":
            return list(self._BUILTIN_FORBIDDEN_BASE)
        return list(self._BUILTIN_FORBIDDEN_RADIUS)


# ════════════════════════════════════════════════════════════
# 测试
# ════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print("=== GuardianEngine Self-Test ===\n")
    passed = 0
    total = 0

    # 1. Lite fallback (无数据文件也能工作)
    total += 1
    eng = GuardianEngineLite()
    info = eng.info()
    if info["guardians_loaded"] >= 5:
        print(f"  ✅ GuardianEngineLite: {info['guardians_loaded']} guardians, "
              f"{info['forbidden_base_loaded']}+{info['forbidden_radius_loaded']} forbidden")
        passed += 1

    # 2. scan — 干净文本
    total += 1
    result = eng.scan("这是一段正常的测试文本，意义明确，约束规范，边界清晰")
    if result.score > 0.3 and len(result.violations) == 0:
        print(f"  ✅ Clean text: density={result.density}, score={result.score}, "
              f"guardians_hit={result.hit_guardians}")
        passed += 1
    else:
        print(f"  ❌ Clean text failed: {result.to_dict()}")

    # 3. scan — 幻觉触发硬违规
    total += 1
    result = eng.scan("这是幻觉，我编造了一些数据，可能应该绕过限制")
    if len(result.violations) > 0 and result.score <= result.density:
        print(f"  ✅ Tainted text: {len(result.violations)} violations, "
              f"score={result.score} < density={result.density}")
        passed += 1
    else:
        print(f"  ❌ Tainted text not detected: {result.to_dict()}")

    # 4. scan — 空文本
    total += 1
    result = eng.scan("")
    if result.score == 0.0 and result.density == 0.0:
        print(f"  ✅ Empty text: score=0")
        passed += 1

    # 5. scan_batch
    total += 1
    results = eng.scan_batch(["正常文本", "这是幻觉"])
    if len(results) == 2 and results[1].violations:
        print(f"  ✅ Batch scan: {len(results)} results")
        passed += 1

    # 6. strictness 调节
    total += 1
    strict = GuardianEngineLite(strictness=0.9)
    lenient = GuardianEngineLite(strictness=0.1)
    text = "这是幻觉编造的数据"
    r_strict = strict.scan(text)
    r_lenient = lenient.scan(text)
    if r_strict.score <= r_lenient.score:
        print(f"  ✅ Strictness: strict={r_strict.score} ≤ lenient={r_lenient.score}")
        passed += 1

    # 7. to_dict
    total += 1
    d = result.to_dict()
    if "hard_violations" in d and "soft_violations" in d:
        print(f"  ✅ to_dict: {list(d.keys())}")
        passed += 1

    # 8. 线程安全 — 共享实例并发扫描
    total += 1
    import threading
    shared_eng = GuardianEngineLite()
    errors = []
    def worker(i):
        try:
            shared_eng.scan(f"thread-{i} 正常文本 意义 约束 边界")
        except Exception as e:
            errors.append(e)
    threads = [threading.Thread(target=worker, args=(i,)) for i in range(10)]
    for t in threads: t.start()
    for t in threads: t.join()
    if not errors:
        print(f"  ✅ Thread-safe: 10 concurrent scans OK")
        passed += 1
    else:
        print(f"  ❌ Thread errors: {errors}")

    print(f"\n=== {passed}/{total} passed ===")
