from __future__ import annotations

from datetime import datetime, timezone

from reflexlearn.common.db import get_qdrant
from reflexlearn.common.config import get_settings
from reflexlearn.memory.reflexion import recall_reflections, write_reflection
from reflexlearn.memory import trim, recursive_summary


class MemoryManager:
    """三级记忆统一门面（docs §6）。

    L1 上下文工程（trim / summary）做成**无状态转发**：layers / messages 由调用方
    （run_session）持有并随 session 存 Redis，本单例绝不持有可变状态 → 跨 session/用户
    零串台（计划「三条不可违背约束」#1）。
    L2 经验（recall / promote）转发 reflexion（无 Mem0）。全程降级，绝不报错中断。
    """

    def __init__(self, qdrant=None, pg_pool=None):
        self.qdrant = qdrant
        self.pg_pool = pg_pool

    def _resolve_qdrant(self):
        if self.qdrant is not None:
            return self.qdrant
        try:
            return get_qdrant()
        except Exception:
            return None

    async def recall(self, task_type: str, query: str, acl: dict) -> list[dict]:
        return await recall_reflections(
            qdrant=self._resolve_qdrant(),
            task_type=task_type,
            query=query,
            acl=acl,
        )

    # —— L1 上下文工程：无状态转发（不持有 layers/messages）——
    def trim_context(self, messages, summary_context: str = "", config=None) -> list[dict]:
        return trim.trim_context(messages, summary_context, config)

    def get_summary_context(self, layers) -> str:
        return recursive_summary.get_context(layers)

    async def update_summary(self, layers, new_messages, llm, config=None) -> list[str]:
        try:
            return await recursive_summary.add_and_compress(layers, new_messages, llm, config)
        except Exception:
            return list(layers or [])  # 摘要失败绝不破坏多轮，保留旧 layers

    # —— L1→L2 经验升迁：复用 reflexion（无 Mem0），全程降级 ——
    async def promote_session(self, *, reflection, user_id: str) -> bool:
        try:
            return await write_reflection(
                pg_pool=self.pg_pool,
                qdrant=self._resolve_qdrant(),
                reflection=reflection,
                user_id=user_id,
                created_at=datetime.now(timezone.utc).isoformat(),
            )
        except Exception:
            return False


async def recall_memory_node(state: dict) -> dict:
    if not get_settings().enable_reflexion:
        return {
            "reflections": [],
            "iteration": state.get("iteration", 0) + 1,
        }

    manager = state.get("_memory_manager") or MemoryManager()
    reflections = await manager.recall(
        task_type="",
        query=state.get("learning_goal", ""),
        acl=state.get("acl", {}),
    )
    return {
        "reflections": reflections,
        "iteration": state.get("iteration", 0) + 1,
    }
