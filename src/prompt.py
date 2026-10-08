"""prompt.py — 三场景 prompt 模板"""
from models import Alert


def _format_snapshots(snapshots: list[dict]) -> str:
    if not snapshots:
        return '快照不可用'
    lines = []
    for i, snap in enumerate(snapshots, 1):
        lines.append(f"--- 第 {i} 次 ({snap.get('timestamp', '')}) ---")
        lines.append(snap.get('content', ''))
        lines.append('')
    return '\n'.join(lines)


def build_prompt(scenario: str, alert: Alert, snapshots: list[dict], context: str = "") -> str:
    builder = _BUILDERS.get(scenario)
    return builder(alert, snapshots, context) if builder else ''


def _header(alert: Alert) -> str:
    return (
        f'- 节点: {alert.instance}\n'
        f'- 严重度: {alert.severity}\n'
        f'- 摘要: {alert.summary}\n'
    )


def _build_cpu_prompt(alert: Alert, snapshots: list[dict], context: str) -> str:
    return f"""你是资深 Linux 系统运维专家，正在处理一条 CPU 告警。

【历史相似处理方案（向量检索）】
{context or '无历史相似案例。'}

【告警信息】
{_header(alert)}
【CPU 快照序列（最近 {len(snapshots)} 次）】
{_format_snapshots(snapshots)}

【你的任务（严格按此顺序输出）】

**一、紧急程度**
一句话判断：需要立即处理 / 需要关注 / 可观察。给出依据。

**二、趋势与预测**
判断是"持续高负载"还是"瞬时抖动"；结合 Load 和 wa 判断是计算瓶颈还是 IO 瓶颈。

**三、最可能的原因（1~2 个）**
结合 Top CPU 进程的演变趋势，指出主要贡献者。

**四、排查命令**
按顺序编号，每个命令用代码块包裹，命令后一句话说明目的。

**五、处置建议**
- 临时缓解：1~2 条
- 长期解决：1~2 条

【输出要求】
- 用中文，Markdown 格式
- 严格使用上述五个标题
- 总长度 500 字以内
"""


def _build_memory_prompt(alert: Alert, snapshots: list[dict], context: str) -> str:
    return f"""你是资深 Linux 系统运维专家，正在处理一条内存告警。

【历史相似处理方案（向量检索）】
{context or '无历史相似案例。'}

【告警信息】
{_header(alert)}
【内存快照序列（最近 {len(snapshots)} 次）】
{_format_snapshots(snapshots)}

【你的任务（严格按此顺序输出）】

**一、紧急程度**
一句话判断。

**二、趋势与预测**
判断是"缓慢泄漏（持续上升）"还是"短期波动"。结合 Swap 判断是真实内存不足还是文件缓存。

**三、最可能的原因（1~2 个）**
结合 Top 内存进程的演变趋势。

**四、排查命令**
按顺序编号，每个命令用代码块包裹。

**五、处置建议**
- 临时缓解：1~2 条
- 长期解决：1~2 条

【输出要求】
- 用中文，Markdown 格式
- 严格使用上述五个标题
- 总长度 500 字以内
"""


def _build_disk_prompt(alert: Alert, snapshots: list[dict], context: str) -> str:
    return f"""你是资深 Linux 系统运维专家，正在处理一条磁盘告警。

【历史相似处理方案（向量检索）】
{context or '无历史相似案例。'}

【告警信息】
{_header(alert)}
【磁盘快照序列（最近 {len(snapshots)} 次）】
{_format_snapshots(snapshots)}

【你的任务（严格按此顺序输出）】

**一、紧急程度**
一句话判断。

**二、趋势与预测**
⚠️ 必做：根据历史数据估算增长率（%/小时），预测多久达到 100% 满盘。
若数据不足，说明"数据不足以预测"。

**三、最可能的原因（1~2 个）**
结合分区使用率、IOPS、%util 判断。IOPS 高吞吐低 → 小文件；吞吐高 IOPS 低 → 大文件。

**四、排查命令**
按顺序编号，每个命令用代码块包裹。

**五、处置建议**
- 临时缓解：1~2 条
- 长期解决：1~2 条

【输出要求】
- 用中文，Markdown 格式
- 严格使用上述五个标题
- 优先保证"紧急程度"和"趋势预测"完整
- 总长度 500 字以内
"""


_BUILDERS = {
    'cpu': _build_cpu_prompt,
    'memory': _build_memory_prompt,
    'disk': _build_disk_prompt,
}