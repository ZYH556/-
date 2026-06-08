"""M4-D 数据清洗纯函数（docs/04 §6.1）：去重 / 标准化 / 术语统一 / 质量过滤。

**引擎无关的纯函数**——`clean_one` / `clean_batch` 不依赖 pyspark/pandas/settings，可在 Spark UDF、
pandas apply、纯 Python 三种 runner 中复用（见 batch.py 三级降级）。无外部依赖即永不降级，是批清洗的
确定性内核；执行引擎只决定并行度，不改变清洗语义。
"""
from __future__ import annotations

import hashlib
import re

# 术语标准化词典（docs §6.1 示例：英文缩写 → 中文统一术语）。可按领域扩充。
TERM_MAP = {
    "SVM": "支持向量机",
    "CNN": "卷积神经网络",
    "RNN": "循环神经网络",
    "NLP": "自然语言处理",
    "LLM": "大语言模型",
}

_WS_RE = re.compile(r"\s+")
_TAG_RE = re.compile(r"<[^>]+>")
_CTRL_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f]")


def normalize_text(text: str) -> str:
    """统一为 UTF-8 干净文本：去 HTML 标签（bs4 优先、缺库回退正则）、去控制字符、合并空白。"""
    if not text:
        return ""
    try:  # bs4 已装（data extra），更稳地剥 HTML；缺库回退正则
        from bs4 import BeautifulSoup

        text = BeautifulSoup(text, "html.parser").get_text(separator=" ")
    except Exception:
        text = _TAG_RE.sub(" ", text)
    text = _CTRL_RE.sub("", text)
    return _WS_RE.sub(" ", text).strip()


def normalize_terms(text: str) -> str:
    """术语标准化：按词典把英文缩写替换为统一中文术语（词边界匹配，避免误伤子串）。"""
    for src, dst in TERM_MAP.items():
        text = re.sub(rf"\b{re.escape(src)}\b", dst, text)
    return text


def content_hash(text: str) -> str:
    """去重键：归一化文本的 sha1 前 16 位。

    简化版——精确 hash 去重（同文判重）。docs §6.1 的 SimHash/MinHash 近似去重（捕获改写/片段重复）
    需额外指纹库，留待；当前精确去重已覆盖「同文档重传」主场景。
    """
    return hashlib.sha1(text.encode("utf-8")).hexdigest()[:16]


def is_quality(text: str, *, min_len: int = 30) -> bool:
    """质量过滤：过短即丢（docs §6.1）。乱码/广告分类器留待，先用长度门槛兜住噪声。"""
    return len(text) >= min_len


def clean_one(doc: dict, *, min_len: int = 30) -> dict | None:
    """清洗单条文档（纯函数）：规范化 + 术语统一 + 质量过滤 + 打 content_hash。

    不合格（过短）返回 None。保留原 doc 其余字段（doc_id/source/tenant_id 等），只覆盖 content 并加 hash。
    """
    content = normalize_terms(normalize_text(doc.get("content", "")))
    if not is_quality(content, min_len=min_len):
        return None
    return {**doc, "content": content, "content_hash": content_hash(content)}


def clean_batch(docs: list[dict], *, min_len: int = 30) -> list[dict]:
    """纯 Python 批清洗：clean_one + 按 content_hash 去重。batch.py 三级 runner 的最终兜底。"""
    out: list[dict] = []
    seen: set[str] = set()
    for d in docs:
        c = clean_one(d, min_len=min_len)
        if c is None:
            continue
        h = c["content_hash"]
        if h in seen:
            continue
        seen.add(h)
        out.append(c)
    return out
