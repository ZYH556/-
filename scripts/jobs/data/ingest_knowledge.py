"""知识入库：读 data/knowledge/*.md → 分块 → embed → upsert 到 qdrant knowledge_chunks。

用法（项目根，需已装 embedding 依赖且模型可用）：
    PYTHONPATH=src .venv/Scripts/python.exe scripts/jobs/data/ingest_knowledge.py
先决条件：先跑 scripts/init/init_qdrant.py 建好 collection。
"""
from __future__ import annotations

import asyncio
from pathlib import Path
from uuid import NAMESPACE_URL, uuid5

from qdrant_client.models import PointStruct

from reflexlearn.common.config import get_settings
from reflexlearn.common.db import get_qdrant
from reflexlearn.common.embedding import embed_documents

KNOWLEDGE_DIR = Path(__file__).resolve().parents[3] / "data" / "knowledge"


def _chunk_markdown(text: str, max_chars: int = 500, overlap: int = 80) -> list[str]:
    """按段落聚合分块：相邻段落拼到 max_chars 上限；超长单段按字符滑窗切（带 overlap）。"""
    paras = [p.strip() for p in text.split("\n\n") if p.strip()]
    chunks: list[str] = []
    cur = ""
    for p in paras:
        if len(cur) + len(p) + 2 <= max_chars:
            cur = f"{cur}\n\n{p}" if cur else p
        else:
            if cur:
                chunks.append(cur)
                cur = ""
            if len(p) <= max_chars:
                cur = p
            else:
                step = max(1, max_chars - overlap)
                for i in range(0, len(p), step):
                    chunks.append(p[i : i + max_chars])
    if cur:
        chunks.append(cur)
    return chunks


def _point_id(source: str, idx: int) -> str:
    """确定性 UUID（同 source+idx 恒等），保证重跑幂等覆盖而非重复堆积。"""
    return str(uuid5(NAMESPACE_URL, f"{source}::{idx}"))


async def main() -> None:
    settings = get_settings()
    files = sorted(KNOWLEDGE_DIR.glob("*.md"))
    if not files:
        print(f"[WARN] 未找到知识文档：{KNOWLEDGE_DIR}")
        return

    contents: list[str] = []
    metas: list[dict] = []
    for f in files:
        text = f.read_text(encoding="utf-8")
        title = text.lstrip().split("\n", 1)[0].lstrip("# ").strip() or f.stem
        for idx, chunk in enumerate(_chunk_markdown(text)):
            contents.append(chunk)
            metas.append({"source": f.name, "title": title, "idx": idx})

    print(f"[..] 对 {len(files)} 个文件、{len(contents)} 个分块做向量化 ...")
    vectors = embed_documents(contents)

    points = [
        PointStruct(
            id=_point_id(m["source"], m["idx"]),
            vector=vec,
            payload={
                "content": c,
                "source": m["source"],
                "title": m["title"],
                "tenant_id": "default",
                "visibility": "public",
                "course_id": "ml-101",
                "source_trust": 0.9,
            },
        )
        for c, m, vec in zip(contents, metas, vectors)
    ]

    qdrant = get_qdrant()
    try:
        await qdrant.upsert(collection_name=settings.knowledge_collection, points=points)
        print(f"[OK] 已写入 {len(points)} 个分块到 '{settings.knowledge_collection}'")
    finally:
        await qdrant.close()


if __name__ == "__main__":
    asyncio.run(main())
