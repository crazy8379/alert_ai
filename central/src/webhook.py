"""
webhook.py — 处理 Alertmanager 告警
"""
from dedup import is_in_cooldown, mark_cooldown
from node_client import get_snapshots
from prompt import build_prompt
from ai import analyze
from notifier import push_wecom


VALID_SCENARIOS = {'cpu', 'memory', 'disk'}


def process_alerts(data):
    """处理一批告警"""
    alerts = data.get('alerts', [])
    print(f"[webhook] 收到 {len(alerts)} 条告警")

    for alert in alerts:
        try:
            handle_one(alert)
        except Exception as e:
            print(f"[error] 处理告警失败: {e}")


def handle_one(alert):
    labels = alert.get('labels', {})
    alertname = labels.get('alertname', '')
    instance = labels.get('instance', '')
    scenario = labels.get('scenario', '')

    print(f"[alert] {alertname} | {instance} | scenario={scenario}")

    # 1. 校验场景
    if scenario not in VALID_SCENARIOS:
        print(f"[skip] 未知场景: {scenario}")
        return

    # 2. 去重
    fingerprint = alert.get('fingerprint', '')
    if is_in_cooldown(fingerprint):
        print(f"[dedup] 冷却中，跳过: {fingerprint}")
        return

    # 3. 拉 Agent 快照
    node_ip = instance.split(':')[0]
    snapshots = get_snapshots(node_ip, scenario, n=5)
    print(f"[node] 拉到 {len(snapshots)} 条快照")

    # 4. 组装 prompt
    prompt = build_prompt(scenario, alert, snapshots)

    # 5. 调 AI
    advice = analyze(prompt)

    # 6. 推企微
    push_wecom(alert, advice)

    # 7. 标记冷却
    mark_cooldown(fingerprint)