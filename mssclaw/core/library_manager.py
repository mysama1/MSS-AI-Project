"""
MSS Library Manager — 统一库管理 + 跨库检索

管理所有库:
  工具库 (ToolRegistry)     — 7 tools
  技能库 (SkillRegistry)    — 5 preset + compiled
  知识库 (kbs)              — 618 entries
  免疫库 (HerdImmunity)     — vaccine signatures
  Agent库 (AgentAbsorber)   — absorbed agents
  会话库 (SessionPersistence) — saved sessions

功能:
  - 分类隔离 (每个库独立命名空间)
  - 跨库检索 (search "security" → 工具+技能+知识+免疫)
  - 引用追踪 (技能 → 工具依赖图)
  - 版本元数据
"""
from __future__ import annotations
import json
import time
from pathlib import Path
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any


@dataclass
class LibraryEntry:
    """统一库条目."""
    key: str
    library: str          # tools | skills | kb | immunity | agents | sessions
    name: str
    description: str = ""
    tags: List[str] = field(default_factory=list)
    references: List[str] = field(default_factory=list)  # 依赖的其他库条目
    version: str = "1.0"
    created_at: float = field(default_factory=time.time)


class LibraryManager:
    """
    统一库管理器.

    用法:
        lm = LibraryManager()
        lm.register("tools", "calculator", "Math evaluation", tags=["math", "safe"])
        results = lm.search("security")  # 跨库检索
        deps = lm.dependencies("skills/code_review")  # 依赖图
    """

    def __init__(self):
        self._libraries: Dict[str, Dict[str, LibraryEntry]] = {
            "tools": {},
            "skills": {},
            "kb": {},
            "models": {},
            "immunity": {},
            "agents": {},
            "sessions": {},
        }
        self._scan_all()

    # ── Registration ──

    def register(self, library: str, key: str, name: str,
                 description: str = "", tags: list = None,
                 references: list = None):
        """注册一个库条目."""
        if library not in self._libraries:
            self._libraries[library] = {}

        entry = LibraryEntry(
            key=key, library=library, name=name,
            description=description,
            tags=tags or [],
            references=references or [],
        )
        self._libraries[library][key] = entry
        return entry

    def get(self, library: str, key: str) -> Optional[LibraryEntry]:
        return self._libraries.get(library, {}).get(key)

    # ── Scanning ──

    def _scan_all(self):
        """自动扫描所有库."""
        self._scan_tools()
        self._scan_skills()
        self._scan_kb()
        self._scan_models()

    def _scan_tools(self):
        try:
            from .tool_registry import ToolRegistry, register_builtin_tools
            tools = ToolRegistry()
            register_builtin_tools(tools)
            for name, tool in tools._tools.items():
                self.register(
                    "tools", name, name,
                    description=tool.description,
                    tags=[tool.category],
                )
        except Exception:
            self.register("tools", "calculator", "calculator", tags=["safe"])
            self.register("tools", "datetime", "datetime", tags=["safe"])
            self.register("tools", "kb_search", "kb_search", tags=["safe"])

    def _scan_skills(self):
        try:
            from .skill_registry import SkillRegistry
            skills = SkillRegistry()
            for name, skill in skills._skills.items():
                self.register(
                    "skills", name, skill.description,
                    tags=[skill.category],
                    references=[f"tools/{t}" for t in skill.tools],
                )
        except Exception:
            self.register("skills", "code_review", "Code review", tags=["general"])

    def _scan_kb(self):
        try:
            self.register("kb", "kb_main", "MSS Knowledge Base",
                         description="618 entries across 7 layers",
                         tags=["knowledge", "mss", "research"])
        except Exception:
            pass

    def _scan_models(self):
        try:
            from .model_library import ModelLibrary
            ml = ModelLibrary()
            for entry in ml.list_all():
                self.register(
                    "models", entry.name, entry.name,
                    description=f"{entry.size_gb}GB | ctx={entry.context_length} | {entry.format}",
                    tags=entry.tags,
                )
        except Exception:
            pass

    # ── Cross-Library Search ──

    def search(self, query: str, libraries: list = None) -> List[LibraryEntry]:
        """
        跨库检索.

        query: 搜索词
        libraries: 限定库 (None = 全部)
        """
        results = []
        query_lower = query.lower()
        libs = libraries or list(self._libraries.keys())

        for lib in libs:
            for key, entry in self._libraries.get(lib, {}).items():
                score = 0
                # Name match
                if query_lower in entry.name.lower():
                    score += 10
                if query_lower in key.lower():
                    score += 8
                # Description match
                if query_lower in entry.description.lower():
                    score += 5
                # Tag match
                for tag in entry.tags:
                    if query_lower in tag.lower():
                        score += 3

                if score > 0:
                    results.append((score, entry))

        results.sort(key=lambda x: x[0], reverse=True)
        return [entry for _, entry in results[:20]]

    # ── Dependencies ──

    def dependencies(self, lib_key: str) -> dict:
        """
        获取库条目的依赖关系.

        lib_key: "skills/code_review" or "tools/calculator"
        """
        parts = lib_key.split("/", 1)
        if len(parts) != 2:
            return {"error": "format: library/key"}

        lib, key = parts
        entry = self.get(lib, key)
        if not entry:
            return {"error": f"not found: {lib_key}"}

        # What does this depend on?
        depends_on = []
        for ref in entry.references:
            r_parts = ref.split("/", 1)
            if len(r_parts) == 2:
                r_entry = self.get(r_parts[0], r_parts[1])
                if r_entry:
                    depends_on.append({
                        "key": ref,
                        "name": r_entry.name,
                        "library": r_entry.library,
                    })

        # What depends on this?
        used_by = []
        for olib, oentries in self._libraries.items():
            for okey, oentry in oentries.items():
                for ref in oentry.references:
                    if ref == lib_key or ref.startswith(f"{lib}/{key}"):
                        used_by.append({
                            "key": f"{olib}/{okey}",
                            "name": oentry.name,
                        })

        return {
            "entry": {"key": lib_key, "name": entry.name, "library": lib},
            "depends_on": depends_on,
            "used_by": used_by,
        }

    # ── Stats ──

    def stats(self) -> dict:
        return {
            "libraries": {
                lib: len(entries)
                for lib, entries in self._libraries.items()
            },
            "total": sum(len(e) for e in self._libraries.values()),
        }

    def catalog(self, library: str = None) -> dict:
        """库目录."""
        libs = [library] if library else list(self._libraries.keys())
        result = {}
        for lib in libs:
            entries = self._libraries.get(lib, {})
            result[lib] = [
                {
                    "key": e.key,
                    "name": e.name,
                    "tags": e.tags,
                    "refs": e.references,
                }
                for e in entries.values()
            ]
        return result


