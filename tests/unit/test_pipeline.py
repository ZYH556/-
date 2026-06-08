from __future__ import annotations

import json

import pytest

from reflexlearn.common.config import get_settings
from reflexlearn.orchestration.graph import dispatch_route, fan_out
from reflexlearn.orchestration.nodes.pipeline import pipeline_node
from reflexlearn.orchestration.nodes.planner import _infer_collab_mode
from reflexlearn.skills.base import SkillResult


class FakeGenSkill:
    """按调用序返回 content；记录每次 inp（含 spec/context），用于断言串接与重试。"""

    def __init__(self, contents: list[str]):
        self.contents = contents
        self.calls: list[dict] = []

    async def run(self, inp, ctx):
        self.calls.append(inp)
        index = min(len(self.calls) - 1, len(self.contents) - 1)
        return SkillResult(ok=True, data={"content": self.contents[index]})


class ScriptedQualitySkill:
    """按 task_id 脚本化校验：前 fail_plan[tid] 次失败，其余通过；unfixable 中的 task 失败时 fixable=False。"""

    def __init__(self, fail_plan: dict | None = None, unfixable: set | None = None):
        self.fail_plan = dict(fail_plan or {})
        self.unfixable = set(unfixable or [])
        self.calls: list[dict] = []

    async def run(self, inp, ctx):
        self.calls.append(inp)
        tid = ctx.task_id
        remaining = self.fail_plan.get(tid, 0)
        if remaining > 0:
            self.fail_plan[tid] = remaining - 1
            return SkillResult(
                ok=True,
                data={"passed": False, "issues": [f"{tid}-issue"], "fixable": tid not in self.unfixable},
            )
        return SkillResult(ok=True, data={"passed": True, "issues": [], "fixable": True})


def make_task(task_id: str, type_: str = "doc", status: str = "pending") -> dict:
    return {
        "task_id": task_id,
        "type": type_,
        "spec": {
            "type": type_,
            "concept_ids": [task_id],
            "difficulty": 0.5,
            "style_hint": "",
            "constraints": [],
        },
        "status": status,
        "attempts": 0,
        "result_ref": None,
    }


def make_skills(gen_map: dict, quality=None) -> dict:
    skills = dict(gen_map)
    if quality is not None:
        skills["quality_check"] = quality
    return skills


def base_state(plan: list[dict], skills: dict) -> dict:
    return {
        "user_id": "u1",
        "acl": {},
        "messages": [],
        "learner_profile": {"cognitive_style": "active"},
        "learning_goal": "测试流水线",
        "collab_mode": "pipeline",
        "plan": plan,
        "completed": [],
        "reflections": [],
        "iteration": 0,
        "replan_count": 0,
        "token_used": 0,
        "halt_reason": None,
        "conflict": None,
        "debate_rounds": None,
        "debate_verdict": None,
        "resource_bundle": None,
        "learning_path": None,
        "_skills": skills,
    }


# ———————————————————— pipeline_node ————————————————————

@pytest.mark.asyncio
async def test_pipeline_runs_chain_in_order_and_threads_context():
    doc = FakeGenSkill(["DOC内容"])
    quiz = FakeGenSkill(["QUIZ内容"])
    plan = [make_task("s1", "doc"), make_task("s2", "quiz")]

    result = await pipeline_node(
        base_state(plan, make_skills({"doc_gen": doc, "quiz_gen": quiz}, ScriptedQualitySkill()))
    )

    units = result["completed"]
    assert [u["status"] for u in units] == ["passed", "passed"]
    assert [u["type"] for u in units] == ["doc", "quiz"]
    assert [u["pipeline_step"] for u in units] == [1, 2]
    # 上游输出入下游：第 2 步 quiz 收到的 context == 第 1 步 doc 产出
    assert quiz.calls[0]["context"] == "DOC内容"
    assert "halt_reason" not in result


@pytest.mark.asyncio
async def test_pipeline_step_retries_on_fixable_failure():
    doc = FakeGenSkill(["短", "完整学习文档"])
    quality = ScriptedQualitySkill(fail_plan={"s1": 1})
    plan = [make_task("s1", "doc")]

    result = await pipeline_node(base_state(plan, make_skills({"doc_gen": doc}, quality)))

    assert result["completed"][0]["status"] == "passed"
    assert len(doc.calls) == 2
    assert doc.calls[1]["spec"]["previous_issues"] == ["s1-issue"]


