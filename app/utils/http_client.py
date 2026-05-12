"""共享 HTTP 客户端配置 — 关闭 SSL 验证以兼容企业网络"""

import httpx


def get_http_client() -> httpx.Client:
    return httpx.Client(verify=False, timeout=60)


def get_async_http_client() -> httpx.AsyncClient:
    return httpx.AsyncClient(verify=False, timeout=60)
