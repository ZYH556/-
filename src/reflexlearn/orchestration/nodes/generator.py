from __future__ import annotations

from reflexlearn.common.config import get_settings
from reflexlearn.orchestration.state import AgentState
from reflexlearn.skills.base import SkillContext


async def generate_resource(state: AgentState) -> dict:
    task = state.get("_current_task")
    if not task:
        plan = state.get("plan", [])
        task = next((t for t in plan if t["status"] == "pending"), None)
        if not task:
            return {"completed": [{"task_id": "none", "status": "failed"}]}

    skills = state.get("_skills", {})
    retrieve_skill = skills.get("retrieve")
    quality_skill = skills.get("quality_check")

    ctx = SkillContext(
        user_id=state.get("user_id", "anonymous"),
        acl=state.get("acl", {}),
        task_id=task["task_id"],
    )

    context_text = await _retrieve_context(task, retrieve_skill, ctx)
    issues: list[str] = []
    max_steps = max(1, get_settings().max_react_steps)

    for step in range(max_steps):
        gen_result = await _run_generation(task, context_text, issues, skills, ctx)
        if not gen_result.ok or not gen_result.data:
            issues = [gen_result.error_type or "生成失败"]
            continue

        content = gen_result.data.get("content", "")
        verify = await _verify_content(content, task, state, quality_skill, ctx)
        if verify.get("passed"):
            return {
                "completed": [
                    {
                        "task_id": task["task_id"],
                        "status": "passed",
                        "type": task["type"],
                        "content": content,
                        "react_steps": step + 1,
                    }
                ]
            }

        issues = verify.get("issues", ["质量校验未通过"])
        if not verify.get("fixable", True):
            break

    return {
        "completed": [
            {
                "task_id": task["task_id"],
                "status": "failed",
                "type": task["type"],
                "issues": issues,
            }
        ]
    }


async def _retrieve_context(task: dict, retrieve_skill, ctx: SkillContext) -> str:
    if retrieve_skill:
        ret_result = await retrieve_skill.run(
            {"query": task["spec"].get("concept_ids", [""])[0]}, ctx
        )
        if ret_result.ok and ret_result.data:
            chunks = ret_result.data.get("chunks", [])
            return "\n".join(c.get("content", "") for c in chunks)
    return ""


async def _run_generation(
    task: dict,
    context_text: str,
    issues: list[str],
    skills: dict,
    ctx: SkillContext,
):
    skill = _select_generation_skill(task.get("type", "doc"), skills)
    if skill is None:
        from reflexlearn.skills.base import SkillResult

        return SkillResult(ok=False, error_type="generation_skill_missing")

    return await skill.run(
        {
            "spec": {
                **task["spec"],
                "previous_issues": issues,
            },
            "context": context_text,
        },
        ctx,
    )


def _select_generation_skill(task_type: str, skills: dict):
    skill_name = f"{task_type}_gen"
    return skills.get(skill_name) or skills.get("doc_gen")


async def _verify_content(
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
