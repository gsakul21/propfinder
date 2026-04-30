"""Shared timestamped logger for worker scripts."""
import sys
import time
from datetime import datetime


def log(prefix: str, msg: str) -> None:
    ts = datetime.now().strftime("%H:%M:%S")
    print(f"{ts}  [{prefix}] {msg}", flush=True)


def elapsed(start: float) -> str:
    """Human-readable duration from a time.time() start value."""
    secs = int(time.time() - start)
    if secs < 60:
        return f"{secs}s"
    m, s = divmod(secs, 60)
    return f"{m}m{s:02d}s"
