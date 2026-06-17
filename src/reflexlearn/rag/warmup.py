"""PERF-D · 启动后台预热 bge 模型，消除首请求 2GB 懒加载卡顿（10–30s）。

`common/embedding._get_model` / `rag.ranking.rerank._get_reranker` 都是懒加载单例：
首个真实请求触发加载会卡 10–30s。本模块在 API 启动后台把它们提前加载好。

铁律：
- **串行**预热（embedding 先、reranker 后），绝不并发加载两个 bge（OOM，见 memory 双模型坑）。
- **丢线程**（`asyncio.to_thread`）：加载是同步重 CPU/IO，不阻塞事件循环。
- **全程降级**：模型缺失 / 离线 / 加载失败只记日志，绝不影响启动或后续请求
  （`is_available()` 本身吞异常返回 False）。
- 只在 `enable_rag` 时预热（RAG 关则 embedding 永不会用，预热纯浪费内存）。
"""

from __future__ import annotations

import asyncio
import logging
import time

logger = logging.getLogger(__name__)


async def warm_models(settings) -> None:
    """启动后台预热入口；不满足门控直接返回。异常不外抛（lifespan 调用方无需 try）。"""
    if not (getattr(settings, "enable_model_warmup", True) and getattr(settings, "enable_rag", True)):
        return
    try:
        await asyncio.to_thread(_warm_embedding)
        if getattr(settings, "enable_rerank", True):
            await asyncio.to_thread(_warm_reranker)
    except Exception as e:  # to_thread 调度异常等极端情况
        logger.info("model warmup aborted: %s", e)


def _warm_embedding() -> None:
    start = time.time()
    try:
        from reflexlearn.common.embedding import is_available

        ok = is_available()  # 触发 _get_model 加载（失败返回 False 不抛）
        logger.info(
            "embedding warmup %s in %.1fs", "ready" if ok else "unavailable", time.time() - start
        )
    except Exception as e:
        logger.info("embedding warmup skipped: %s", e)


def _warm_reranker() -> None:
    start = time.time()
    try:
        from reflexlearn.rag.ranking.rerank import is_available

        ok = is_available()  # 触发 _get_reranker 加载（失败返回 False 不抛）
        logger.info(
            "reranker warmup %s in %.1fs", "ready" if ok else "unavailable", time.time() - start
        )
    except Exception as e:
        logger.info("reranker warmup skipped: %s", e)
