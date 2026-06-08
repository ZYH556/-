"""知识变更事件 schema（M4-C Kafka 增量链路）· 对齐 docs/04 §7.1。

纯数据 + 编解码，**无 aiokafka 依赖**——可被 route（生产端）、consumer、单测放心 import。
事件经 `knowledge.changes` topic 流转，消费端解码后走 `ingest_document` 唯一写入口（与上传 API 同链路）。
"""
from __future__ import annotations

import base64

from pydantic import BaseModel, Field

TOPIC_KNOWLEDGE_CHANGES = "knowledge.changes"

EVENT_DOC_ADDED = "doc_added"
EVENT_DOC_UPDATED = "doc_updated"
EVENT_DOC_DELETED = "doc_deleted"


class KnowledgeEvent(BaseModel):
    event_type: str = EVENT_DOC_ADDED  # doc_added | doc_updated | doc_deleted
    doc_id: str = ""
    tenant_id: str = "default"
    timestamp: str = ""
    # 变更内容：filename / content_b64 / course_id / user_id / visibility / title
    payload: dict = Field(default_factory=dict)


def build_doc_event(
    *,
    doc_id: str,
    filename: str,
    raw: bytes,
    course_id: str = "",
    user_id: str = "",
    tenant_id: str = "default",
    visibility: str = "public",
    title: str = "",
    event_type: str = EVENT_DOC_ADDED,
    timestamp: str = "",
) -> KnowledgeEvent:
    """构造文档变更事件：原始字节 base64 内联进 payload。

    M4-C 简化：小/中文档内联 bytes（注意 Kafka 默认单消息 ~1MB 上限）。M4-D 接 MinIO 后改投递
    object key、消费端从对象存储拉取，规避大消息边界——届时 payload 用 file_path（见 docs/04 §7.3）。
    """
    return KnowledgeEvent(
        event_type=event_type,
        doc_id=doc_id,
        tenant_id=tenant_id,
        timestamp=timestamp,
        payload={
            "filename": filename,
            "content_b64": base64.b64encode(raw).decode("ascii"),
            "course_id": course_id,
            "user_id": user_id,
            "visibility": visibility,
            "title": title,
        },
    )


def decode_payload_raw(event: KnowledgeEvent) -> bytes:
    """从事件 payload 还原原始字节（消费端用）。"""
    return base64.b64decode(event.payload.get("content_b64", "") or "")
