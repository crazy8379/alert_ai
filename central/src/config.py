"""
config.py — 中心服务配置
"""
import os
from dotenv import load_dotenv

load_dotenv()


def get_config():
    return {
        'API_KEY': os.getenv('API_KEY', ''),
        'API_URL': os.getenv('API_URL', 'https://api.deepseek.com/v1'),
        'MODEL_NAME': os.getenv('MODEL_NAME', 'deepseek-chat'),
        'WECOM_URL': os.getenv('WECOM_URL', ''),
        'COOLDOWN': int(os.getenv('COOLDOWN', '300')),   # 冷却窗口 5 分钟
        'WEBHOOK_PORT': int(os.getenv('WEBHOOK_PORT', '8080')),
    }