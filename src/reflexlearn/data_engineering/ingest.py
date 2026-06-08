"""核心写链路：解析 → 结构感知分块 →（可选 contextual 摘要）→ 向量化 → upsert Qdrant
+ documents 表登记 + 关键词索引失效。上传 API 与 Kafka 消费者共用此唯一入口。

降级铁律（docs §6）：每个外部依赖（embedding / qdrant / pg / llm）独立 try/except，任一不可用都
不中断、不抛错、不假装成功——返回 IngestResult 并在 degraded 列出降级项，写链路始终给出确定结果。

依赖注入（仿 memory.reflexion.write_reflection）：qdrant / pg_pool 由调用方传入，单测可注入假对象
或 None，既能覆盖成功路径、又不触发真实 asyncpg 连接（conftest 的 hermetic 守卫不拦 pg）。
"""
from __future__ import annotations

import asyncio
import logging

from pydantic import BaseModel, Field
from uuid import NAMESPACE_URL, uuid5

from reflexlearn.common.config import get_settings
from reflexlearn.data_engineering.chunking import Chunk, chunk_sections
from reflexlearn.data_engineering.parsing import ParserUnavailable, detect_format, parse_document

logger = logging.getLogger(__name__)

# 用户上传文档的来源可信度（介于种子知识 0.9 与默认 0.5 之间，weighted_sort 用）。
UPLOAD_SOURCE_TRUST = 0.7


class IngestResult(BaseModel):
    doc_id: str
    title: str
    format: str
    chunks: int = 0
    embedded: int = 0
    qdrant_written: int = 0
    pg_written: bool = False
    contextual: bool = False
    graph: str = "disabled"  # M4-B 图谱抽取状态：disabled | skipped | ok | degraded
    graph_concepts: int = 0
    graph_relations: int = 0
    degraded: list[str] = Field(default_factory=list)
    status: str = "ok"  # ok | degraded | empty


def _doc_id(tenant_id: str, course_id: str, filename: str) -> str:
    """确定性文档 ID：同租户 + 同课程 + 同文件名 → 同 doc_id，重传幂等覆盖。"""
    return str(uuid5(NAMESPACE_URL, f"{tenant_id}::{course_id}::{filename}"))


def _point_id(doc_id: str, idx: int) -> str:
    """确定性 chunk point ID，保证重跑幂等覆盖而非堆积。"""
    return str(uuid5(NAMESPACE_URL, f"{doc_id}::{idx}"))


