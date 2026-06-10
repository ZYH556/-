"""W3-E: 从最近导出的 LoRA 样本做质量门禁 + 版本化。质量不达标非 0 退出。"""

from __future__ import annotations

import sys
import time
from pathlib import Path

from reflexlearn.training.dataset_quality import check_dataset
from reflexlearn.training.dataset_registry import write_dataset_version
from reflexlearn.training.lora_samples import load_lora_samples


def main() -> int:
    src = sys.argv[1] if len(sys.argv) > 1 else "logs/lora_samples/lora_samples_latest.jsonl"
    samples = load_lora_samples(src)
    report = check_dataset(samples)
    label = time.strftime("%Y%m%d-%H%M%S", time.localtime())
    version = write_dataset_version(samples, report, label=label)
    print(f"[dataset] label={label} samples={report.metrics.sample_count} ready={version.ready}")
    print(f"[dataset] dir={version.directory}")
    print(f"[dataset] metrics={report.metrics.model_dump()}")
    if report.issues:
        print(f"[dataset] issues={report.issues}")
    if not Path(src).exists():
        print(f"[dataset] WARNING: source not found: {src} (export samples first)")
    return 0 if version.ready else 1


if __name__ == "__main__":
    raise SystemExit(main())
