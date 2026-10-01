"""notifier.py — 推企业微信"""
import requests

from config import settings
from models import Alert

# 企微 text 消息上限约 2048 字节（UTF-8）
_MAX_BYTES = 2000


def _truncate(msg: str, limit: int = _MAX_BYTES) -> str:
    b = msg.encode('utf-8')
    if len(b) <= limit:
        return msg
    return b[:limit].decode('utf-8', errors='ignore') + '\n...(已截断)'


def push_wecom(alert: Alert, advice: str | None) -> bool:
    if not settings.WECOM_URL:
        print('[notifier] 未配置 WECOM_URL')
        return False

    message = (
        f'【{alert.summary or "告警"}】\n'
        f'节点: {alert.instance}\n'
        f'场景: {alert.scenario}\n'
        f'严重度: {alert.severity}\n'
    )
    if advice:
        message += f'\n【AI 建议】\n{advice}'
    message = _truncate(message)

    try:
        resp = requests.post(
            settings.WECOM_URL,
            json={'msgtype': 'text', 'text': {'content': message}},
            timeout=10,
        )
        result = resp.json()
        if result.get('errcode') != 0:
            print(f'[notifier] 推送失败: {result}')
            return False
        print('[notifier] 推送成功')
        return True
    except Exception as e:
        print(f'[notifier] 推送异常: {e}')
        return False