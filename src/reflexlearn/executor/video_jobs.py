"""M4-E 多模态视频异步作业（docs/05 §3.3 重任务）：SeeDance 生成 + 轮询。

设计：用轻量 **asyncio 后台任务**（非 Celery worker，免独立进程）。提交作业立即返回 job_id（pending），
后台 `process_job` 调 SeeDance 更新状态，前端轮询 `GET /api/video/jobs/{id}`。

降级铁律：
- 作业存储 `JobStore` 优先 Redis（持久、多 worker 共享），不可用 → **内存 dict**（同进程轮询仍工作）；
- SeeDance 未启用 / 无凭证 / 外呼失败 → 作业落 **degraded**，`storyboard` 分镜脚本作占位返回（前端展示脚本，
  不假装出视频），呼应 docs/00 §「降级图文」风险对策。

依赖注入：`JobStore(redis=...)` / `call_seedance(client=...)` 可注入，单测注入假对象绝不真连 Redis/外呼。
"""
from __future__ import annotations

import asyncio
import logging
import time
import uuid

from pydantic import BaseModel

from reflexlearn.common.config import get_settings
from reflexlearn.observability.metrics import observe_video_job

logger = logging.getLogger(__name__)


class SeeDanceUnavailable(RuntimeError):
    pass


class VideoJob(BaseModel):
    job_id: str
    user_id: str = ""
    tenant_id: str = "default"
    status: str = "pending"  # pending | running | done | degraded | failed
    storyboard: str = ""
    video_url: str | None = None
    error: str | None = None
    created_at: float = 0.0


class JobStore:
    """作业存储：Redis 优先（video_job:{id} JSON + TTL），不可用降级内存 dict（仿 session_store）。"""

    def __init__(self, *, redis=None):
        self._redis = redis
        self._mem: dict[str, VideoJob] = {}

    async def _get_redis(self):
        if self._redis is not None:
            return self._redis
        from reflexlearn.common.db import get_redis

        return await get_redis()

    async def save(self, job: VideoJob) -> None:
        try:
            r = await self._get_redis()
            await r.set(f"video_job:{job.job_id}", job.model_dump_json(), ex=get_settings().video_job_ttl)
        except Exception as e:
            logger.info("video job store fallback to memory: %s", e)
            self._mem[job.job_id] = job

    async def get(self, job_id: str) -> VideoJob | None:
        try:
            r = await self._get_redis()
            raw = await r.get(f"video_job:{job_id}")
            if raw:
                return VideoJob.model_validate_json(raw)
        except Exception:
            pass
        return self._mem.get(job_id)


_store: JobStore | None = None


def get_job_store() -> JobStore:
    global _store
    if _store is None:
        _store = JobStore()
    return _store


async def call_seedance(prompt: str, settings, *, client=None) -> str:
    """调火山 SeeDance 生成视频，返回 video_url。未启用 / 无凭证 → 抛 SeeDanceUnavailable（上层降级 storyboard）。

    注：SeeDance 真实为异步任务（提交返回 task_id，再轮询 SeeDance 侧取结果）；此处为骨架，
    直接从响应取 url。真凭证就绪后按其 API 补轮询。client 注入便于单测。
    """
    if not settings.enable_seedance or not settings.seedance_api_key:
        raise SeeDanceUnavailable("seedance_disabled_or_no_key")

    import httpx

    headers = {
        "Authorization": f"Bearer {settings.seedance_api_key}",
        "Content-Type": "application/json",
    }
    payload = {"model": settings.seedance_model, "content": [{"type": "text", "text": prompt[:2000]}]}
    own = client is None
    c = client or httpx.AsyncClient(timeout=30)
    try:
        resp = await c.post(settings.seedance_endpoint, json=payload, headers=headers)
        resp.raise_for_status()
        data = resp.json()
    finally:
        if own:
            await c.aclose()
    url = data.get("video_url") or (data.get("content") or {}).get("video_url")
    if not url:
        raise SeeDanceUnavailable("seedance_no_url_in_response")
    return url


async def process_job(job_id: str, prompt: str, *, store: JobStore, settings=None) -> VideoJob | None:
    """后台执行：running → SeeDance → done / degraded（storyboard 占位）/ failed。"""
    settings = settings or get_settings()
    job = await store.get(job_id)
    if job is None:
        return None
    job.status = "running"
    await store.save(job)
    observe_video_job(job.status)
    try:
        url = await call_seedance(prompt, settings)
        job.status = "done"
        job.video_url = url
    except SeeDanceUnavailable as e:
        job.status = "degraded"  # storyboard 已在 job 内，前端展示分镜脚本占位
        job.error = str(e)
    except Exception as e:
        job.status = "failed"
        job.error = type(e).__name__
    await store.save(job)
    observe_video_job(job.status)
    return job


async def submit_video_job(
    *, storyboard: str, prompt: str | None = None, store: JobStore | None = None,
    settings=None, autostart: bool = True, user_id: str = "", tenant_id: str = "default",
) -> VideoJob:
    """创建视频作业（pending）并后台触发生成。autostart=False 仅创建不跑后台（单测用）。"""
    store = store or get_job_store()
    job = VideoJob(
        job_id=uuid.uuid4().hex,
        user_id=user_id,
        tenant_id=tenant_id,
        status="pending",
        storyboard=storyboard,
        created_at=time.time(),
    )
    await store.save(job)
    observe_video_job(job.status)
    if autostart:
        asyncio.create_task(process_job(job.job_id, prompt or storyboard, store=store, settings=settings))
    return job


async def get_video_job(job_id: str, *, store: JobStore | None = None) -> VideoJob | None:
    store = store or get_job_store()
    return await store.get(job_id)