async def ingest_document(
    *,
    filename: str,
    raw: bytes,
    course_id: str = "",
    user_id: str = "",
    tenant_id: str = "default",
    visibility: str = "public",
    title: str | None = None,
    qdrant=None,
    pg_pool=None,
    neo4j=None,
    enable_contextual: bool | None = None,
    enable_graph_build: bool | None = None,
) -> IngestResult:
    settings = get_settings()
    doc_id = _doc_id(tenant_id, course_id, filename)
    degraded: list[str] = []

    # 1) 解析（缺库 / 不支持 / 打开失败 → 降级早退，链路仍成功）
    try:
        parsed = parse_document(filename, raw)
    except ParserUnavailable as e:
        logger.warning("parse degraded for %s: %s", filename, e)
        return IngestResult(
            doc_id=doc_id, title=title or filename, format=detect_format(filename),
            degraded=[f"parse:{e}"], status="degraded",
        )
    doc_title = title or parsed.title or filename

    # 2) 结构感知分块
    chunks = chunk_sections(parsed.sections)
    if not chunks:
        return IngestResult(
            doc_id=doc_id, title=doc_title, format=parsed.format,
            degraded=["empty:no_chunks"], status="empty",
        )

    # 3) contextual 摘要（默认关；显式入参覆盖 settings）
    use_ctx = settings.enable_contextual if enable_contextual is None else enable_contextual
    contents = [c.text for c in chunks]
    contextual_done = False
    if use_ctx:
        contents, contextual_done, ctx_note = await _contextualize(chunks, doc_title, settings)
        if ctx_note:
            degraded.append(ctx_note)

    # 4) 向量化（embedding 不可用 / RAG 关 → 跳过向量，绝不写零向量；PG 仍登记）
    vectors: list[list[float]] = []
    if not settings.enable_rag:
        degraded.append("embedding:rag_disabled")
    else:
        try:
            from reflexlearn.common.embedding import embed_documents

            vectors = embed_documents(contents)
        except Exception as e:  # EmbeddingUnavailable / 依赖缺失
            logger.info("embedding degraded: %s", e)
            degraded.append(f"embedding:{type(e).__name__}")
    embedded = len(vectors)

    # 5) upsert Qdrant（content 存原文用于检索展示；向量含 contextual 增强语义）
    qdrant_written = 0
    if vectors and qdrant is not None:
        try:
            from qdrant_client.models import PointStruct

            points = [
                PointStruct(
                    id=_point_id(doc_id, c.idx),
                    vector=vec,
                    payload={
                        "content": c.text,
                        "source": filename,
                        "title": doc_title,
                        "heading": c.heading,
                        "doc_id": doc_id,
                        "tenant_id": tenant_id,
                        "visibility": visibility,
                        "course_id": course_id,
                        "user_id": user_id,
                        "source_trust": UPLOAD_SOURCE_TRUST,
                    },
                )
                for c, vec in zip(chunks, vectors)
            ]
            await qdrant.upsert(collection_name=settings.knowledge_collection, points=points)
            qdrant_written = len(points)
        except Exception as e:
            logger.warning("qdrant write degraded: %s", e)
            degraded.append(f"qdrant:{type(e).__name__}")
    elif vectors and qdrant is None:
        degraded.append("qdrant:unavailable")

    # 6) documents 表登记（幂等 upsert）
    pg_written = False
    if pg_pool is not None:
        try:
            async with pg_pool.acquire() as conn:
                await conn.execute(
                    """
                    INSERT INTO documents (
                        doc_id, title, format, user_id, tenant_id, course_id,
                        visibility, section_count
                    )
                    VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                    ON CONFLICT (doc_id) DO UPDATE SET
                        title = EXCLUDED.title,
                        format = EXCLUDED.format,
                        section_count = EXCLUDED.section_count
                    """,
                    doc_id, doc_title, parsed.format, user_id, tenant_id, course_id,
                    visibility, len(chunks),
                )
            pg_written = True
        except Exception as e:
            logger.warning("documents pg write degraded: %s", e)
            degraded.append(f"pg:{type(e).__name__}")
    else:
        degraded.append("pg:unavailable")

    # 6.5) 图谱构建（M4-B）：LLM 抽取概念/关系 MERGE 入 Neo4j（schema 对齐 graph_retrieval 读侧 ACL）。
    #      独立降级：无开关→disabled，无 neo4j/LLM/抽不出→skipped，MERGE 异常→degraded，均不中断主链路。
    use_graph = settings.enable_graph_build if enable_graph_build is None else enable_graph_build
    graph_status, graph_concepts, graph_relations = "disabled", 0, 0
    if use_graph:
        from reflexlearn.data_engineering.graph_build import build_graph

        graph_status, graph_concepts, graph_relations, graph_notes = await build_graph(
            chunks=chunks, doc_title=doc_title, doc_id=doc_id,
            tenant_id=tenant_id, visibility=visibility, neo4j=neo4j, settings=settings,
        )
        degraded.extend(graph_notes)

    # 7) 关键词索引失效：新 chunk 立即可被 BM25 关键词路命中（写→读闭环）
    if qdrant_written:
        try:
            from reflexlearn.rag.keyword import KeywordIndex

            KeywordIndex.invalidate()
        except Exception:
            pass

    status = "ok" if (qdrant_written or pg_written) else "degraded"
    return IngestResult(
        doc_id=doc_id, title=doc_title, format=parsed.format,
        chunks=len(chunks), embedded=embedded, qdrant_written=qdrant_written,
        pg_written=pg_written, contextual=contextual_done,
        graph=graph_status, graph_concepts=graph_concepts, graph_relations=graph_relations,
        degraded=degraded, status=status,
    )


async def _contextualize(
    chunks: list[Chunk], doc_title: str, settings
) -> tuple[list[str], bool, str]:
    """为每个 chunk 生成一句 LLM 定位摘要前缀（Anthropic contextual retrieval）。

    控成本/时延：并发上限 4；超 contextual_max_chunks 则整体跳过。LLM 不可用（llm_no_api_key）
    → 逐块回退原文，标注 degraded。返回 (contents, 是否真正加了摘要, 降级说明)。
    """
    max_n = settings.contextual_max_chunks
    if len(chunks) > max_n:
        return [c.text for c in chunks], False, f"contextual:skipped_over_{max_n}"
    try:
        from reflexlearn.llm_gateway.gateway import LLMGateway

        gw = LLMGateway()
    except Exception as e:
        return [c.text for c in chunks], False, f"contextual:{type(e).__name__}"

    sem = asyncio.Semaphore(4)

    async def _one(c: Chunk) -> str:
        async with sem:
            try:
                comp = await gw.complete(
                    messages=[
                        {
                            "role": "system",
                            "content": "用一句中文概括该片段在全文中的定位，不超过 30 字，只输出该句。",
                        },
                        {"role": "user", "content": f"文档《{doc_title}》片段：\n{c.text[:800]}"},
                    ],
                    task_type="summary",
                    temperature=0.3,
                )
                ctx = (comp.text or "").strip().replace("\n", " ")
                return f"{ctx}\n\n{c.text}" if ctx else c.text
            except Exception:  # llm_no_api_key / 外呼失败 → 原文
                return c.text

    out = list(await asyncio.gather(*[_one(c) for c in chunks]))
    done = any(o != c.text for o, c in zip(out, chunks))
    note = "" if done else "contextual:llm_unavailable"
    return out, done, note
