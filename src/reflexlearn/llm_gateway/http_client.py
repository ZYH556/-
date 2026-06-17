"""LLM 外呼的共享 httpx.AsyncClient（PERF-C 连接复用）。

每次 LLM 调用新建 AsyncClient 会重做 TCP+TLS 握手（docs/19 §1 因素②：+0.3–1s/次）。
模块级单例复用 keep-alive 连接池，省去握手。timeout 在创建时按 settings 设定（read/connect
分级，PERF-C）。生产单事件循环创建一次；单测每用例新循环，用 reset_async_client() 重置。

放独立模块避免 gateway↔streaming 循环导入（两者都从这里取 client）。
"""

from __future__ import annotations

_async_client = None


def get_async_client(settings):
    """取共享 AsyncClient（懒建、复用连接池）。timeout 沿用 PERF-C 的 read/connect 分级。"""
    global _async_client
    if _async_client is None:
        import httpx

        _async_client = httpx.AsyncClient(
            timeout=httpx.Timeout(
                settings.llm_request_timeout_s,
                connect=settings.llm_connect_timeout_s,
            )
        )
    return _async_client


def reset_async_client() -> None:
    """丢弃缓存 client（单测每用例新事件循环；不主动 close，替身无真实连接）。"""
    global _async_client
    _async_client = None


async def aclose_async_client() -> None:
    """优雅关停：关闭并丢弃共享 client（应用 lifespan 退出时调用）。"""
    global _async_client
    client = _async_client
    _async_client = None
    if client is not None:
        try:
            await client.aclose()
        except Exception:
            pass
