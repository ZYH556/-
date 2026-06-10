from __future__ import annotations

import numpy as np
import pytest
import sys
import importlib
from types import SimpleNamespace

import reflexlearn.common.embedding as emb


class _FakeModel:
    """记录 encode 输入；返回固定维度向量。用于在不加载真实模型的前提下测封装逻辑。"""

    def __init__(self):
        self.inputs = []

    def encode(self, text, normalize_embeddings=True, convert_to_numpy=True):
        self.inputs.append(text)
        if isinstance(text, list):
            return np.array([[0.1] * emb.EMBED_DIM for _ in text], dtype=float)
        return np.array([0.1] * emb.EMBED_DIM, dtype=float)


def test_embed_query_prepends_instruction(monkeypatch):
    fake = _FakeModel()
    monkeypatch.setattr(emb, "_get_model", lambda *a, **k: fake)
    vec = emb.embed_query("线性回归怎么求解")
    assert len(vec) == emb.EMBED_DIM
    # bge 查询侧必须加检索指令前缀
    assert fake.inputs[0].startswith(emb._QUERY_INSTRUCTION)
    assert "线性回归怎么求解" in fake.inputs[0]


def test_embed_documents_no_instruction(monkeypatch):
    fake = _FakeModel()
    monkeypatch.setattr(emb, "_get_model", lambda *a, **k: fake)
    vecs = emb.embed_documents(["文档一", "文档二"])
    assert len(vecs) == 2 and len(vecs[0]) == emb.EMBED_DIM
    # 文档侧整体传入，且不加查询指令前缀
    assert fake.inputs[0] == ["文档一", "文档二"]


def test_embed_documents_empty_skips_model():
    # 空输入不触发模型加载（即使依赖未安装也安全）
    assert emb.embed_documents([]) == []


def test_is_available_false_on_load_failure(monkeypatch):
    def boom(*a, **k):
        raise emb.EmbeddingUnavailable("no deps")

    monkeypatch.setattr(emb, "_get_model", boom)
    assert emb.is_available() is False


def test_is_available_true_when_model_loads(monkeypatch):
    monkeypatch.setattr(emb, "_get_model", lambda *a, **k: _FakeModel())
    assert emb.is_available() is True


def test_get_model_uses_local_files_only_when_offline(monkeypatch):
    calls = []

    class FakeSentenceTransformer:
        def __init__(self, *args, **kwargs):
            calls.append((args, kwargs))

    monkeypatch.setenv("HF_HUB_OFFLINE", "1")
    monkeypatch.setitem(
        sys.modules,
        "sentence_transformers",
        SimpleNamespace(SentenceTransformer=FakeSentenceTransformer),
    )
    monkeypatch.setitem(
        sys.modules,
        "torch",
        SimpleNamespace(set_num_threads=lambda _n: None),
    )
    real_emb = importlib.reload(emb)
    monkeypatch.setattr(real_emb, "_model", None)
    monkeypatch.setattr(real_emb, "_load_failed", False)

    model = real_emb._get_model("BAAI/bge-large-zh-v1.5")

    assert isinstance(model, FakeSentenceTransformer)
    assert calls[0][1]["local_files_only"] is True


def test_get_model_uses_local_files_only_by_default(monkeypatch):
    calls = []

    class FakeSentenceTransformer:
        def __init__(self, *args, **kwargs):
            calls.append((args, kwargs))

    monkeypatch.delenv("HF_HUB_OFFLINE", raising=False)
    monkeypatch.delenv("TRANSFORMERS_OFFLINE", raising=False)
    monkeypatch.delenv("REFLEXLEARN_ALLOW_MODEL_DOWNLOAD", raising=False)
    monkeypatch.setitem(
        sys.modules,
        "sentence_transformers",
        SimpleNamespace(SentenceTransformer=FakeSentenceTransformer),
    )
    monkeypatch.setitem(
        sys.modules,
        "torch",
        SimpleNamespace(set_num_threads=lambda _n: None),
    )
    real_emb = importlib.reload(emb)
    monkeypatch.setattr(real_emb, "_model", None)
    monkeypatch.setattr(real_emb, "_load_failed", False)

    real_emb._get_model("BAAI/bge-large-zh-v1.5")

    assert calls[0][1]["local_files_only"] is True


def test_offline_model_kwargs_sets_hf_offline_env_by_default(monkeypatch):
    monkeypatch.delenv("HF_HUB_OFFLINE", raising=False)
    monkeypatch.delenv("TRANSFORMERS_OFFLINE", raising=False)
    monkeypatch.delenv("HF_DATASETS_OFFLINE", raising=False)
    monkeypatch.delenv("DISABLE_SAFETENSORS_CONVERSION", raising=False)
    monkeypatch.delenv("REFLEXLEARN_ALLOW_MODEL_DOWNLOAD", raising=False)
    real_emb = importlib.reload(emb)

    assert real_emb._offline_model_kwargs() == {"local_files_only": True}
    assert real_emb.os.getenv("HF_HUB_OFFLINE") == "1"
    assert real_emb.os.getenv("TRANSFORMERS_OFFLINE") == "1"
    assert real_emb.os.getenv("HF_DATASETS_OFFLINE") == "1"
    assert real_emb.os.getenv("DISABLE_SAFETENSORS_CONVERSION") == "1"
