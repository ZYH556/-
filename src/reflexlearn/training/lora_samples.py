from __future__ import annotations

import hashlib
import json
import re
import shutil
import time
from collections import defaultdict
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field

from reflexlearn.collaboration.traces import CollaborationTraceEvent

Role = Literal["system", "user", "assistant"]

SENSITIVE_KEYS = {
    "api_key",
    "authorization",
    "password",
    "secret",
    "tenant_id",
    "token",
    "user_id",
}


class TrainingMessage(BaseModel):
    role: Role
    content: str


class LoraSampleMetadata(BaseModel):
    sample_id: str
    session_id: str
    source_trace_ids: list[str] = Field(default_factory=list)
    nodes: list[str] = Field(default_factory=list)
    user_hash: str
    tenant_hash: str
    sanitized: bool = True
    created_at: float = 0.0


class LoraSftSample(BaseModel):
    messages: list[TrainingMessage] = Field(default_factory=list)
    metadata: LoraSampleMetadata


class LoraExportRecord(BaseModel):
    file_path: str
    sample_count: int
    created_at: float
    sanitized: bool = True


class LoraExportList(BaseModel):
    items: list[LoraExportRecord] = Field(default_factory=list)


class ExportResult(BaseModel):
    sample_count: int
    filtered_count: int
    file_path: str
    latest_file_path: str
    sanitized: bool
    items: list[LoraSftSample] = Field(default_factory=list)


def build_lora_samples(
    events: list[CollaborationTraceEvent],
    *,
    user_id: str,
    tenant_id: str,
    max_payload_chars: int = 1200,
) -> list[LoraSftSample]:
    """按 session 聚合协作轨迹，产出脱敏 SFT 样本。"""
    sessions: dict[str, list[CollaborationTraceEvent]] = defaultdict(list)
    for event in events:
        if event.user_id == user_id and event.tenant_id == tenant_id:
            sessions[event.session_id].append(event)

    samples: list[LoraSftSample] = []
    for session_id, session_events in sessions.items():
        ordered = sorted(session_events, key=lambda item: item.created_at)
        if not ordered:
            continue
        sample = _session_to_sample(
            ordered,
            user_id=user_id,
            tenant_id=tenant_id,
            max_payload_chars=max_payload_chars,
        )
        if sample is not None:
            samples.append(sample)
    return samples


def export_lora_samples(
    events: list[CollaborationTraceEvent],
    *,
    user_id: str,
    tenant_id: str,
    output_dir: str | Path = "logs/lora_samples",
    now_label: str | None = None,
) -> ExportResult:
    samples = build_lora_samples(events, user_id=user_id, tenant_id=tenant_id)
    session_count = len({event.session_id for event in events if event.user_id == user_id and event.tenant_id == tenant_id})
    filtered_count = max(0, session_count - len(samples))

    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    label = now_label or time.strftime("%Y%m%d-%H%M%S", time.localtime())
    target = output_path / f"{label}.jsonl"
    latest = output_path / "lora_samples_latest.jsonl"
    _write_jsonl(target, samples)
    if target != latest:
        shutil.copyfile(target, latest)
    return ExportResult(
        sample_count=len(samples),
        filtered_count=filtered_count,
        file_path=str(target),
        latest_file_path=str(latest),
        sanitized=True,
        items=samples,
    )


def list_lora_exports(*, output_dir: str | Path = "logs/lora_samples") -> LoraExportList:
    path = Path(output_dir)
    if not path.exists():
        return LoraExportList()
    records = [
        _record_for_file(item)
        for item in path.glob("*.jsonl")
        if item.name != "lora_samples_latest.jsonl"
    ]
    records.sort(key=lambda item: item.created_at, reverse=True)
    return LoraExportList(items=records)


