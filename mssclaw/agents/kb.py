"""
KB-Agent — 知识库守护者.

职责：
  - H 条目维护、编号分配、缺口扫描
  - 跨 Agent 知识检索
  - 知识一致性校验（防 H180/H455 漂移）
  - 新知识入库质检
"""
from .base import BaseAgent
from ..swarm.protocol import Message, MessageType


class KBAgent(BaseAgent):
    role = "KB-Agent"
    capabilities = ["kb_management", "search", "consistency", "archiving"]

    def __init__(self, name: str = "KB", kb_path: str = "", **kwargs):
        super().__init__(name=name, **kwargs)
        self._kb_path = kb_path or "data/knowledge_base/"
        self._index: dict[str, dict] = {}  # h_id → metadata
        self._gaps: list[str] = []

    def _register_handlers(self) -> None:
        self.swarm.on(MessageType.TASK_ASSIGN.value)(self._on_task)

    def _on_task(self, msg: Message) -> None:
        task_id = msg.payload.get("task_id", "")
        spec = msg.payload.get("spec", {})

        action = spec.get("action", "search")
        if action == "search":
            result = self.search(spec.get("query", ""))
            self.report(task_id, result, True)
        elif action == "scan_gaps":
            gaps = self.scan_gaps()
            self.report(task_id, {"gaps": gaps}, True)
        elif action == "add_entry":
            ok = self.add_entry(spec.get("entry", {}))
            self.report(task_id, {"added": ok}, ok)
        elif action == "check_consistency":
            issues = self.check_consistency()
            self.report(task_id, {"issues": issues}, len(issues) == 0)
        elif action == "find_related":
            result = self.find_related(spec.get("h_id", ""))
            self.report(task_id, result, True)
        else:
            self.report(task_id, {"error": f"Unknown action: {action}"}, False)

    def search(self, query: str) -> dict:
        """搜索知识库"""
        q = query.lower()
        matches = []
        for h_id, meta in self._index.items():
            if q in json.dumps(meta, ensure_ascii=False).lower():
                matches.append({"h_id": h_id, "title": meta.get("title", ""),
                                "layer": meta.get("layer", 0)})
        return {"query": query, "matches": matches[:20], "total": len(matches)}

    def scan_gaps(self) -> list[dict]:
        """扫描知识缺口"""
        # 检查编号连续性
        sorted_ids = sorted(
            [k for k in self._index if k.startswith("H")],
            key=lambda x: int(x[1:]) if x[1:].isdigit() else 0,
        )
        gaps = []
        for i in range(len(sorted_ids) - 1):
            try:
                curr = int(sorted_ids[i][1:])
                next_id = int(sorted_ids[i + 1][1:])
                if next_id - curr > 1:
                    for gap in range(curr + 1, next_id):
                        gaps.append({"missing": f"H{gap}", "between": [sorted_ids[i], sorted_ids[i + 1]]})
            except ValueError:
                continue
        return gaps

    def add_entry(self, entry: dict) -> bool:
        """添加入库条目"""
        h_id = entry.get("h_id", "")
        if not h_id:
            return False
        self._index[h_id] = entry
        return True

    def check_consistency(self) -> list[dict]:
        """检查条目间一致性"""
        issues = []
        # 检查重复标题
        titles: dict[str, list] = {}
        for h_id, meta in self._index.items():
            title = meta.get("title", "")
            titles.setdefault(title, []).append(h_id)
        for title, ids in titles.items():
            if len(ids) > 1 and title:
                issues.append({"type": "duplicate_title", "h_ids": ids, "title": title})
        return issues

    def find_related(self, h_id: str) -> dict:
        """查找相关条目"""
        entry = self._index.get(h_id, {})
        return {"h_id": h_id, "entry": entry, "related": []}


import json  # noqa: E402
