from __future__ import annotations

import json
import time
import uuid
from typing import Any

from pydantic import BaseModel, Field


class MistakeCreate(BaseModel):
    question: str
    answer: str
    expected: str
    concept: str = ""
    source_resource_id: str = ""


class MistakeItem(BaseModel):
    mistake_id: str
    user_id: str
    tenant_id: str
    question: str
    answer: str
    expected: str
    concept: str = ""
    source_resource_id: str = ""
    status: str = "open"
    analysis: dict[str, Any] = Field(default_factory=dict)
    created_at: float = 0.0
    degraded: list[str] = Field(default_factory=list)


class MistakeReview(BaseModel):
    mistake_id: str
    cause: str
    weakness_tags: list[str] = Field(default_factory=list)
    review_plan: list[str] = Field(default_factory=list)
    refine_hint: str = ""
    recommended_resource_types: list[str] = Field(default_factory=list)


class MistakeList(BaseModel):
    items: list[MistakeItem] = Field(default_factory=list)
    degraded: list[str] = Field(default_factory=list)


class MistakeStore:
    def __init__(self) -> None:
        self._mem: dict[str, MistakeItem] = {}

    async def create(
        self,
        *,
        body: MistakeCreate,
        user_id: str,
        tenant_id: str,
        pg_pool=None,
    ) -> MistakeItem:
        item = MistakeItem(
            mistake_id=uuid.uuid4().hex,
            user_id=user_id,
            tenant_id=tenant_id,
            question=body.question,
            answer=body.answer,
            expected=body.expected,
            concept=body.concept,
            source_resource_id=body.source_resource_id,
            created_at=time.time(),
        )
        if pg_pool is None:
            item.degraded.append("pg:unavailable")
            self._mem[item.mistake_id] = item
            return item
        try:
            async with pg_pool.acquire() as conn:
                await conn.execute(
                    """
                    INSERT INTO mistakes (
                        mistake_id, user_id, tenant_id, question, answer,
                        expected, concept, source_resource_id, status, analysis
                    )
                    VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10::jsonb)
                    """,
                    item.mistake_id,
                    item.user_id,
                    item.tenant_id,
                    item.question,
                    item.answer,
                    item.expected,
                    item.concept,
                    item.source_resource_id,
                    item.status,
                    json.dumps(item.analysis, ensure_ascii=False),
                )
            return item
        except Exception:
            item.degraded.append("pg:unavailable")
            self._mem[item.mistake_id] = item
            return item

    async def get(self, mistake_id: str, *, pg_pool=None) -> MistakeItem | None:
        if pg_pool is not None:
            try:
                async with pg_pool.acquire() as conn:
                    row = await conn.fetchrow(
                        "SELECT * FROM mistakes WHERE mistake_id=$1",
                        mistake_id,
                    )
                if row:
                    return _row_to_item(row)
            except Exception:
                pass
        return self._mem.get(mistake_id)

    async def list_for_user(
        self,
        *,
        user_id: str,
        tenant_id: str,
        pg_pool=None,
        limit: int = 50,
    ) -> MistakeList:
        if pg_pool is not None:
            try:
                async with pg_pool.acquire() as conn:
                    rows = await conn.fetch(
                        """
                        SELECT * FROM mistakes
                        WHERE user_id=$1 AND tenant_id=$2
                        ORDER BY created_at DESC
                        LIMIT $3
                        """,
                        user_id,
                        tenant_id,
                        limit,
                    )
                return MistakeList(items=[_row_to_item(row) for row in rows])
            except Exception:
                pass
        items = [
            item
            for item in self._mem.values()
            if item.user_id == user_id and item.tenant_id == tenant_id
        ]
        items.sort(key=lambda item: item.created_at, reverse=True)
        return MistakeList(items=items[:limit], degraded=["pg:unavailable"])

    async def save_review(
        self,
        item: MistakeItem,
        review: MistakeReview,
        *,
        pg_pool=None,
    ) -> None:
        item.analysis = review.model_dump()
        item.status = "reviewed"
        self._mem[item.mistake_id] = item
        if pg_pool is None:
            return
        try:
            async with pg_pool.acquire() as conn:
                await conn.execute(
                    """
                    UPDATE mistakes
                    SET analysis=$2::jsonb, status='reviewed'
                    WHERE mistake_id=$1
                    """,
                    item.mistake_id,
                    json.dumps(item.analysis, ensure_ascii=False),
                )
        except Exception:
            return

    async def save_analysis(
        self,
        item: MistakeItem,
        *,
        patch: dict[str, Any],
        status: str | None = None,
        pg_pool=None,
    ) -> MistakeItem:
        item.analysis = {**(item.analysis or {}), **patch}
        if status:
            item.status = status
        self._mem[item.mistake_id] = item
        if pg_pool is None:
            return item
        try:
            async with pg_pool.acquire() as conn:
                await conn.execute(
                    """
                    UPDATE mistakes
                    SET analysis=$2::jsonb, status=$3
                    WHERE mistake_id=$1
                    """,
                    item.mistake_id,
                    json.dumps(item.analysis, ensure_ascii=False),
                    item.status,
                )
        except Exception:
            return item
        return item


def build_mistake_review(item: MistakeItem) -> MistakeReview:
    concept = item.concept.strip() or "待归类概念"
    answer = item.answer.strip()
    expected = item.expected.strip()
    cause = "答案与参考要点不一致"
    if not answer:
        cause = "答案为空，缺少可评估的解题过程"
    elif expected and answer in expected:
        cause = "答案只覆盖了部分参考要点，需要补全推理链路"
    return MistakeReview(
        mistake_id=item.mistake_id,
        cause=f"{cause}：重点复盘「{concept}」。",
        weakness_tags=[concept, "概念辨析", "迁移应用"],
        review_plan=[
            f"重读「{concept}」核心定义，写出 3 个关键词。",
            "用自己的话复述正确解法，并标注与原答案差异。",
            "生成 2 道同概念变式题，隔天复测。",
        ],
        refine_hint=f"围绕错题「{concept}」生成针对性讲解，先解释错误原因，再给出反例和练习。",
        recommended_resource_types=["doc", "quiz"],
    )


def _row_to_item(row) -> MistakeItem:
    data = dict(row)
    created = data.get("created_at")
    created_at = created.timestamp() if hasattr(created, "timestamp") else time.time()
    analysis = data.get("analysis") or {}
    if isinstance(analysis, str):
        try:
            analysis = json.loads(analysis)
        except json.JSONDecodeError:
            analysis = {}
    return MistakeItem(
        mistake_id=data["mistake_id"],
        user_id=data["user_id"],
        tenant_id=data["tenant_id"],
        question=data["question"],
        answer=data["answer"],
        expected=data["expected"],
        concept=data.get("concept") or "",
        source_resource_id=data.get("source_resource_id") or "",
        status=data.get("status") or "open",
        analysis=analysis,
        created_at=created_at,
    )
