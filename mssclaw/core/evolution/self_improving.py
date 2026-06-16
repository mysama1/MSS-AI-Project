"""
mssclaw/core/self_improving.py

Hermes-inspired: Generalized Learning Loop + FTS5 Search + Cron Scheduler.

v1.1: FTS5 jieba CJK tokenizer integration.

1. SkillLearner    — 泛化学习循环 (从 VideoPromptAgent 中提取)
2. FTS5KB          — SQLite FTS5 知识库全文搜索 (v1.1: jieba CJK)
3. CronScheduler   — 定时任务调度器

Usage:
    from mssclaw.core.self_improving import SkillLearner, FTS5KB, CronScheduler
"""
import json, os, time, sqlite3, threading
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional, Callable
from collections import defaultdict


# ══════════════════════════════════════════
# 1. SkillLearner — 泛化自学习引擎
# ══════════════════════════════════════════

@dataclass
class SkillRecord:
    """通用技能记录 (泛化了 PromptRecord)."""
    skill_type: str           # "prompt","code","translation","diagnostic"...
    input_data: str           # 输入 (提示词/代码/文本)
    output_data: str = ""     # 产出 (生成的代码/翻译结果...)
    score: float = 0.0        # 用户评分 0-1
    feedback: str = ""        # 用户反馈
    tags: list = field(default_factory=list)  # ["security","gufeng","email"]
    metadata: dict = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)


class SkillLearner:
    """泛化自学习引擎 — 任何 Agent 都可以接入.

    Hermes 吸收: Closed Learning Loop → 技能创建 + 自动改进 + 偏好建模.

    Usage:
        learner = SkillLearner("my_agent")
        learner.learn("code", "def validate(x): return x", score=0.9, tags=["security"])
        hints = learner.get_hints("code")
        top = learner.top_skills("code", min_score=0.7)
    """

    def __init__(self, agent_name: str, db_path: str = ""):
        self.name = agent_name
        self._path = Path(db_path or f"data/learner_{agent_name}.json")
        self._records: list[SkillRecord] = []
        self._stats = defaultdict(lambda: {"count": 0, "sum_score": 0.0})
        self._tag_weights: dict[str, float] = {}
        self._load()

    def _load(self):
        if self._path.exists():
            data = json.loads(self._path.read_text(encoding="utf-8"))
            self._records = [SkillRecord(**r) for r in data.get("records", [])]
            self._tag_weights = data.get("tag_weights", {})

    def _save(self):
        self._path.parent.mkdir(parents=True, exist_ok=True)
        data = {
            "agent": self.name,
            "records": [r.__dict__ for r in self._records],
            "tag_weights": self._tag_weights,
        }
        self._path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    def learn(self, skill_type: str, input_data: str, score: float = 0.5,
              feedback: str = "", output_data: str = "", tags: list = None, **meta):
        """学习一条新记录."""
        record = SkillRecord(
            skill_type=skill_type, input_data=input_data, output_data=output_data,
            score=score, feedback=feedback, tags=tags or [], metadata=meta,
        )
        self._records.append(record)

        # 更新统计
        self._stats[skill_type]["count"] += 1
        self._stats[skill_type]["sum_score"] += score

        # 更新标签权重
        for tag in (tags or []):
            current = self._tag_weights.get(tag, 0.5)
            self._tag_weights[tag] = current * 0.8 + score * 0.2

        self._save()

    def get_hints(self, skill_type: str = "", min_weight: float = 0.6) -> list[str]:
        """获取当前已学会的偏好提示."""
        hints = []
        # 从标签权重中提取
        top_tags = sorted(self._tag_weights.items(), key=lambda x: x[1], reverse=True)
        hints.extend([t for t, w in top_tags[:8] if w >= min_weight])

        # 从高分记录中提取关键词
        relevant = [r for r in self._records if (not skill_type or r.skill_type == skill_type) and r.score >= 0.7]
        for r in relevant[:5]:
            words = r.input_data.lower().split()
            hints.extend([w for w in words if len(w) > 3 and w not in hints])

        return list(dict.fromkeys(hints))[:10]  # 去重 + limit

    def top_skills(self, skill_type: str = "", min_score: float = 0.5, limit: int = 5) -> list[SkillRecord]:
        """获取评分最高的技能记录."""
        results = self._records
        if skill_type:
            results = [r for r in results if r.skill_type == skill_type]
        return sorted([r for r in results if r.score >= min_score],
                      key=lambda r: r.score, reverse=True)[:limit]

    def stats(self) -> dict:
        return {
            "total": len(self._records),
            "by_type": {k: {"count": v["count"], "avg": round(v["sum_score"] / v["count"], 2) if v["count"] else 0}
                        for k, v in self._stats.items()},
            "top_tags": sorted(self._tag_weights.items(), key=lambda x: x[1], reverse=True)[:5],
        }


