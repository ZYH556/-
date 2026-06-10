"""M4-C Kafka 增量链路：生产者投递文档变更事件 + 消费者增量入库。

降级铁律：aiokafka 已装但 broker 可能未起。
- **生产端**：broker 不可用 → `publish_event` 返回 False、`enqueue_document` 返回 None，由 route 落
  同步 `ingest_document`（用户仍立即得结果，绝不因 broker 挂而上传失败）。
- **消费端**：独立进程（`scripts/jobs/data/kafka_consumer.py`），broker 挂则启动即报错退出，不影响后端主进程。

依赖注入：`publish_event` / `handle_event` 的 producer / qdrant / pg_pool / neo4j 由调用方传入，
单测注入假对象——aiokafka 已装故 import 不降级，但**绝不真连 broker**（会超时卡死）。
"""
from __future__ import annotations

import logging

from reflexlearn.common.config import get_settings
from reflexlearn.data_engineering.events import (
    EVENT_DOC_ADDED,
    EVENT_DOC_UPDATED,
    TOPIC_KNOWLEDGE_CHANGES,
    KnowledgeEvent,
    build_doc_event,
    decode_payload_raw,
)

logger = logging.getLogger(__name__)


class KafkaUnavailable(RuntimeError):
    pass


_producer = None


async def _get_producer():
    """AIOKafkaProducer 惰性单例。aiokafka 缺库 / start 连不上 broker → 抛 KafkaUnavailable。"""
    global _producer
    if _producer is None:
        try:
            from aiokafka import AIOKafkaProducer
        except Exception as e:  # 缺库（未装 kafka extra）
            raise KafkaUnavailable(f"aiokafka import failed: {e}")
        s = get_settings()
        p = AIOKafkaProducer(bootstrap_servers=s.kafka_bootstrap_servers)
        try:
            await p.start()
        except Exception as e:  # broker 未起 / 网络不可达
            raise KafkaUnavailable(f"kafka broker unavailable: {e}")
        _producer = p
    return _producer


async def publish_event(event: KnowledgeEvent, *, producer=None) -> bool:
    """投递事件到 knowledge.changes。失败（库/broker 不可用）返回 False（调用方降级同步链路）。

    key=doc_id 保证同文档事件路由到同分区（顺序性）；value=事件 JSON（消费端 model_validate_json）。
    """
    try:
        p = producer or await _get_producer()
        await p.send_and_wait(
            TOPIC_KNOWLEDGE_CHANGES,
            key=event.doc_id.encode("utf-8"),
            value=event.model_dump_json().encode("utf-8"),
        )
        return True
    except Exception as e:
        logger.warning("kafka publish degraded: %s", e)
        return False


async def enqueue_document(
    *,
    doc_id: str,
    filename: str,
    raw: bytes,
    course_id: str = "",
    user_id: str = "",
    tenant_id: str = "default",
    visibility: str = "public",
    title: str = "",
    producer=None,
) -> dict | None:
    """enable_kafka 时由 route 调用：投递 doc_added 事件。

    成功返回 queued dict；broker 不可用返回 None（route 据此降级为同步 ingest_document）。
    """
    event = build_doc_event(
        doc_id=doc_id, filename=filename, raw=raw, course_id=course_id, user_id=user_id,
        tenant_id=tenant_id, visibility=visibility, title=title,
    )
    if await publish_event(event, producer=producer):
        return {"status": "queued", "doc_id": doc_id, "event_type": event.event_type}
    return None


async def handle_event(event: KnowledgeEvent, *, qdrant=None, pg_pool=None, neo4j=None):
    """消费一条事件 → ingest_document 唯一写入口。

    doc_added / doc_updated 走全链路（含图谱构建）；doc_deleted 暂记日志（删除受 doc_id 无 payload
    index 边界限制，见 memory reflexlearn-ingest-idempotent）。返回 IngestResult | None。
    """
    from reflexlearn.data_engineering.ingest import ingest_document

    if event.event_type in (EVENT_DOC_ADDED, EVENT_DOC_UPDATED):
        p = event.payload
        return await ingest_document(
            filename=p.get("filename", "upload.bin"),
            raw=decode_payload_raw(event),
            course_id=p.get("course_id", ""),
            user_id=p.get("user_id", ""),
            tenant_id=event.tenant_id,
            visibility=p.get("visibility", "public"),
            title=p.get("title") or None,
            qdrant=qdrant,
            pg_pool=pg_pool,
            neo4j=neo4j,
            enable_graph_build=True,  # 异步消费不阻塞用户，走全链路含图谱抽取
        )
    logger.info("doc_deleted event %s: delete-by-doc_id not yet supported (see idempotent memory)", event.doc_id)
    return None


async def run_consumer():  # pragma: no cover - 独立进程长循环；单测覆盖 handle_event 而非循环本身
    """消费循环（独立脚本调用）：拉 knowledge.changes → handle_event。broker 不可用则启动即抛出退出。"""
    from aiokafka import AIOKafkaConsumer

    from reflexlearn.common import db

    s = get_settings()
    consumer = AIOKafkaConsumer(
        TOPIC_KNOWLEDGE_CHANGES,
        bootstrap_servers=s.kafka_bootstrap_servers,
        group_id="reflexlearn-ingest",
        auto_offset_reset="earliest",
    )
    await consumer.start()
    logger.info("kafka consumer started on %s topic=%s", s.kafka_bootstrap_servers, TOPIC_KNOWLEDGE_CHANGES)

    def _safe_qdrant():
        try:
            return db.get_qdrant()
        except Exception:
            return None

    def _safe_neo4j():
        try:
            return db.get_neo4j()
        except Exception:
            return None

    async def _safe_pg():
        try:
            return await db.get_pg_pool()
        except Exception:
            return None

    try:
        async for msg in consumer:
            try:
                event = KnowledgeEvent.model_validate_json(msg.value)
                res = await handle_event(
                    event, qdrant=_safe_qdrant(), pg_pool=await _safe_pg(), neo4j=_safe_neo4j()
                )
                logger.info(
                    "consumed %s doc=%s → %s", event.event_type, event.doc_id, getattr(res, "status", None)
                )
            except Exception as e:  # 单条事件失败不拖垮整个消费循环
                logger.warning("consume one event failed: %s", e)
    finally:
        await consumer.stop()
