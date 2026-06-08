"""M4-D MinIO 原始存储（docs/04 §2 原始存储层）：上传原始文档 / 批清洗中间结果的对象存储。

minio 7.2 已装（import 不降级，只连接降级）。所有 I/O try/except 吞错——无 MinIO 服务时批处理
跳过、上传链路不受影响（降级铁律）。client 由调用方注入，单测注入内存假 client，绝不真连。
"""
from __future__ import annotations

import json
import logging
from io import BytesIO

from reflexlearn.common.config import get_settings

logger = logging.getLogger(__name__)


class MinioUnavailable(RuntimeError):
    pass


def make_minio_client():
    """构造 Minio 客户端（惰性，不立即连接）。minio 缺库时抛 MinioUnavailable。"""
    try:
        from minio import Minio
    except Exception as e:  # 未装 storage extra
        raise MinioUnavailable(f"minio import failed: {e}")
    s = get_settings()
    return Minio(
        s.minio_endpoint,
        access_key=s.minio_access_key,
        secret_key=s.minio_secret_key,
        secure=s.minio_secure,
    )


def put_bytes(client, bucket: str, key: str, raw: bytes) -> bool:
    """存字节对象（自动建桶）。失败降级返回 False。"""
    try:
        if not client.bucket_exists(bucket):
            client.make_bucket(bucket)
        client.put_object(bucket, key, BytesIO(raw), length=len(raw))
        return True
    except Exception as e:
        logger.warning("minio put degraded (%s/%s): %s", bucket, key, e)
        return False


def get_bytes(client, bucket: str, key: str) -> bytes | None:
    """取字节对象。不存在 / 失败返回 None。"""
    try:
        resp = client.get_object(bucket, key)
        return resp.read()
    except Exception as e:
        logger.info("minio get degraded (%s/%s): %s", bucket, key, e)
        return None


def put_documents(client, bucket: str, key: str, docs: list[dict]) -> bool:
    """以 JSON Lines 存文档集合（每行一条，UTF-8）。"""
    raw = "\n".join(json.dumps(d, ensure_ascii=False) for d in docs).encode("utf-8")
    return put_bytes(client, bucket, key, raw)


def get_documents(client, bucket: str, key: str) -> list[dict]:
    """读 JSON Lines 文档集合。不存在 / 失败返回空列表。"""
    raw = get_bytes(client, bucket, key)
    if not raw:
        return []
    out: list[dict] = []
    for line in raw.decode("utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            out.append(json.loads(line))
        except Exception:
            continue  # 跳过坏行，不中断
    return out