def cmd_library(args_rest):
    """CLI: 库管理."""
    lm = LibraryManager()

    if not args_rest:
        s = lm.stats()
        print("MSS Libraries")
        print("─" * 20)
        for lib, count in s["libraries"].items():
            print(f"  {lib:12s}: {count} entries")
        print(f"  {'total':12s}: {s['total']}")
        return

    cmd = args_rest[0]
    query = " ".join(args_rest[1:]) if len(args_rest) > 1 else ""

    if cmd == "search" and query:
        results = lm.search(query)
        print(f"Search '{query}': {len(results)} results")
        for r in results:
            print(f"  [{r.library}] {r.key}: {r.name} [{','.join(r.tags)}]")

    elif cmd == "export":
        import json as _j
        manifest = {
            "name": "mssclaw", "version": "0.3.0",
            "exported_at": time.time(),
            "libraries": {}
        }
        for lib, entries in lm._libraries.items():
            manifest["libraries"][lib] = [
                {"key": e.key, "name": e.name, "tags": e.tags, "refs": e.references}
                for e in entries.values()
            ]
        path = Path.home() / ".mssclaw" / "ecosystem.json"
        path.parent.mkdir(exist_ok=True)
        path.write_text(_j.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"Exported to {path}")
        print(f"  {sum(len(e) for e in manifest['libraries'].values())} entries across {len(manifest['libraries'])} libraries")

    elif cmd == "deps" and query:
        deps = lm.dependencies(query)
        if "error" in deps:
            print(deps["error"])
        else:
            e = deps["entry"]
            print(f"{e['library']}/{e['key']}: {e['name']}")
            if deps["depends_on"]:
                print("  Depends on:")
                for d in deps["depends_on"]:
                    print(f"    → {d['key']} ({d['name']})")
            if deps["used_by"]:
                print("  Used by:")
                for u in deps["used_by"]:
                    print(f"    ← {u['key']} ({u['name']})")

    elif cmd == "catalog":
        lib = args_rest[1] if len(args_rest) > 1 else None
        cat = lm.catalog(lib)
        for lib_name, entries in cat.items():
            print(f"\n[{lib_name}]")
            for e in entries:
                refs = f" → {e['refs']}" if e['refs'] else ""
                print(f"  {e['key']}: {e['name']}{refs}")

    else:
        print("mssclaw library [search|deps|catalog]")
