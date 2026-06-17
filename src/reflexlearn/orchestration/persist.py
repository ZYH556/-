"""对话会话结束后的后台持久化任务。"""

from __future__ import annotations

import asyncio
import logging

from reflexlearn.memory.graph_autogrow import autogrow_session_graph
from reflexlearn.memory.manager import MemoryManager
from reflexlearn.orchestration.schemas import Reflection

logger = logging.getLogger(__name__)

# PERF-C：持有强引用防 task 被 GC；drain 供单测与优雅关停 await 收尾。
_PERSIST_TASKS: set = set()


def spawn_persist(coro) -> None:
    try:
        task = asyncio.ensure_future(coro)
    except RuntimeError:
        coro.close()
        return
    _PERSIST_TASKS.add(task)
    task.add_done_callback(_PERSIST_TASKS.discard)


async def drain_persist_tasks() -> None:
    """等待所有后台 PERSIST 收尾（单测断言持久化副作用前调用；生产可用于优雅关停）。"""
    if _PERSIST_TASKS:
        await asyncio.gather(*list(_PERSIST_TASKS), return_exceptions=True)


async def persist_session(
    *,
    scoped_session_id: str,
    message: str,
    user_id: str,
    tenant_id: str,
    session_id: str,
    prior_messages: list[dict],
    summary_layers: list[str],
    assistant_summary: str | None,
    final_profile: dict,
    settings,
    llm,
) -> None:
    """写回 Redis 短期记忆 + 溢出递归摘要 + 画像保存 + promote/autogrow。"""
    try:
        from reflexlearn.memory import session_store
        from reflexlearn.memory.recursive_summary import add_and_compress
        from reflexlearn.memory.trim import TrimConfig

        new_user = {"role": "user", "content": message}
        new_assistant = {
            "role": "assistant",
            "content": assistant_summary or "[本轮已完成]",
        }
        full_messages = prior_messages + [new_user, new_assistant]

        recent_count = TrimConfig.from_settings().recent_turns * 2
        new_layers = summary_layers
        if len(full_messages) > recent_count:
            overflow = full_messages[:-recent_count]
            new_layers = await add_and_compress(summary_layers, overflow, llm)

        await session_store.persist(
            scoped_session_id,
            messages=full_messages,
            summary_layers=new_layers,
        )
        if final_profile:
            await session_store.save_profile(user_id, tenant_id=tenant_id, profile=final_profile)
        if getattr(settings, "enable_promote", False):
            reflection = Reflection(
                task_type="session",
                failure_type="none" if assistant_summary else "incomplete",
                cause=f"学习目标：{message}；结果：{assistant_summary or '[未形成资源包]'}",
                fix_strategy="复用本轮学习画像、资源规划和质量校验经验。",
                success=bool(assistant_summary),
            )
            await MemoryManager().promote_session(reflection=reflection, user_id=user_id)
        if getattr(settings, "enable_graph_autogrow", False):
            try:
                from reflexlearn.common.db import get_neo4j

                neo4j = get_neo4j()
            except Exception:
                neo4j = None
            await autogrow_session_graph(
                text=f"{message}\n{assistant_summary or '[本轮已完成]'}",
                tenant_id=tenant_id,
                visibility="public",
                doc_id=f"session:{tenant_id}:{user_id}:{session_id}",
                neo4j=neo4j,
                settings=settings,
                gateway=llm,
            )
    except Exception:
        logger.info("persist session degraded", exc_info=True)