def _session_to_sample(
    events: list[CollaborationTraceEvent],
    *,
    user_id: str,
    tenant_id: str,
    max_payload_chars: int,
) -> LoraSftSample | None:
    nodes = [event.node for event in events]
    user_goal = _session_goal(events)
    assistant = _assistant_summary(events, max_payload_chars=max_payload_chars)
    if not assistant.strip():
        return None
    metadata = LoraSampleMetadata(
        sample_id=_hash_text(f"{tenant_id}:{user_id}:{events[0].session_id}")[:24],
        session_id=f"sha256:{_hash_text(f'{tenant_id}:{user_id}:{events[0].session_id}')[:16]}",
        source_trace_ids=[event.trace_id for event in events],
        nodes=nodes,
        user_hash=f"sha256:{_hash_text(user_id)[:16]}",
        tenant_hash=f"sha256:{_hash_text(tenant_id)[:16]}",
        sanitized=True,
        created_at=max(event.created_at for event in events),
    )
    return LoraSftSample(
        messages=[
            TrainingMessage(
                role="system",
                content="你是 ReflexLearn 的学习协作智能体，请根据轨迹产出高质量学习资源与改进建议。",
            ),
            TrainingMessage(role="user", content=user_goal),
            TrainingMessage(role="assistant", content=assistant),
        ],
        metadata=metadata,
    )


def _session_goal(events: list[CollaborationTraceEvent]) -> str:
    for event in events:
        if event.node == "session_start":
            message = event.payload.get("message", "")
            if isinstance(message, str) and message.strip():
                return _sanitize_text(message, max_chars=500)
    return "根据本轮协作轨迹完成个性化学习任务。"


def _assistant_summary(events: list[CollaborationTraceEvent], *, max_payload_chars: int) -> str:
    lines = []
    for event in events:
        if event.node == "session_start":
            continue
        payload = _sanitize_payload(event.payload)
        text = json.dumps(payload, ensure_ascii=False, sort_keys=True)
        lines.append(f"- {event.node}: {_sanitize_text(text, max_chars=max_payload_chars)}")
    if not lines:
        # 只有 session_start 的空轨迹不可作为训练样本（上游据空串过滤）
        return ""
    return "\n".join(["协作轨迹摘要：", *lines])


def _sanitize_payload(value):
    if isinstance(value, dict):
        cleaned = {}
        for key, item in value.items():
            normalized = str(key).lower()
            if normalized in SENSITIVE_KEYS:
                continue
            cleaned[key] = _sanitize_payload(item)
        return cleaned
    if isinstance(value, list):
        return [_sanitize_payload(item) for item in value]
    if isinstance(value, str):
        return _sanitize_text(value, max_chars=1200)
    return value


def _sanitize_text(value: str, *, max_chars: int) -> str:
    text = _scrub_url_queries(value)
    text = re.sub(
        r"(?i)\bauthorization\s*[:=]\s*bearer\s+[^\s,;]+",
        "Authorization=[redacted]",
        text,
    )
    text = re.sub(
        r"(?i)\b(token|api_key|secret|password|authorization)\s*[:=]\s*[^\s,;]+",
        r"\1=[redacted]",
        text,
    )
    text = re.sub(r"(?i)bearer\s+[a-z0-9._\-]+", "Bearer [redacted]", text)
    if len(text) > max_chars:
        return text[:max_chars] + "...[truncated]"
    return text


def _scrub_url_queries(value: str) -> str:
    return re.sub(r"(https?://[^\s?\"']+)\?[^ \n\"']+", r"\1?[redacted]", value)


def _write_jsonl(path: Path, samples: list[LoraSftSample]) -> None:
    with path.open("w", encoding="utf-8", newline="\n") as fh:
        for sample in samples:
            fh.write(json.dumps(sample.model_dump(), ensure_ascii=False, sort_keys=True))
            fh.write("\n")


def _record_for_file(path: Path) -> LoraExportRecord:
    try:
        sample_count = sum(1 for line in path.read_text(encoding="utf-8").splitlines() if line.strip())
    except OSError:
        sample_count = 0
    return LoraExportRecord(
        file_path=str(path),
        sample_count=sample_count,
        created_at=path.stat().st_mtime,
        sanitized=True,
    )


def _hash_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def load_lora_samples(path: str | Path) -> list[LoraSftSample]:
    """从 JSONL 读回 SFT 样本（供数据质量门禁/版本化使用）；坏行跳过。"""
    file_path = Path(path)
    if not file_path.exists():
        return []
    out: list[LoraSftSample] = []
    for line in file_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            out.append(LoraSftSample.model_validate_json(line))
        except Exception:  # noqa: BLE001 - 坏行跳过，不中断
            continue
    return out