@pytest.mark.asyncio
async def test_pipeline_rollback_one_step_then_succeeds():
    k = max(1, get_settings().max_react_steps)
    doc = FakeGenSkill(["DOC-v1", "DOC-v2"])
    quiz = FakeGenSkill(["QUIZ"])
    # quiz 首次失败 k 次（耗尽步内重试）→ 触发回退；回退重做 doc 后再进 quiz 通过
    quality = ScriptedQualitySkill(fail_plan={"s2": k})
    plan = [make_task("s1", "doc"), make_task("s2", "quiz")]

    result = await pipeline_node(
        base_state(plan, make_skills({"doc_gen": doc, "quiz_gen": quiz}, quality))
    )

    units = result["completed"]
    assert [u["status"] for u in units] == ["passed", "passed"]
    assert len(doc.calls) == 2  # doc 被重做一次 = 回退一格的证据
    assert "halt_reason" not in result


@pytest.mark.asyncio
async def test_pipeline_partial_result_on_exhausted_rollback():
    doc = FakeGenSkill(["DOC"])
    quiz = FakeGenSkill(["QUIZ"])
    quality = ScriptedQualitySkill(fail_plan={"s2": 999})  # quiz 永远失败（可修复）
    plan = [make_task("s1", "doc"), make_task("s2", "quiz")]

    result = await pipeline_node(
        base_state(plan, make_skills({"doc_gen": doc, "quiz_gen": quiz}, quality))
    )

    units = result["completed"]
    assert result["halt_reason"] == "pipeline_partial"
    passed = [u for u in units if u["status"] == "passed"]
    failed = [u for u in units if u["status"] == "failed"]
    assert len(passed) == 1 and passed[0]["type"] == "doc"
    assert len(failed) == 1 and failed[0]["type"] == "quiz"


@pytest.mark.asyncio
async def test_pipeline_first_step_hard_fail_degrades_immediately():
    doc = FakeGenSkill(["DOC"])
    quality = ScriptedQualitySkill(fail_plan={"s1": 1}, unfixable={"s1"})
    plan = [make_task("s1", "doc"), make_task("s2", "quiz")]

    result = await pipeline_node(
        base_state(plan, make_skills({"doc_gen": doc, "quiz_gen": FakeGenSkill(["Q"])}, quality))
    )

    units = result["completed"]
    assert result["halt_reason"] == "pipeline_partial"
    assert len(units) == 1 and units[0]["status"] == "failed"
    assert len(doc.calls) == 1  # 不可修复失败不重试


@pytest.mark.asyncio
async def test_pipeline_empty_plan_returns_no_completed():
    plan = [make_task("s1", "doc", status="passed")]  # 无 pending

    result = await pipeline_node(
        base_state(plan, make_skills({"doc_gen": FakeGenSkill(["X"])}, ScriptedQualitySkill()))
    )

    assert result["completed"] == []
    assert "halt_reason" not in result


@pytest.mark.asyncio
async def test_pipeline_passes_through_without_quality_skill():
    doc = FakeGenSkill(["DOC"])
    quiz = FakeGenSkill(["QUIZ"])
    plan = [make_task("s1", "doc"), make_task("s2", "quiz")]

    result = await pipeline_node(base_state(plan, make_skills({"doc_gen": doc, "quiz_gen": quiz})))

    assert [u["status"] for u in result["completed"]] == ["passed", "passed"]


# ———————————————————— dispatch_route（路由零回归）————————————————————

def test_dispatch_route_pipeline_mode_sends_to_pipeline():
    state = {"collab_mode": "pipeline", "plan": [make_task("s1"), make_task("s2")]}

    sends = dispatch_route(state)

    assert len(sends) == 1
    assert sends[0].node == "pipeline"


