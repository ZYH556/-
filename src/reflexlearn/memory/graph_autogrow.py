"""会话结束后的知识图谱自生长封装。"""
from __future__ import annotations

from reflexlearn.data_engineering.chunking import chunk_text
from reflexlearn.data_engineering import graph_build


async def autogrow_session_graph(
    *,
    text: str,
    tenant_id: str,
    visibility: str,
    doc_id: str,
    neo4j,
    settings,
    gateway=None,
) -> tuple[str, int, int, list[str]]:
    """把本轮交互文本抽概念入图；开关关闭或异常时降级跳过。"""
    if not bool(getattr(settings, "enable_graph_autogrow", False)):
        return "disabled", 0, 0, []
    try:
        chunks = chunk_text(text)
        return await graph_build.build_graph(
            chunks=chunks,
            doc_title="session",
            doc_id=doc_id,
            tenant_id=tenant_id,
            visibility=visibility,
            neo4j=neo4j,
            settings=settings,
            gateway=gateway,
        )
    except Exception as exc:
        return "degraded", 0, 0, [f"graph_autogrow:{type(exc).__name__}"]
