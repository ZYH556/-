from __future__ import annotations

from reflexlearn.data_engineering.chunking import _split_paragraphs, chunk_sections, chunk_text
from reflexlearn.data_engineering.parsing import Section


def test_split_aggregates_short_paragraphs():
    """短段落聚合进同一块（不超过 max_chars）。"""
    out = _split_paragraphs("a\n\nb\n\nc", max_chars=500, overlap=80)
    assert out == ["a\n\nb\n\nc"]


def test_split_long_paragraph_sliding_window():
    """超长单段按字符滑窗切，每片不超过 max_chars。"""
    out = _split_paragraphs("x" * 1200, max_chars=500, overlap=80)
    assert len(out) >= 3
    assert all(len(o) <= 500 for o in out)


def test_chunk_sections_respects_boundary():
    """跨 section 不合并（保留文档结构边界），heading 随块带出。"""
    chunks = chunk_sections([Section("H1", "aaa"), Section("H2", "bbb")])
    assert len(chunks) == 2
    assert chunks[0].heading == "H1" and chunks[1].heading == "H2"


def test_chunk_idx_sequential():
    chunks = chunk_sections([Section("", "a"), Section("", "b"), Section("", "c")])
    assert [c.idx for c in chunks] == [0, 1, 2]


def test_chunk_carries_heading():
    chunks = chunk_sections([Section("第1章", "内容内容内容")])
    assert chunks and chunks[0].heading == "第1章"


def test_chunk_text_single_section():
    chunks = chunk_text("hello world")
    assert len(chunks) == 1
    assert chunks[0].heading == ""
    assert chunks[0].text == "hello world"


def test_chunk_empty_yields_nothing():
    assert chunk_sections([Section("", "")]) == []
    assert chunk_sections([]) == []
