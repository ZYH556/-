from __future__ import annotations

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse

from reflexlearn.api.acl import assert_object_access
from reflexlearn.api.deps import get_current_user
from reflexlearn.api.service_deps import safe_pg_pool
from reflexlearn.common.auth import CurrentUser
from reflexlearn.learning.mistake_flywheel import (
    ReviewPatch,
    build_remedial_plan,
    generate_targeted_resources,
    reflect_mistake,
)
from reflexlearn.learning.mistakes import (
    MistakeCreate,
    MistakeItem,
    MistakeList,
    MistakeStore,
    build_mistake_review,
)

router = APIRouter()
_store = MistakeStore()


def get_mistake_store() -> MistakeStore:
    return _store


def reset_mistake_store_for_tests() -> None:
    global _store
    _store = MistakeStore()


@router.post("/mistakes")
async def create_mistake(
    body: MistakeCreate,
    user: CurrentUser = Depends(get_current_user),
) -> MistakeItem:
    pg_pool = await safe_pg_pool()
    return await get_mistake_store().create(
        body=body,
        user_id=user.user_id,
        tenant_id=user.tenant_id,
        pg_pool=pg_pool,
    )


@router.get("/mistakes")
async def list_mistakes(
    user: CurrentUser = Depends(get_current_user),
) -> MistakeList:
    pg_pool = await safe_pg_pool()
    return await get_mistake_store().list_for_user(
        user_id=user.user_id,
        tenant_id=user.tenant_id,
        pg_pool=pg_pool,
    )


@router.get("/mistakes/{mistake_id}")
async def get_mistake(
    mistake_id: str,
    user: CurrentUser = Depends(get_current_user),
) -> MistakeItem:
    pg_pool = await safe_pg_pool()
    item = await get_mistake_store().get(mistake_id, pg_pool=pg_pool)
    if item is None:
        return JSONResponse(status_code=404, content={"error": "mistake_not_found"})
    assert_object_access(
        user=user,
        owner_user_id=item.user_id,
        tenant_id=item.tenant_id,
        visibility="private",
    )
    return item


async def _owned_mistake(mistake_id: str, user: CurrentUser, pg_pool) -> MistakeItem | JSONResponse:
    item = await get_mistake_store().get(mistake_id, pg_pool=pg_pool)
    if item is None:
        return JSONResponse(status_code=404, content={"error": "mistake_not_found"})
    assert_object_access(
        user=user,
        owner_user_id=item.user_id,
        tenant_id=item.tenant_id,
        visibility="private",
    )
    return item


@router.post("/mistakes/{mistake_id}/review")
async def review_mistake(
    mistake_id: str,
    user: CurrentUser = Depends(get_current_user),
):
    pg_pool = await safe_pg_pool()
    item = await get_mistake_store().get(mistake_id, pg_pool=pg_pool)
    if item is None:
        return JSONResponse(status_code=404, content={"error": "mistake_not_found"})
    assert_object_access(
        user=user,
        owner_user_id=item.user_id,
        tenant_id=item.tenant_id,
        visibility="private",
    )
    review = build_mistake_review(item)
    await get_mistake_store().save_review(item, review, pg_pool=pg_pool)
    return review


@router.post("/mistakes/{mistake_id}/reflect")
async def reflect_mistake_route(
    mistake_id: str,
    user: CurrentUser = Depends(get_current_user),
):
    pg_pool = await safe_pg_pool()
    item = await _owned_mistake(mistake_id, user, pg_pool)
    if isinstance(item, JSONResponse):
        return item
    reflection = reflect_mistake(item)
    await get_mistake_store().save_analysis(
        item,
        patch={"reflection": reflection.model_dump()},
        status="reviewing",
        pg_pool=pg_pool,
    )
    return reflection


@router.post("/mistakes/{mistake_id}/plan")
async def plan_mistake_route(
    mistake_id: str,
    user: CurrentUser = Depends(get_current_user),
):
    pg_pool = await safe_pg_pool()
    item = await _owned_mistake(mistake_id, user, pg_pool)
    if isinstance(item, JSONResponse):
        return item
    reflection = reflect_mistake(item)
    plan = await build_remedial_plan(item, reflection)
    await get_mistake_store().save_analysis(
        item,
        patch={"reflection": reflection.model_dump(), "remedial_plan": plan.model_dump()},
        status="reviewing",
        pg_pool=pg_pool,
    )
    return plan


@router.post("/mistakes/{mistake_id}/resources")
async def mistake_resources_route(
    mistake_id: str,
    user: CurrentUser = Depends(get_current_user),
):
    pg_pool = await safe_pg_pool()
    item = await _owned_mistake(mistake_id, user, pg_pool)
    if isinstance(item, JSONResponse):
        return item
    reflection = reflect_mistake(item)
    pack = await generate_targeted_resources(item, reflection)
    await get_mistake_store().save_analysis(
        item,
        patch={"reflection": reflection.model_dump(), "targeted_resources": pack.model_dump()},
        status="reviewing",
        pg_pool=pg_pool,
    )
    return pack


@router.patch("/mistakes/{mistake_id}/review")
async def patch_mistake_review(
    mistake_id: str,
    body: ReviewPatch,
    user: CurrentUser = Depends(get_current_user),
) -> MistakeItem:
    pg_pool = await safe_pg_pool()
    item = await _owned_mistake(mistake_id, user, pg_pool)
    if isinstance(item, JSONResponse):
        return item
    return await get_mistake_store().save_analysis(
        item,
        patch={"review_status": body.review_status},
        status=body.review_status,
        pg_pool=pg_pool,
    )
