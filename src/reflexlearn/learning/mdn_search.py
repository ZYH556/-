"""MDN Web Docs 官方文档真实搜索（公开 search API）。

针对 Web/前端学习概念（fetch/Promise/CSS Grid…）补充权威官方文档；
非 Web 概念（机器学习等）MDN 无结果 → 返回 None，上层回落静态候选，
形成天然的领域适配。红线同 B 站：metadata_only + 失败降级，绝不搞挂 discover。
"""

from __future__ import annotations

import logging
import time

import httpx
from pydantic import BaseModel

logger = logging.getLogger(__name__)

_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/126.0 Safari/537.36"
)
_MDN_BASE = "https://developer.mozilla.org"
_SEARCH_URL = "https://developer.mozilla.org/api/v1/search"

CACHE_TTL_S = 3600.0
RATE_WINDOW_S = 60.0
RATE_MAX_CALLS = 10
MIN_SCORE = 5.0  # 过滤低相关：Web 概念命中 score 多 >40，非 Web 概念返回空/低分

# MDN 只覆盖 Web/前端：领域门控，避免 ML 等非 Web 查询误配（如"入门"匹配到 Svelte 入门）
_WEB_KEYWORDS = (
    "javascript", "typescript", "css", "html", "web", "前端", "浏览器",
    "promise", "async", "await", "fetch", "react", "vue", "svelte",
    "angular", "网页", "样式", "布局", "闭包", "原型链", "es6", "事件循环", "ajax",
)


def is_web_topic(text: str) -> bool:
    low = text.lower()
    return any(kw in low for kw in _WEB_KEYWORDS)


class MdnDoc(BaseModel):
    title: str
    url: str
    summary: str = ""
    score: float = 0.0


def parse_mdn_payload(payload: dict, limit: int, min_score: float = MIN_SCORE) -> list[MdnDoc]:
    documents = payload.get("documents") or []
    docs: list[MdnDoc] = []
    for item in documents:
        score = float(item.get("score") or 0.0)
        url = str(item.get("mdn_url") or "").strip()
        title = str(item.get("title") or "").strip()
        if score < min_score or not url or not title:
            continue
        docs.append(
            MdnDoc(
                title=title,
                url=f"{_MDN_BASE}{url}" if url.startswith("/") else url,
                summary=str(item.get("summary") or "")[:160],
                score=score,
            )
        )
        if len(docs) >= limit:
            break
    return docs


class MdnSearchClient:
    """惰性 httpx 客户端 + 关键词缓存 + 滑窗限频；无签名/无 cookie，比 B 站简单。"""

    def __init__(self, *, timeout_s: float = 6.0) -> None:
        self._timeout_s = timeout_s
        self._client: httpx.AsyncClient | None = None
        self._cache: dict[str, tuple[float, list[MdnDoc]]] = {}
        self._call_times: list[float] = []

    async def search_docs(
        self, keyword: str, *, limit: int = 2, locale: str = "zh-CN"
    ) -> list[MdnDoc] | None:
        keyword = keyword.strip()
        if not keyword:
            return None
        cached = self._cache.get(keyword)
        if cached and time.time() - cached[0] < CACHE_TTL_S:
            return cached[1][:limit] or None
        if not self._rate_allow():
            logger.info("mdn search rate limited, fallback static")
            return None
        try:
            client = await self._ensure_client()
            resp = await client.get(_SEARCH_URL, params={"q": keyword, "locale": locale})
            docs = parse_mdn_payload(resp.json(), limit=max(limit, 5))
            self._cache[keyword] = (time.time(), docs)
            return docs[:limit] or None
        except Exception as exc:
            logger.info("mdn search degraded: %s", exc)
            return None

    def _rate_allow(self) -> bool:
        now = time.time()
        self._call_times = [t for t in self._call_times if now - t < RATE_WINDOW_S]
        if len(self._call_times) >= RATE_MAX_CALLS:
            return False
        self._call_times.append(now)
        return True

    async def _ensure_client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(
                headers={"User-Agent": _UA},
                timeout=self._timeout_s,
                follow_redirects=True,
                trust_env=False,  # 本机死代理：绝不读环境代理变量
            )
        return self._client


_client: MdnSearchClient | None = None


def get_mdn_client() -> MdnSearchClient:
    global _client
    if _client is None:
        from reflexlearn.common.config import get_settings

        _client = MdnSearchClient(timeout_s=get_settings().mdn_search_timeout_s)
    return _client


def reset_mdn_client_for_tests() -> None:
    global _client
    _client = None
