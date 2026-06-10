"""W3-E: LoRA 数据集版本化单元测试。"""

from __future__ import annotations

from pathlib import Path

from reflexlearn.training.dataset_quality import check_dataset
from reflexlearn.training.dataset_registry import write_dataset_version
from reflexlearn.training.lora_samples import (
    LoraSampleMetadata,
    LoraSftSample,
    TrainingMessage,
    load_lora_samples,
)


def _sample(*, assistant: str = "x" * 30) -> LoraSftSample:
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
            nodes=["critic"],
        ),
    )


def test_write_ready_dataset(tmp_path):
    samples = [_sample(assistant="a" * 30)]
    report = check_dataset(samples)
    assert report.passed
    version = write_dataset_version(samples, report, label="v1", base_dir=tmp_path)
    assert version.ready
    d = Path(version.directory)
    assert (d / "train.jsonl").exists()
    assert (d / "manifest.json").exists()
    assert (d / "quality_report.md").exists()
    assert (d / "READY").exists()


def test_write_not_ready_dataset(tmp_path):
    samples = [_sample(assistant="短")]  # too short → 不达标
    report = check_dataset(samples)
    assert not report.passed
    version = write_dataset_version(samples, report, label="v2", base_dir=tmp_path)
    assert not version.ready
    assert not (Path(version.directory) / "READY").exists()
    assert version.manifest.issues


def test_load_lora_samples_roundtrip(tmp_path):
    samples = [_sample(assistant="a" * 30)]
    report = check_dataset(samples)
    version = write_dataset_version(samples, report, label="v3", base_dir=tmp_path)
    loaded = load_lora_samples(Path(version.directory) / "train.jsonl")
    assert len(loaded) == 1
    assert loaded[0].messages[-1].content == "a" * 30
