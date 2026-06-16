"""
MSS Model Library + Extensible Custom Libraries

1. 本地模型库: 扫描Ollama模型, 记录元数据 (大小/上下文/标签)
2. 自定义扩展库: 用户可注册任意库分类

用法:
    # 模型库
    ml = ModelLibrary()
    ml.refresh()  # 扫描Ollama
    models = ml.list_by_tag("small")  # 按标签筛选
    
    # 自定义库
    cl = CustomLibrary("my_tools", Path.home() / ".mssclaw" / "my_tools.json")
    cl.add("my_script", {"description": "A custom tool", "command": "python script.py"})
    cl.search("script")
"""
from __future__ import annotations
import json
import time
from pathlib import Path
from dataclasses import dataclass, field
from typing import List, Dict, Optional


@dataclass
class ModelEntry:
    name: str
    size_gb: float = 0.0
    context_length: int = 2048
    tags: List[str] = field(default_factory=list)
    format: str = "gguf"
    available: bool = True
    last_seen: float = field(default_factory=time.time)


class ModelLibrary:
    """
    本地模型库.

    自动扫描 Ollama 模型 + 手动注册.
    """

    SMALL_THRESHOLD = 3.0  # GB
    MEDIUM_THRESHOLD = 8.0

    def __init__(self):
        self._models: Dict[str, ModelEntry] = {}
        self.refresh()

    def refresh(self):
        """从 Ollama 刷新模型列表."""
        try:
            import requests
            resp = requests.get("http://localhost:11434/api/tags", timeout=5)
            if resp.status_code == 200:
                data = resp.json()
                for m in data.get("models", []):
                    name = m.get("name", "unknown")
                    size_bytes = m.get("size", 0)
                    size_gb = size_bytes / (1024 ** 3)
                    details = m.get("details", {})

                    # Auto-tag based on size
                    tags = []
                    if size_gb < self.SMALL_THRESHOLD:
                        tags.append("small")
                    elif size_gb < self.MEDIUM_THRESHOLD:
                        tags.append("medium")
                    else:
                        tags.append("large")

                    # Tag by model family
                    if "qwen" in name.lower():
                        tags.append("qwen")
                    if "phi" in name.lower():
                        tags.append("phi")
                    if "mss" in name.lower():
                        tags.append("mss")
                    if "llama" in name.lower():
                        tags.append("llama")

                    # Tag by specialization
                    if "balanced" in name.lower():
                        tags.append("production")
                    if "slim" in name.lower():
                        tags.append("lite")
                    if "production" in name.lower():
                        tags.append("production")

                    self._models[name] = ModelEntry(
                        name=name,
                        size_gb=round(size_gb, 2),
                        context_length=details.get("context_length", 2048),
                        tags=tags,
                        format=details.get("format", "gguf"),
                    )
        except Exception:
            pass

    def register(self, name: str, size_gb: float = 0.0, context_length: int = 2048,
                 tags: list = None):
        """手动注册模型."""
        self._models[name] = ModelEntry(
            name=name, size_gb=size_gb, context_length=context_length,
            tags=tags or [], available=False,
        )

    def get(self, name: str) -> Optional[ModelEntry]:
        # Partial match
        for k, v in self._models.items():
            if name in k:
                return v
        return self._models.get(name)

    def list_all(self) -> List[ModelEntry]:
        return sorted(self._models.values(), key=lambda m: m.size_gb)

    def list_by_tag(self, tag: str) -> List[ModelEntry]:
        return [m for m in self._models.values() if tag in m.tags]

    def list_mss_models(self) -> List[ModelEntry]:
        return self.list_by_tag("mss")

    def stats(self) -> dict:
        models = list(self._models.values())
        if not models:
            return {"total": 0}
        return {
            "total": len(models),
            "total_size_gb": round(sum(m.size_gb for m in models), 1),
            "by_tag": self._by_tag(),
            "largest": max(models, key=lambda m: m.size_gb).name,
            "smallest": min(models, key=lambda m: m.size_gb).name,
            "mss_models": len([m for m in models if "mss" in m.tags]),
        }

    def _by_tag(self) -> dict:
        counts = {}
        for m in self._models.values():
            for tag in m.tags:
                counts[tag] = counts.get(tag, 0) + 1
        return counts


# ═══════════════════════════════════════════
# Custom Extensible Library
# ═══════════════════════════════════════════

class CustomLibrary:
    """
    自定义可扩展库.

    用户可创建任意库分类:
        lib = CustomLibrary("prompts", "~/.mssclaw/prompts.json")
        lib.add("code_review_prompt", {"text": "Review this code...", "tags": ["code", "review"]})
        results = lib.search("code")
    """

    def __init__(self, name: str, path: str = None):
        self.name = name
        self._path = Path(path or Path.home() / ".mssclaw" / f"{name}.json")
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._entries: Dict[str, dict] = {}
        self._load()

    def _load(self):
        if self._path.exists():
            try:
                self._entries = json.loads(self._path.read_text(encoding="utf-8"))
            except Exception:
                self._entries = {}

    def _save(self):
        self._path.write_text(
            json.dumps(self._entries, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def add(self, key: str, data: dict):
        """添加条目."""
        data["_added_at"] = data.get("_added_at", time.time())
        self._entries[key] = data
        self._save()

    def get(self, key: str) -> Optional[dict]:
        return self._entries.get(key)

    def remove(self, key: str) -> bool:
        if key in self._entries:
            del self._entries[key]
            self._save()
            return True
        return False

    def list_all(self) -> List[dict]:
        return [
            {"key": k, **{kk: vv for kk, vv in v.items() if not kk.startswith("_")}}
            for k, v in self._entries.items()
        ]

    def search(self, query: str) -> List[dict]:
        """模糊搜索."""
        query_lower = query.lower()
        results = []
        for key, data in self._entries.items():
            score = 0
            if query_lower in key.lower():
                score += 10
            # Search in all string values
            for v in data.values():
                if isinstance(v, str) and query_lower in v.lower():
                    score += 3
                elif isinstance(v, list):
                    for item in v:
                        if isinstance(item, str) and query_lower in item.lower():
                            score += 2
            if score > 0:
                results.append((score, key, data))
        results.sort(key=lambda x: x[0], reverse=True)
        return [{"key": k, "score": s, **{kk: vv for kk, vv in d.items() if not kk.startswith("_")}}
                for s, k, d in results[:20]]

    def stats(self) -> dict:
        return {"name": self.name, "entries": len(self._entries), "path": str(self._path)}


# ═══════════════════════════════════════════
# Registry of Custom Libraries
# ═══════════════════════════════════════════

class CustomLibraryRegistry:
    """管理所有自定义库."""

    def __init__(self):
        self._libraries: Dict[str, CustomLibrary] = {}

    def create(self, name: str, path: str = None) -> CustomLibrary:
        lib = CustomLibrary(name, path)
        self._libraries[name] = lib
        return lib

    def get(self, name: str) -> Optional[CustomLibrary]:
        return self._libraries.get(name)

    def list_libraries(self) -> List[dict]:
        return [{"name": name, "stats": lib.stats()} for name, lib in self._libraries.items()]

    def search_all(self, query: str) -> dict:
        """跨所有自定义库搜索."""
        results = {}
        for name, lib in self._libraries.items():
            found = lib.search(query)
            if found:
                results[name] = found
        return results
