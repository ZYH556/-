#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/_lib.sh"

ensure_logs
cd_root
use_local_network
use_python_defaults

{
  log_header "check_bigdata"
  "$(python_cmd)" - <<'PY'
import asyncio
import io
import time
import uuid

from reflexlearn.common.config import get_settings


async def check_kafka(settings) -> None:
    from aiokafka import AIOKafkaConsumer, AIOKafkaProducer

    topic = f"reflexlearn.health.{uuid.uuid4().hex}"
    group_id = f"reflexlearn-health-{uuid.uuid4().hex}"
    payload = f"ping:{time.time()}".encode("utf-8")

    producer = AIOKafkaProducer(bootstrap_servers=settings.kafka_bootstrap_servers)
    await producer.start()
    try:
        await producer.send_and_wait(topic, payload)
    finally:
        await producer.stop()

    consumer = AIOKafkaConsumer(
        topic,
        bootstrap_servers=settings.kafka_bootstrap_servers,
        group_id=group_id,
        auto_offset_reset="earliest",
        enable_auto_commit=False,
    )
    await consumer.start()
    try:
        msg = await asyncio.wait_for(consumer.getone(), timeout=20)
        if msg.value != payload:
            raise RuntimeError("kafka health payload mismatch")
    finally:
        await consumer.stop()

    print(f"[OK] kafka produce/consume via {settings.kafka_bootstrap_servers}")


def check_minio(settings) -> None:
    from minio import Minio

    client = Minio(
        settings.minio_endpoint,
        access_key=settings.minio_access_key,
        secret_key=settings.minio_secret_key,
        secure=settings.minio_secure,
    )
    bucket = settings.minio_bucket
    if not client.bucket_exists(bucket):
        client.make_bucket(bucket)

    key = f"health/{uuid.uuid4().hex}.txt"
    payload = b"minio-health-ok"
    client.put_object(bucket, key, io.BytesIO(payload), length=len(payload))
    obj = client.get_object(bucket, key)
    try:
        data = obj.read()
    finally:
        obj.close()
        obj.release_conn()
    client.remove_object(bucket, key)

    if data != payload:
        raise RuntimeError("minio health payload mismatch")

    print(f"[OK] minio put/get/remove via {settings.minio_endpoint}/{bucket}")


async def main() -> None:
    settings = get_settings()
    check_minio(settings)
    await check_kafka(settings)


asyncio.run(main())
PY
} 2>&1 | tee -a "$LOG_DIR/check_bigdata.log"
