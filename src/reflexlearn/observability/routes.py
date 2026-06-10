from __future__ import annotations

from fastapi import APIRouter, Response

from reflexlearn.observability.metrics import export_metrics, metrics_content_type

router = APIRouter()


@router.get("/metrics")
async def metrics() -> Response:
    return Response(content=export_metrics(), media_type=metrics_content_type())
