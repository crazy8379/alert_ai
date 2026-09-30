"""
notifier.py — 推企业微信
"""
import os
import requests


def push_wecom(alert, advice):
    url = os.getenv('WECOM_URL')
    if not url:
        print("[notifier] 未配置 WECOM_URL")
        return

    labels = alert.get('labels', {})
    annotations = alert.get('annotations', {})

    message = (
        f"【{annotations.get('summary', '告警')}】\n"
        f"节点: {labels.get('instance', 'unknown')}\n"
        f"场景: {labels.get('scenario', 'unknown')}\n"
        f"严重度: {labels.get('severity', 'unknown')}\n"
    )
    if advice:
        message += f"\n【AI 建议】\n{advice}"

    try:
        requests.post(url, json={
            "msgtype": "text",
            "text": {"content": message}
        }, timeout=10)
        print("[notifier] 推送成功")
    except Exception as e:
        print(f"[notifier] 推送失败: {e}")