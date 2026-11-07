"""config.py — 全局配置（模块级单例）"""
import os
from dotenv import load_dotenv


load_dotenv()


class Settings:
    def __init__(self):
        # Prometheus
        self.PROM_URL = os.getenv('PROM_URL', 'http://prometheus:9090').rstrip('/')
        self.PROM_TIMEOUT = int(os.getenv('PROM_TIMEOUT', '10'))

        # DeepSeek
        self.API_KEY = os.getenv('API_KEY', '')
        self.API_URL = os.getenv('API_URL', 'https://api.deepseek.com/v1').rstrip('/')
        self.MODEL_NAME = os.getenv('MODEL_NAME', 'deepseek-chat')
        self.AI_TIMEOUT = int(os.getenv('AI_TIMEOUT', '30'))
        self.AI_MAX_TOKENS = int(os.getenv('AI_MAX_TOKENS', '2048'))
        self.AI_TEMPERATURE = float(os.getenv('AI_TEMPERATURE', '0.3'))

        # 企业微信
        self.WECOM_URL = os.getenv('WECOM_URL', '')

        # 服务
        self.WEBHOOK_PORT = int(os.getenv('WEBHOOK_PORT', '8080'))

        # 两段式通知并发
        self.NOTIFY_WORKERS = int(os.getenv('NOTIFY_WORKERS', '4'))
        self.ANALYSIS_WORKERS = int(os.getenv('ANALYSIS_WORKERS', '2'))

        # 快照
        # CPU/内存使用非均匀时间点，单位为秒前
        raw_offsets = os.getenv(
            'SNAPSHOT_CPU_MEM_OFFSETS',
            '600,300,180,60,30,0',
        )
        self.SNAPSHOT_CPU_MEM_OFFSETS = tuple(
            sorted(
                {int(item.strip()) for item in raw_offsets.split(',') if item.strip()},
                reverse=True,
            )
        )
        # 磁盘使用均匀窗口
        self.SNAPSHOT_DELAY = int(os.getenv('SNAPSHOT_DELAY', '30'))
        self.SNAPSHOT_DISK_N = int(os.getenv('SNAPSHOT_DISK_N', '7'))
        self.SNAPSHOT_DISK_STEP = int(os.getenv('SNAPSHOT_DISK_STEP', '600'))


settings = Settings()