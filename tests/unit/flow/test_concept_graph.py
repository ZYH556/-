"""阶段6：path_plan 真实拓扑回填测试。

两部分：
1. PathPlanSkill._rule_based_order(graph) / _topo_order —— Kahn 拓扑排序、真实前置依赖、
   中文模糊对齐、有环退化、off-graph 附末尾、graph=None 零回归。纯逻辑，不碰 LLM/Neo4j。
2. nodes.path_plan._load_concept_graph —— mock Neo4j driver，验证建图、异常/空图退 None（降级安全）。
"""
from __future__ import annotations

import pytest

from reflexlearn.skills.path_plan import PathPlanSkill


class _FailLLM:
    """占位 LLM：_rule_based_order 是纯方法不调用它，仅满足 PathPlanSkill(llm) 构造。"""

    async def complete(self, messages, **kwargs):
        raise RuntimeError("llm offline")


def _skill() -> PathPlanSkill:
    return PathPlanSkill(_FailLLM())


def _res(tid: str, concept: str, rtype: str = "doc", diff: float = 0.5) -> dict:
    return {"task_id": tid, "resource_type": rtype, "concept": concept, "difficulty": diff}


# ---------- _topo_order / _rule_based_order(graph) ----------


def test_topo_orders_by_prerequisite():
    """真实 PREREQUISITE_OF：线性回归→梯度下降→神经网络，乱序输入也按依赖定序。"""
    graph = {"梯度下降": ["线性回归"], "神经网络基础": ["梯度下降"]}
    resources = [_res("t_nn", "神经网络基础"), _res("t_lr", "线性回归"), _res("t_gd", "梯度下降")]
    steps = _skill()._rule_based_order(resources, {}, "ML", graph)["steps"]
    seq = [s["concept"] for s in steps]
    assert seq.index("线性回归") < seq.index("梯度下降") < seq.index("神经网络基础")


def test_topo_depends_on_real_prereq():
    """跨概念前置写入 depends_on：梯度下降步骤依赖线性回归的资源 task_id。"""
    graph = {"梯度下降": ["线性回归"]}
    resources = [_res("t_gd", "梯度下降"), _res("t_lr", "线性回归")]
    steps = _skill()._rule_based_order(resources, {}, "ML", graph)["steps"]
    gd = next(s for s in steps if s["concept"] == "梯度下降")
    assert "t_lr" in gd["depends_on"]


def test_topo_tie_break_by_teaching_order():
    """同概念多资源拓扑后仍按教学序(doc<quiz)，tie-break 不被破坏。"""
    graph = {"线性回归": []}
    resources = [_res("t_quiz", "线性回归", "quiz"), _res("t_doc", "线性回归", "doc")]
    steps = _skill()._rule_based_order(resources, {}, "ML", graph)["steps"]
    seq = [s["task_id"] for s in steps]
    assert seq.index("t_doc") < seq.index("t_quiz")


def test_topo_fuzzy_concept_match():
    """concept 与图节点名包含匹配即对齐：'线性回归基础'/'梯度下降算法' 命中图节点。"""
    graph = {"梯度下降": ["线性回归"]}
    resources = [_res("t_gd", "梯度下降算法"), _res("t_lr", "线性回归基础")]
    steps = _skill()._rule_based_order(resources, {}, "ML", graph)["steps"]
    seq = [s["task_id"] for s in steps]
    assert seq.index("t_lr") < seq.index("t_gd")


def test_topo_cycle_falls_back_to_heuristic():
    """图有环 → 退化启发式排序，绝不崩、绝不漏资源。"""
    graph = {"A": ["B"], "B": ["A"]}
    resources = [_res("t_a", "A"), _res("t_b", "B")]
    steps = _skill()._rule_based_order(resources, {}, "ML", graph)["steps"]
    assert len(steps) == 2  # 不崩，全部资源仍排出


