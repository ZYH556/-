from __future__ import annotations

import pytest

from reflexlearn.skills.base import SkillResult


def _project_root():
    from pathlib import Path

    return Path(__file__).resolve().parents[3]


class _FakeSkill:
    name = "fake"

    def __init__(self):
        self.calls: list[dict] = []

    async def run(self, inp, ctx):
        self.calls.append({"inp": inp, "ctx": ctx})
        return SkillResult(ok=True, data={"echo": inp["query"]}, duration_ms=1)


class _BoomSkill:
    name = "boom"

    async def run(self, inp, ctx):
        raise RuntimeError("skill down")


@pytest.mark.asyncio
async def test_call_skill_uses_public_acl_and_serializes_result():
    from reflexlearn.mcp_tools.server import call_skill

    skill = _FakeSkill()
    result = await call_skill(
        skill,
        {"query": "线性回归"},
        user_id="u1",
        tenant_id="t1",
        task_id="mcp-1",
    )

    assert result["ok"] is True
    assert result["data"] == {"echo": "线性回归"}
    ctx = skill.calls[0]["ctx"]
    assert ctx.user_id == "u1"
    assert ctx.task_id == "mcp-1"
    assert ctx.acl == {"user_id": "u1", "tenant_id": "t1", "visibility": ["public"]}


@pytest.mark.asyncio
async def test_call_skill_degrades_exceptions_to_error_payload():
    from reflexlearn.mcp_tools.server import call_skill

    result = await call_skill(_BoomSkill(), {"query": "x"})

    assert result["ok"] is False
    assert result["error_type"] == "RuntimeError"
    assert result["data"] == {}


def test_supported_tools_are_safe_default_subset():
    from reflexlearn.mcp_tools.server import supported_tool_names

    assert supported_tool_names() == ["retrieve", "doc_gen", "quiz_gen"]


def test_pyproject_declares_mcp_optional_dependency():
    import tomllib

    root = _project_root()
    data = tomllib.loads((root / "pyproject.toml").read_text(encoding="utf-8"))

    assert "mcp" in data["project"]["optional-dependencies"]
    assert any(dep.startswith("mcp>=") for dep in data["project"]["optional-dependencies"]["mcp"])


def test_start_mcp_script_uses_project_logging_contract():
    root = _project_root()
    wrapper_text = (root / "scripts/start_mcp.sh").read_text(encoding="utf-8")
    text = (root / "scripts/ops/start_mcp.sh").read_text(encoding="utf-8")

    assert 'source "$SCRIPT_DIR/_lib.sh"' in wrapper_text
    assert 'exec "$SCRIPT_DIR/ops/start_mcp.sh" "$@"' in wrapper_text
    assert 'source "$SCRIPTS_ROOT/_lib.sh"' in text
    assert "ensure_logs" in text
    assert "use_python_defaults" in text
    assert "python_cmd" in text
    assert "reflexlearn.mcp_tools.server" in text
    assert 'tee -a "$LOG_DIR/start_mcp.log"' in text
