"""结构感知分块：在 section 边界内按段落聚合到 max_chars，超长单段字符滑窗（带 overlap）。

承接 parsing 的 Section：同一 heading 下的文本聚合成块、heading 随块带出，跨 section 不合并
（保留文档结构语义）。段落聚合算法与 scripts/ingest_knowledge._chunk_markdown 一致，避免双份实现漂移。
"""
from __future__ import annotations

from dataclasses import dataclass

from reflexlearn.data_engineering.parsing import Section


@dataclass
class Chunk:
    idx: int
    heading: str
    text: str


def _split_paragraphs(text: str, max_chars: int, overlap: int) -> list[str]:
    """按段落聚合：相邻段落拼到 max_chars 上限；超长单段按字符滑窗切（带 overlap）。"""
    paras = [p.strip() for p in (text or "").split("\n\n") if p.strip()]
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


def chunk_sections(sections: list[Section], max_chars: int = 500, overlap: int = 80) -> list[Chunk]:
    """逐 section 分块，全局连续编号 idx，heading 随块带出（contextual / 前端染色用）。"""
    chunks: list[Chunk] = []
    for sec in sections:
        for piece in _split_paragraphs(sec.text, max_chars, overlap):
            chunks.append(Chunk(idx=len(chunks), heading=sec.heading, text=piece))
    return chunks


def chunk_text(text: str, max_chars: int = 500, overlap: int = 80) -> list[Chunk]:
    """纯文本入口（无结构信息），等价于单 section 分块。"""
    return chunk_sections([Section("", text)], max_chars, overlap)
