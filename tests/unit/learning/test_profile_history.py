import json


from reflexlearn.learning.profile_history import (
    ProfileHistorySnapshot,
    build_profile_trend,
    save_profile_snapshot,
)


class _FakeConn:
    def __init__(self, latest_dimensions=None):
        self.latest_dimensions = latest_dimensions
        self.inserts: list[tuple] = []

    async def fetchrow(self, *args, **kwargs):
        if self.latest_dimensions is None:
            return None
        return {"dimensions": self.latest_dimensions}

    async def fetchval(self, *args, **kwargs):
        return 2

    async def execute(self, *args, **kwargs):
        self.inserts.append(args)
        return "INSERT 0 1"


class _AcquireCtx:
    def __init__(self, conn):
        self._conn = conn

    async def __aenter__(self):
        return self._conn

    async def __aexit__(self, *exc):
        return False


class _FakePgPool:
    def __init__(self, latest_dimensions=None):
        self.conn = _FakeConn(latest_dimensions)

    def acquire(self):
        return _AcquireCtx(self.conn)


def test_profile_trend_calculates_progress_and_weak_point_changes():
    trend = build_profile_trend(
        [
            ProfileHistorySnapshot(
                version=1,
                created_at=1000.0,
                goal="掌握线性回归",
                progress=0.35,
                weak_points=["损失函数", "梯度方向"],
                knowledge_base={"损失函数": 0.3},
            ),
            ProfileHistorySnapshot(
                version=2,
                created_at=2000.0,
                goal="掌握线性回归",
                progress=0.62,
                weak_points=["梯度方向", "学习率"],
                knowledge_base={"损失函数": 0.7, "学习率": 0.4},
            ),
        ]
    )

    assert trend.start_progress == 0.35
    assert trend.latest_progress == 0.62
    assert trend.progress_delta == 0.27
    assert trend.resolved_weak_points == ["损失函数"]
    assert trend.new_weak_points == ["学习率"]
    assert trend.mastery_delta["损失函数"] == 0.4


def test_profile_trend_empty_history_is_explicit():
    trend = build_profile_trend([])

    assert trend.start_progress == 0.0
    assert trend.latest_progress == 0.0
    assert trend.progress_delta == 0.0
    assert trend.items == []
    assert "profile_history:empty" in trend.degraded



async def test_save_profile_snapshot_skips_when_content_unchanged():
    profile = {"goal": "线性回归入门", "progress": 0.0, "weak_points": ["数学推导"]}
    pool = _FakePgPool(latest_dimensions=json.dumps(profile, ensure_ascii=False))

    await save_profile_snapshot("student-a", profile, pool)

    assert pool.conn.inserts == []



async def test_save_profile_snapshot_writes_when_content_changed():
    old = {"goal": "线性回归入门", "progress": 0.0, "weak_points": ["数学推导"]}
    new = {"goal": "线性回归入门", "progress": 0.4, "weak_points": ["模型评估"]}
    pool = _FakePgPool(latest_dimensions=json.dumps(old, ensure_ascii=False))

    await save_profile_snapshot("student-a", new, pool)

    assert len(pool.conn.inserts) == 1



async def test_save_profile_snapshot_writes_first_snapshot():
    pool = _FakePgPool(latest_dimensions=None)

    await save_profile_snapshot("student-a", {"goal": "g", "progress": 0.1}, pool)

    assert len(pool.conn.inserts) == 1
