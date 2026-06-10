"""M4-E 多模态视频作业单测：注入假 Redis / 假 httpx client，绝不真连 Redis、绝不真外呼 SeeDance。

autouse fixture 重置作业单例 + 禁真实 get_redis（默认 store 降级内存）；JobStore Redis 路径用注入假 redis 测。
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

import reflexlearn.common.db as db
import reflexlearn.executor.video_jobs as vj
from reflexlearn.api.app import create_app
from reflexlearn.executor.video_jobs import (
    JobStore,
    SeeDanceUnavailable,
    VideoJob,
    call_seedance,
    get_video_job,
    process_job,
    submit_video_job,
)


class _FakeRedis:
    def __init__(self):
        self.store: dict = {}

    async def set(self, k, v, ex=None):
        self.store[k] = v

    async def get(self, k):
        return self.store.get(k)


class _BoomRedis:
    async def set(self, *a, **k):
        raise RuntimeError("redis down")

    async def get(self, *a, **k):
        raise RuntimeError("redis down")


class _SettingsNoSeedance:
    enable_seedance = False
    seedance_api_key = ""
    seedance_model = "m"
    seedance_endpoint = "http://x"
    video_job_ttl = 100


class _SettingsSeedanceOn:
    enable_seedance = True
    seedance_api_key = "key"
    seedance_model = "m"
    seedance_endpoint = "http://seedance.test/gen"
    video_job_ttl = 100


class _FakeHttpxResp:
    def __init__(self, data):
        self._data = data

    def raise_for_status(self):
        pass

    def json(self):
        return self._data


class _FakeHttpxClient:
    def __init__(self, data):
        self._data = data
        self.posted = []

    async def post(self, url, json=None, headers=None):
        self.posted.append((url, json, headers))
        return _FakeHttpxResp(self._data)


def auth_headers(client: TestClient) -> dict[str, str]:
    resp = client.post(
        "/api/auth/login",
        json={"username": "admin", "password": "reflexlearn-admin"},
    )
    assert resp.status_code == 200
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


@pytest.fixture(autouse=True)
def _reset_and_no_redis(monkeypatch):
    """重置作业单例 + 禁真实 get_redis（默认 store 降级内存，绝不真连 127.0.0.1:16379）。"""
    vj._store = None

    async def _boom_redis():
        raise RuntimeError("redis disabled in unit tests")

    monkeypatch.setattr(db, "get_redis", _boom_redis)
    yield
    vj._store = None


# ---------- JobStore ----------
@pytest.mark.asyncio
async def test_jobstore_redis_roundtrip():
    store = JobStore(redis=_FakeRedis())
    job = VideoJob(job_id="j1", storyboard="sb")
    await store.save(job)
    got = await store.get("j1")
    assert got is not None and got.job_id == "j1" and got.storyboard == "sb"


@pytest.mark.asyncio
async def test_jobstore_redis_down_falls_back_memory():
    store = JobStore(redis=_BoomRedis())
    job = VideoJob(job_id="j2", storyboard="sb2")
    await store.save(job)  # redis 挂 → 内存
    got = await store.get("j2")
    assert got is not None and got.job_id == "j2"


# ---------- call_seedance ----------
@pytest.mark.asyncio
async def test_call_seedance_no_key_raises():
    with pytest.raises(SeeDanceUnavailable):
        await call_seedance("prompt", _SettingsNoSeedance())


@pytest.mark.asyncio
async def test_call_seedance_with_client_returns_url():
    client = _FakeHttpxClient({"video_url": "http://v/1.mp4"})
    url = await call_seedance("分镜脚本", _SettingsSeedanceOn(), client=client)
    assert url == "http://v/1.mp4"
    assert client.posted and client.posted[0][0] == "http://seedance.test/gen"


@pytest.mark.asyncio
async def test_call_seedance_no_url_in_response_raises():
    with pytest.raises(SeeDanceUnavailable):
        await call_seedance("p", _SettingsSeedanceOn(), client=_FakeHttpxClient({"foo": "bar"}))


# ---------- process_job ----------
@pytest.mark.asyncio
async def test_process_job_degrades_without_seedance(monkeypatch):
    monkeypatch.setattr(vj, "get_settings", lambda: _SettingsNoSeedance())
    store = JobStore(redis=_FakeRedis())
    await store.save(VideoJob(job_id="j3", storyboard="分镜：第一幕..."))
    job = await process_job("j3", "分镜：第一幕...", store=store)
    assert job.status == "degraded"
    assert job.video_url is None and job.storyboard == "分镜：第一幕..."  # storyboard 占位保留


@pytest.mark.asyncio
async def test_process_job_done_with_seedance(monkeypatch):
    monkeypatch.setattr(vj, "get_settings", lambda: _SettingsSeedanceOn())

    async def fake_call(prompt, settings, *, client=None):
        return "http://v/done.mp4"

    monkeypatch.setattr(vj, "call_seedance", fake_call)
    store = JobStore(redis=_FakeRedis())
    await store.save(VideoJob(job_id="j4", storyboard="sb"))
    job = await process_job("j4", "sb", store=store)
    assert job.status == "done" and job.video_url == "http://v/done.mp4"


@pytest.mark.asyncio
async def test_process_job_missing_returns_none():
    store = JobStore(redis=_FakeRedis())
    assert await process_job("nope", "p", store=store) is None


# ---------- submit / get ----------
@pytest.mark.asyncio
async def test_submit_creates_pending_job():
    store = JobStore(redis=_FakeRedis())
    job = await submit_video_job(storyboard="sb", store=store, autostart=False)
    assert job.status == "pending" and job.job_id
    assert (await get_video_job(job.job_id, store=store)).job_id == job.job_id


# ---------- route ----------
def test_video_route_submit_and_query():
    client = TestClient(create_app())
    headers = auth_headers(client)
    resp = client.post("/api/video/jobs", json={"storyboard": "分镜脚本内容"}, headers=headers)
    assert resp.status_code == 200
    jid = resp.json()["job_id"]
    assert jid and resp.json()["status"] in ("pending", "running", "degraded", "done", "failed")
    r2 = client.get(f"/api/video/jobs/{jid}", headers=headers)
    assert r2.status_code == 200 and r2.json()["job_id"] == jid


def test_video_route_404():
    client = TestClient(create_app())
    resp = client.get("/api/video/jobs/nonexistent-id", headers=auth_headers(client))
    assert resp.status_code == 404
