from __future__ import annotations

from reflexlearn.rag.routing.router import route_strategy


def test_default_is_semantic_plus_keyword():
    """默认即两路混合（语义 + 关键词），不开图谱。"""
    s = route_strategy("线性回归", "default")
    assert s.use_semantic and s.use_keyword
    assert not s.use_graph


def test_concept_dependency_enables_graph():
    s = route_strategy("线性回归的前置知识", "concept_dependency")
    assert s.use_graph and s.use_semantic and s.use_keyword


def test_code_example_uses_keyword():
    s = route_strategy("快速排序代码", "code_example")
    assert s.use_keyword and s.use_semantic


def test_factual_lookup_semantic_only():
    s = route_strategy("什么是学习率", "factual_lookup")
    assert s.use_semantic and not s.use_keyword and not s.use_graph


def test_unknown_type_falls_back_to_default():
    s = route_strategy("x", "weird_type")
    assert s.use_semantic and s.top_k > 0


def test_default_top_k_passthrough():
    s = route_strategy("x", "default", default_top_k=7)
    assert s.top_k == 7
