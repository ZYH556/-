"""知识上传 API：multipart 文档上传 → 核心写链路（解析/分块/向量化/入库）。

依赖获取走 _safe_* 包装：qdrant 单例惰性、pg pool 连接失败均吞为 None，由 ingest_document
内部按 None 降级——已认证请求在依赖服务缺失时仍返回 200（degraded 标注），呼应降级铁律。
"""
from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, File, Form, UploadFile

from reflexlearn.api.deps import get_current_user
from reflexlearn.api.upload_guard import read_validated_upload, validate_visibility
from reflexlearn.common.auth import CurrentUser
from reflexlearn.common import db
from reflexlearn.common.config import get_settings
from reflexlearn.data_engineering.ingest import ingest_document

router = APIRouter()
logger = logging.getLogger(__name__)


def _safe_qdrant():
    try:
        return db.get_qdrant()
    except Exception as e:
        logger.info("qdrant unavailable for upload: %s", e)
        return None


async def _safe_pg():
    try:
        return await db.get_pg_pool()
    except Exception as e:
        logger.info("pg unavailable for upload: %s", e)
        return None


def _safe_neo4j():
    """get_neo4j 是同步工厂（仿 _safe_qdrant）；neo4j 包未装 / 连接失败均吞为 None。"""
    try:
        return db.get_neo4j()
    except Exception as e:
        logger.info("neo4j unavailable for upload: %s", e)
        return None


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
        qdrant=_safe_qdrant(),
        pg_pool=await _safe_pg(),
        neo4j=_safe_neo4j(),
        enable_contextual=enable_contextual,
        enable_graph_build=enable_graph_build,
    )
    return result.model_dump()
