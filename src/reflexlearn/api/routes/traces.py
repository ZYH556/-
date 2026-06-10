from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Depends

from reflexlearn.api.deps import get_current_user
from reflexlearn.api.service_deps import safe_pg_pool
from reflexlearn.collaboration.traces import (
    TraceList,
    get_default_trace_store,
    reset_default_trace_store,
)
from reflexlearn.common.auth import CurrentUser
from reflexlearn.training.lora_samples import (
    ExportResult,
    LoraExportList,
    export_lora_samples,
    list_lora_exports,
)

router = APIRouter()


def get_trace_store():
    return get_default_trace_store()


def reset_trace_store_for_tests() -> None:
    reset_default_trace_store()


def lora_output_dir() -> Path:
    return Path("logs/lora_samples")


@router.get("/collaboration/traces")
async def list_traces(
    user: CurrentUser = Depends(get_current_user),
) -> TraceList:
    pg_pool = await safe_pg_pool()
    return await get_trace_store().list_for_user(
        user_id=user.user_id,
        tenant_id=user.tenant_id,
        pg_pool=pg_pool,
    )


@router.post("/growth/lora-samples/export")
async def export_growth_lora_samples(
    user: CurrentUser = Depends(get_current_user),
) -> ExportResult:
    pg_pool = await safe_pg_pool()
    traces = await get_trace_store().list_for_user(
        user_id=user.user_id,
        tenant_id=user.tenant_id,
        pg_pool=pg_pool,
        limit=200,
    )
    return export_lora_samples(
        traces.items,
        user_id=user.user_id,
        tenant_id=user.tenant_id,
        output_dir=lora_output_dir(),
    )


@router.get("/growth/lora-samples")
async def list_growth_lora_samples(
    user: CurrentUser = Depends(get_current_user),
) -> LoraExportList:
    _ = user
    return list_lora_exports(output_dir=lora_output_dir())
