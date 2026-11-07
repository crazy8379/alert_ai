"""notifier.py — 企业微信通知：基础告警和 AI 分析分两条发送。"""
import requests

from config import settings
from models import Alert

# 企微限制：text 2048 字节，markdown 4096 字节（UTF-8）
_MAX_TEXT_BYTES = 2000
_MAX_MARKDOWN_BYTES = 3900


def _truncate(msg: str, limit: int = _MAX_TEXT_BYTES) -> str:
    b = msg.encode('utf-8')
    if len(b) <= limit:
        return msg
    return b[:limit].decode('utf-8', errors='ignore') + '\n...(已截断)'


def _send(message: str, msgtype: str = 'text', limit: int | None = None) -> bool:
    if not settings.WECOM_URL:
        print('[notifier] 未配置 WECOM_URL')
        return False

    if msgtype == 'markdown':
        limit = limit or _MAX_MARKDOWN_BYTES
        payload = {'msgtype': 'markdown', 'markdown': {'content': _truncate(message, limit)}}
    else:
        limit = limit or _MAX_TEXT_BYTES
        payload = {'msgtype': 'text', 'text': {'content': _truncate(message, limit)}}

    try:
        resp = requests.post(
            settings.WECOM_URL,
            json=payload,
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


def _alert_head(alert: Alert) -> str:
    title = alert.summary or alert.alertname or '系统告警'
    lines = [
        title,
        f'节点: {alert.instance}',
        f'场景: {alert.scenario}',
        f'严重度: {alert.severity or "未设置"}',
        f'状态: {alert.status or "firing"}',
    ]
    if alert.fingerprint:
        lines.append(f'指纹: {alert.fingerprint}')
    return '\n'.join(lines)


def push_alert(alert: Alert) -> bool:
    """第一阶段：只发基础告警，不等待 AI。"""
    message = (
        f'【告警】{_alert_head(alert)}\n'
        f'AI 分析中，结果稍后补发。'
    )
    return _send(message)


def push_analysis(alert: Alert, advice: str) -> bool:
    """第二阶段：补发 AI 分析结果（markdown 渲染加粗和代码块）。"""
    message = (
        f'**【AI 分析】{(alert.summary or alert.alertname or "系统告警")}**\n'
        f'> 节点：{alert.instance}\n'
        f'> 场景：{alert.scenario}\n'
        f'> 严重度：{alert.severity or "未设置"}\n'
        f'> 状态：{alert.status or "firing"}\n\n'
        f'{advice}'
    )
    return _send(message, msgtype='markdown')


def push_raw(alert: Alert) -> bool:
    """未接入 AI 的告警：只转发事实，不查指标、不调模型。"""
    title = '【恢复】' if alert.status == 'resolved' else '【告警】'
    lines = [f'{title}{alert.summary or alert.alertname or "系统告警"}']

    if alert.instance:
        lines.append(f'实例: {alert.instance}')
    lines.append(f'告警: {alert.alertname or "未知"}')
    lines.append(f'严重度: {alert.severity or "未设置"}')
    lines.append(f'状态: {alert.status or "firing"}')
    if alert.description:
        lines.append(f'详情: {alert.description}')

    if alert.status != 'resolved':
        lines.append('')
        lines.append('该类型未接入 AI 诊断，请人工处理。')
    return _send('\n'.join(lines))
