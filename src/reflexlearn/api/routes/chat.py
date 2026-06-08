from __future__ import annotations

import json
import uuid

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from reflexlearn.api.deps import get_current_user
from reflexlearn.common.auth import CurrentUser
from reflexlearn.orchestration.graph import run_session

router = APIRouter()


def sse_event(event: str, payload: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(payload, ensure_ascii=False)}\n\n"


class ChatRequest(BaseModel):
    message: str
    user_id: str = "anonymous"
    session_id: str = ""


async def event_stream(message: str, user_id: str, tenant_id: str, session_id: str):
    # 首帧回传原始 session_id：前端仅在当前浏览器会话内保存，服务端存储另做用户/租户隔离。
    yield sse_event("session", {"session_id": session_id})
    yield sse_event("agent_step", {"step": "session_start", "message": message})

    try:
        async for event in run_session(message, user_id, session_id, tenant_id):
            for node_name, node_output in event.items():
                if node_name == "profile":
                    yield sse_event("agent_step", {"step": "profile", "detail": "画像构建完成"})

                elif node_name == "planner":
                    plan = node_output.get("plan", [])
                    yield sse_event(
                        "agent_step",
                        {"step": "planner", "detail": f"规划了 {len(plan)} 个资源任务"},
                    )

                elif node_name == "generate_resource":
                    completed = node_output.get("completed", [])
                    for item in completed:
                        if item.get("status") == "passed":
                            yield sse_event(
                                "resource_card",
                                {
                                    "type": item.get("type", "doc"),
                                    "task_id": item.get("task_id", ""),
                                    "content": item.get("content", "")[:200],
                                },
                            )

                elif node_name == "gate":
                    yield sse_event("agent_step", {"step": "gate", "detail": "验收完成"})

                elif node_name == "critic":
                    reflections = node_output.get("reflections", [])
                    latest = reflections[-1] if reflections else {}
                    yield sse_event(
                        "agent_step",
                        {
                            "step": "critic",
                            "detail": latest.get("fix_strategy", "失败归因完成，准备重规划"),
                        },
                    )

                elif node_name == "debate":
                    for item in node_output.get("debate_rounds", []):
                        yield sse_event("debate_round", item)

                elif node_name == "judge":
                    yield sse_event(
                        "judge_verdict",
                        node_output.get("debate_verdict", {}),
                    )

                elif node_name == "pipeline":
                    completed = node_output.get("completed", [])
                    for item in completed:
                        if item.get("status") == "passed":
                            yield sse_event(
                                "resource_card",
                                {
                                    "type": item.get("type", "doc"),
                                    "task_id": item.get("task_id", ""),
                                    "content": item.get("content", "")[:200],
                                },
                            )
                    passed_n = sum(1 for c in completed if c.get("status") == "passed")
                    yield sse_event(
                        "agent_step",
                        {"step": "pipeline", "detail": f"流水线完成 {passed_n} 段"},
                    )

                elif node_name == "assemble":
                    bundle = node_output.get("resource_bundle", {})
                    total = bundle.get("total", 0)
                    yield sse_event(
                        "agent_step",
                        {"step": "assemble", "detail": f"组装完成，共 {total} 个资源"},
                    )

                    if bundle.get("resources"):
                        for res in bundle["resources"]:
                            yield sse_event(
                                "resource_card",
                                {
                                    "type": res.get("type", "doc"),
                                    "task_id": res.get("task_id", ""),
                                    "content": res.get("content", ""),
                                },
                            )

                elif node_name == "path_plan":
                    path = node_output.get("learning_path", []) or []
                    yield sse_event(
                        "learning_path",
                        {
                            "steps": path,
                            "summary": node_output.get("path_summary", ""),
                            "strategy": node_output.get("path_strategy", ""),
                        },
                    )
                    yield sse_event(
                        "agent_step",
                        {"step": "path_plan", "detail": f"生成 {len(path)} 步个性化学习路径"},
                    )

    except Exception as e:
        yield sse_event("error", {"error": str(e)})

    yield sse_event("done", {"status": "completed"})


@router.post("/chat")
async def chat(req: ChatRequest, user: CurrentUser = Depends(get_current_user)):
    # session_id 缺省由后端生成（uuid hex）；前端首轮不带、后续带回延续会话
    session_id = req.session_id or uuid.uuid4().hex
    return StreamingResponse(
        event_stream(req.message, user.user_id, user.tenant_id, session_id),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Content-Type": "text/event-stream; charset=utf-8",
        },
    )
