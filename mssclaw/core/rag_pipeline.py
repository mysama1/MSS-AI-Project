"""
MSS RAG Pipeline — 轻量检索增强生成

零外部依赖 (无需向量数据库/embedding模型).
基于 BM25 + 关键词 + 意义场密度排序.

用法:
    store = DocStore()
    store.add("mss_theory.txt", "A3热税是MSS框架的核心公理...")
    store.add("mss_theory.txt", "Δ协议检测意义开放度...")
    
    retriever = DocRetriever(store)
    chunks = retriever.search("什么是热税")  # → top-3 chunks
    
    agent = MSSAgent("rag-agent", llm=be)
    result = agent.run_with_docs("解释热税", chunks)
"""
from __future__ import annotations
import re
import math
import json
import time
from pathlib import Path
from dataclasses import dataclass, field
from typing import List, Optional
from collections import Counter


@dataclass
class DocChunk:
    """文档片段."""
    doc_id: str
    chunk_id: int
    text: str
    metadata: dict = field(default_factory=dict)
    meaning_density: float = 0.5  # MSS: 意义密度评分


class DocStore:
    """
    文档存储 + 分块.

    分块策略: 按段落 (\\n\\n), 最大 500 字符/chunk.
    """

    MAX_CHUNK_SIZE = 500
    OVERLAP = 50

    def __init__(self):
        self._chunks: List[DocChunk] = []
        self._doc_ids = set()

    def add(self, doc_id: str, text: str, metadata: dict = None) -> int:
        """添加文档, 返回 chunk 数量."""
        self._doc_ids.add(doc_id)
        chunks = self._split(text, doc_id, metadata or {})
        self._chunks.extend(chunks)
        return len(chunks)

    def add_file(self, path: str) -> int:
        """从文件添加."""
        p = Path(path)
        if not p.exists():
            return 0
        text = p.read_text(encoding="utf-8", errors="replace")
        return self.add(p.name, text, {"path": str(p), "size": p.stat().st_size})

    def _split(self, text: str, doc_id: str, meta: dict) -> List[DocChunk]:
        paragraphs = text.split("\n\n")
        chunks = []
        chunk_id = 0
        current = ""

        for para in paragraphs:
            para = para.strip()
            if not para:
                continue

            if len(current) + len(para) > self.MAX_CHUNK_SIZE:
                if current:
                    chunks.append(DocChunk(
                        doc_id=doc_id, chunk_id=chunk_id,
                        text=current.strip(), metadata=meta,
                        meaning_density=self._calc_density(current),
                    ))
                    chunk_id += 1
                    current = para[-self.OVERLAP:] + "\n\n" + para if self.OVERLAP > 0 else para
                else:
                    current = para
            else:
                current += ("\n\n" + para) if current else para

        if current:
            chunks.append(DocChunk(
                doc_id=doc_id, chunk_id=chunk_id,
                text=current.strip(), metadata=meta,
                meaning_density=self._calc_density(current),
            ))
            chunk_id += 1

        return chunks

    def _calc_density(self, text: str) -> float:
        """计算文本的意义密度."""
        words = text.split()
        if not words:
            return 0.5
        # Long unique words = higher meaning density
        unique_ratio = len(set(w.lower() for w in words)) / len(words)
        avg_len = sum(len(w) for w in words) / len(words)
        return min(1.0, (unique_ratio * 0.5 + avg_len / 10 * 0.5))

    def stats(self) -> dict:
        return {
            "documents": len(self._doc_ids),
            "chunks": len(self._chunks),
            "total_chars": sum(len(c.text) for c in self._chunks),
            "avg_density": round(
                sum(c.meaning_density for c in self._chunks) / max(len(self._chunks), 1), 3
            ),
        }


class DocRetriever:
    """
    BM25 + 关键词 + 意义密度 混合检索.

    不需要 embedding 模型, 纯统计算法.
    """

    def __init__(self, store: DocStore):
        self._store = store
        self._index_tokens()

    def _index_tokens(self):
        """构建倒排索引."""
        self._doc_freq = Counter()
        self._term_freqs = []
        self._doc_lengths = []
        self._avg_dl = 0

        for chunk in self._store._chunks:
            tokens = self._tokenize(chunk.text)
            tf = Counter(tokens)
            self._term_freqs.append(tf)
            self._doc_lengths.append(len(tokens))
            for term in set(tokens):
                self._doc_freq[term] += 1

        if self._doc_lengths:
            self._avg_dl = sum(self._doc_lengths) / len(self._doc_lengths)

    @staticmethod
    def _tokenize(text: str) -> List[str]:
        """中英文混合分词."""
        # Split on non-alphanumeric + CJK characters individually
        tokens = []
        for word in re.findall(r'[a-zA-Z0-9]+|[\u4e00-\u9fff]', text.lower()):
            if re.match(r'[\u4e00-\u9fff]', word):
                tokens.extend(word)  # CJK: char by char
            else:
                if len(word) > 2:
                    tokens.append(word)
        return tokens

    def search(self, query: str, top_k: int = 5) -> List[DocChunk]:
        """
        BM25 + 意义密度 混合检索.

        分数 = BM25 × 0.7 + 意义密度 × 0.3
        """
        query_tokens = self._tokenize(query)
        if not query_tokens or not self._store._chunks:
            return []

        k1, b = 1.5, 0.75
        N = len(self._store._chunks)
        scores = []

        for i, chunk in enumerate(self._store._chunks):
            score = 0.0
            dl = self._doc_lengths[i]
            tf = self._term_freqs[i]

            for term in query_tokens:
                if term not in tf:
                    continue
                f = tf[term]
                df = self._doc_freq.get(term, 1)
                idf = math.log((N - df + 0.5) / (df + 0.5) + 1)
                tf_norm = (f * (k1 + 1)) / (f + k1 * (1 - b + b * dl / max(self._avg_dl, 1)))
                score += idf * tf_norm

            # Meaning density bonus
            score = score * 0.7 + chunk.meaning_density * 0.3
            scores.append((score, i))

        scores.sort(key=lambda x: x[0], reverse=True)
        top = scores[:top_k]
        return [self._store._chunks[i] for _, i in top if scores[scores.index((_, i))][0] > 0]


def rag_context(chunks: List[DocChunk], max_tokens: int = 2000) -> str:
    """将检索到的 chunks 拼接为 Agent 上下文."""
    context_parts = []
    total_chars = 0
    for chunk in chunks:
        if total_chars + len(chunk.text) > max_tokens * 3:
            break
        context_parts.append(f"[{chunk.doc_id}#{chunk.chunk_id}] {chunk.text}")
        total_chars += len(chunk.text)
    return "\n\n---\n\n".join(context_parts)
