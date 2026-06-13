"""B 站视频真实搜索（wbi 签名公开接口）。

红线：只取元数据（标题/bvid/作者/时长/简介），metadata_only +
embed_or_redirect_only，绝不下载转存内容。降级铁律：风控/网络/解析
任何失败返回 None，上层回落静态候选模板——搜索永远不能搞挂 discover。
"""

from __future__ import annotations

import hashlib
import logging
import re
import time
import urllib.parse

import httpx
from pydantic import BaseModel

logger = logging.getLogger(__name__)

_MIXIN_TAB = [
    46, 47, 18, 2, 53, 8, 23, 32, 15, 50, 10, 31, 58, 3, 45, 35, 27, 43, 5, 49,
    33, 9, 42, 19, 29, 28, 14, 39, 12, 38, 41, 13, 37, 48, 7, 16, 24, 55, 40,
    61, 26, 17, 0, 1, 60, 51, 30, 4, 22, 25, 54, 21, 56, 59, 6, 63, 57, 62, 11,
    36, 20, 34, 44, 52,
]
_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/126.0 Safari/537.36"
)
_EM_TAG = re.compile(r"</?em[^>]*>")

WBI_TTL_S = 3600.0
CACHE_TTL_S = 3600.0
RATE_WINDOW_S = 60.0
RATE_MAX_CALLS = 10


class BiliVideo(BaseModel):
    title: str
    bvid: str
    author: str = ""
    duration_minutes: int = 10
    description: str = ""


def mixin_key(img_key: str, sub_key: str) -> str:
    raw = img_key + sub_key
    return "".join(raw[i] for i in _MIXIN_TAB)[:32]


def sign_params(params: dict, key: str, *, now: float | None = None) -> dict:
    signed = {**params, "wts": int(now if now is not None else time.time())}
    cleaned = {
        k: "".join(ch for ch in str(v) if ch not in "!'()*")
        for k, v in sorted(signed.items())
    }
    query = urllib.parse.urlencode(cleaned)
    signed["w_rid"] = hashlib.md5((query + key).encode()).hexdigest()
    return signed


def parse_duration_minutes(raw: str) -> int:
    parts = [p for p in str(raw).split(":") if p.strip().isdigit()]
    if not parts:
        return 10
    seconds = 0
    for part in parts:
        seconds = seconds * 60 + int(part)
    # 向上取整：预计时长宁多勿少
    return max(1, -(-seconds // 60))


def parse_search_payload(payload: dict, limit: int) -> list[BiliVideo]:
    if payload.get("code") != 0:
        raise ValueError(f"bili code {payload.get('code')}")
    results = (payload.get("data") or {}).get("result") or []
    videos: list[BiliVideo] = []
    for item in results:
        bvid = str(item.get("bvid") or "").strip()
        title = _EM_TAG.sub("", str(item.get("title") or "")).strip()
        if not bvid or not title:
            continue
        videos.append(
            BiliVideo(
                title=title,
                bvid=bvid,
                author=str(item.get("author") or ""),
                duration_minutes=parse_duration_minutes(item.get("duration") or ""),
                description=str(item.get("description") or "")[:160],
            )
        )
        if len(videos) >= limit:
            break
    return videos


class BiliSearchClient:
    """惰性 httpx 客户端 + wbi key 缓存 + 关键词结果缓存 + 滑窗限频。"""

    def __init__(self, *, timeout_s: float = 6.0) -> None:
        self._timeout_s = timeout_s
        self._client: httpx.AsyncClient | None = None
        self._wbi_key: str = ""
        self._wbi_fetched_at: float = 0.0
        self._cache: dict[str, tuple[float, list[BiliVideo]]] = {}
        self._call_times: list[float] = []

    async def search_videos(self, keyword: str, *, limit: int = 3) -> list[BiliVideo] | None:
        keyword = keyword.strip()
        if not keyword:
            return None
        cached = self._cache.get(keyword)
        if cached and time.time() - cached[0] < CACHE_TTL_S:
            return cached[1][:limit]
        if not self._rate_allow():
            logger.info("bili search rate limited, fallback static")
            return None
        try:
            client = await self._ensure_client()
            key = await self._ensure_wbi_key(client)
            params = sign_params(
                {"search_type": "video", "keyword": keyword, "page": 1, "page_size": 20},
                key,
            )
            resp = await client.get(
                "https://api.bilibili.com/x/web-interface/search/type", params=params
            )
            videos = parse_search_payload(resp.json(), limit=max(limit, 5))
            self._cache[keyword] = (time.time(), videos)
            return videos[:limit]
        except Exception as exc:
            logger.info("bili search degraded: %s", exc)
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
                headers={"User-Agent": _UA, "Referer": "https://www.bilibili.com/"},
                timeout=self._timeout_s,
                follow_redirects=True,
                trust_env=False,  # 本机死代理：绝不读环境代理变量
            )
            await self._client.get("https://www.bilibili.com/")  # 取 buvid cookie
        return self._client

    async def _ensure_wbi_key(self, client: httpx.AsyncClient) -> str:
        if self._wbi_key and time.time() - self._wbi_fetched_at < WBI_TTL_S:
            return self._wbi_key
        nav = (await client.get("https://api.bilibili.com/x/web-interface/nav")).json()
        wbi = (nav.get("data") or {}).get("wbi_img") or {}
        img_key = str(wbi.get("img_url", "")).rsplit("/", 1)[-1].split(".")[0]
        sub_key = str(wbi.get("sub_url", "")).rsplit("/", 1)[-1].split(".")[0]
        if not img_key or not sub_key:
            raise ValueError("wbi keys unavailable")
        self._wbi_key = mixin_key(img_key, sub_key)
        self._wbi_fetched_at = time.time()
        return self._wbi_key


_client: BiliSearchClient | None = None


def get_bili_client() -> BiliSearchClient:
    global _client
    if _client is None:
        _client = BiliSearchClient()
    return _client


def reset_bili_client_for_tests() -> None:
    global _client
    _client = None
