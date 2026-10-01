"""webhook.py — 处理 Alertmanager 告警的编排逻辑"""
from dedup import is_in_cooldown, mark_cooldown
from models import Alert
from prom_client import VALID_SCENARIOS, get_snapshots
from prompt import build_prompt
from ai import analyze
from notifier import push_wecom


def process_alerts(data: dict) -> None:
    alerts = data.get('alerts', []) or []
    print(f'[webhook] 收到 {len(alerts)} 条告警')

    for raw in alerts:
        try:
            handle_one(raw)
        except Exception as e:
            print(f'[error] 处理告警失败: {e}')


def handle_one(raw: dict) -> None:
    alert = Alert.from_raw(raw)
    print(f'[alert] {alert.alertname} | {alert.instance} | scenario={alert.scenario}')

    # 1. 场景校验
    if alert.scenario not in VALID_SCENARIOS:
        print(f'[skip] 未知场景: {alert.scenario}')
        return
    if not alert.instance:
        print('[skip] 缺少 instance')
        return

    # 2. 去重（只读，不写）
    if is_in_cooldown(alert.fingerprint):
        print(f'[dedup] 冷却中，跳过: {alert.fingerprint}')
        return

    # 3. 拉 Prometheus 快照
    snapshots = get_snapshots(alert.instance, alert.scenario)
    print(f'[prom] 拉到 {len(snapshots)} 个时间点')

    # 4. 组装 prompt
    prompt = build_prompt(alert.scenario, alert, snapshots)

    # 5. 调 AI
    advice = analyze(prompt)

    # 6. 推企微
    ok = push_wecom(alert, advice)

    # 7. 只有推送成功才标记冷却，失败可重试
    if ok:
        mark_cooldown(alert.fingerprint)
    else:
        print('[webhook] 推送失败，本次不标记冷却，下轮告警可重试')