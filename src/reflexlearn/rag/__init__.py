from reflexlearn.rag.access.acl import acl_check, build_qdrant_filter
from reflexlearn.rag.ranking.fusion import fuse_and_dedup, rrf_fuse, weighted_sort
from reflexlearn.rag.ranking.rerank import RerankerUnavailable, is_available, rerank
from reflexlearn.rag.retrieval.graph_retrieval import graph_expand
from reflexlearn.rag.retrieval.keyword import KeywordIndex
from reflexlearn.rag.retrieval.semantic import semantic_search
from reflexlearn.rag.routing.router import route_strategy
from reflexlearn.rag.schemas import ChunkMeta, RetrievalResult, RetrievalStrategy

__all__ = [
    "ChunkMeta",
    "KeywordIndex",
    "RAGService",
    "RerankerUnavailable",
    "RetrievalResult",
    "RetrievalStrategy",
    "acl_check",
    "build_qdrant_filter",
    "fuse_and_dedup",
    "graph_expand",
    "is_available",
    "rerank",
    "route_strategy",
    "rrf_fuse",
    "semantic_search",
    "weighted_sort",
]


def __getattr__(name: str):
    if name == "RAGService":
        from reflexlearn.rag.service import RAGService

        return RAGService
    raise AttributeError(name)
