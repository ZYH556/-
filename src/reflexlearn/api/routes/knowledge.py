"""知识上传 API：multipart 文档上传 → 隔离区扫描 → 核心写链路（解析/分块/向量化/入库）。

依赖获取走 _safe_* 包装：qdrant 单例惰性、pg pool 连接失败均吞为 None，由 ingest_document
内部按 None 降级——已认证请求在依赖服务缺失时仍返回 200（degraded 标注），呼应降级铁律。
W3-D：上传先入隔离区扫描，拒绝可执行/危险 HTML 内容。
"""
from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile

from reflexlearn.api.deps import get_current_user
from reflexlearn.api.service_deps import safe_neo4j, safe_pg_pool, safe_qdrant
from reflexlearn.api.upload_guard import read_validated_upload, validate_visibility
from reflexlearn.common.auth import CurrentUser
from reflexlearn.common.config import get_settings
from reflexlearn.data_engineering.ingest import ingest_document
from reflexlearn.security.audit import AuditEvent, AuditLog
from reflexlearn.security.uploads import ACCEPTED, REJECTED, UploadQuarantineStore, scan_upload

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/knowledge/upload")
async def upload_knowledge(
    file: UploadFile = File(...),
    course_id: str = Form(""),
    visibility: str = Form("public"),
    title: str = Form(""),
    enable_contextual: bool = Form(False),
    enable_graph_build: bool = Form(False),
    user: CurrentUser = Depends(get_current_user),
):
    settings = get_settings()
    visibility = validate_visibility(visibility)
    upload = await read_validated_upload(file, settings)
    raw = upload.raw
    filename = upload.filename
    pool = await safe_pg_pool()

    # W3-D：隔离区扫描——拒绝可执行/危险 HTML 内容（占位规则引擎，非企业级杀毒）
    if settings.enable_upload_quarantine:
        quarantine = UploadQuarantineStore(pg_pool=pool)
        obj = await quarantine.register(
            user_id=user.user_id,
            tenant_id=user.tenant_id,
            original_name=filename,
            raw=raw,
            content_type=upload.content_type,
        )
        reasons = scan_upload(raw=raw, extension=upload.extension)
        if reasons:
            await quarantine.mark(obj, REJECTED, reasons)
            await AuditLog(pg_pool=pool).record(
                AuditEvent(
                    event_type="upload.rejected",
                    user_id=user.user_id,
                    tenant_id=user.tenant_id,
                    object_type="upload",
                    object_id=obj.object_id,
                    status="rejected",
                    detail={"reasons": reasons, "name": filename},
                )
            )
            raise HTTPException(status_code=422, detail="upload_rejected")
        await quarantine.mark(obj, ACCEPTED)

    # enable_kafka：先投异步增量链路；broker 不可用则降级同步（降级铁律，用户仍立即得结果）
    if settings.enable_kafka:
        from reflexlearn.data_engineering.ingest import _doc_id
        from reflexlearn.data_engineering.kafka_io import enqueue_document

        queued = await enqueue_document(
            doc_id=_doc_id(user.tenant_id, course_id, filename),
            filename=filename,
            raw=raw,
            course_id=course_id,
            user_id=user.user_id,
            tenant_id=user.tenant_id,
            visibility=visibility,
            title=title,
        )
        if queued is not None:
            return queued
        logger.info("kafka unavailable, fallback to sync ingest for %s", filename)

    result = await ingest_document(
        filename=filename,
        raw=raw,
        course_id=course_id,
        user_id=user.user_id,
        tenant_id=user.tenant_id,
        visibility=visibility,
        title=title or None,
        qdrant=safe_qdrant(),
        pg_pool=pool,
        neo4j=safe_neo4j(),
        enable_contextual=enable_contextual,
        enable_graph_build=enable_graph_build,
    )
    return result.model_dump()
