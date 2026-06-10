from fastapi.testclient import TestClient

import reflexlearn.common.db as db
import reflexlearn.executor.video_jobs as vj
from reflexlearn.api.app import create_app
from reflexlearn.common.auth import CurrentUser, issue_token
from reflexlearn.common.config import Settings


def _headers(user_id: str, tenant_id: str = "default") -> dict[str, str]:
    token = issue_token(
        CurrentUser(user_id=user_id, tenant_id=tenant_id, role="student"),
        Settings(),
    )
    return {"Authorization": f"Bearer {token}"}


def test_video_job_cross_user_returns_403(monkeypatch):
    async def _no_redis():
        raise RuntimeError("redis disabled in unit tests")

    monkeypatch.setattr(db, "get_redis", _no_redis)
    vj._store = None
    client = TestClient(create_app())

    created = client.post(
        "/api/video/jobs",
        json={"storyboard": "scene"},
        headers=_headers("u1"),
    )
    assert created.status_code == 200

    job_id = created.json()["job_id"]
    same_user = client.get(f"/api/video/jobs/{job_id}", headers=_headers("u1"))
    other_user = client.get(f"/api/video/jobs/{job_id}", headers=_headers("u2"))

    assert same_user.status_code == 200
    assert other_user.status_code == 403
    assert other_user.json()["detail"] == "permission_denied"
    vj._store = None
