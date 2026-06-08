"""M4-D 数据清洗 + 批 runner + MinIO 存储单测。

clean 纯函数无外部依赖、真实可跑；batch runner 当前环境真实走纯 Python 兜底（pyspark/pandas 未装）；
MinIO 注入内存假 client，绝不真连服务（仿写链路注入范式）。
"""
from __future__ import annotations

import pytest

from reflexlearn.data_engineering import storage
from reflexlearn.data_engineering.batch import run_cleaning, run_cleaning_job
from reflexlearn.data_engineering.cleaning import (
    clean_batch,
    clean_one,
    content_hash,
    is_quality,
    normalize_terms,
    normalize_text,
)


# ---------- cleaning 纯函数 ----------
def test_normalize_text_strips_html_and_whitespace():
    assert normalize_text("<p>线性  回归</p>\n\n模型") == "线性 回归 模型"
    assert normalize_text("") == ""


def test_normalize_terms_maps_dictionary():
    assert "支持向量机" in normalize_terms("学习 SVM 算法")
    assert "卷积神经网络" in normalize_terms("CNN 用于图像")
    assert normalize_terms("SVMX") == "SVMX"  # 词边界：不误伤子串


def test_content_hash_stable_and_distinct():
    assert content_hash("abc") == content_hash("abc")
    assert content_hash("abc") != content_hash("abd")


def test_is_quality_length_gate():
    assert is_quality("x" * 50, min_len=30) is True
    assert is_quality("短", min_len=30) is False


def test_clean_one_normalizes_and_filters():
    out = clean_one({"content": "<b>SVM</b> 是一种" + "监督学习" * 10, "doc_id": "d1"}, min_len=10)
    assert out is not None
    assert "支持向量机" in out["content"] and "<b>" not in out["content"]
    assert out["doc_id"] == "d1" and "content_hash" in out
    assert clean_one({"content": "短"}, min_len=30) is None  # 过短被过滤


def test_clean_batch_dedup_and_filter():
    docs = [
        {"content": "机器学习" * 20, "doc_id": "a"},
        {"content": "机器学习" * 20, "doc_id": "b"},  # 内容同 → 去重
        {"content": "短", "doc_id": "c"},             # 过短 → 过滤
        {"content": "深度学习" * 20, "doc_id": "d"},
    ]
    out = clean_batch(docs, min_len=30)
    assert len(out) == 2  # 去重 + 过滤后剩 2


# ---------- batch runner（三级降级，当前环境真实走 python）----------
def test_run_cleaning_reports_engine_and_counts():
    docs = [
        {"content": "线性回归" * 20, "doc_id": "a"},
        {"content": "线性回归" * 20, "doc_id": "b"},  # 重复
        {"content": "噪声", "doc_id": "c"},           # 过短
    ]
    cleaned, report = run_cleaning(docs, min_len=30)
    assert report.engine in ("spark", "pandas", "python")
    assert report.input_count == 3 and report.output_count == 1 and report.removed == 2


def test_run_cleaning_empty():
    cleaned, report = run_cleaning([], min_len=30)
    assert cleaned == [] and report.input_count == 0 and report.output_count == 0


# ---------- MinIO storage（内存假 client，绝不真连）----------
class _FakeMinio:
    def __init__(self, fail: bool = False):
        self.store: dict = {}
        self.buckets: set = set()
        self.fail = fail

    def bucket_exists(self, b):
        return b in self.buckets

    def make_bucket(self, b):
        self.buckets.add(b)

    def put_object(self, bucket, key, data, length):
        if self.fail:
            raise RuntimeError("minio down")
        self.store[(bucket, key)] = data.read()

    def get_object(self, bucket, key):
        if self.fail or (bucket, key) not in self.store:
            raise RuntimeError("not found")
        import io

        return io.BytesIO(self.store[(bucket, key)])


def test_storage_put_get_documents_roundtrip():
    c = _FakeMinio()
    docs = [{"content": "a", "doc_id": "1"}, {"content": "b", "doc_id": "2"}]
    assert storage.put_documents(c, "bkt", "k.jsonl", docs) is True
    assert storage.get_documents(c, "bkt", "k.jsonl") == docs


def test_storage_put_degrades_on_failure():
    c = _FakeMinio(fail=True)
    assert storage.put_bytes(c, "b", "k", b"x") is False
    assert storage.get_documents(c, "b", "k") == []  # 取不到降级空列表


def test_run_cleaning_job_with_injected_client():
    c = _FakeMinio()
    raw_docs = [
        {"content": "机器学习导论" * 10, "doc_id": "a"},
        {"content": "机器学习导论" * 10, "doc_id": "b"},  # 重复
        {"content": "x", "doc_id": "c"},                 # 过短
    ]
    storage.put_documents(c, "reflexlearn-raw", "raw/in.jsonl", raw_docs)
    report = run_cleaning_job(
        input_key="raw/in.jsonl", output_key="cleaned/out.jsonl", client=c, min_len=30
    )
    assert report is not None and report.output_count == 1
    cleaned = storage.get_documents(c, "reflexlearn-raw", "cleaned/out.jsonl")
    assert len(cleaned) == 1 and "content_hash" in cleaned[0]


def test_run_cleaning_job_no_minio_returns_none(monkeypatch):
    def _boom():
        raise storage.MinioUnavailable("no minio")

    monkeypatch.setattr(storage, "make_minio_client", _boom)
    assert run_cleaning_job(input_key="a", output_key="b", client=None) is None
