"""
prompt.py — 三场景 prompt 模板
"""


def _format_snapshots(snapshots):
    """把快照序列格式化成文本"""
    if not snapshots:
        return "快照不可用"

    lines = []
    for i, snap in enumerate(snapshots, 1):
        ts = snap.get('timestamp', '')
        content = snap.get('content', '')
        lines.append(f"--- 第 {i} 次 ({ts}) ---")
        lines.append(content)
        lines.append("")
    return "\n".join(lines)


def build_prompt(scenario, alert, snapshots):
    """按场景组装 prompt"""
    if scenario == 'cpu':
        return _build_cpu_prompt(alert, snapshots)
    elif scenario == 'memory':
        return _build_memory_prompt(alert, snapshots)
    elif scenario == 'disk':
        return _build_disk_prompt(alert, snapshots)
    return ""


def _build_cpu_prompt(alert, snapshots):
    labels = alert.get('labels', {})
    annotations = alert.get('annotations', {})
    snap_str = _format_snapshots(snapshots)

    return f"""
你是资深 Linux 系统运维专家，正在处理一条 CPU 告警。

【告警信息】
- 节点: {labels.get('instance', '')}
- 严重度: {labels.get('severity', '')}
- 摘要: {annotations.get('summary', '')}

【CPU 快照序列（来自 Agent，最近 5 次）】
{snap_str}

【你的任务（严格按此顺序输出）】

**一、紧急程度**
用一句话判断：需要立即处理 / 需要关注 / 可观察。给出依据。

**二、趋势与预测**
判断是"持续高负载"还是"瞬时抖动"，结合 Load 和 wa 判断是计算瓶颈还是 IO 瓶颈。

**三、最可能的原因（1~2 个）**
结合 Top CPU 进程的演变趋势，指出谁是主要贡献者。

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


def _build_memory_prompt(alert, snapshots):
    labels = alert.get('labels', {})
    annotations = alert.get('annotations', {})
    snap_str = _format_snapshots(snapshots)

    return f"""
你是资深 Linux 系统运维专家，正在处理一条内存告警。

【告警信息】
- 节点: {labels.get('instance', '')}
- 严重度: {labels.get('severity', '')}
- 摘要: {annotations.get('summary', '')}

【内存快照序列（来自 Agent，最近 5 次）】
{snap_str}

【你的任务（严格按此顺序输出）】

**一、紧急程度**
用一句话判断。

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


def _build_disk_prompt(alert, snapshots):
    labels = alert.get('labels', {})
    annotations = alert.get('annotations', {})
    snap_str = _format_snapshots(snapshots)

    return f"""
你是资深 Linux 系统运维专家，正在处理一条磁盘告警。

【告警信息】
- 节点: {labels.get('instance', '')}
- 严重度: {labels.get('severity', '')}
- 摘要: {annotations.get('summary', '')}

【磁盘快照序列（来自 Agent，最近 5 次）】
{snap_str}

【你的任务（严格按此顺序输出）】

**一、紧急程度**
用一句话判断。

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