"""学习路径节点操作 API：标完成 / 插入错题补救节点。"""

from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from reflexlearn.api.deps import get_current_user
from reflexlearn.api.service_deps import safe_pg_pool
from reflexlearn.common.auth import CurrentUser
from reflexlearn.learning.path_ops import (
    PathOwnershipError,
    insert_remedial_item,
    pin_resource_to_item,
    update_item_status,
)

router = APIRouter()


class UpdateItemStatusRequest(BaseModel):
    status: Literal["not_started", "in_progress", "done"]


class InsertRemedialRequest(BaseModel):
    after_item_id: int = Field(ge=1)
    concept: str = Field(min_length=1, max_length=80)
    objective: str = Field(default="", max_length=300)
    rationale: str = Field(default="", max_length=300)


class PinResourceRequest(BaseModel):
    resource_id: str = Field(default="", max_length=64)  # 空=解绑


@router.patch("/plan/items/{item_id}/status")
async def patch_plan_item_status(
    item_id: int,
    req: UpdateItemStatusRequest,
    user: CurrentUser = Depends(get_current_user),
):
    pg_pool = await safe_pg_pool()
    try:
        return await update_item_status(
            item_id,
            req.status,
            user_id=user.user_id,
            tenant_id=user.tenant_id,
            pg_pool=pg_pool,
        )
    except PathOwnershipError:
        return JSONResponse(status_code=403, content={"error": "path_item_forbidden"})
    except LookupError:
        return JSONResponse(status_code=404, content={"error": "path_item_not_found"})


@router.put("/plan/items/{item_id}/resource")
async def put_plan_item_resource(
    item_id: int,
    req: PinResourceRequest,
    user: CurrentUser = Depends(get_current_user),
):
    """把候选资源显式绑定到该节点（resource_id 为空则解绑）。"""
    pg_pool = await safe_pg_pool()
    try:
        return await pin_resource_to_item(
            item_id,
            req.resource_id,
            user_id=user.user_id,
            tenant_id=user.tenant_id,
            pg_pool=pg_pool,
        )
    except PathOwnershipError as exc:
        reason = "resource_forbidden" if str(exc) == "resource_forbidden" else "path_item_forbidden"
        return JSONResponse(status_code=403, content={"error": reason})
    except LookupError:
        return JSONResponse(status_code=404, content={"error": "path_item_not_found"})


@router.post("/plan/items/insert")
async def post_plan_item_insert(
    req: InsertRemedialRequest,
    user: CurrentUser = Depends(get_current_user),
):
    pg_pool = await safe_pg_pool()
    try:
        return await insert_remedial_item(
            req.after_item_id,
            concept=req.concept,
            objective=req.objective or f"补救「{req.concept}」相关薄弱点",
            rationale=req.rationale or "来自错题复盘：先补上这一步再继续推进。",
            user_id=user.user_id,
            tenant_id=user.tenant_id,
            pg_pool=pg_pool,
        )
    except PathOwnershipError:
        return JSONResponse(status_code=403, content={"error": "path_item_forbidden"})
    except LookupError:
        return JSONResponse(status_code=404, content={"error": "path_item_not_found"})
