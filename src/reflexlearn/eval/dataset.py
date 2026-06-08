from __future__ import annotations

from reflexlearn.eval.schemas import EvalCase


def default_eval_cases() -> list[EvalCase]:
    """M5 最小评测集：先围绕机器学习核心知识点，保证离线快速可跑。"""
    return [
        EvalCase(
            case_id="ml-001",
            goal="学习线性回归的原理和 Python 实现",
            profile={
                "knowledge_base": {"statistics": 0.5, "python": 0.7},
                "cognitive_style": "active",
                "weak_points": ["数学推导"],
                "progress": 0.2,
            },
            expected_resource_types=["doc", "quiz", "code"],
            reference_concepts=["线性回归", "最小二乘法", "梯度下降"],
            difficulty_min=0.2,
            difficulty_max=0.7,
            tags=["supervised_learning", "basic"],
        ),
        EvalCase(
            case_id="ml-002",
            goal="系统理解过拟合、正则化和泛化能力",
            profile={
                "knowledge_base": {"machine_learning": 0.4},
                "cognitive_style": "visual",
                "weak_points": ["模型评估"],
                "progress": 0.35,
            },
            expected_resource_types=["doc", "mindmap", "quiz"],
            reference_concepts=["过拟合", "正则化", "泛化能力"],
            difficulty_min=0.3,
            difficulty_max=0.8,
            tags=["model_selection", "regularization"],
        ),
        EvalCase(
            case_id="ml-003",
            goal="从零搭建神经网络入门学习路径",
            profile={
                "knowledge_base": {"linear_algebra": 0.4, "python": 0.6},
                "cognitive_style": "reflective",
                "weak_points": ["反向传播"],
                "progress": 0.25,
            },
            expected_resource_types=["doc", "reading", "video"],
            reference_concepts=["神经网络", "反向传播", "激活函数"],
            difficulty_min=0.3,
            difficulty_max=0.8,
            tags=["deep_learning", "path"],
        ),
        EvalCase(
            case_id="ml-004",
            goal="基于课程知识库解释 RAG 三路检索如何帮助学习线性回归",
            profile={
                "knowledge_base": {"machine_learning": 0.35, "information_retrieval": 0.2},
                "cognitive_style": "verbal",
                "weak_points": ["检索增强", "知识图谱"],
                "progress": 0.3,
            },
            expected_resource_types=["doc", "mindmap", "reading"],
            reference_concepts=["Qdrant", "BM25", "Neo4j", "RRF", "ACL"],
            difficulty_min=0.4,
            difficulty_max=0.85,
            tags=["ablation", "rag_required"],
        ),
        EvalCase(
            case_id="ml-005",
            goal="围绕一次质量校验失败，生成线性回归学习资源的修复方案",
            profile={
                "knowledge_base": {"machine_learning": 0.45, "python": 0.55},
                "cognitive_style": "reflective",
                "weak_points": ["失败复盘", "自我修正"],
                "progress": 0.4,
            },
            expected_resource_types=["doc", "quiz", "code"],
            reference_concepts=["失败归因", "修复策略", "重规划", "质量校验", "Reflexion"],
            difficulty_min=0.35,
            difficulty_max=0.8,
            tags=["ablation", "reflexion_required"],
        ),
    ]


def select_eval_cases(
    *,
    tags: list[str] | None = None,
    max_cases: int | None = None,
) -> list[EvalCase]:
    cases = default_eval_cases()
    required = {tag for tag in (tags or []) if tag}
    if required:
        cases = [case for case in cases if required.issubset(set(case.tags))]
    if max_cases is not None and max_cases > 0:
        return cases[:max_cases]
    return cases
