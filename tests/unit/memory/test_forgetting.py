from __future__ import annotations

from pathlib import Path

import pytest

from reflexlearn.memory.forgetting import forget_stale, run_forgetting_job


class _Point:
    def __init__(self, point_id: str, payload: dict):
        self.id = point_id
        self.payload = payload


class _FakeQdrant:
    def __init__(self, points):
        self._points = points
        self.scrolls: list[dict] = []
        self.deletes: list[dict] = []

    async def scroll(self, **kwargs):
        self.scrolls.append(kwargs)
        return self._points, None

    async def delete(self, **kwargs):
        self.deletes.append(kwargs)


@pytest.mark.asyncio
async def test_forget_stale_deletes_only_expired_low_reuse_points():
    qdrant = _FakeQdrant(
        [
            _Point("old-low", {"created_at": "2026-01-01T00:00:00+00:00", "hit_count": 0}),
            _Point("old-used", {"created_at": "2026-01-01T00:00:00+00:00", "hit_count": 2}),
            _Point("recent", {"created_at": "2026-06-08T00:00:00+00:00", "hit_count": 0}),
            _Point("legacy", {"hit_count": 0}),
        ]
    )

    deleted = await forget_stale(
        qdrant=qdrant,
        now_iso="2026-06-09T00:00:00+00:00",
        ttl_days=90,
        min_hits=1,
    )

    assert deleted == 1
    assert qdrant.deletes == [
        {"collection_name": "experience_memory", "points_selector": ["old-low"]}
    ]


@pytest.mark.asyncio
async def test_run_forgetting_job_skips_when_disabled():
    class _Settings:
        enable_forgetting = False
        memory_ttl_days = 90
        memory_forget_min_hits = 1

    qdrant = _FakeQdrant(
        [_Point("old-low", {"created_at": "2026-01-01T00:00:00+00:00", "hit_count": 0})]
    )

    deleted = await run_forgetting_job(
        qdrant=qdrant,
        settings=_Settings(),
        now_iso="2026-06-09T00:00:00+00:00",
    )

    assert deleted == 0
    assert qdrant.deletes == []


def test_run_forget_script_contract():
    root = Path(__file__).resolve().parents[3]
    wrapper = (root / "scripts" / "run_forget.sh").read_text(encoding="utf-8")
    sh = (root / "scripts" / "jobs" / "run_forget.sh").read_text(encoding="utf-8")
    py = (root / "scripts" / "jobs" / "run_forget.py").read_text(encoding="utf-8")

    assert "exec \"$SCRIPT_DIR/jobs/run_forget.sh\" \"$@\"" in wrapper
    assert "source \"$SCRIPTS_ROOT/_lib.sh\"" in sh
    assert "tee -a \"$LOG_DIR/run_forget.log\"" in sh
    assert "run_forgetting_job" in py
