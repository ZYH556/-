from __future__ import annotations

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse

from reflexlearn.api.acl import assert_object_access
from reflexlearn.api.deps import get_current_user
from reflexlearn.api.service_deps import safe_pg_pool
from reflexlearn.common.auth import CurrentUser
from reflexlearn.learning.assets import LearningAssetStore

router = APIRouter()
_store = LearningAssetStore()


def get_asset_store() -> LearningAssetStore:
    return _store


def set_asset_store_for_tests(store: LearningAssetStore) -> None:
    global _store
    _store = store


def reset_asset_store_for_tests() -> None:
    global _store
    _store = LearningAssetStore()


@router.get("/spaces")
async def list_spaces(user: CurrentUser = Depends(get_current_user)):
    pg_pool = await safe_pg_pool()
    return await get_asset_store().list_spaces(
        user_id=user.user_id,
        tenant_id=user.tenant_id,
        pg_pool=pg_pool,
    )


@router.get("/spaces/{space_id}")
async def get_space(space_id: str, user: CurrentUser = Depends(get_current_user)):
    pg_pool = await safe_pg_pool()
    item = await get_asset_store().get_space(space_id, pg_pool=pg_pool)
    if item is None:
        return JSONResponse(status_code=404, content={"error": "space_not_found"})
    assert_object_access(
        user=user,
        owner_user_id=item.user_id,
        tenant_id=item.tenant_id,
        visibility="private",
    )
    return item


@router.get("/resources")
async def list_resources(user: CurrentUser = Depends(get_current_user)):
    pg_pool = await safe_pg_pool()
    return await get_asset_store().list_resources(
        user_id=user.user_id,
        tenant_id=user.tenant_id,
        pg_pool=pg_pool,
    )


@router.get("/resources/{resource_id}")
async def get_resource(resource_id: str, user: CurrentUser = Depends(get_current_user)):
    pg_pool = await safe_pg_pool()
    item = await get_asset_store().get_resource(resource_id, pg_pool=pg_pool)
    if item is None:
        return JSONResponse(status_code=404, content={"error": "resource_not_found"})
    assert_object_access(
        user=user,
        owner_user_id=item.user_id,
        tenant_id=item.tenant_id,
        visibility=item.visibility,
    )
    return item


@router.get("/knowledge/documents")
async def list_documents(user: CurrentUser = Depends(get_current_user)):
    pg_pool = await safe_pg_pool()
    return await get_asset_store().list_documents(
        user_id=user.user_id,
        tenant_id=user.tenant_id,
        pg_pool=pg_pool,
    )


@router.get("/knowledge/documents/{doc_id}")
async def get_document(doc_id: str, user: CurrentUser = Depends(get_current_user)):
    pg_pool = await safe_pg_pool()
    item = await get_asset_store().get_document(doc_id, pg_pool=pg_pool)
    if item is None:
        return JSONResponse(status_code=404, content={"error": "document_not_found"})
    assert_object_access(
        user=user,
        owner_user_id=item.user_id,
        tenant_id=item.tenant_id,
        visibility=item.visibility,
    )
    return item
