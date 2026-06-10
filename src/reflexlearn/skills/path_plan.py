"""学习路径规划 Skill：把一组已生成资源组织成个性化、可解释的学习路径。

LLM 优先（按画像/目标排序，并产出每步「学习目标」与「排序理由」）；任何 LLM 异常
（无凭证 OFFLINE_TAG / 网络 / JSON 解析失败）一律降级到规则排序（教学序 + 难度梯度 +
薄弱点前置），仍返回 ok=True —— path_plan 是终态节点、无重试循环，规则排序不依赖 LLM，
没有理由因 LLM 不可用就放弃排序。ok=False 只留给「规则排序自身抛异常」这种不该发生的情况。

graph（概念依赖图）为 Neo4j 混合检索预留：非 None 时用真实前置依赖修正顺序，本轮恒 None
→ 走启发式（同概念软依赖）。这是「接口先行」，下一轮混合检索做好后由 node 注入真实依赖图。
"""
from __future__ import annotations

import json
import logging
import time
from typing import Optional

from reflexlearn.llm_gateway.gateway import LLMGateway
from reflexlearn.orchestration.schemas import LearningPathPlan
from reflexlearn.skills.base import SkillContext, SkillResult
from reflexlearn.skills.offline import OFFLINE_TAG
from reflexlearn.skills.path_topology import topo_order

logger = logging.getLogger(__name__)

# 教学序权重：先建立认知(doc) → 构建框架(mindmap) → 动手实践(code) → 检验巩固(quiz)
#            → 拓展深化(reading) → 多模态辅助(video)。未知类型(如 debate 结论)排末位。
TEACH_ORDER = {"doc": 0, "mindmap": 1, "code": 2, "quiz": 3, "reading": 4, "video": 5}
UNKNOWN_ORDER = 99

_OBJECTIVE = {
    "doc": "建立对「{c}」的整体认知与核心概念理解",
    "mindmap": "用思维导图梳理「{c}」的知识框架与脉络",
    "code": "通过可运行代码动手实践「{c}」，把概念落到实现",
    "quiz": "通过练习题检验并巩固「{c}」的掌握程度",
    "reading": "拓展阅读深化对「{c}」的理解与视野",
    "video": "借助多模态视频直观理解「{c}」",
    "debate": "通过多方辩论厘清「{c}」的争议与适用边界",
}

_RATIONALE_STAGE = {
    "doc": "作为认知起点，先建立概念基础",
    "mindmap": "在讲解之后构建结构化框架，串联知识点",
    "code": "理解概念后动手实践，加深记忆",
    "quiz": "实践之后检验掌握程度，查漏补缺",
    "reading": "掌握主干后拓展深化",
    "video": "多模态辅助，可按需穿插观看",
    "debate": "作为争议性结论的补充判断",
}


def _objective(rtype: str, concept: str) -> str:
    tmpl = _OBJECTIVE.get(rtype, "系统学习「{c}」")
    return tmpl.format(c=concept or "该主题")


def _rationale(rtype: str, difficulty: float, weak: bool) -> str:
    parts: list[str] = []
    if weak:
        parts.append("针对学习者薄弱点，优先前置")
    parts.append(_RATIONALE_STAGE.get(rtype, "作为补充内容纳入路径"))
    parts.append(f"难度约 {float(difficulty):.1f}")
    return "；".join(parts)