# ══════════════════════════════════════════
# 2. FTS5KB — SQLite FTS5 全文搜索知识库 (v1.1: jieba CJK)
# ══════════════════════════════════════════

class FTS5KB:
    """FTS5 知识库 — jieba 分词 + FTS5 全文索引.

    v1.1 改进:
      - 索引前用 jieba 分词 (解决 '' 空格分词对 CJK 无效)
      - search() 输入也先分词再构造 FTS5 MATCH 查询
      - 保留 LIKE fallback 作为兜底

    Usage:
        kb = FTS5KB("data/fts5_kb.db")
        kb.index("h001", "A1公理: 信息具有意义层级", ["axiom","L0"])
        results = kb.search("意义层级")  # → jieba → FTS5 MATCH
    """

    def __init__(self, db_path: str = "data/fts5_kb.db"):
        self._conn = sqlite3.connect(db_path, check_same_thread=False)
        self._lock = threading.Lock()
        self._jieba = None
        self._conn.execute("PRAGMA journal_mode=WAL")
        # Single table: tokens column stores jieba-segmented text for CJK search
        self._conn.execute("""
            CREATE VIRTUAL TABLE IF NOT EXISTS kb_fts USING fts5(
                entry_id, title, content, tokens, tags,
                tokenize='unicode61'
            )
        """)
        self._conn.commit()

    def _get_jieba(self):
        """懒加载 jieba."""
        if self._jieba is None:
            try:
                import jieba
                jieba.setLogLevel(20)  # 抑制 jieba 日志
                self._jieba = jieba
            except ImportError:
                self._jieba = False
        return self._jieba if self._jieba else None

    def _tokenize_cjk(self, text: str) -> str:
        """CJK 分词: jieba cut → 空格连接."""
        jieba = self._get_jieba()
        if jieba is None:
            return text  # fallback: 原样返回
        tokens = jieba.cut(text)
        return " ".join(t for t in tokens if t.strip())

    def index(self, entry_id: str, title: str, content: str, tags: list = None):
        """索引一条知识条目 (jieba 分词写入 tokens 列)."""
        tags_str = ",".join(tags) if tags else ""
        tokens = self._tokenize_cjk(title + " " + content)

        with self._lock:
            self._conn.execute(
                "INSERT OR REPLACE INTO kb_fts(entry_id, title, content, tokens, tags) VALUES (?,?,?,?,?)",
                (entry_id, title, content, tokens, tags_str)
            )
            self._conn.commit()

    def search(self, query: str, limit: int = 10) -> list[dict]:
        """全文搜索 (jieba 分词 + FTS5 MATCH).

        策略:
          1. jieba 分词 → FTS5 MATCH (tokens 列 + content 列)
          2. 无 jieba → 空格分词 FTS5 (英文有效)
          3. 0 结果 → LIKE fallback
        """
        with self._lock:
            jieba = self._get_jieba()

            # 策略 1: jieba 分词 + FTS5 MATCH
            if jieba:
                tokens = list(jieba.cut(query))
                tokens = [t.strip() for t in tokens if t.strip() and len(t.strip()) >= 1]
                if tokens:
                    fts5_query = " OR ".join(tokens)
                    try:
                        rows = self._conn.execute(
                            "SELECT entry_id, title, content, tags, rank FROM kb_fts "
                            "WHERE kb_fts MATCH ? ORDER BY rank LIMIT ?",
                            (fts5_query, limit)
                        ).fetchall()
                        if rows:
                            return [{"entry_id": r[0], "title": r[1], "content": r[2][:200],
                                     "tags": r[3], "rank": r[4]} for r in rows]
                    except sqlite3.OperationalError:
                        pass  # 特殊字符导致 MATCH 失败 → fallback

            # 策略 2: 空格分词 FTS5 (英文/数字) + 简单中文单字
            terms = [t for t in query.strip().split() if t]
            if terms:
                fts5_query = " OR ".join(terms)
                try:
                    rows = self._conn.execute(
                        "SELECT entry_id, title, content, tags, rank FROM kb_fts "
                        "WHERE kb_fts MATCH ? ORDER BY rank LIMIT ?",
                        (fts5_query, limit)
                    ).fetchall()
                    if rows:
                        return [{"entry_id": r[0], "title": r[1], "content": r[2][:200],
                                 "tags": r[3], "rank": r[4]} for r in rows]
                except sqlite3.OperationalError:
                    pass

            # 策略 3: LIKE fallback
            pattern = f"%{query}%"
            try:
                rows = self._conn.execute(
                    "SELECT entry_id, title, content, tags, 0 as rank FROM kb_fts "
                    "WHERE content LIKE ? OR title LIKE ? OR tokens LIKE ? LIMIT ?",
                    (pattern, pattern, pattern, limit)
                ).fetchall()
            except Exception:
                rows = []
            return [{"entry_id": r[0], "title": r[1], "content": r[2][:200],
                     "tags": r[3], "rank": r[4]} for r in rows]

    def delete(self, entry_id: str):
        with self._lock:
            self._conn.execute("DELETE FROM kb_fts WHERE entry_id = ?", (entry_id,))
            self._conn.commit()

    def stats(self) -> dict:
        count = self._conn.execute("SELECT COUNT(*) FROM kb_fts").fetchone()[0]
        return {"total_entries": count, "jieba_enabled": self._get_jieba() is not None}

    def close(self):
        self._conn.close()


