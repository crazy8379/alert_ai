"""webhook.py — 两段式告警处理：先发基础通知，再异步补发 AI 分析。"""
import atexit
from concurrent.futures import ThreadPoolExecutor

from ai import analyze
from config import settings
from models import Alert
from notifier import push_alert, push_analysis, push_raw
from prom_client import get_snapshots
from prompt import build_combined_prompt

_SCENARIO_ORDER = ('cpu', 'memory', 'disk')
_SCENARIO_KEYWORDS = (
    ('cpu', 'cpu'),
    ('mem', 'memory'),
    ('memory', 'memory'),
    ('disk', 'disk'),
)

# 基础通知和 AI 分析使用独立线程池，避免 AI 慢调用阻塞告警通知。
_NOTIFY_POOL = ThreadPoolExecutor(
    max_workers=settings.NOTIFY_WORKERS,
    thread_name_prefix='alert-notify',
)
_ANALYSIS_POOL = ThreadPoolExecutor(
    max_workers=settings.ANALYSIS_WORKERS,
    thread_name_prefix='alert-ai',
)

atexit.register(_NOTIFY_POOL.shutdown, wait=False)
atexit.register(_ANALYSIS_POOL.shutdown, wait=False)


def _extract_scenarios(labels: dict) -> set[str]:
    """遍历告警 labels，收集其中实际出现的指标场景。"""
    scenarios = set()
    for key, value in labels.items():
        if str(key).lower() == 'instance':
            continue
        text = f'{key} {value}'.lower()
        for keyword, scenario in _SCENARIO_KEYWORDS:
            if keyword in text:
                scenarios.add(scenario)
    return scenarios


def process_alerts(data: dict) -> int:
    """解析并提交告警任务，不在请求线程中执行网络或 AI 调用。"""
    alerts = data.get('alerts', []) or []
    print(f'[webhook] 收到 {len(alerts)} 条告警')

    accepted = 0
    for raw in alerts:
        try:
            if handle_one(raw):
                accepted += 1
        except Exception as e:
            print(f'[error] 提交告警失败: {e}')
    return accepted


def _push_raw_safe(alert: Alert) -> None:
    try:
        if not push_raw(alert):
            print(f'[notify] 告警转发失败: {alert.alertname}')
    except Exception as e:
        print(f'[notify] 告警转发异常: {e}')


def handle_one(raw: dict) -> bool:
    alert = Alert.from_raw(raw)
    labels = raw.get('labels') or {}
    scenarios = _extract_scenarios(labels)

    if not scenarios:
        # 非资源类告警（服务存活、外部探测等）不接 AI，但必须转发，避免 P0 告警被静默丢弃。
        print(f'[passthrough] 未匹配到 cpu/memory/disk，直接转发: {alert.alertname}')
        _NOTIFY_POOL.submit(_push_raw_safe, alert)
        return True

    if not alert.instance:
        print('[skip] 缺少 instance，无法采集指标')
        return False

    ordered_scenarios = [s for s in _SCENARIO_ORDER if s in scenarios]
    alert.scenario = ','.join(ordered_scenarios)
    print(f'[alert] {alert.alertname} | {alert.instance} | scenarios={alert.scenario}')

    _NOTIFY_POOL.submit(_send_base_then_analyze, alert, ordered_scenarios)
    return True


def _send_base_then_analyze(alert: Alert, scenarios: list[str]) -> None:
    """第一阶段：发送基础告警；成功后立即进入第二阶段分析。"""
    try:
        base_ok = push_alert(alert)
    except Exception as e:
        print(f'[notify] 基础告警异常: {e}')
        return

    if not base_ok:
        print('[notify] 基础告警发送失败')
        return

    print('[notify] 基础告警已发送，开始 AI 分析')

    try:
        _ANALYSIS_POOL.submit(_analyze_and_notify, alert, scenarios)
    except Exception as e:
        print(f'[ai] 提交分析任务失败: {e}')


def _analyze_and_notify(alert: Alert, scenarios: list[str]) -> None:
    """第二阶段：拉取指标、调用 AI，成功后补发分析版消息。"""
    try:
        snapshots = {
            scenario: get_snapshots(alert.instance, scenario)
            for scenario in scenarios
        }
        prompt = build_combined_prompt([alert], snapshots)
        advice = analyze(prompt)

        if not advice:
            print(f'[ai] 未生成分析结果，基础告警已发送: {alert.fingerprint}')
            return

        if not push_analysis(alert, advice):
            print(f'[notify] AI 分析补发失败: {alert.fingerprint}')
    except Exception as e:
        print(f'[ai] 分析链路异常，基础告警已发送: {e}')
