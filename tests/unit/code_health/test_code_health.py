from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[3]


def test_known_python_files_stay_under_line_budget():
    files = [
        PROJECT_ROOT / "src/reflexlearn/skills/path_plan.py",
        PROJECT_ROOT / "src/reflexlearn/llm_gateway/gateway.py",
    ]

    over_budget = {
        str(path.relative_to(PROJECT_ROOT)): len(path.read_text(encoding="utf-8").splitlines())
        for path in files
        if len(path.read_text(encoding="utf-8").splitlines()) > 300
    }

    assert over_budget == {}


def test_unit_root_keeps_test_files_grouped_by_domain():
    root_test_files = list((PROJECT_ROOT / "tests/unit").glob("test_*.py"))

    assert len(root_test_files) <= 8


def test_prompt_kit_components_are_kept_available_without_forcing_chat_runtime():
    prompt_kit = PROJECT_ROOT / "frontend/components/prompt-kit"
    chat_input = (PROJECT_ROOT / "frontend/components/chat/ChatInput.tsx").read_text(
        encoding="utf-8"
    )

    assert (prompt_kit / "prompt-input.tsx").exists()
    assert (prompt_kit / "message.tsx").exists()
    assert (prompt_kit / "markdown.tsx").exists()
    assert "@/components/prompt-kit/prompt-input" not in chat_input
