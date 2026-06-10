from __future__ import annotations

from fastapi import HTTPException, status

from reflexlearn.common.auth import CurrentUser


def can_access_object(
    *,
    user: CurrentUser,
    owner_user_id: str,
    tenant_id: str,
    visibility: str = "private",
) -> bool:
    """对象级 ACL：同租户内 public 可读，private 必须本人。"""
    if tenant_id != user.tenant_id:
        return False
    if visibility == "public":
        return True
    return owner_user_id == user.user_id


def assert_object_access(
    *,
    user: CurrentUser,
    owner_user_id: str,
    tenant_id: str,
    visibility: str = "private",
) -> None:
    if not can_access_object(
        user=user,
        owner_user_id=owner_user_id,
        tenant_id=tenant_id,
        visibility=visibility,
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="permission_denied",
        )
