from __future__ import annotations

import json
import uuid
from typing import Literal, Optional

from pydantic import BaseModel, Field, ValidationError

from reflexlearn.orchestration.state import AgentState, ResourceTask
from reflexlearn.orchestration.schemas import ResourceSpec
from reflexlearn.memory.recursive_summary import get_context


class PlanItem(BaseModel):
    type: ResourceSpec.model_fields["type"].annotation
    concept_ids: list[str] = Field(default_factory=list)
    difficulty: float = Field(default=0.5, ge=0, le=1)
    style_hint: str = ""
    constraints: list[str] = Field(default_factory=list)


class PlanOutput(BaseModel):
    tasks: list[PlanItem] = Field(min_length=1, max_length=6)
    collab_mode: Optional[Literal["central", "pipeline", "debate"]] = None


SUPPORTED_TYPES = {"doc", "quiz", "mindmap", "code", "reading", "video"}

PIPELINE_KEYWORDS = (
    "系统", "路径", "循序渐进", "从入门到", "分阶段",
    "进阶", "体系", "由浅入深", "学习路线", "step by step",
)

DEBATE_KEYWORDS = (
    "辩论", "争议", "对比", "优劣", "利弊", "该不该", "是否应该",
    "哪个更好", "之争", "孰优孰劣", "正方", "反方", "vs",
)


def _infer_collab_mode(goal: str, llm_mode: Optional[str], tasks: list) -> str:
    """判定协作模式：LLM 显式合法值优先；否则 goal 命中辩论关键词 → debate
    （对单一议题的正反交锋，不要求任务数，且优先于 pipeline——「对立/取舍」意图
    比「循序渐进」更窄更强）；命中强依赖关键词且任务数≥2 → pipeline；默认 central。"""
    if llm_mode in {"central", "pipeline", "debate"}:
        return llm_mode
    goal_lower = (goal or "").lower()
    if any(kw.lower() in goal_lower for kw in DEBATE_KEYWORDS):
        return "debate"
    if any(kw.lower() in goal_lower for kw in PIPELINE_KEYWORDS) and len(tasks) >= 2:
        return "pipeline"
    return "central"


async def planner_node(state: AgentState) -> dict:
    goal = state.get("learning_goal", "")
    profile = state.get("learner_profile", {})
    llm = state.get("_llm")

    plan, llm_mode = await _plan_with_llm(
        goal, profile, state.get("reflections", []), llm, state.get("summary_layers", [])
    )
    if not plan:
        plan = _fallback_plan(goal, profile)
        llm_mode = None

    tasks = [_to_resource_task(item) for item in plan]
    collab_mode = _infer_collab_mode(goal, llm_mode, plan)
    result = {"plan": tasks, "collab_mode": collab_mode, "iteration": state.get("iteration", 0) + 1}
    # 仅辩论模式注入 conflict 点火 gate→debate→judge 链路；其它模式不写该 key，
    # 保持 central / pipeline 流的 state 与改造前逐字节一致。
    if collab_mode == "debate":
        result["conflict"] = _build_debate_conflict(goal, profile)
    return result


async def _plan_with_llm(
    goal: str,
    profile: dict,
    reflections: list[dict],
    llm,
    summary_layers: list[str] | None = None,
) -> tuple[list[PlanItem], Optional[str]]:
    if llm is None:
        return [], None

    # L1 多轮：历史摘要注入 system prompt 末尾（仿 reflections 注入），非空才注入 → 单轮零回归
    system_content = (
        "你是 ReflexLearn 的 Planner Agent。"
        "请把学习目标拆成 1 到 4 个可执行资源任务。"
        "只输出 JSON，格式为 {\"tasks\": [...]}。"
        "tasks 中每项必须包含 type、concept_ids、difficulty、style_hint、constraints。"
        "type 只能使用 doc、quiz、mindmap、code、reading、video。"
    )
    summary_ctx = get_context(summary_layers or [])
    if summary_ctx:
        system_content += f"\n\n【历史对话摘要】（用于理解多轮上下文，勿直接复述）：\n{summary_ctx}"

    messages = [
        {
            "role": "system",
            "content": system_content,
        },
        {
            "role": "user",
            "content": json.dumps(
                {
                    "learning_goal": goal,
                    "learner_profile": profile,
                    "reflections": reflections[:3],
                },
                ensure_ascii=False,
            ),
        },
    ]

    try:
        completion = await llm.complete(
            messages,
            task_type="planning",
            schema=PlanOutput,
            temperature=0.1,
        )
        output = PlanOutput.model_validate_json(completion.text)
        items = [_normalize_item(item, goal, profile) for item in output.tasks]
        return items, output.collab_mode
    except (ValidationError, ValueError, json.JSONDecodeError, AttributeError):
        return [], None
    except Exception:
        return [], None


