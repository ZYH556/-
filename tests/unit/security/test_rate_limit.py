"""W3-B: 登录限流（Redis 优先，进程内存降级）。"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from reflexlearn.api.app import create_app
from reflexlearn.common.config import Settings
from reflexlearn.security.rate_limit import (
    RateLimiter,
    get_login_limiter,
    reset_login_limiter_for_tests,
)


@pytest.fixture(autouse=True)
def _reset(monkeypatch):
    import reflexlearn.common.db as db

    async def _none():
        return None

    monkeypatch.setattr(db, "get_pg_pool", _none)
    monkeypatch.setattr(db, "get_redis", _none)
    reset_login_limiter_for_tests()


async def test_memory_window_blocks_after_limit():
    limiter = RateLimiter(settings=Settings(login_rate_limit=3, login_rate_window_s=300))
    key = "default/1.2.3.4/admin"
    assert await limiter.hit(key) is True
    assert await limiter.hit(key) is True
    assert await limiter.hit(key) is True
    assert await limiter.hit(key) is False


async def test_keys_independent():
    limiter = RateLimiter(settings=Settings(login_rate_limit=1))
    assert await limiter.hit("k1") is True
    assert await limiter.hit("k1") is False
    assert await limiter.hit("k2") is True


async def test_redis_path_uses_incr():
    class FakeRedis:
        def __init__(self):
            self.store: dict[str, int] = {}

        async def incr(self, k):
            self.store[k] = self.store.get(k, 0) + 1
            return self.store[k]

        async def expire(self, k, s):
            return True

    r = FakeRedis()
    limiter = RateLimiter(settings=Settings(login_rate_limit=2))
    assert await limiter.hit("k", redis=r) is True
    assert await limiter.hit("k", redis=r) is True
    assert await limiter.hit("k", redis=r) is False


async def test_redis_failure_falls_back_to_memory():
    class BrokenRedis:
        async def incr(self, k):
            raise RuntimeError("redis down")

        async def expire(self, k, s):
            raise RuntimeError("redis down")

    limiter = RateLimiter(settings=Settings(login_rate_limit=1))
    assert await limiter.hit("k", redis=BrokenRedis()) is True
    assert await limiter.hit("k", redis=BrokenRedis()) is False


def test_reset_login_limiter_singleton():
    reset_login_limiter_for_tests()
    a = get_login_limiter()
    reset_login_limiter_for_tests()
    b = get_login_limiter()
    assert a is not b


def test_login_rate_limit_via_api():
    client = TestClient(create_app())
    # 默认 login_rate_limit=5：连续 5 次失败尝试后第 6 次 429
    for _ in range(5):
        client.post("/api/auth/login", json={"username": "admin", "password": "wrong"})
    resp = client.post("/api/auth/login", json={"username": "admin", "password": "wrong"})
    assert resp.status_code == 429
    assert resp.json()["detail"] == "too_many_attempts"
