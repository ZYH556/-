import pytest

from reflexlearn.learning.path_ops import (
    PathOwnershipError,
    insert_remedial_item,
    load_active_path_items,
    pin_resource_to_item,
    update_item_status,
)


class _FakeConn:
    def __init__(self, owner=("student-a", "demo")):
        self.owner = owner
        self.executes: list[tuple] = []
        self.path_id = 7
        self.resource_owned = True  # SELECT 1 FROM resources ... 命中与否
        self.items = [
            {"id": 1, "sequence": 1, "concept": "建立直觉", "objective": "o1", "rationale": "r1", "mastery_status": "done", "pinned_resource_id": ""},
            {"id": 2, "sequence": 2, "concept": "数学推导", "objective": "o2", "rationale": "r2", "mastery_status": "not_started", "pinned_resource_id": ""},
        ]
        self.resource_rows = [
            {"resource_id": "11", "concept": "数学推导", "type": "doc", "title": "推导讲解", "created_at": 2},
            {"resource_id": "12", "concept": "数学推导", "type": "quiz", "title": "推导练习", "created_at": 1},
            {"resource_id": "13", "concept": "数学推导", "type": "video", "title": "推导视频", "created_at": 0},
        ]

    async def fetchval(self, query, *args):
        if "FROM learning_paths lp" in query:
            return self.path_id
        if "SELECT 1 FROM resources" in query:
            return 1 if self.resource_owned else None
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
        if "FROM resources" in query:
            return self.resource_rows
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


async def test_load_active_path_items_attaches_resources_by_concept():
    items = await load_active_path_items(user_id="u", tenant_id="t", pg_pool=_FakePool())

    # 「建立直觉」无匹配资源；「数学推导」匹配 3 个但每节点最多 2 个
    assert items[0].resources == []
    assert [r.resource_id for r in items[1].resources] == ["11", "12"]
    assert items[1].resources[0].title == "推导讲解"


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


async def test_pin_resource_to_item_sets_resource_id():
    pool = _FakePool()

    result = await pin_resource_to_item(
        2, "11", user_id="student-a", tenant_id="demo", pg_pool=pool
    )

    assert result.ok is True
    assert result.goal_progress == round(2 / 3, 4)
    pinned = [args for op, args in pool.conn.executes if op == "update" and args == (2, "11")]
    assert pinned, "应把 path_item=2 的 resource_id 设为 11"


async def test_pin_resource_empty_unbinds():
    pool = _FakePool()

    result = await pin_resource_to_item(
        2, "", user_id="student-a", tenant_id="demo", pg_pool=pool
    )

    assert result.ok is True
    # 空 resource_id 解绑：写 NULL，且不做资源归属校验
    assert any(op == "update" and args == (2, None) for op, args in pool.conn.executes)


async def test_pin_resource_rejects_unowned_resource():
    conn = _FakeConn()
    conn.resource_owned = False
    pool = _FakePool(conn)

    with pytest.raises(PathOwnershipError):
        await pin_resource_to_item(2, "999", user_id="student-a", tenant_id="demo", pg_pool=pool)


async def test_pin_resource_forbidden_for_other_user():
    pool = _FakePool(_FakeConn(owner=("owner-b", "demo")))

    with pytest.raises(PathOwnershipError):
        await pin_resource_to_item(2, "11", user_id="student-a", tenant_id="demo", pg_pool=pool)


async def test_pin_resource_degrades_without_pg():
    result = await pin_resource_to_item(2, "11", user_id="u", tenant_id="t", pg_pool=None)

    assert result.ok is False
    assert "pg:unavailable" in result.degraded
