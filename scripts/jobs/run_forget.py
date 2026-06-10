"""离线经验遗忘作业入口。

真实删除由 `ENABLE_FORGETTING=true` 显式开启；默认空跑，避免误删。
"""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone

from reflexlearn.common.config import get_settings
from reflexlearn.memory.forgetting import run_forgetting_job

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger(__name__)


async def main() -> None:
    settings = get_settings()
    try:
        from reflexlearn.common.db import get_qdrant

        qdrant = get_qdrant()
    except Exception as exc:
        logger.info("forgetting qdrant unavailable: %s", exc)
        qdrant = None

    deleted = await run_forgetting_job(
        qdrant=qdrant,
        settings=settings,
        now_iso=datetime.now(timezone.utc).isoformat(),
    )
    logger.info("forgetting job finished deleted=%s enabled=%s", deleted, settings.enable_forgetting)


if __name__ == "__main__":
    asyncio.run(main())
