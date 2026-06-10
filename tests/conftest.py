import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


@pytest.fixture(autouse=True)
def _hermetic_guard(monkeypatch):
    """单元测试 hermetic 守卫：禁加载真实大模型（bge embedding + bge-reranker）、禁连真实外部库（qdrant）。

    - embedding/rerank：拦在 _get_model / _get_reranker，未显式 mock 的调用抛 *Unavailable，上层降级。
    - qdrant：拦 get_qdrant（三处绑定：db 给 rag.retrieval semantic/keyword 的函数内 import；manager / critic
      为顶层 import，须各自命名空间拦）。否则单测会连本机真实 qdrant，且 AsyncQdrantClient 单例
      跨 pytest-asyncio 事件循环会卡死。manager.recall / critic._persist_reflection 对 get_qdrant
      抛已 try/except 降级，故拦后 e2e 优雅退化为空召回 / 跳过写 / retrieve 退 mock，零回归。
    需要真实行为的测试自行 monkeypatch 覆盖（embed_query / _get_reranker / db.get_qdrant 等）。
    """
    import reflexlearn.common.db as db
    import reflexlearn.common.embedding as emb
    import reflexlearn.memory.manager as mgr
    import reflexlearn.orchestration.nodes.reflection.critic as critic
    import reflexlearn.rag.ranking.rerank as rr

    def _blocked_emb(*args, **kwargs):
        raise emb.EmbeddingUnavailable("real embedding model disabled in unit tests")

    def _blocked_rr(*args, **kwargs):
        raise rr.RerankerUnavailable("real reranker model disabled in unit tests")

    def _blocked_qdrant(*args, **kwargs):
        raise RuntimeError("real qdrant disabled in unit tests")

    monkeypatch.setattr(emb, "_get_model", _blocked_emb)
    monkeypatch.setattr(rr, "_get_reranker", _blocked_rr)
    monkeypatch.setattr(db, "get_qdrant", _blocked_qdrant)
    monkeypatch.setattr(mgr, "get_qdrant", _blocked_qdrant)
    monkeypatch.setattr(critic, "get_qdrant", _blocked_qdrant)
