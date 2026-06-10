from __future__ import annotations

import json

import pytest

from reflexlearn.llm_gateway.gateway import Completion
from reflexlearn.orchestration.nodes.planning.path_plan import path_plan_node
from reflexlearn.skills.base import SkillContext
from reflexlearn.skills.path_plan import PathPlanSkill


class FakeLLM:
    """payload→返回该 JSON；should_fail→抛错（fail_msg 控制是否含 OFFLINE_TAG）。记录 calls。"""

    def __init__(self, payload: dict | None = None, should_fail: bool = False, fail_msg: str = "llm unavailable"):
        self.payload = payload or {}
        self.should_fail = should_fail
        self.fail_msg = fail_msg
        self.calls: list[dict] = []

    async def complete(self, messages, **kwargs):
        self.calls.append({"messages": messages, "kwargs": kwargs})
        if self.should_fail:
            raise RuntimeError(self.fail_msg)
        return Completion(text=json.dumps(self.payload, ensure_ascii=False))


def make_resource(task_id: str, rtype: str, concept: str, difficulty: float = 0.5) -> dict:
    return {"task_id": task_id, "resource_type": rtype, "concept": concept, "difficulty": difficulty}


def ctx() -> SkillContext:
    return SkillContext(user_id="u1", acl={}, task_id="path_plan")


def plan_task(task_id: str, rtype: str = "doc", concept: str | None = None, difficulty: float = 0.5) -> dict:
    return {
        "task_id": task_id,
        "type": rtype,
        "spec": {"type": rtype, "concept_ids": [concept or task_id], "difficulty": difficulty},
        "status": "passed",
        "attempts": 0,
        "result_ref": None,
    }


def node_state(plan: list, completed: list, profile: dict | None = None, skills: dict | None = None, goal: str = "线性回归") -> dict:
    return {
        "user_id": "u1",
        "acl": {},
        "learning_goal": goal,
        "learner_profile": profile or {},
        "plan": plan,
        "completed": completed,
        "_skills": skills if skills is not None else {},
    }


# ———————————————————— Skill：规则排序 ————————————————————

@pytest.mark.asyncio
async def test_rule_based_order_respects_teaching_sequence():
    skill = PathPlanSkill(FakeLLM(should_fail=True))
    resources = [
        make_resource("v1", "video", "c"),
        make_resource("d1", "doc", "c"),
        make_resource("co1", "code", "c"),
        make_resource("q1", "quiz", "c"),
    ]
    res = await skill.run({"resources": resources, "profile": {}, "goal": "线性回归"}, ctx())

    assert res.ok and res.data["mode"] == "rule"
    assert [s["resource_type"] for s in res.data["path"]] == ["doc", "code", "quiz", "video"]
    assert all(s["objective"] and s["rationale"] for s in res.data["path"])
    assert [s["sequence"] for s in res.data["path"]] == [1, 2, 3, 4]


@pytest.mark.asyncio
async def test_rule_based_order_sorts_by_difficulty():
    skill = PathPlanSkill(FakeLLM(should_fail=True))
    resources = [
        make_resource("d3", "doc", "c", 0.7),
        make_resource("d1", "doc", "c", 0.2),
        make_resource("d2", "doc", "c", 0.5),
    ]
    res = await skill.run({"resources": resources, "profile": {}, "goal": "g"}, ctx())

    assert [s["task_id"] for s in res.data["path"]] == ["d1", "d2", "d3"]


@pytest.mark.asyncio
async def test_profile_weak_points_promoted():
    skill = PathPlanSkill(FakeLLM(should_fail=True))
    resources = [
        make_resource("d1", "doc", "线性回归", 0.5),
        make_resource("r1", "reading", "过拟合", 0.4),
    ]
    res = await skill.run(
        {"resources": resources, "profile": {"weak_points": ["过拟合"]}, "goal": "g"}, ctx()
    )
    path = res.data["path"]

    # 薄弱点「过拟合」前置，即使其资源(reading)在教学序中本应靠后
    assert path[0]["concept"] == "过拟合"
    assert "薄弱点" in path[0]["rationale"]


# ———————————————————— Skill：LLM 路径与降级 ————————————————————

@pytest.mark.asyncio
async def test_llm_path_parsed():
    payload = {
        "steps": [
            {"sequence": 1, "task_id": "q1", "resource_type": "quiz", "concept": "c",
             "objective": "先练习", "rationale": "以练促学", "difficulty": 0.5, "depends_on": []},
            {"sequence": 2, "task_id": "d1", "resource_type": "doc", "concept": "c",
             "objective": "后精读", "rationale": "练后补全", "difficulty": 0.5, "depends_on": []},
        ],
        "summary": "LLM 路径",
        "strategy": "LLM 策略",
    }
    llm = FakeLLM(payload)
    skill = PathPlanSkill(llm)
    resources = [make_resource("q1", "quiz", "c"), make_resource("d1", "doc", "c")]

    res = await skill.run({"resources": resources, "profile": {}, "goal": "g"}, ctx())

    assert res.ok and res.data["mode"] == "llm"
    # LLM 给的顺序（quiz 在前，反教学序）被保留，证明采纳了 LLM 排序而非规则
    assert [s["task_id"] for s in res.data["path"]] == ["q1", "d1"]
    assert res.data["summary"] == "LLM 路径"
    assert llm.calls[0]["kwargs"]["task_type"] == "planning"
    assert llm.calls[0]["kwargs"]["temperature"] == 0.1


