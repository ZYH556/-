"""M4-D 批清洗 runner（docs/04 §6.2）：Spark local[*] → pandas → 纯 Python 三级降级。

清洗语义由 `cleaning.clean_one` 纯函数固定，三引擎只决定并行度、不改语义。当前环境 pyspark/pandas
均未装 → 真实走纯 Python 兜底；装上任一即自动提速，无需改清洗逻辑。`run_cleaning_job` 串 MinIO 读写。
"""
from __future__ import annotations

import logging

from pydantic import BaseModel

from reflexlearn.common.config import get_settings
from reflexlearn.data_engineering.cleaning import clean_batch, clean_one

logger = logging.getLogger(__name__)


class CleaningReport(BaseModel):
    engine: str            # spark | pandas | python
    input_count: int
    output_count: int
    removed: int           # 过滤 + 去重移除的条数


def _run_spark(docs: list[dict], min_len: int) -> list[dict]:
    """Spark local[*]：clean_one 作 map UDF，按 content_hash dedup。pyspark 缺则 import 抛 → 上层降级。"""
    from pyspark.sql import SparkSession

    spark = SparkSession.builder.appName("knowledge-clean").master("local[*]").getOrCreate()
    try:
        rdd = spark.sparkContext.parallelize(docs)
        cleaned = rdd.map(lambda d: clean_one(d, min_len=min_len)).filter(lambda x: x is not None)
        deduped = (
            cleaned.keyBy(lambda d: d["content_hash"])
            .reduceByKey(lambda a, b: a)
            .map(lambda kv: kv[1])
        )
        return deduped.collect()
    finally:
        spark.stop()


def _run_pandas(docs: list[dict], min_len: int) -> list[dict]:
    """pandas DataFrame.apply 清洗 + 去重。pandas 缺则 import 抛 → 上层降级。"""
    import pandas as pd

    df = pd.DataFrame(docs)
    rows = [clean_one(r, min_len=min_len) for r in df.to_dict("records")]
    out: list[dict] = []
    seen: set[str] = set()
    for r in rows:
        if r is None or r["content_hash"] in seen:
            continue
        seen.add(r["content_hash"])
        out.append(r)
    return out


def run_cleaning(docs: list[dict], *, min_len: int | None = None) -> tuple[list[dict], CleaningReport]:
    """三级降级批清洗。返回 (cleaned_docs, report)。engine 标记实际生效的执行引擎。"""
    if min_len is None:
        min_len = get_settings().clean_min_chars

    engine = "python"
    try:
        import pyspark  # noqa: F401

        cleaned = _run_spark(docs, min_len)
        engine = "spark"
    except Exception as e:
        logger.info("spark unavailable (%s), trying pandas", type(e).__name__)
        try:
            import pandas  # noqa: F401

            cleaned = _run_pandas(docs, min_len)
            engine = "pandas"
        except Exception as e2:
            logger.info("pandas unavailable (%s), using pure-python", type(e2).__name__)
            cleaned = clean_batch(docs, min_len=min_len)
            engine = "python"

    report = CleaningReport(
        engine=engine,
        input_count=len(docs),
        output_count=len(cleaned),
        removed=len(docs) - len(cleaned),
    )
    return cleaned, report


def run_cleaning_job(
    *, input_key: str, output_key: str, client=None, min_len: int | None = None
) -> CleaningReport | None:
    """MinIO 原始 JSON Lines → 清洗 → 写回 MinIO。无 MinIO 返回 None（降级跳过）。"""
    from reflexlearn.data_engineering import storage

    if client is None:
        try:
            client = storage.make_minio_client()
        except Exception as e:
            logger.warning("minio unavailable, cleaning job skipped: %s", e)
            return None
    bucket = get_settings().minio_bucket
    docs = storage.get_documents(client, bucket, input_key)
    cleaned, report = run_cleaning(docs, min_len=min_len)
    storage.put_documents(client, bucket, output_key, cleaned)
    logger.info("cleaning job done: %s", report.model_dump())
    return report
