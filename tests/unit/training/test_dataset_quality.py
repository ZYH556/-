"""W3-E: LoRA 数据质量门禁单元测试。"""

from __future__ import annotations

from reflexlearn.training.dataset_quality import check_dataset, quality_report_markdown
from reflexlearn.training.lora_samples import LoraSampleMetadata, LoraSftSample, TrainingMessage


def _sample(*, assistant: str = "x" * 30, nodes: list[str] | None = None) -> LoraSftSample:
    return LoraSftSample(
        messages=[
            TrainingMessage(role="system", content="系统提示"),
            TrainingMessage(role="user", content="学习目标"),
            TrainingMessage(role="assistant", content=assistant),
        ],
        metadata=LoraSampleMetadata(
            sample_id="s1",
            session_id="sha256:x",
            user_hash="sha256:u",
            tenant_hash="sha256:t",
            nodes=nodes or ["critic", "generate_resource"],
        ),
    )


def test_clean_dataset_passes():
    samples = [_sample(assistant="a" * 30, nodes=["critic"]), _sample(assistant="b" * 30, nodes=["metacognition"])]
    report = check_dataset(samples)
    assert report.passed
    assert report.metrics.sample_count == 2
    assert report.metrics.node_coverage == 1.0


def test_too_few_samples_fails():
    report = check_dataset([], min_samples=1)
    assert not report.passed
    assert any("too_few" in i for i in report.issues)


def test_incomplete_triplet_fails():
    report = check_dataset([_sample(assistant="")])
    assert not report.passed
    assert any("incomplete" in i for i in report.issues)


def test_sensitive_leak_fails():
    report = check_dataset([_sample(assistant="泄漏密钥 sk-ABCDEFGH12345678 " + "x" * 20)])
    assert not report.passed
    assert any("sensitive_leak" in i for i in report.issues)


def test_high_duplicate_rate_fails():
    same = "完全相同的助手回答内容用于测试重复率检测逻辑"
    report = check_dataset([_sample(assistant=same) for _ in range(3)], max_duplicate_rate=0.5)
    assert not report.passed
    assert any("duplicate" in i for i in report.issues)


def test_short_assistant_fails():
    report = check_dataset([_sample(assistant="短")], min_assistant_chars=20)
    assert not report.passed
    assert any("too_short" in i for i in report.issues)


def test_low_focus_node_coverage_fails():
    report = check_dataset([_sample(nodes=["session_start", "planner"])])
    assert not report.passed
    assert any("low_node_coverage" in i for i in report.issues)


def test_quality_report_markdown():
    report = check_dataset([_sample(assistant="a" * 30)])
    md = quality_report_markdown(report)
    assert "数据集质量报告" in md
    assert "样本数" in md
