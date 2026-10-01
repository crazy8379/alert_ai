"""dedup.py — 指纹去重（进程内，单 worker 使用）"""
import threading
import time

from config import settings

_lock = threading.Lock()
_cache: dict[str, float] = {}


def is_in_cooldown(fingerprint: str) -> bool:
    if not fingerprint:
        return False
    now = time.time()
    with _lock:
        last = _cache.get(fingerprint, 0)
        return now - last < settings.COOLDOWN


def mark_cooldown(fingerprint: str) -> None:
    if not fingerprint:
        return
    now = time.time()
    with _lock:
        _cache[fingerprint] = now
        expired = [k for k, v in _cache.items() if now - v >= settings.COOLDOWN]
        for k in expired:
            _cache.pop(k, None)