def test_dispatch_route_central_mode_matches_fan_out():
    state = {"collab_mode": "central", "plan": [make_task("s1"), make_task("s2")]}

    routed = dispatch_route(state)
    expected = fan_out(state)

    assert [s.node for s in routed] == [s.node for s in expected] == ["generate_resource", "generate_resource"]
    assert [s.arg["_current_task"]["task_id"] for s in routed] == ["s1", "s2"]
    # collab_mode 缺失也等同 central —— 证明对现有中心化路径零回归
    state_none = {"plan": [make_task("s1"), make_task("s2")]}
    assert [s.node for s in dispatch_route(state_none)] == ["generate_resource", "generate_resource"]


def test_dispatch_route_pipeline_empty_plan_returns_empty():
    state = {"collab_mode": "pipeline", "plan": [make_task("s1", status="passed")]}

    assert dispatch_route(state) == []


# ———————————————————— _infer_collab_mode（协作模式判定）————————————————————

def test_infer_collab_mode_pipeline_from_keywords():
    assert _infer_collab_mode("机器学习从入门到精通的系统学习路径", None, [1, 2]) == "pipeline"


def test_infer_collab_mode_central_for_plain_goal():
    assert _infer_collab_mode("解释线性回归原理", None, [1, 2]) == "central"


def test_infer_collab_mode_respects_llm_explicit():
    assert _infer_collab_mode("解释线性回归原理", "pipeline", [1]) == "pipeline"


def test_infer_collab_mode_keyword_needs_two_tasks():
    # 命中关键词但只有 1 个任务 → 退化为 central（单任务无流水线意义）
    assert _infer_collab_mode("系统学习路径", None, [1]) == "central"


def test_infer_collab_mode_debate_from_keywords():
    assert _infer_collab_mode("Transformer 和 RNN 哪个更好", None, [1, 2]) == "debate"


def test_infer_collab_mode_debate_priority_over_pipeline():
    # 同时含 pipeline 词（系统）与 debate 词（对比/优劣）→ debate 优先
    assert _infer_collab_mode("系统对比监督与无监督学习的优劣", None, [1, 2]) == "debate"


def test_infer_collab_mode_debate_ignores_task_count():
    # debate 不要求 ≥2 任务（区别于 pipeline 的单任务退化）
    assert _infer_collab_mode("该不该早停", None, [1]) == "debate"


# ———————————————————— 端到端可达性（防 dead-path 回归）————————————————————

class _E2EFakeLLM:
    """planning 返回 2 任务 + collab_mode=pipeline；其余返回足够长文本以通过 quality 的长度规则。"""

    async def complete(self, messages, *, task_type="generation", schema=None, temperature=0.7):
        from reflexlearn.llm_gateway.gateway import Completion

        if task_type == "planning":
            return Completion(text=json.dumps({
                "tasks": [
                    {"type": "doc", "concept_ids": ["c1"], "difficulty": 0.4, "style_hint": "active", "constraints": []},
                    {"type": "quiz", "concept_ids": ["c2"], "difficulty": 0.5, "style_hint": "active", "constraints": []},
                ],
                "collab_mode": "pipeline",
            }, ensure_ascii=False))
        return Completion(
            text="ML teaching content long enough to pass the length-based rule quality check and serve as downstream context."
        )


@pytest.mark.asyncio
async def test_pipeline_end_to_end_reachable():
    """astream 从 START 应真正走到 pipeline 节点并产出资源包——确保 pipeline 端到端可达，不是 dead path。"""
    from reflexlearn.orchestration.graph import build_graph

    graph = build_graph(_E2EFakeLLM())
    initial = {
        "user_id": "u1", "acl": {"user_id": "u1"},
        "messages": [{"role": "user", "content": "ML path"}],
        "learner_profile": {}, "learning_goal": "systematic learning path",
        "collab_mode": "central",
        "plan": [], "completed": [], "reflections": [],
        "iteration": 0, "replan_count": 0, "token_used": 0,
        "halt_reason": None, "conflict": None,
        "debate_rounds": None, "debate_verdict": None,
        "resource_bundle": None, "learning_path": None,
    }

    seen, final = [], None
    async for event in graph.astream(initial, stream_mode="updates"):
        for node_name, output in event.items():
            seen.append(node_name)
            if node_name == "assemble":
                final = output

    assert "pipeline" in seen          # 真正进入 pipeline 节点
    assert "debate" not in seen        # 未误入 debate
    assert final["resource_bundle"]["total"] == 2
