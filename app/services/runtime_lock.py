from __future__ import annotations

import atexit
import logging
import os
from contextlib import suppress
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

_lock_handle = None
_lock_path: Optional[Path] = None


def acquire_runtime_lock(lock_path: str | os.PathLike[str] = "runtime/waifu_bot.lock") -> bool:
    """
    Prevent accidental double-starts of the same bot copy.

    Current version is designed to run as a single process.
    """
    global _lock_handle, _lock_path

    if _lock_handle is not None:
        return True

    path = Path(lock_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    handle = path.open("a+", encoding="utf-8")

    try:
        if os.name == "nt":
            import msvcrt

            handle.seek(0)
            handle.write(str(os.getpid()))
            handle.flush()
            handle.seek(0)
            msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
        else:
            import fcntl

            fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
    except Exception:
        with suppress(Exception):
            handle.close()
        logger.exception(
            "Another bot instance is already running. "
            "Use a single process for this version."
        )
        return False

    handle.seek(0)
    handle.truncate(0)
    handle.write(str(os.getpid()))
    handle.flush()

    _lock_handle = handle
    _lock_path = path
    atexit.register(release_runtime_lock)
    logger.info("Runtime lock acquired: %s", path)
    return True


def release_runtime_lock() -> None:
    global _lock_handle, _lock_path

    handle = _lock_handle
    if handle is None:
        return

    try:
        if os.name == "nt":
            import msvcrt

            handle.seek(0)
            with suppress(Exception):
                msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
        else:
            import fcntl

            with suppress(Exception):
                fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
    finally:
        with suppress(Exception):
            handle.close()
        logger.info("Runtime lock released%s", f" ({_lock_path})" if _lock_path else "")
        _lock_handle = None
        _lock_path = None
