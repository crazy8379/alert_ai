"""
load_config.py — 配置加载
"""
import os
import platform
from dotenv import load_dotenv

load_dotenv()

DEFAULT_DISK = 'C:\\' if platform.system() == 'Windows' else '/'


def load_config():
    return {
        'DISK_PATH': os.getenv('DISK_PATH', DEFAULT_DISK),
        'HOST_PROC': os.getenv('HOST_PROC'),
        'HEALTH_PORT': int(os.getenv('HEALTH_PORT', '8001')),
        'SNAPSHOT_PORT': int(os.getenv('SNAPSHOT_PORT', '9101')),
    }