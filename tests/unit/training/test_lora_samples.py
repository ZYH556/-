import json

from reflexlearn.collaboration.traces import CollaborationTraceStore
from reflexlearn.training.lora_samples import (
    build_lora_samples,
    export_lora_samples,
    list_lora_exports,
)


def _events():
    store = CollaborationTraceStore(pg_pool=None)
    store.record_memory(
        user_id="real-user",
        tenant_id="tenant-a",
        session_id="s1",
        node="session_start",
        event_type="agent_step",
        payload={
            "message": "学习线性回归，token=secret-token，链接 https://example.com/path?token=abc",
            "user_id": "real-user",
        },
    )
    store.record_memory(
        user_id="real-user",
        tenant_id="tenant-a",
        session_id="s1",
        node="planner",
        event_type="agent_step",
        payload={"plan_count": 3, "tenant_id": "tenant-a"},
    )
    store.record_memory(
        user_id="real-user",
        tenant_id="tenant-a",
        session_id="s1",
        node="metacognition",
        event_type="agent_step",
        payload={"refine_hint": "补充梯度下降例子", "api_key": "sk-live"},
    )
    store.record_memory(
        user_id="real-user",
        tenant_id="tenant-a",
        session_id="s1",
        node="assemble",
        event_type="agent_step",
        payload={"total": 3},
    )
    return store.list_memory(user_id="real-user", tenant_id="tenant-a", limit=20)


def test_build_lora_samples_groups_trace_and_sanitizes_sensitive_fields():
    samples = build_lora_samples(_events(), user_id="real-user", tenant_id="tenant-a")

    assert len(samples) == 1
    sample = samples[0]
    raw = json.dumps(sample.model_dump(), ensure_ascii=False)
    assert [message.role for message in sample.messages] == ["system", "user", "assistant"]
    assert "planner" in sample.messages[2].content
    assert "metacognition" in sample.messages[2].content
    assert "real-user" not in raw
    assert "tenant-a" not in raw
    assert "secret-token" not in raw
    assert "sk-live" not in raw
    assert "https://example.com/path?[redacted]" in raw
    assert sample.metadata.user_hash.startswith("sha256:")
    assert sample.metadata.tenant_hash.startswith("sha256:")
    assert sample.metadata.sanitized is True


def test_build_lora_samples_skips_session_start_only_trace():
    store = CollaborationTraceStore(pg_pool=None)
    store.record_memory(
        user_id="real-user",
        tenant_id="tenant-a",
        session_id="empty-session",
        node="session_start",
        event_type="agent_step",
        payload={"message": "只有起始帧，不能作为训练样本"},
    )

    samples = build_lora_samples(
        store.list_memory(user_id="real-user", tenant_id="tenant-a", limit=20),
        user_id="real-user",
        tenant_id="tenant-a",
    )

    assert samples == []


def test_export_lora_samples_writes_jsonl_and_lists_exports(tmp_path):
    result = export_lora_samples(
        _events(),
        user_id="real-user",
        tenant_id="tenant-a",
        output_dir=tmp_path,
        now_label="20260609-120000",
    )

    assert result.sample_count == 1
    assert result.filtered_count == 0
    assert result.sanitized is True
    path = tmp_path / "20260609-120000.jsonl"
    assert result.file_path == str(path)
    rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
    assert rows[0]["messages"][0]["role"] == "system"
    assert rows[0]["metadata"]["sample_id"]
    listed = list_lora_exports(output_dir=tmp_path)
    assert listed.items[0].file_path == str(path)
    assert listed.items[0].sample_count == 1
