"""L1 短期记忆 · 多轮会话 Redis 持久化（薄封装，全程降级）。

设计要点（docs/03 §1/§7 的落地，含刻意差异）：
- 所有 Redis I/O 收敛到本模块，便于单测 monkeypatch —— tests/conftest.py 的 hermetic
  守卫不拦 get_redis，集成测试只需 patch 本模块的 load/persist 即可 hermetic。
- 单 key 存 JSON：{messages, summary_layers}，避免多 key 一致性问题。
- API 层传入的原始 session_id 必须先经 scoped_session_id 绑定 user/tenant，再用于 Redis。
- 全程 try/except：Redis 不可用 / key 不存在 / JSON 损坏 → load 返回空、persist 返回
  False，多轮静默退化单轮，绝不报错中断（项目铁律）。
- summary_layers 随 session 持久化（per-session 状态归属），绝不放 MemoryManager 单例
  实例属性 —— 否则跨 session/用户串台（见计划「三条不可违背约束」）。
"""
from __future__ import annotations

import hashlib
import json
import logging

from reflexlearn.common.config import get_settings
from reflexlearn.common.db import get_redis

logger = logging.getLogger(__name__)

SESSION_PREFIX = "session:"
# 防 messages 无限膨胀，只留最近 N 条原文（更早的已压进 summary_layers）
MAX_PERSISTED_MESSAGES = 40


def _empty() -> dict:
    return {"messages": [], "summary_layers": []}


def scoped_session_id(session_id: str, *, user_id: str, tenant_id: str) -> str:
    """把客户端 sid 派生成绑定用户和租户的内部 sid，避免跨账号复用会话历史。"""
    if not session_id:
        return ""
    raw = "\0".join([tenant_id or "default", user_id or "anonymous", session_id])
    digest = hashlib.sha256(raw.encode("utf-8")).hexdigest()
    return f"v2:{digest}"


async def load(session_id: str) -> dict:
    """读取会话短期记忆。返回 {"messages": list[dict], "summary_layers": list[str]}。
    session_id 为空 / Redis 不可用 / key 不存在 / JSON 损坏 → 返回空（降级单轮）。"""
    if not session_id:
        return _empty()
    try:
        redis = await get_redis()
        raw = await redis.get(SESSION_PREFIX + session_id)
        if not raw:
            return _empty()
        data = json.loads(raw)
        return {
            "messages": data.get("messages", []) or [],
            "summary_layers": data.get("summary_layers", []) or [],
        }
    except Exception as e:  # 连接失败 / 解析失败 → 当作新 session
        logger.info("session_store.load degraded (%s): %s", session_id, e)
        return _empty()


async def persist(
    session_id: str, *, messages: list[dict], summary_layers: list[str]
) -> bool:
    """整体覆盖写会话短期记忆并刷新 TTL。失败静默返回 False（不影响已 yield 的响应）。"""
    if not session_id:
        return False
    try:
        ttl = get_settings().session_ttl
    except Exception:
        ttl = 7200
    try:
        redis = await get_redis()
        payload = json.dumps(
            {
                "messages": (messages or [])[-MAX_PERSISTED_MESSAGES:],
                "summary_layers": summary_layers or [],
            },
            ensure_ascii=False,
        )
        await redis.set(SESSION_PREFIX + session_id, payload, ex=ttl)
        return True
    except Exception as e:
        logger.info("session_store.persist degraded (%s): %s", session_id, e)
        return False