def _build_debate_conflict(goal: str, profile: dict) -> dict:
    """为辩论模式构造围绕学习目标的正反方证据 chunks。字段对齐 debate._fallback_position：
    source→perspective、content→claim/evidence_summary、relevance_score→confidence。
    离线无 LLM 时即以此内容辩论；有 LLM 时由 debater 在此基础上深化。"""
    topic = goal or "该学习议题"
    weak = "、".join(profile.get("weak_points", []) or [])
    con_tail = f"，尤其需结合学习者薄弱点（{weak}）审慎评估" if weak else ""
    chunks = [
        {
            "source": "正方 / 支持派",
            "content": (
                f"针对「{topic}」，正方主张：该方法 / 结论在主流场景下成立且收益明确，"
                "有成熟实践与典型案例支撑、落地成本可控，应优先采用。"
            ),
            "relevance_score": 0.7,
        },
        {
            "source": "反方 / 审慎派",
            "content": (
                f"针对「{topic}」，反方主张：结论需附加前提与边界条件，"
                f"在特定数据规模 / 任务类型下可能失效{con_tail}，不宜无条件套用。"
            ),
            "relevance_score": 0.6,
        },
    ]
    return {"has_conflict": True, "topic": topic, "chunks": chunks}


def _fallback_item(goal: str, profile: dict) -> PlanItem:
    return PlanItem(
        type="doc",
        concept_ids=[goal or "学习目标"],
        difficulty=_profile_difficulty(profile),
        style_hint=profile.get("cognitive_style", "active"),
        constraints=["控制在 500 字以内", "包含示例", "优先解释薄弱点"],
    )


def _fallback_plan(goal: str, profile: dict) -> list[PlanItem]:
    """无 LLM / LLM 失败时的规则规划：围绕目标产出一套多模态基础资源
    （文档 + 导图 + 练习 + 代码 + 拓展阅读 + 视频脚本，覆盖全部 6 种资源类型）。
    既保证离线可用与鲁棒降级，也让流水线协作与多模态卡片在无凭证环境下
    仍可端到端体验，并满足「≥5 种资源」的 P0 硬指标（含多模态视频 / 动画）。"""
    concept = goal or "学习目标"
    difficulty = _profile_difficulty(profile)
    style = profile.get("cognitive_style", "active")
    extras = [
        ("mindmap", ["层级清晰", "覆盖核心概念与常见误区"]),
        ("quiz", ["3 道题", "含答案与解析"]),
        ("code", ["可运行", "含运行说明与要点"]),
        ("reading", ["3-5 项进阶材料", "由易到难", "标注类型与推荐理由"]),
        ("video", ["3-5 个分镜", "含画面与旁白文案", "可作视频生成输入"]),
    ]
    plan = [_fallback_item(goal, profile)]
    plan += [
        PlanItem(
            type=t,
            concept_ids=[concept],
            difficulty=difficulty,
            style_hint=style,
            constraints=c,
        )
        for t, c in extras
    ]
    return plan


def _normalize_item(item: PlanItem, goal: str, profile: dict) -> PlanItem:
    resource_type = item.type if item.type in SUPPORTED_TYPES else "doc"
    concept_ids = item.concept_ids or [goal or "学习目标"]
    style_hint = item.style_hint or profile.get("cognitive_style", "active")
    constraints = item.constraints or ["结构清晰", "匹配学习者画像"]

    return PlanItem(
        type=resource_type,
        concept_ids=concept_ids,
        difficulty=item.difficulty,
        style_hint=style_hint,
        constraints=constraints,
    )


def _profile_difficulty(profile: dict) -> float:
    knowledge = profile.get("knowledge_base", {})
    if not knowledge:
        return 0.5
    avg_mastery = sum(knowledge.values()) / len(knowledge)
    return min(max(0.25 + avg_mastery * 0.5, 0.2), 0.8)


def _to_resource_task(item: PlanItem) -> ResourceTask:
    spec = ResourceSpec(
        type=item.type,
        concept_ids=item.concept_ids,
        difficulty=item.difficulty,
        style_hint=item.style_hint,
        constraints=item.constraints,
    )
    return {
        "task_id": str(uuid.uuid4())[:8],
        "type": item.type,
        "spec": spec.model_dump(),
        "status": "pending",
        "attempts": 0,
        "result_ref": None,
    }
