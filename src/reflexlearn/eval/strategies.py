from __future__ import annotations

import os
from collections.abc import Iterator
from contextlib import contextmanager
from typing import Protocol

from pydantic import BaseModel, Field

from reflexlearn.eval.schemas import EvalCase, EvalReport


class EvalStrategy(BaseModel):
    name: str
    description: str
    env: dict[str, str] = Field(default_factory=dict)


class RunnerLike(Protocol):
    async def run(self, cases: list[EvalCase], *, strategy: str) -> EvalReport:
        """EvalRunner-compatible subset."""


class RunnerFactory(Protocol):
    def __call__(self, profile: EvalStrategy) -> RunnerLike:
        """Build runner under a strategy-specific environment."""


def default_eval_strategies() -> list[EvalStrategy]:
    return [
        EvalStrategy(
            name="full-smoke",
            description="完整编排 smoke；默认关闭慢依赖以保证速度",
            env={
                "ENABLE_RAG": "false",
                "ENABLE_MULTI_TURN": "false",
                "ENABLE_REFLEXION": "false",
            },
        ),
        EvalStrategy(
            name="no_rag",
            description="关闭 RAG，用于观察检索增强对结果的影响",
            env={
                "ENABLE_RAG": "false",
                "ENABLE_MULTI_TURN": "false",
                "ENABLE_REFLEXION": "false",
            },
        ),
        EvalStrategy(
            name="no_reflexion",
            description="关闭 Reflexion，用于观察失败学习闭环的影响",
            env={
                "ENABLE_REFLEXION": "false",
                "ENABLE_RAG": "false",
                "ENABLE_MULTI_TURN": "false",
            },
        ),
        EvalStrategy(
            name="controlled_rag",
            description="受控 RAG 基线：注入固定参考知识，不触碰外部向量库",
            env={
                "EVAL_BASELINE": "controlled_rag",
                "ENABLE_RAG": "false",
                "ENABLE_MULTI_TURN": "false",
                "ENABLE_REFLEXION": "false",
            },
        ),
        EvalStrategy(
            name="controlled_reflexion",
            description="受控 Reflexion 基线：注入固定失败修复经验，不触碰外部记忆库",
            env={
                "EVAL_BASELINE": "controlled_reflexion",
                "ENABLE_RAG": "false",
                "ENABLE_MULTI_TURN": "false",
                "ENABLE_REFLEXION": "false",
            },
        ),
        EvalStrategy(
            name="single_agent_baseline",
            description="单 Agent 朴素生成基线，不走多智能体规划/RAG/反思",
            env={
                "EVAL_BASELINE": "single_agent",
                "ENABLE_RAG": "false",
                "ENABLE_MULTI_TURN": "false",
                "ENABLE_REFLEXION": "false",
            },
        ),
    ]


@contextmanager
def strategy_env(profile: EvalStrategy) -> Iterator[None]:
    old_values = {key: os.environ.get(key) for key in profile.env}
    try:
        for key, value in profile.env.items():
            os.environ[key] = value
        _clear_settings_cache()
        yield
    finally:
        for key, old in old_values.items():
            if old is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = old
        _clear_settings_cache()


async def run_strategy_suite(
    cases: list[EvalCase],
    *,
    profiles: list[EvalStrategy],
    runner_factory: RunnerFactory,
) -> list[EvalReport]:
    reports: list[EvalReport] = []
    for profile in profiles:
        with strategy_env(profile):
            runner = runner_factory(profile)
            reports.append(await runner.run(cases, strategy=profile.name))
    return reports


def _clear_settings_cache() -> None:
    try:
        from reflexlearn.common.config import get_settings

        get_settings.cache_clear()
    except Exception:
        return
