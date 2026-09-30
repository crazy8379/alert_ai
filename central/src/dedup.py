"""
dedup.py — 指纹去重

职责:
  - 同一告警在冷却窗口内只处理一次
  - 冷却时间从环境变量 COOLDOWN 读取（默认 300 秒）
  - 内存存储（重启丢失，够用）
"""
import os
import time

COOLDOWN = int(os.getenv('COOLDOWN', '300'))

_cache = {}


def is_in_cooldown(fingerprint):
    """检查是否在冷却期"""
    if not fingerprint:
        return False
    last = _cache.get(fingerprint, 0)
    return (time.time() - last) < COOLDOWN


def mark_cooldown(fingerprint):
    """标记已处理"""
    if fingerprint:
        _cache[fingerprint] = time.time()