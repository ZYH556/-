"""bge-large-zh-v1.5 语义向量封装（单例 + 懒加载 + 降级）。

为 RAG 检索与知识入库提供统一 embedding 接口。模型较大（1024 维），
采用懒加载：首次调用 embed_* 时才加载，避免后端启动卡顿。
当依赖未安装 / 模型下载失败 / 加载异常时抛 EmbeddingUnavailable，
由上层（RetrieveSkill）捕获后降级回 mock，保证离线 / 受限环境下系统不破坏。
"""
from __future__ import annotations

import logging
import os
import threading

logger = logging.getLogger(__name__)

EMBED_DIM = 1024
_DEFAULT_MODEL = "BAAI/bge-large-zh-v1.5"
# bge 系列检索任务要求「查询」侧加指令前缀，「文档」侧不加（官方约定）
_QUERY_INSTRUCTION = "为这个句子生成表示以用于检索相关文章："

_model = None
_load_failed = False
_lock = threading.Lock()


class EmbeddingUnavailable(RuntimeError):
    """embedding 不可用（缺依赖 / 模型加载失败）——上层据此降级。"""


def _resolve_model_name() -> str:
    try:
        from reflexlearn.common.config import get_settings

        return get_settings().embedding_model or _DEFAULT_MODEL
    except Exception:
        return _DEFAULT_MODEL


def _offline_model_kwargs() -> dict:
    allow_download = os.getenv("REFLEXLEARN_ALLOW_MODEL_DOWNLOAD") == "1"
    offline = (
        not allow_download
        or os.getenv("HF_HUB_OFFLINE") == "1"
        or os.getenv("TRANSFORMERS_OFFLINE") == "1"
    )
    if offline:
        os.environ.setdefault("HF_HUB_OFFLINE", "1")
        os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")
        os.environ.setdefault("HF_DATASETS_OFFLINE", "1")
        os.environ.setdefault("DISABLE_SAFETENSORS_CONVERSION", "1")
    return {"local_files_only": True} if offline else {}


def _get_model(model_name: str | None = None):
    """懒加载并缓存模型；加载失败后置位 _load_failed，后续直接抛错不再重试。"""
    global _model, _load_failed
    if _model is not None:
        return _model
    if _load_failed:
        raise EmbeddingUnavailable("embedding model previously failed to load")
    with _lock:
        if _model is not None:
            return _model
        if _load_failed:
            raise EmbeddingUnavailable("embedding model previously failed to load")
        try:
            from sentence_transformers import SentenceTransformer

            try:
                import torch

                torch.set_num_threads(1)  # 防 OpenBLAS / OMP 过度并发导致 OOM
            except Exception:
                pass

            name = model_name or _resolve_model_name()
            logger.info("loading embedding model: %s", name)
            _model = SentenceTransformer(name, device="cpu", **_offline_model_kwargs())
            return _model
        except Exception as e:  # 依赖缺失 / 模型下载失败 / 加载异常
            _load_failed = True
            logger.warning("embedding model load failed: %s", e)
            raise EmbeddingUnavailable(str(e)) from e


def is_available() -> bool:
    """探测 embedding 是否可用（尝试加载，失败返回 False，不抛错）。"""
    try:
        _get_model()
        return True
    except EmbeddingUnavailable:
        return False


def embed_documents(texts: list[str]) -> list[list[float]]:
    """文档侧向量（入库用，不加指令前缀）。空输入返回空列表，不触发加载。"""
    if not texts:
        return []
    model = _get_model()
    vecs = model.encode(texts, normalize_embeddings=True, convert_to_numpy=True)
    return [v.tolist() for v in vecs]


def embed_query(text: str) -> list[float]:
    """查询侧向量（检索用，加 bge 检索指令前缀）。"""
    model = _get_model()
    vec = model.encode(
        _QUERY_INSTRUCTION + (text or ""),
        normalize_embeddings=True,
        convert_to_numpy=True,
    )
    return vec.tolist()
