"""models.py — 告警数据模型"""
from dataclasses import dataclass


@dataclass
class Alert:
    status: str = ''
    alertname: str = ''
    instance: str = ''
    scenario: str = ''
    severity: str = ''
    summary: str = ''
    fingerprint: str = ''

    @classmethod
    def from_raw(cls, raw: dict) -> 'Alert':
        labels = raw.get('labels') or {}
        annotations = raw.get('annotations') or {}
        return cls(
            status=raw.get('status') or '',
            alertname=labels.get('alertname') or '',
            instance=labels.get('instance') or '',
            scenario=(labels.get('scenario') or '').lower(),
            severity=labels.get('severity') or '',
            summary=annotations.get('summary') or '',
            fingerprint=raw.get('fingerprint') or '',
        )