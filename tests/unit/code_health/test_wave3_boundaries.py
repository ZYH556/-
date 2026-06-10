"""波次 3 风险门禁：冻结关键 Run & Debug 入口与安全红线声明。

W3-0 的目的是在动安全/训练/部署前固化基线，避免后续把环境问题
误判成代码回归，并防止派工书里的安全红线被误删。
"""

from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[3]


def test_required_root_script_entries_exist():
    """波次 3 依赖的根脚本入口必须存在（含本卡新增的 preflight）。"""
    required = [
        "scripts/test_unit.sh",
        "scripts/build_frontend.sh",
        "scripts/check_api_security.sh",
        "scripts/check_wave2_api.sh",
        "scripts/check_lora_export.sh",
        "scripts/check_wave3_preflight.sh",
    ]
    missing = [rel for rel in required if not (PROJECT_ROOT / rel).is_file()]
    assert missing == []


def test_wave3_dispatch_doc_exists():
    doc = PROJECT_ROOT / "docs/17-波次3任务派工书.md"
    assert doc.is_file()


def test_wave3_forbids_sessionstorage_in_production():
    """派工书必须明确禁止把 demo Bearer/sessionStorage 方案带到生产。"""
    doc = PROJECT_ROOT / "docs/17-波次3任务派工书.md"
    text = doc.read_text(encoding="utf-8")
    assert "demo Bearer/sessionStorage 方案带到生产上线" in text


def test_wave3_preflight_real_impl_exists():
    """根包装必须对应 checks/ops 下的真实实现，保持目录治理约定。"""
    real_impl = PROJECT_ROOT / "scripts/checks/ops/check_wave3_preflight.sh"
    assert real_impl.is_file()
