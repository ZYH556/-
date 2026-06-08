"""关键词检索（BM25）：对已入库 knowledge_chunks 建进程内单例索引。

中文分词：jieba 精确模式优先（纯 Python、无下载、不碰网络），ImportError 回退字符 bigram。
索引用 Qdrant 真实 point.id 作 chunk_id，保证与语义/图谱三路 ID 对齐（RRF 去重正确）。
ACL 无法像 qdrant 那样下推，故在 search 出结果后用 acl.acl_check 内存过滤。
数据量小（几十 chunk），单例缓存；重新 ingest 后需重启常驻后端或 invalidate() 刷新。
"""
from __future__ import annotations

import logging
import threading

from reflexlearn.rag.acl import acl_check
from reflexlearn.rag.schemas import ChunkMeta

logger = logging.getLogger(__name__)


def _tokenize(text: str) -> list[str]:
    """中文分词：jieba 优先，失败回退字符 bigram。"""
    try:
        import jieba

        toks = [t.strip() for t in jieba.lcut(text or "") if t.strip()]
    except Exception:
        s = (text or "").replace("\n", "").replace(" ", "")
        toks = [s[i : i + 2] for i in range(max(0, len(s) - 1))]  # 字符 bigram
    return [t for t in toks if t and not t.isspace()]


class KeywordIndex:
    """BM25 关键词索引单例。get() 首次 scroll qdrant 全量 chunk 构建；构建失败返回 None。"""

    _instance: "KeywordIndex | None" = None
    _lock = threading.Lock()

    def __init__(self, chunk_ids: list[str], contents: list[str], metas: list[dict]):
        from rank_bm25 import BM25Okapi  # 局部 import：未装时由 get() 捕获 -> keyword 路跳过

        self._chunk_ids = chunk_ids
        self._contents = contents
        self._metas = metas
        self._bm25 = BM25Okapi([_tokenize(c) for c in contents])

    @classmethod
    async def get(cls) -> "KeywordIndex | None":
        if cls._instance is not None:
            return cls._instance
        with cls._lock:
            if cls._instance is not None:
                return cls._instance
            try:
                cls._instance = await cls._build_from_qdrant()
            except Exception as e:  # qdrant 连不上 / rank_bm25 缺 / 空库
                logger.warning("keyword index build failed: %s", e)
                return None
            return cls._instance

    @classmethod
    async def _build_from_qdrant(cls) -> "KeywordIndex":
        from reflexlearn.common.config import get_settings
        from reflexlearn.common.db import get_qdrant

        settings = get_settings()
        qdrant = get_qdrant()
        chunk_ids: list[str] = []
        contents: list[str] = []
        metas: list[dict] = []
        offset = None
        while True:
            points, offset = await qdrant.scroll(
                collection_name=settings.knowledge_collection,
                limit=256,
                offset=offset,
                with_payload=True,
                with_vectors=False,
            )
            for p in points:
                payload = getattr(p, "payload", None) or {}
                content = payload.get("content", "")
                if not content:
                    continue
                chunk_ids.append(str(getattr(p, "id", "")))
                contents.append(content)
                metas.append(payload)
            if offset is None:
                break
        return cls(chunk_ids, contents, metas)

    def search(self, query: str, top_k: int = 5, acl: dict | None = None) -> list[ChunkMeta]:
        if not self._chunk_ids:
            return []
        scores = self._bm25.get_scores(_tokenize(query))
        ranked = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)
        out: list[ChunkMeta] = []
        for i in ranked:
            if scores[i] <= 0:  # BM25 0 分 = 无关键词命中，丢弃
                continue
            meta = self._metas[i]
            if acl is not None and not acl_check(meta, acl):
                continue  # ACL 物理过滤
            out.append(
                ChunkMeta(
                    chunk_id=self._chunk_ids[i],
                    content=self._contents[i],
                    source=meta.get("source") or meta.get("title") or "",
                    relevance_score=float(scores[i]),
                    source_trust=float(meta.get("source_trust", 0.5)),
                    origin="keyword",
                )
            )
            if len(out) >= top_k:
                break
        return out

    @classmethod
    def invalidate(cls) -> None:
        cls._instance = None
