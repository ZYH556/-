"""检索策略路由：按问题类型决定走哪几路召回（仿 docs/03 §3.2）。

default 即「语义 + 关键词」两路混合（日常 generator 检索）；concept_dependency 额外开图谱路。
图谱路是否真正生效还要叠加 settings.enable_graph_retrieval 门控（在 service 层收口），
此处只表达「该问题类型想不想用图」。conflict_check 本轮不实现，故不在 strategy 中体现。
"""
from __future__ import annotations

from reflexlearn.rag.schemas import RetrievalStrategy


def route_strategy(query: str, query_type: str = "default", default_top_k: int = 5) -> RetrievalStrategy:
    qt = query_type or "default"
    if qt == "concept_dependency":
        # 概念依赖类：需要图谱扩展前置/相关概念
        return RetrievalStrategy(use_semantic=True, use_keyword=True, use_graph=True, top_k=8)
    if qt == "code_example":
        # 代码示例类：关键词命中 API/函数名更准
        return RetrievalStrategy(use_semantic=True, use_keyword=True, use_graph=False, top_k=8)
    if qt == "factual_lookup":
        # 事实查询类：语义足够，收窄 top_k
        return RetrievalStrategy(use_semantic=True, use_keyword=False, use_graph=False, top_k=5)
    # default / 未知类型：语义 + 关键词两路混合
    return RetrievalStrategy(use_semantic=True, use_keyword=True, use_graph=False, top_k=default_top_k)
