"""Kafka 消费者进程：拉 knowledge.changes 增量事件 → ingest_document 入库（M4-C）。

用法（项目根，需 docker compose 起 kafka + 后端 enable_kafka=true 投递事件）：
    NO_PROXY='*' PYTHONPATH=src .venv/Scripts/python.exe scripts/jobs/data/kafka_consumer.py
broker 不可用时启动即报错退出（不影响后端主进程；后端 enable_kafka 上传会自动降级同步链路）。
"""
from __future__ import annotations

import asyncio
import logging

from reflexlearn.data_engineering.kafka_io import run_consumer

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")


if __name__ == "__main__":
    asyncio.run(run_consumer())
