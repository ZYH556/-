from __future__ import annotations

import asyncio
from collections.abc import Mapping
from typing import Any

from reflexlearn.llm_gateway.gateway import LLMGateway
from reflexlearn.skills.base import SkillContext
from reflexlearn.skills.doc_gen import DocGenSkill
from reflexlearn.skills.quiz_gen import QuizGenSkill
from reflexlearn.skills.retrieve import RetrieveSkill

SAFE_TOOL_NAMES = ["retrieve", "doc_gen", "quiz_gen"]


def supported_tool_names() -> list[str]:
    return list(SAFE_TOOL_NAMES)


def build_skills(llm: LLMGateway | None = None) -> dict[str, Any]:
    llm = llm or LLMGateway()
    return {
        "retrieve": RetrieveSkill(),
        "doc_gen": DocGenSkill(llm),
        "quiz_gen": QuizGenSkill(llm),
    }


def _public_acl(user_id: str, tenant_id: str) -> dict:
    return {"user_id": user_id, "tenant_id": tenant_id, "visibility": ["public"]}


async def call_skill(
    skill,
    inp: Mapping[str, Any],
    *,
    user_id: str = "mcp-user",
    tenant_id: str = "default",
    task_id: str = "mcp",
) -> dict:
    ctx = SkillContext(
        user_id=user_id,
        acl=_public_acl(user_id, tenant_id),
        task_id=task_id,
    )
    try:
        result = await skill.run(dict(inp), ctx)
        data = result.model_dump()
        data["data"] = data.get("data") or {}
        return data
    except Exception as exc:
        return {
            "ok": False,
            "data": {},
            "error_type": type(exc).__name__,
            "duration_ms": 0,
            "cached": False,
        }


def build_mcp_server():
    try:
        from mcp.server.fastmcp import FastMCP
    except Exception as exc:
        raise RuntimeError("mcp_sdk_unavailable: install with uv pip install -e .[mcp]") from exc

    app = FastMCP("reflexlearn")
    skills = build_skills()

    @app.tool()
    async def retrieve(query: str, user_id: str = "mcp-user", tenant_id: str = "default") -> dict:
        return await call_skill(
            skills["retrieve"],
            {"query": query, "query_type": "default"},
            user_id=user_id,
            tenant_id=tenant_id,
            task_id="mcp-retrieve",
        )

    @app.tool()
    async def doc_gen(
        concept: str,
        difficulty: float = 0.5,
        user_id: str = "mcp-user",
        tenant_id: str = "default",
    ) -> dict:
        return await call_skill(
            skills["doc_gen"],
            {"spec": {"concept_ids": [concept], "difficulty": difficulty}, "context": ""},
            user_id=user_id,
            tenant_id=tenant_id,
            task_id="mcp-doc-gen",
        )

    @app.tool()
    async def quiz_gen(
        concept: str,
        difficulty: float = 0.5,
        user_id: str = "mcp-user",
        tenant_id: str = "default",
    ) -> dict:
        return await call_skill(
            skills["quiz_gen"],
            {"spec": {"concept_ids": [concept], "difficulty": difficulty}, "context": ""},
            user_id=user_id,
            tenant_id=tenant_id,
            task_id="mcp-quiz-gen",
        )

    return app


def main() -> None:
    server = build_mcp_server()
    result = server.run()
    if asyncio.iscoroutine(result):
        asyncio.run(result)


if __name__ == "__main__":
    main()
