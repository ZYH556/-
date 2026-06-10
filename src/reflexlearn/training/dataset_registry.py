"""W3-E LoRA 数据集版本化：写 train.jsonl + manifest.json + quality_report.md。

质量不达标时不写 READY 标记（训练脚本据此拒绝训练）。
"""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel, Field

from reflexlearn.training.dataset_quality import QualityReport, quality_report_markdown
from reflexlearn.training.lora_samples import LoraSftSample


class DatasetManifest(BaseModel):
    label: str
    sample_count: int
    ready: bool
    issues: list[str] = Field(default_factory=list)
    train_file: str
    quality_report_file: str


class DatasetVersion(BaseModel):
    label: str
    directory: str
    ready: bool
    manifest: DatasetManifest


def write_dataset_version(
    samples: list[LoraSftSample],
    report: QualityReport,
    *,
    label: str,
    base_dir: str | Path = "logs/lora_datasets",
) -> DatasetVersion:
    out = Path(base_dir) / label
    out.mkdir(parents=True, exist_ok=True)

    train_file = out / "train.jsonl"
    with train_file.open("w", encoding="utf-8", newline="\n") as fh:
        for sample in samples:
            fh.write(json.dumps(sample.model_dump(), ensure_ascii=False, sort_keys=True))
            fh.write("\n")

    report_file = out / "quality_report.md"
    report_file.write_text(quality_report_markdown(report), encoding="utf-8")

    manifest = DatasetManifest(
        label=label,
        sample_count=len(samples),
        ready=report.passed,
        issues=report.issues,
        train_file=str(train_file),
        quality_report_file=str(report_file),
    )
    (out / "manifest.json").write_text(
        json.dumps(manifest.model_dump(), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    ready_marker = out / "READY"
    if report.passed:
        ready_marker.write_text("ok\n", encoding="utf-8")
    elif ready_marker.exists():
        ready_marker.unlink()

    return DatasetVersion(
        label=label,
        directory=str(out),
        ready=report.passed,
        manifest=manifest,
    )
