from __future__ import annotations

import logging

from reflexlearn.common import db

logger = logging.getLogger(__name__)


def safe_qdrant():
    try:
        return db.get_qdrant()
    except Exception as exc:
        logger.info("qdrant unavailable: %s", exc)
        return None


async def safe_pg_pool():
    try:
        return await db.get_pg_pool()
    except Exception as exc:
        logger.info("pg unavailable: %s", exc)
        return None


async def safe_redis():
    try:
        return await db.get_redis()
    except Exception as exc:
        logger.info("redis unavailable: %s", exc)
        return None


def safe_neo4j():
    try:
        return db.get_neo4j()
    except Exception as exc:
        logger.info("neo4j unavailable: %s", exc)
        return None
