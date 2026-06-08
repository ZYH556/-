from __future__ import annotations

import logging
import os
from pathlib import Path


def configure_logging(*, force: bool = False) -> None:
    log_file = os.getenv("REFLEXLEARN_LOG_FILE", "logs/api.log")
    path = Path(log_file)
    if path.parent:
        path.parent.mkdir(parents=True, exist_ok=True)

    root = logging.getLogger()
    formatter = logging.Formatter(
        "%(asctime)s %(levelname)s [%(name)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    level = os.getenv("REFLEXLEARN_LOG_LEVEL", "INFO").upper()

    if force:
        file_handler = logging.FileHandler(path, encoding="utf-8")
        file_handler.setFormatter(formatter)
        stream_handler = logging.StreamHandler()
        stream_handler.setFormatter(formatter)
        logging.basicConfig(level=level, handlers=[file_handler, stream_handler], force=True)
        return

    root.setLevel(level)
    if not root.handlers:
        stream_handler = logging.StreamHandler()
        stream_handler.setFormatter(formatter)
        root.addHandler(stream_handler)

    target = str(path.resolve())
    for handler in root.handlers:
        if isinstance(handler, logging.FileHandler):
            if str(Path(handler.baseFilename).resolve()) == target:
                return

    file_handler = logging.FileHandler(path, encoding="utf-8")
    file_handler.setFormatter(formatter)
    root.addHandler(file_handler)