@pytest.mark.asyncio
async def test_llm_failure_degrades_to_rules():
    # should_fail 抛 "llm unavailable"（非 OFFLINE_TAG）→ 终态节点仍 ok=True，降级规则排序
    skill = PathPlanSkill(FakeLLM(should_fail=True))
    resources = [make_resource("d1", "doc", "c"), make_resource("q1", "quiz", "c")]

    res = await skill.run({"resources": resources, "profile": {}, "goal": "g"}, ctx())

    assert res.ok is True
    assert res.data["mode"] == "rule"
    assert [s["resource_type"] for s in res.data["path"]] == ["doc", "quiz"]


@pytest.mark.asyncio
async def test_no_api_key_degrades_to_rules():
    skill = PathPlanSkill(FakeLLM(should_fail=True, fail_msg="no_api_key"))
    resources = [make_resource("d1", "doc", "c")]

    res = await skill.run({"resources": resources, "profile": {}, "goal": "g"}, ctx())

    assert res.ok and res.data["mode"] == "rule"
    assert len(res.data["path"]) == 1


@pytest.mark.asyncio
async def test_skill_empty_resources_returns_empty():
    skill = PathPlanSkill(FakeLLM(should_fail=True))
    res = await skill.run({"resources": [], "profile": {}, "goal": "g"}, ctx())
    assert res.ok and res.data["path"] == []


# ———————————————————— Node：join / 容错 / 兜底 ————————————————————

@pytest.mark.asyncio
async def test_node_joins_plan_for_concept_difficulty():
    plan = [plan_task("t1", "doc", concept="梯度下降", difficulty=0.3)]
    completed = [{"task_id": "t1", "status": "passed", "type": "doc", "content": "x"}]
    skills = {"path_plan": PathPlanSkill(FakeLLM(should_fail=True))}

    res = await path_plan_node(node_state(plan, completed, skills=skills))
    path = res["learning_path"]

    # completed 项本身无 concept/difficulty，由 node 按 task_id join plan[].spec 补回
    assert len(path) == 1
    assert path[0]["concept"] == "梯度下降"
    assert path[0]["difficulty"] == 0.3


@pytest.mark.asyncio
async def test_node_handles_debate_verdict():
    plan = [plan_task("t1", "doc", concept="A", difficulty=0.3)]
    completed = [
        {"task_id": "t1", "status": "passed", "type": "doc", "content": "x"},
        {"task_id": "debate-verdict", "status": "passed", "type": "debate",
         "content": "...", "winner_position": "正方胜出"},
    ]
    skills = {"path_plan": PathPlanSkill(FakeLLM(should_fail=True))}

    res = await path_plan_node(node_state(plan, completed, skills=skills))
    path = res["learning_path"]

    assert len(path) == 2  # 不在 plan 的 debate-verdict 不致 KeyError
    debate_step = next(s for s in path if s["resource_type"] == "debate")
    assert debate_step["difficulty"] == 0.5          # join miss 默认难度
    assert debate_step["concept"] == "正方胜出"       # winner_position 兜底
    assert path[-1]["resource_type"] == "debate"     # 未知类型排末位


@pytest.mark.asyncio
async def test_node_empty_passed_returns_empty_path():
    completed = [{"task_id": "t1", "status": "failed", "type": "doc", "issues": ["x"]}]
    skills = {"path_plan": PathPlanSkill(FakeLLM(should_fail=True))}

    res = await path_plan_node(node_state([], completed, skills=skills))

    # 无 passed 资源 → 合法空路径（如实反映"无资源"，与 assemble 一致；不报错、不假装）
    assert res["learning_path"] == []
    assert "iteration" not in res


@pytest.mark.asyncio
async def test_node_skill_missing_falls_back_to_simple():
    completed = [
        {"task_id": "t1", "status": "passed", "type": "doc", "content": "x"},
        {"task_id": "t2", "status": "passed", "type": "quiz", "content": "y"},
    ]
    res = await path_plan_node(node_state([], completed, skills={}))  # 无 path_plan skill
    path = res["learning_path"]

    assert len(path) == 2
    assert path[0] == {"sequence": 1, "resource_type": "doc", "task_id": "t1"}
    assert all("objective" not in p for p in path)  # 简单兜底路径不含 objective


@pytest.mark.asyncio
async def test_node_does_not_bump_iteration():
    completed = [{"task_id": "t1", "status": "passed", "type": "doc", "content": "x"}]
    skills = {"path_plan": PathPlanSkill(FakeLLM(should_fail=True))}

    res = await path_plan_node(node_state([plan_task("t1")], completed, skills=skills))

    assert "iteration" not in res  # path_plan 是末端节点，不自增 iteration