class PathPlanSkill:
    name = "path_plan"
    max_calls_per_task = 2
    cache_ttl = None

    def __init__(self, llm: LLMGateway):
        self.llm = llm

    async def run(self, inp: dict, ctx: SkillContext) -> SkillResult:
        start = time.time()
        resources = inp.get("resources") or []
        profile = inp.get("profile") or {}
        goal = inp.get("goal") or ""
        graph = inp.get("graph")

        if not resources:
            return SkillResult(
                ok=True,
                data={"path": [], "summary": "", "strategy": "", "mode": "empty"},
                duration_ms=int((time.time() - start) * 1000),
            )

        plan = await self._plan_with_llm(resources, profile, goal)
        mode = "llm"
        if plan is None:
            plan = self._rule_based_order(resources, profile, goal, graph)
            mode = "rule"

        return SkillResult(
            ok=True,
            data={
                "path": plan["steps"],
                "summary": plan["summary"],
                "strategy": plan["strategy"],
                "mode": mode,
            },
            duration_ms=int((time.time() - start) * 1000),
        )

    # —— LLM 排序（智能，失败即降级） ——
    async def _plan_with_llm(self, resources: list[dict], profile: dict, goal: str) -> Optional[dict]:
        brief = [
            {
                "task_id": r.get("task_id", ""),
                "type": r.get("resource_type", "doc"),
                "concept": r.get("concept", ""),
                "difficulty": r.get("difficulty", 0.5),
            }
            for r in resources
        ]
        messages = [
            {
                "role": "system",
                "content": (
                    "你是 ReflexLearn 的学习路径规划 Agent。给定一组已生成的学习资源和学习者画像，"
                    "把它们排成一条个性化、由浅入深的学习路径。"
                    "排序原则：先建立概念认知，再构建框架，再动手实践与检验，最后拓展；"
                    "优先照顾学习者薄弱点；难度由低到高。"
                    "只输出 JSON：{\"steps\":[{\"sequence\",\"task_id\",\"resource_type\","
                    "\"concept\",\"objective\",\"rationale\",\"difficulty\",\"depends_on\"}],"
                    "\"summary\",\"strategy\"}。objective=这一步的学习目标；rationale=为什么排在这个位置"
                    "（要可解释）。task_id 必须来自给定资源，不要新增或编造。"
                ),
            },
            {
                "role": "user",
                "content": json.dumps(
                    {"learning_goal": goal, "learner_profile": profile, "resources": brief},
                    ensure_ascii=False,
                ),
            },
        ]
        try:
            completion = await self.llm.complete(
                messages, task_type="planning", schema=LearningPathPlan, temperature=0.1
            )
            parsed = LearningPathPlan.model_validate_json(completion.text)
            steps = self._finalize_llm_steps(parsed, resources)
            if not steps:
                return None
            return {
                "steps": steps,
                "summary": parsed.summary or f"围绕「{goal or '学习目标'}」规划 {len(steps)} 步学习路径。",
                "strategy": parsed.strategy or "由 LLM 按学习者画像与教学逻辑排序，先补薄弱点、由浅入深。",
            }
        except Exception as e:  # 无凭证 / 网络 / JSON / 校验，统一降级
            if OFFLINE_TAG in str(e):
                logger.info("path_plan degraded (no api key) -> rule based")
            else:
                logger.info("path_plan degraded (llm %s) -> rule based", type(e).__name__)
            return None

    def _finalize_llm_steps(self, parsed: LearningPathPlan, resources: list[dict]) -> list[dict]:
        """以 LLM 给的顺序为准，但用真实资源校准：丢弃编造/重复的 task_id，
        resource_type/difficulty 以真实资源为准（防 LLM 幻觉），并把 LLM 漏掉的资源补到末尾。"""
        by_id = {r.get("task_id"): r for r in resources}
        seen: set[str] = set()
        steps: list[dict] = []
        for s in parsed.steps:
            r = by_id.get(s.task_id)
            if r is None or s.task_id in seen:
                continue
            seen.add(s.task_id)
            rtype = r.get("resource_type", "doc")
            concept = s.concept or r.get("concept", "")
            steps.append(
                {
                    "sequence": len(steps) + 1,
                    "task_id": s.task_id,
                    "resource_type": rtype,
                    "concept": concept,
                    "objective": s.objective or _objective(rtype, concept),
                    "rationale": s.rationale or _rationale(rtype, r.get("difficulty", 0.5), False),
                    "difficulty": float(r.get("difficulty", 0.5)),
                    "depends_on": [d for d in s.depends_on if d in by_id and d != s.task_id],
                }
            )
        for r in resources:  # 补 LLM 漏排的资源
            tid = r.get("task_id", "")
            if tid in seen:
                continue
            rtype = r.get("resource_type", "doc")
            concept = r.get("concept", "")
            steps.append(
                {
                    "sequence": len(steps) + 1,
                    "task_id": tid,
                    "resource_type": rtype,
                    "concept": concept,
                    "objective": _objective(rtype, concept),
                    "rationale": _rationale(rtype, r.get("difficulty", 0.5), False),
                    "difficulty": float(r.get("difficulty", 0.5)),
                    "depends_on": [],
                }
            )
            seen.add(tid)
        return steps

    # —— 规则排序（离线/降级，纯 Python 不碰 LLM） ——
    def _rule_based_order(self, resources: list[dict], profile: dict, goal: str, graph) -> dict:
        weak = [w.lower() for w in (profile.get("weak_points") or []) if w]

        def is_weak(concept: str) -> bool:
            if not weak:
                return False
            c = (concept or "").lower()
            return any(w in c or c in w for w in weak)

        def sort_key(r: dict):
            order = TEACH_ORDER.get(r.get("resource_type"), UNKNOWN_ORDER)
            weak_rank = 0 if is_weak(r.get("concept", "")) else 1
            return (weak_rank, order, float(r.get("difficulty", 0.5)))

        # graph 非 None：按 Neo4j 真实 PREREQUISITE_OF 拓扑排序；否则启发式（现状，零回归）
        prereq_tids: dict[str, list[str]] = {}
        if graph:
            ordered, prereq_tids = topo_order(resources, graph, sort_key)
        else:
            ordered = sorted(resources, key=sort_key)

        steps: list[dict] = []
        prev_by_concept: dict[str, str] = {}
        for i, r in enumerate(ordered):
            concept = r.get("concept") or goal or "该主题"
            rtype = r.get("resource_type", "doc")
            tid = r.get("task_id", "")
            weak_hit = is_weak(r.get("concept", ""))
            # 同概念前一步作软依赖（概念内教学序）
            soft = [prev_by_concept[concept]] if concept in prev_by_concept else []
            if graph:
                # 真实跨概念前置(PREREQUISITE_OF) ∪ 同概念前一步，去重保序
                depends_on = list(dict.fromkeys(prereq_tids.get(tid, []) + soft))
            else:
                depends_on = soft
            steps.append(
                {
                    "sequence": i + 1,
                    "task_id": tid,
                    "resource_type": rtype,
                    "concept": concept,
                    "objective": _objective(rtype, concept),
                    "rationale": _rationale(rtype, r.get("difficulty", 0.5), weak_hit),
                    "difficulty": float(r.get("difficulty", 0.5)),
                    "depends_on": depends_on,
                }
            )
            prev_by_concept[concept] = tid

        summary = f"围绕「{goal or '学习目标'}」规划了 {len(steps)} 步学习路径，由浅入深、先补薄弱点。"
        if graph:
            strategy = "图谱拓扑排序：按知识点真实前置依赖(Neo4j PREREQUISITE_OF)定序 + 教学序 + 难度升序"
        else:
            strategy = "规则排序：薄弱点优先 → 教学序（讲解→框架→实践→检验→拓展→视频）→ 难度升序"
        return {"steps": steps, "summary": summary, "strategy": strategy}
