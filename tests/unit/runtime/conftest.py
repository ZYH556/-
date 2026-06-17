import pytest


@pytest.fixture(autouse=True)
def reset_shared_http_client():
    """网关共享 client 是模块级单例；runtime 测试每例重置，避免 monkeypatch 串扰。"""
    from reflexlearn.llm_gateway.http_client import reset_async_client

    reset_async_client()
    yield
    reset_async_client()
