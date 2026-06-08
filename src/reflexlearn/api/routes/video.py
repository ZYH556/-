"""多模态视频作业轮询 API（M4-E）：提交作业 → 后台 SeeDance 生成 → 前端轮询状态/结果。

降级铁律：作业系统全程不阻塞——提交立即返回 pending，SeeDance 不可用时作业落 degraded、
storyboard 分镜脚本作占位（前端展示脚本，不假装出视频）。
"""
from __future__ import annotations

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from reflexlearn.api.deps import get_current_user
from reflexlearn.common.auth import CurrentUser
from reflexlearn.executor.video_jobs import get_video_job, submit_video_job

router = APIRouter()


class VideoJobRequest(BaseModel):
    storyboard: str            # VideoGenSkill 产出的分镜脚本（SeeDance 输入 + 降级占位）
    prompt: str | None = None  # 可选：覆盖送入 SeeDance 的提示词（默认用 storyboard）


@router.post("/video/jobs")
async def create_video_job(
    body: VideoJobRequest,
    user: CurrentUser = Depends(get_current_user),
):
    job = await submit_video_job(storyboard=body.storyboard, prompt=body.prompt)
    return {"job_id": job.job_id, "status": job.status}


@router.get("/video/jobs/{job_id}")
async def query_video_job(
    job_id: str,
    user: CurrentUser = Depends(get_current_user),
):
    job = await get_video_job(job_id)
    if job is None:
        return JSONResponse(status_code=404, content={"error": "job_not_found"})
    return job.model_dump()