def test_topo_off_graph_concept_appended():
    """概念不在图中 → 附末尾，不干扰图内拓扑序。"""
    graph = {"线性回归": []}
    resources = [_res("t_x", "量子力学"), _res("t_lr", "线性回归")]
    steps = _skill()._rule_based_order(resources, {}, "ML", graph)["steps"]
    seq = [s["concept"] for s in steps]
    assert seq.index("线性回归") < seq.index("量子力学")


def test_graph_none_keeps_heuristic_soft_dep():
    """graph=None → 现状软依赖(同概念前一步)，零回归。"""
    resources = [_res("t_doc", "线性回归", "doc"), _res("t_quiz", "线性回归", "quiz")]
    steps = _skill()._rule_based_order(resources, {}, "ML", None)["steps"]
    quiz = next(s for s in steps if s["resource_type"] == "quiz")
    assert quiz["depends_on"] == ["t_doc"]


def test_graph_strategy_label_differs():
    """graph 模式 strategy 标注图谱拓扑，便于前端/日志区分。"""
    graph = {"线性回归": []}
    out = _skill()._rule_based_order([_res("t_lr", "线性回归")], {}, "ML", graph)
    assert "拓扑" in out["strategy"]


# ---------- nodes.path_plan._load_concept_graph (mock Neo4j) ----------


class _Rec:
    def __init__(self, d: dict):
        self._d = d

    def data(self) -> dict:
        return self._d


class _RecStream:
    def __init__(self, rows: list[dict]):
        self._rows = [_Rec(r) for r in rows]

    def __aiter__(self):
        self._it = iter(self._rows)
        return self

    async def __anext__(self):
        try:
            return next(self._it)
        except StopIteration:
            raise StopAsyncIteration


class _Session:
    def __init__(self, rows: list[dict]):
        self._rows = rows

    async def __aenter__(self):
        return self

    async def __aexit__(self, *a):
        return False

    async def run(self, cypher, **kw):
        return _RecStream(self._rows)


class _FakeNeo4j:
    def __init__(self, rows: list[dict]):
        self._rows = rows

    def session(self):
        return _Session(self._rows)


@pytest.mark.asyncio
async def test_load_concept_graph_builds_map(monkeypatch):
    """Neo4j 返回 (prereq, concept) 行 → 聚合成 {concept:[prereqs]}。"""
    import reflexlearn.orchestration.nodes.planning.path_plan as pp

    rows = [
        {"prereq": "线性回归", "concept": "梯度下降"},
        {"prereq": "梯度下降", "concept": "神经网络基础"},
        {"prereq": "过拟合与正则化", "concept": "神经网络基础"},
    ]
    monkeypatch.setattr("reflexlearn.common.db.get_neo4j", lambda: _FakeNeo4j(rows))
    graph = await pp._load_concept_graph({"tenant_id": "default"})
    assert graph["梯度下降"] == ["线性回归"]
    assert set(graph["神经网络基础"]) == {"梯度下降", "过拟合与正则化"}


@pytest.mark.asyncio
async def test_load_concept_graph_error_returns_none(monkeypatch):
    """get_neo4j 抛(未装/连不上) → None，path_plan 退启发式，不崩。"""
    import reflexlearn.orchestration.nodes.planning.path_plan as pp

    def boom():
        raise RuntimeError("neo4j driver missing / bolt closed")

    monkeypatch.setattr("reflexlearn.common.db.get_neo4j", boom)
    assert await pp._load_concept_graph({"tenant_id": "default"}) is None


@pytest.mark.asyncio
async def test_load_concept_graph_empty_returns_none(monkeypatch):
    """图无边 → None（区别于空 dict），触发启发式降级。"""
    import reflexlearn.orchestration.nodes.planning.path_plan as pp

    monkeypatch.setattr("reflexlearn.common.db.get_neo4j", lambda: _FakeNeo4j([]))
    assert await pp._load_concept_graph({}) is None
