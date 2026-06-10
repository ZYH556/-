"""登录限流：Redis 优先（跨进程），不可用退进程内存滑动窗口。

绝不在限流逻辑内自取 redis（conftest 不拦 get_redis）；redis 由调用方注入，
不可用/异常一律降级内存，绝不阻断主链路。
"""

from __future__ import annotations

import time
from typing import Any

from reflexlearn.common.config import Settings, get_settings


class RateLimiter:
    def __init__(self, *, settings: Settings | None = None) -> None:
        self._settings = settings or get_settings()
        self._mem: dict[str, list[float]] = {}

    async def hit(self, key: str, *, redis: Any = None) -> bool:
        """记录一次尝试。返回 True=允许，False=超出窗口限额。"""
        cfg = self._settings
        limit = cfg.login_rate_limit
        window = cfg.login_rate_window_s
        if redis is not None:
            try:
                full = f"ratelimit:login:{key}"
                count = await redis.incr(full)
                if count == 1:
                    await redis.expire(full, window)
                return int(count) <= limit
            except Exception:
                pass  # Redis 异常 → 降级内存
        now = time.time()
        hits = [t for t in self._mem.get(key, []) if now - t < window]
        hits.append(now)
        self._mem[key] = hits
        return len(hits) <= limit


_login_limiter: RateLimiter | None = None


def get_login_limiter(settings: Settings | None = None) -> RateLimiter:
    global _login_limiter
    if _login_limiter is None:
        _login_limiter = RateLimiter(settings=settings)
    return _login_limiter


def reset_login_limiter_for_tests() -> None:
    global _login_limiter
    _login_limiter = None
