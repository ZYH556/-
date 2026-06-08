from __future__ import annotations

from reflexlearn.common.config import get_settings
from reflexlearn.orchestration.state import AgentState
from reflexlearn.skills.base import SkillContext, SkillResult


ROLLBACK_BUDGET = 1


async def pipeline_node(state: AgentState) -> dict:
    """流水线协作：把 plan 当作强依赖链顺序执行，上游产出作为下游 context（上游输出入下游 spec）。

    每步后置校验 + 步内重试；某步彻底失败时回退一格（最多 ROLLBACK_BUDGET 次）重做上一步；
    回退预算耗尽或首步即失败则截断，已完成段作为部分结果并置 halt_reason，由 gate_route 短路降级收尾。
    整条链封装在单节点内（与 debate_node 同构），便于在节点内维护游标与回退。
    """
    plan = [t for t in state.get("plan", []) if t.get("status") == "pending"]
    skills = state.get("_skills", {})
    quality_skill = skills.get("quality_check")
    max_retries = max(1, get_settings().max_react_steps)

    if not plan:
        return {"completed": [], "iteration": state.get("iteration", 0) + 1}

    units: list[dict] = []
    upstream_content = ""
    rollback_budget = ROLLBACK_BUDGET
    i = 0

    while i < len(plan):
        task = plan[i]
        ctx = SkillContext(
            user_id=state.get("user_id", "anonymous"),
            acl=state.get("acl", {}),
            task_id=task["task_id"],
        )
        issues: list[str] = []
        step_passed = False

        for _ in range(max_retries):
            gen = await _run_step(task, upstream_content, issues, skills, ctx)
            if not gen.ok or not gen.data:
                issues = [gen.error_type or "生成失败"]
                continue

            content = gen.data.get("content", "")
            verify = await _verify_step(content, task, state, quality_skill, ctx)
            if verify.get("passed"):
                units.append(_passed_unit(task, content, i))
                upstream_content = content  # 上游产出注入下一步 context
                step_passed = True
                break

            issues = verify.get("issues", ["质量校验未通过"])
            if not verify.get("fixable", True):
                break

        if step_passed:
            i += 1
            continue

        # 失败回退一格：丢弃上一步产物、回退上游 context、重做上一步
        if i > 0 and rollback_budget > 0:
            rollback_budget -= 1
            units.pop()
            upstream_content = units[-1]["content"] if units else ""
            i -= 1
            continue

        # 回退预算耗尽 / 首步即失败：截断，部分结果降级收尾
        units.append(_failed_unit(task, issues))
        return {
            "completed": units,
            "halt_reason": "pipeline_partial",
            "iteration": state.get("iteration", 0) + 1,
        }

    return {"completed": units, "iteration": state.get("iteration", 0) + 1}


async def _run_step(
    task: dict,
    upstream_content: str,
    issues: list[str],
    skills: dict,
    ctx: SkillContext,
) -> SkillResult:
    skill = _select_gen_skill(task.get("type", "doc"), skills)
    if skill is None:
        return SkillResult(ok=False, error_type="generation_skill_missing")

    return await skill.run(
        {
            "spec": {**task["spec"], "previous_issues": issues},
            "context": upstream_content,
        },
        ctx,
    )


async def _verify_step(
    content: str,
    task: dict,
    state: AgentState,
    quality_skill,
    ctx: SkillContext,
) -> dict:
    if quality_skill is None:
        return {"passed": True, "issues": [], "fixable": True}

    result = await quality_skill.run(
        {
            "content": content,
            "spec": task["spec"],
            "profile": state.get("learner_profile", {}),
        },
        ctx,
    )
    if result.ok and result.data:
        return {
            "passed": result.data.get("passed", False),
            "issues": result.data.get("issues", []),
            "fixable": result.data.get("fixable", True),
        }
    return {"passed": False, "issues": [result.error_type or "质量校验失败"], "fixable": True}


def _select_gen_skill(task_type: str, skills: dict):
    return skills.get(f"{task_type}_gen") or skills.get("doc_gen")


def _passed_unit(task: dict, content: str, step_index: int) -> dict:
    return {
        "task_id": task["task_id"],
        "status": "passed",
        "type": task.get("type", "doc"),
        "content": content,
        "pipeline_step": step_index + 1,
    }


def _failed_unit(task: dict, issues: list[str]) -> dict:
    return {
        "task_id": task["task_id"],
        "status": "failed",
        "type": task.get("type", "doc"),
        "issues": issues,
    }
