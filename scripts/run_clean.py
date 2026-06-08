"""批清洗作业入口（M4-D · docs/04 §6.2）：MinIO 原始 JSON Lines → 清洗 → 写回 MinIO。

用法（项目根，需 docker 起 minio + enable_minio，原始数据已上传到 input_key）：
    NO_PROXY='*' PYTHONPATH=src .venv/Scripts/python.exe scripts/run_clean.py raw/in.jsonl cleaned/out.jsonl
无 MinIO 自动跳过；无 pyspark/pandas 自动降级纯 Python（清洗语义不变）。
"""
from __future__ import annotations

import logging
import sys

from reflexlearn.data_engineering.batch import run_cleaning_job

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")


def main() -> None:
    input_key = sys.argv[1] if len(sys.argv) > 1 else "raw/input.jsonl"
    output_key = sys.argv[2] if len(sys.argv) > 2 else "cleaned/output.jsonl"
    report = run_cleaning_job(input_key=input_key, output_key=output_key)
    if report is None:
        print("[SKIP] MinIO 不可用，批清洗作业未执行")
    else:
        print(
            f"[OK] engine={report.engine} in={report.input_count} "
            f"out={report.output_count} removed={report.removed}"
        )


if __name__ == "__main__":
    main()
