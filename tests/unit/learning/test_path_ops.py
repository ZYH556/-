import pytest

from reflexlearn.learning.path_ops import (
    PathOwnershipError,
    insert_remedial_item,
    load_active_path_items,
    update_item_status,
)


class _FakeConn:
    def __init__(self, owner=("student-a", "demo")):
        self.owner = owner
        self.executes: list[tuple] = []
        self.path_id = 7
        self.items = [
            {"id": 1, "sequence": 1, "concept": "建立直觉", "objective": "o1", "rationale": "r1", "mastery_status": "done"},
            {"id": 2, "sequence": 2, "concept": "数学推导", "objective": "o2", "rationale": "r2", "mastery_status": "not_started"},
        ]

    async def fetchval(self, query, *args):
        if "FROM learning_paths lp" in query:
            return self.path_id
        if "SELECT sequence FROM path_items" in query:
            return 2
        if "RETURNING id" in query:
            self.executes.append(("insert", args))
            return 99
        return None

    async def fetchrow(self, query, *args):
        if "JOIN learning_goals lg" in query and "pi.id=" in query.replace("$1", "1"):
            if args and args[0] == 404:
                return None
            return {"path_id": self.path_id, "user_id": self.owner[0], "tenant_id": self.owner[1]}
        if "COUNT(*) FILTER" in query:
            return {"total": 3, "done": 2}
        return None

    async def fetch(self, query, *args):
        return self.items

    async def execute(self, query, *args):
        self.executes.append((query.strip().split()[0].lower(), args))
        return "UPDATE 1"


class _AcquireCtx:
    def __init__(self, conn):
        self._conn = conn

    async def __aenter__(self):
        return self._conn

    async def __aexit__(self, *exc):
        return False


class _FakePool:
    def __init__(self, conn=None):
        self.conn = conn or _FakeConn()

    def acquire(self):
        return _AcquireCtx(self.conn)


async def test_load_active_path_items_maps_rows():
    items = await load_active_path_items(user_id="u", tenant_id="t", pg_pool=_FakePool())

    assert [i.item_id for i in items] == [1, 2]
    assert items[0].mastery_status == "done"


async def test_load_active_path_items_empty_without_pg():
    assert await load_active_path_items(user_id="u", tenant_id="t", pg_pool=None) == []


async def test_update_item_status_recalcs_goal_progress():
    pool = _FakePool()

    result = await update_item_status(
        2, "done", user_id="student-a", tenant_id="demo", pg_pool=pool
    )

    assert result.ok is True
    assert result.goal_progress == round(2 / 3, 4)
    assert any(op == "update" for op, _ in pool.conn.executes)


async def test_update_item_status_forbidden_for_other_user():
    pool = _FakePool(_FakeConn(owner=("owner-b", "demo")))

    with pytest.raises(PathOwnershipError):
        await update_item_status(2, "done", user_id="student-a", tenant_id="demo", pg_pool=pool)


async def test_update_item_status_degrades_without_pg():
    result = await update_item_status(2, "done", user_id="u", tenant_id="t", pg_pool=None)

    assert result.ok is False
    assert "pg:unavailable" in result.degraded


async def test_insert_remedial_item_shifts_sequence_and_inserts():
    pool = _FakePool()

    result = await insert_remedial_item(
        2,
        concept="损失函数",
        objective="补救损失函数",
        rationale="来自错题",
        user_id="student-a",
        tenant_id="demo",
        pg_pool=pool,
    )

    assert result.ok is True
    assert result.item_id == 99
    shift = [args for op, args in pool.conn.executes if op == "update" and len(args) == 2]
    assert (7, 2) in shift  # path_id=7 的 sequence>2 后移
