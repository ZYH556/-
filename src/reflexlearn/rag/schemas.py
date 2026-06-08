"""混合检索的纯数据模型（无 IO）。被 rag 模块各处依赖。

ChunkMeta 刻意不携带 ACL 字段（visibility/tenant_id/user_id）——权限过滤在各路数据源头
完成（semantic 走 qdrant query_filter、keyword/graph 走 acl.acl_check），检索结果保持纯净。
"""
from __future__ import annotations

from pydantic import BaseModel, Field


class ChunkMeta(BaseModel):
    chunk_id: str
    content: str
    source: str = ""
    relevance_score: float = 0.0
    source_trust: float = 0.5  # 来源可信度，weighted_sort 用；payload 缺失时默认 0.5
    origin: str = "semantic"  # semantic | keyword | graph，便于调试与未来前端染色


class RetrievalStrategy(BaseModel):
    use_semantic: bool = True
    use_graph: bool = False
    use_keyword: bool = False
    top_k: int = 5
    rerank: bool = True


class RetrievalResult(BaseModel):
    chunks: list[ChunkMeta] = Field(default_factory=list)
    strategy_used: str = ""
    routes_used: list[str] = Field(default_factory=list)  # 降级后实际生效的路
    has_conflict: bool = False  # 冲突检测占位（本轮 DoD 不含，恒 False）
