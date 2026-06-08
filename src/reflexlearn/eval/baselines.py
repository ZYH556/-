from __future__ import annotations

from collections.abc import AsyncIterator

from reflexlearn.eval.schemas import EvalCase


async def single_agent_baseline(case: EvalCase) -> AsyncIterator[dict]:
    """单 Agent 朴素基线：不规划、不检索、不生成多资源，只产出一份 doc。"""
    content = (
        f"# 单 Agent 基线\n\n"
        f"学习目标：{case.goal}\n\n"
        "这是一个直接生成的简短讲解，不使用多智能体规划、RAG 检索、"
        "反思重试或多资源协作。"
    )
    yield {"planner": {"plan": [{"type": "doc", "baseline": True}]}}
    yield {
        "assemble": {
            "resource_bundle": {
                "resources": [
                    {
                        "task_id": f"{case.case_id}-baseline-doc",
                        "type": "doc",
                        "content": content,
                        "difficulty": 0.5,
                    }
                ],
                "total": 1,
            }
        }
    }


async def controlled_rag_baseline(case: EvalCase) -> AsyncIterator[dict]:
    """受控 RAG 消融基线：仅对 rag_required case 注入固定参考知识。"""
    concepts = case.reference_concepts if "rag_required" in case.tags else []
    async for event in _controlled_baseline(case, mode="controlled_rag", concepts=concepts):
        yield event


async def controlled_reflexion_baseline(case: EvalCase) -> AsyncIterator[dict]:
    """受控 Reflexion 消融基线：仅对 reflexion_required case 注入固定修复经验。"""
    concepts = case.reference_concepts if "reflexion_required" in case.tags else []
    async for event in _controlled_baseline(
        case,
        mode="controlled_reflexion",
        concepts=concepts,
    ):
        yield event


async def _controlled_baseline(
    case: EvalCase,
    *,
    mode: str,
    concepts: list[str],
) -> AsyncIterator[dict]:
    resource_types = case.expected_resource_types or ["doc"]
    yield {"planner": {"plan": [{"type": item, "baseline": mode} for item in resource_types]}}
    yield {
        "assemble": {
            "resource_bundle": {
                "resources": [
                    _controlled_resource(case, resource_type, mode=mode, concepts=concepts)
                    for resource_type in resource_types
                ],
                "total": len(resource_types),
            }
        }
    }


def _controlled_resource(
    case: EvalCase,
    resource_type: str,
    *,
    mode: str,
    concepts: list[str],
) -> dict:
    concept_text = "、".join(concepts) if concepts else "未注入外部参考知识"
    if mode == "controlled_rag":
        evidence = (
            f"受控 RAG 上下文命中：{concept_text}。"
            "该资源明确使用检索增强证据解释问题、合并语义检索、关键词检索与图谱关系。"
        )
    else:
        evidence = (
            f"受控 Reflexion 经验命中：{concept_text}。"
            "该资源先做失败归因，再给出修复策略、重规划步骤和质量校验清单。"
        )
    return {
        "task_id": f"{case.case_id}-{mode}-{resource_type}",
        "type": resource_type,
        "content": (
            f"# {resource_type} · {case.goal}\n\n"
            f"{evidence}\n\n"
            "## 学习安排\n"
            "1. 先定位目标知识点与学习者薄弱点。\n"
            "2. 再用证据或经验补齐缺失上下文。\n"
            "3. 最后产出可检查、可复盘的学习资源。\n\n"
            f"参考概念：{concept_text}。"
        ),
        "difficulty": max(case.difficulty_min, min(0.6, case.difficulty_max)),
    }
