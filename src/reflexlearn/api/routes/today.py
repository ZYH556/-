from __future__ import annotations

from collections.abc import Mapping

from fastapi import APIRouter, Depends

from reflexlearn.api import service_deps
from reflexlearn.api.deps import get_current_user
from reflexlearn.common.auth import CurrentUser
from reflexlearn.learning.assets import AssetList, LearningAssetStore
from reflexlearn.learning.mistakes import MistakeList, MistakeStore
from reflexlearn.learning.path_ops import load_active_path_items
from reflexlearn.learning.today import TodaySummary, build_today_summary
from reflexlearn.memory import session_store

router = APIRouter()
_asset_store = LearningAssetStore()
_mistake_store = MistakeStore()


def get_today_asset_store() -> LearningAssetStore:
    return _asset_store


def get_today_mistake_store() -> MistakeStore:
    return _mistake_store


@router.get("/today")
async def get_today(user: CurrentUser = Depends(get_current_user)) -> TodaySummary:
    pg_pool = await service_deps.safe_pg_pool()
    degraded: list[str] = []

    spaces_result = await get_today_asset_store().list_spaces(
        user_id=user.user_id,
        tenant_id=user.tenant_id,
        pg_pool=pg_pool,
    )
    resources_result = await get_today_asset_store().list_resources(
        user_id=user.user_id,
        tenant_id=user.tenant_id,
        pg_pool=pg_pool,
    )
    mistakes_result = await get_today_mistake_store().list_for_user(
        user_id=user.user_id,
        tenant_id=user.tenant_id,
        pg_pool=pg_pool,
    )
    profile = await session_store.load_profile(user.user_id, tenant_id=user.tenant_id)
    path_items = await load_active_path_items(
        user_id=user.user_id, tenant_id=user.tenant_id, pg_pool=pg_pool
    )

    degraded.extend(_degraded(spaces_result))
    degraded.extend(_degraded(resources_result))
    degraded.extend(_degraded(mistakes_result))

    return build_today_summary(
        user_id=user.user_id,
        spaces=[_dump(item) for item in spaces_result.items],
        resources=[_dump(item) for item in resources_result.items],
        mistakes=[_dump(item) for item in mistakes_result.items],
        profile=profile,
        path_items=[item.model_dump() for item in path_items],
        degraded=degraded,
    )


def _degraded(result: AssetList | MistakeList) -> list[str]:
    return list(result.degraded)


def _dump(item: object) -> dict:
    if hasattr(item, "model_dump"):
        data = item.model_dump()
        return data if isinstance(data, dict) else {}
    if isinstance(item, Mapping):
        return dict(item)
    return {}
