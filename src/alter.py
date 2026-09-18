"""
alter.py — Webhook 告警发送模块

职责:
  - 组装告警消息（时间 + 资源 + 当前值 + 阈值 + 现场快照 + AI 建议）
  - POST 到企业微信/钉钉/飞书 Webhook
"""
import requests


def log_alter(url, system_time, resource, current_value, threshold, advice=None, diag=None):
    if not url:
        print("未设置 webhook url，跳过告警")
        return

    message = f"时间: {system_time}\n资源: {resource}\n当前值: {current_value}%\n阈值: {threshold}%"

    if diag:
        message += f"\n\n{diag}"

    if advice:
        message += f"\n\n【AI 建议】\n{advice}"

    data = {"msgtype": "text", "text": {"content": message}}
    try:
        r = requests.post(url, json=data, timeout=10)
        print("告警成功" if r.status_code == 200 else f"告警失败: {r.status_code}")
    except Exception as e:
        print(f"告警异常: {e}")