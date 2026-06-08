"""bge-reranker 精排封装（CrossEncoder）。懒加载单例，仿 common/embedding.py。

模型 BAAI/bge-reranker-v2-m3（多语种、中文强、rerank SOTA）。复用已装的 sentence-transformers，
无需新 pip 依赖，仅首次加载下载权重。加载失败抛 RerankerUnavailable，由 service 降级到 weighted_sort。
死锁规避：torch.set_num_threads(1)（与 embedding 共存防 OOM）；service 只在召回 gather 结束后串行调用。
"""
from __future__ import annotations

import logging
import threading

from reflexlearn.rag.schemas import ChunkMeta

logger = logging.getLogger(__name__)

_DEFAULT_RERANKER = "BAAI/bge-reranker-v2-m3"

_reranker = None
_rr_load_failed = False
_rr_lock = threading.Lock()


class RerankerUnavailable(RuntimeError):
    """reranker 不可用（缺依赖 / 模型加载失败）——上层据此降级到 weighted_sort。"""


def _resolve_reranker_name() -> str:
    try:
        from reflexlearn.common.config import get_settings

        return get_settings().reranker_model or _DEFAULT_RERANKER
    except Exception:
        return _DEFAULT_RERANKER


def _get_reranker(model_name: str | None = None):
    """懒加载并缓存 CrossEncoder；加载失败后置位，后续直接抛错不再重试。"""
    global _reranker, _rr_load_failed
    if _reranker is not None:
        return _reranker
    if _rr_load_failed:
        raise RerankerUnavailable("reranker previously failed to load")
    with _rr_lock:
        if _reranker is not None:
            return _reranker
        if _rr_load_failed:
            raise RerankerUnavailable("reranker previously failed to load")
        try:
            from sentence_transformers import CrossEncoder

            try:
                import torch

                torch.set_num_threads(1)  # 与 bge-embedding 共存，防 OpenBLAS/OMP 过并发 OOM
            except Exception:
                pass

            name = model_name or _resolve_reranker_name()
            logger.info("loading reranker model: %s", name)
            _reranker = CrossEncoder(name, device="cpu", max_length=512)
            return _reranker
        except Exception as e:  # 依赖缺失 / 下载失败 / 加载异常
            _rr_load_failed = True
            logger.warning("reranker load failed: %s", e)
            raise RerankerUnavailable(str(e)) from e


def is_available() -> bool:
    """探测 reranker 是否可用（尝试加载，失败返回 False，不抛错）。"""
    try:
        _get_reranker()
        return True
    except RerankerUnavailable:
        return False


def rerank(query: str, chunks: list[ChunkMeta]) -> list[ChunkMeta]:
    """cross-encoder 精排；覆盖 relevance_score 后按分降序。

    chunks ≤ 1 直接返回（不触发模型）；模型不可用抛 RerankerUnavailable（上层降级）。
    """
    if len(chunks) <= 1:
        return chunks
    model = _get_reranker()
    pairs = [[query, c.content] for c in chunks]
    scores = model.predict(pairs, convert_to_numpy=True)
    for c, s in zip(chunks, scores):
        c.relevance_score = float(s)
    return sorted(chunks, key=lambda c: c.relevance_score, reverse=True)
