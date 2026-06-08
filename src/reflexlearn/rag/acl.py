"""ACL 物理过滤：检索层做权限隔离，不依赖提示词（呼应 docs/03 §3.3）。

两个出口：
- build_qdrant_filter：semantic 路下推到 qdrant query_filter（提取自 retrieve.py 原 _build_acl_filter）。
- acl_check：keyword / graph 路在内存对 payload 做等价过滤（这两路无法像 qdrant 那样下推）。

语义统一：可见 public、或属于该 user（private 必须本人）、或同 tenant。种子知识均 public，
demo 下默认可见；接入私有课程资料时这层即生效，无需改调用方。
"""
from __future__ import annotations


def build_qdrant_filter(acl: dict):
    """按 ACL 构造 qdrant 过滤（should=OR）。qdrant_client 缺失时返回 None（不过滤，由降级兜底）。"""
    try:
        from qdrant_client.models import FieldCondition, Filter, MatchValue
    except Exception:
        return None

    should = [FieldCondition(key="visibility", match=MatchValue(value="public"))]
    user_id = acl.get("user_id")
    if user_id:
        should.append(FieldCondition(key="user_id", match=MatchValue(value=user_id)))
    tenant_id = acl.get("tenant_id")
    if tenant_id:
        should.append(FieldCondition(key="tenant_id", match=MatchValue(value=tenant_id)))
    return Filter(should=should)


def acl_check(meta: dict, acl: dict) -> bool:
    """内存 ACL 过滤（与 build_qdrant_filter 同语义）。meta 为 chunk 的 payload（含 visibility 等）。"""
    visibility = meta.get("visibility", "public")
    if visibility == "public":
        return True
    if visibility == "private":
        # 私有：必须本人
        user_id = acl.get("user_id")
        return bool(user_id) and meta.get("user_id") == user_id
    # 其它（tenant/course 级）：同租户可见
    tenant_id = acl.get("tenant_id")
    return bool(tenant_id) and meta.get("tenant_id") == tenant_id