# ══════════════════════════════════════════
# 3. CronScheduler — 定时任务调度
# ══════════════════════════════════════════

@dataclass
class CronJob:
    name: str
    interval_seconds: int
    callback: Callable[[], None]
    last_run: float = 0.0
    run_count: int = 0
    enabled: bool = True


class CronScheduler:
    """轻量级定时任务调度器 (非持久化, 内存级).

    Usage:
        sched = CronScheduler()
        sched.add("health_check", 300, lambda: print("checking..."))
        sched.start()
    """

    def __init__(self):
        self._jobs: dict[str, CronJob] = {}
        self._running = False
        self._thread: Optional[threading.Thread] = None

    def add(self, name: str, interval_seconds: int, callback: Callable):
        self._jobs[name] = CronJob(name=name, interval_seconds=interval_seconds, callback=callback)

    def remove(self, name: str):
        self._jobs.pop(name, None)

    def start(self):
        self._running = True
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

    def stop(self):
        self._running = False

    def _loop(self):
        while self._running:
            now = time.time()
            for job in list(self._jobs.values()):
                if job.enabled and now - job.last_run >= job.interval_seconds:
                    try:
                        job.callback()
                        job.run_count += 1
                    except Exception as e:
                        print(f"[Cron] {job.name} failed: {e}")
                    job.last_run = now
            time.sleep(1)

    def run_now(self, name: str):
        """立即执行某个任务."""
        job = self._jobs.get(name)
        if job:
            try:
                job.callback()
                job.run_count += 1
                job.last_run = time.time()
            except Exception as e:
                print(f"[Cron] {name} failed: {e}")

    def status(self) -> dict:
        return {
            "running": self._running,
            "jobs": {n: {"interval_s": j.interval_seconds, "runs": j.run_count,
                         "last": j.last_run, "enabled": j.enabled}
                     for n, j in self._jobs.items()}
        }
