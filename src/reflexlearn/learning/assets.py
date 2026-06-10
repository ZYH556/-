from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


Visibility = Literal["public", "private", "course"]


class LearningSpace(BaseModel):
    space_id: str
    user_id: str
    tenant_id: str
    title: str
    status: str = "active"


class LearningResource(BaseModel):
    resource_id: str
    user_id: str
    tenant_id: str
    type: str
    title: str = ""
    content_preview: str = ""
    visibility: Visibility = "private"


class KnowledgeDocument(BaseModel):
    doc_id: str
    user_id: str
    tenant_id: str
    title: str
    visibility: Visibility = "private"
    course_id: str = ""
    format: str = ""


class AssetList(BaseModel):
    items: list = Field(default_factory=list)
    degraded: list[str] = Field(default_factory=list)


class LearningAssetStore:
    def __init__(self) -> None:
        self._spaces: dict[str, LearningSpace] = {}
        self._resources: dict[str, LearningResource] = {}
        self._documents: dict[str, KnowledgeDocument] = {}

    def seed_memory(
        self,
        *,
        spaces: list[dict] | None = None,
        resources: list[dict] | None = None,
        documents: list[dict] | None = None,
    ) -> None:
        for item in spaces or []:
            model = LearningSpace.model_validate(item)
            self._spaces[model.space_id] = model
        for item in resources or []:
            model = LearningResource.model_validate(item)
            self._resources[model.resource_id] = model
        for item in documents or []:
            model = KnowledgeDocument.model_validate(item)
            self._documents[model.doc_id] = model

    async def list_spaces(self, *, user_id: str, tenant_id: str, pg_pool=None) -> AssetList:
        if pg_pool is not None:
            try:
                async with pg_pool.acquire() as conn:
                    rows = await conn.fetch(
                        """
                        SELECT id::text AS space_id, user_id, tenant_id, goal_text AS title, status
                        FROM learning_goals
                        WHERE user_id=$1 AND tenant_id=$2
                        ORDER BY created_at DESC
                        LIMIT 100
                        """,
                        user_id,
                        tenant_id,
                    )
                return AssetList(items=[LearningSpace.model_validate(dict(row)) for row in rows])
            except Exception:
                pass
        items = [
            item for item in self._spaces.values()
            if item.user_id == user_id and item.tenant_id == tenant_id
        ]
        return AssetList(items=items, degraded=["pg:unavailable"])

    async def get_space(self, space_id: str, *, pg_pool=None) -> LearningSpace | None:
        if pg_pool is not None:
            try:
                async with pg_pool.acquire() as conn:
                    row = await conn.fetchrow(
                        """
                        SELECT id::text AS space_id, user_id, tenant_id, goal_text AS title, status
                        FROM learning_goals
                        WHERE id::text=$1
                        """,
                        space_id,
                    )
                if row:
                    return LearningSpace.model_validate(dict(row))
            except Exception:
                pass
        return self._spaces.get(space_id)

    async def list_resources(self, *, user_id: str, tenant_id: str, pg_pool=None) -> AssetList:
        if pg_pool is not None:
            try:
                async with pg_pool.acquire() as conn:
                    rows = await conn.fetch(
                        """
                        SELECT id::text AS resource_id, user_id, tenant_id, type,
                               COALESCE(meta->>'title', type) AS title,
                               LEFT(COALESCE(content, ''), 180) AS content_preview,
                               visibility
                        FROM resources
                        WHERE user_id=$1 AND tenant_id=$2
                        ORDER BY created_at DESC
                        LIMIT 100
                        """,
                        user_id,
                        tenant_id,
                    )
                return AssetList(items=[LearningResource.model_validate(dict(row)) for row in rows])
            except Exception:
                pass
        items = [
            item for item in self._resources.values()
            if item.user_id == user_id and item.tenant_id == tenant_id
        ]
        return AssetList(items=items, degraded=["pg:unavailable"])

    async def get_resource(self, resource_id: str, *, pg_pool=None) -> LearningResource | None:
        if pg_pool is not None:
            try:
                async with pg_pool.acquire() as conn:
                    row = await conn.fetchrow(
                        """
                        SELECT id::text AS resource_id, user_id, tenant_id, type,
                               COALESCE(meta->>'title', type) AS title,
                               LEFT(COALESCE(content, ''), 180) AS content_preview,
                               visibility
                        FROM resources
                        WHERE id::text=$1
                        """,
                        resource_id,
                    )
                if row:
                    return LearningResource.model_validate(dict(row))
            except Exception:
                pass
        return self._resources.get(resource_id)

    async def list_documents(self, *, user_id: str, tenant_id: str, pg_pool=None) -> AssetList:
        if pg_pool is not None:
            try:
                async with pg_pool.acquire() as conn:
                    rows = await conn.fetch(
                        """
                        SELECT doc_id, user_id, tenant_id, title, visibility, course_id, format
                        FROM documents
                        WHERE tenant_id=$1 AND (user_id=$2 OR visibility='public')
                        ORDER BY created_at DESC
                        LIMIT 100
                        """,
                        tenant_id,
                        user_id,
                    )
                return AssetList(items=[KnowledgeDocument.model_validate(dict(row)) for row in rows])
            except Exception:
                pass
        items = [
            item for item in self._documents.values()
            if item.tenant_id == tenant_id and (item.user_id == user_id or item.visibility == "public")
        ]
        return AssetList(items=items, degraded=["pg:unavailable"])

    async def get_document(self, doc_id: str, *, pg_pool=None) -> KnowledgeDocument | None:
        if pg_pool is not None:
            try:
                async with pg_pool.acquire() as conn:
                    row = await conn.fetchrow(
                        """
                        SELECT doc_id, user_id, tenant_id, title, visibility, course_id, format
                        FROM documents
                        WHERE doc_id=$1
                        """,
                        doc_id,
                    )
                if row:
                    return KnowledgeDocument.model_validate(dict(row))
            except Exception:
                pass
        return self._documents.get(doc_id)
