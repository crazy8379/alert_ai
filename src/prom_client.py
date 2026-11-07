"""
prom_client.py — 从 Prometheus 拉场景快照

对外接口：
  get_snapshots(instance, scenario, offsets=None)
  → [{'timestamp': '...', 'content': '多行文本'}, ...]

instance 形如 '10.0.0.1:9100'（node_exporter 的 target）
"""
import time
import requests

from config import settings


# ============ 底层查询 ============

def _query(promql: str, t: float | None = None) -> list[dict]:
    params = {'query': promql}
    if t is not None:
        params['time'] = t
    try:
        r = requests.get(
            f'{settings.PROM_URL}/api/v1/query',
            params=params,
            timeout=settings.PROM_TIMEOUT,
        )
        r.raise_for_status()
        return r.json().get('data', {}).get('result', []) or []
    except Exception as e:
        print(f'[prom] 查询失败: {e} | {promql[:100]}')
        return []


def _scalar(promql: str, t: float | None = None, default: float = 0.0) -> float:
    res = _query(promql, t)
    if not res:
        return default
    try:
        return float(res[0]['value'][1])
    except (KeyError, IndexError, ValueError, TypeError):
        return default


def _first_value(res: list[dict]) -> float | None:
    try:
        return float(res[0]['value'][1])
    except (KeyError, IndexError, ValueError, TypeError):
        return None


def _has_process_exporter(instance: str, t: float) -> bool:
    """探测 process_exporter 是否在采这个实例"""
    res = _query(
        f'count(namedprocess_namegroup_cpu_seconds_total{{instance="{instance}"}})',
        t,
    )
    return bool(res) and _scalar(
        f'count(namedprocess_namegroup_cpu_seconds_total{{instance="{instance}"}})',
        t,
    ) > 0


# ============ 场景 1：CPU ============

def _cpu_snapshot(instance: str, t: float) -> str:
    lines = ['【CPU 现场】']

    # 每核使用率
    percpu = _query(
        f'100 - (avg by (cpu) (rate(node_cpu_seconds_total'
        f'{{instance="{instance}",mode="idle"}}[1m])) * 100)',
        t,
    )
    if percpu:
        try:
            percpu.sort(key=lambda x: int(x['metric'].get('cpu', 0)))
        except ValueError:
            pass
        vals = ', '.join(f"{float(p['value'][1]):.0f}%" for p in percpu)
        lines.append(f'每核使用率: {vals}')

    # 各模式占比
    user = _scalar(f'avg(rate(node_cpu_seconds_total{{instance="{instance}",mode="user"}}[1m])) * 100', t)
    sy = _scalar(f'avg(rate(node_cpu_seconds_total{{instance="{instance}",mode="system"}}[1m])) * 100', t)
    wa = _scalar(f'avg(rate(node_cpu_seconds_total{{instance="{instance}",mode="iowait"}}[1m])) * 100', t)
    idle = _scalar(f'avg(rate(node_cpu_seconds_total{{instance="{instance}",mode="idle"}}[1m])) * 100', t)
    lines.append(f'用户态 us: {user:.1f}%  内核态 sy: {sy:.1f}%  '
                 f'IO等待 wa: {wa:.1f}%  空闲 id: {idle:.1f}%')
    if wa > 20:
        lines.append('⚠️ wa 高，可能不是 CPU 问题，是 IO 瓶颈')

    # Load
    l1 = _scalar(f'node_load1{{instance="{instance}"}}', t)
    l5 = _scalar(f'node_load5{{instance="{instance}"}}', t)
    l15 = _scalar(f'node_load15{{instance="{instance}"}}', t)
    cpu_count = _scalar(
        f'count(node_cpu_seconds_total{{instance="{instance}",mode="idle"}})',
        t, default=1,
    ) or 1
    load_pct = l1 / cpu_count * 100
    lines.append(f'Load: {l1:.2f} / {l5:.2f} / {l15:.2f}  '
                 f'(CPU核数 {cpu_count:.0f}，负载率 {load_pct:.0f}%)')

    # 上下文切换 / 中断
    ctx = _scalar(f'rate(node_context_switches_total{{instance="{instance}"}}[1m])', t)
    intr = _scalar(f'rate(node_intr_total{{instance="{instance}"}}[1m])', t)
    lines.append(f'上下文切换: {ctx:.0f}/s  中断: {intr:.0f}/s')

    # Top 5 CPU 进程（依赖 process_exporter）
    top = _query(
        f'topk(5, rate(namedprocess_namegroup_cpu_seconds_total'
        f'{{instance="{instance}"}}[1m]))',
        t,
    )
    if top:
        lines.append('')
        lines.append('Top 5 CPU 进程:')
        for p in top:
            name = p['metric'].get('groupname', '?')
            val = float(p['value'][1]) * 100
            lines.append(f'  {name}  CPU {val:.1f}%')

    return '\n'.join(lines)


# ============ 场景 2：内存 ============

def _mem_snapshot(instance: str, t: float) -> str:
    lines = ['【内存 现场】']

    total = _scalar(f'node_memory_MemTotal_bytes{{instance="{instance}"}}', t)
    avail = _scalar(f'node_memory_MemAvailable_bytes{{instance="{instance}"}}', t)
    if total <= 0:
        lines.append('[无法获取内存总量，node_exporter 可能未暴露该指标]')
        return '\n'.join(lines)

    used = total - avail
    used_pct = used / total * 100
    avail_pct = avail / total * 100
    lines.append(f'总计: {total / 1024**3:.1f} GB  '
                 f'已用: {used / 1024**3:.1f} GB ({used_pct:.1f}%)  '
                 f'可用: {avail / 1024**3:.1f} GB')

    cached = _scalar(f'node_memory_Cached_bytes{{instance="{instance}"}}', t)
    buffers = _scalar(f'node_memory_Buffers_bytes{{instance="{instance}"}}', t)
    if cached or buffers:
        lines.append(f'缓存: {cached / 1024**3:.1f} GB  缓冲: {buffers / 1024**3:.1f} GB')

    if used_pct > 80 and avail_pct > 30:
        lines.append(f'⚠️ used {used_pct:.0f}% 但 available 仍有 {avail_pct:.0f}%，'
                     f'可能是文件缓存，非真实压力')

    # Swap
    sw_total = _scalar(f'node_memory_SwapTotal_bytes{{instance="{instance}"}}', t)
    sw_free = _scalar(f'node_memory_SwapFree_bytes{{instance="{instance}"}}', t)
    if sw_total > 0:
        sw_used = sw_total - sw_free
        sw_pct = sw_used / sw_total * 100
        lines.append(f'Swap: {sw_used / 1024**3:.1f} GB / {sw_total / 1024**3:.1f} GB ({sw_pct:.1f}%)')
        if sw_pct > 10:
            lines.append('⚠️ Swap 使用中，说明真实内存不足')
    else:
        lines.append('Swap: 未启用')

    # Top 5 内存进程
    top = _query(
        f'topk(5, namedprocess_namegroup_memory_bytes'
        f'{{instance="{instance}",memtype="resident"}})',
        t,
    )
    if top:
        lines.append('')
        lines.append('Top 5 内存进程:')
        for p in top:
            name = p['metric'].get('groupname', '?')
            val = float(p['value'][1]) / 1024**3
            lines.append(f'  {name}  MEM {val:.2f} GB')

    return '\n'.join(lines)


# ============ 场景 3：磁盘 ============

_FS_FILTER = 'fstype!~"tmpfs|overlay|squashfs|autofs"'


def _disk_snapshot(instance: str, t: float) -> str:
    lines = ['【磁盘 现场】']

    # 吞吐 / IOPS / 繁忙度
    read_mb = _scalar(f'sum(rate(node_disk_read_bytes_total{{instance="{instance}"}}[1m])) / 1024 / 1024', t)
    write_mb = _scalar(f'sum(rate(node_disk_written_bytes_total{{instance="{instance}"}}[1m])) / 1024 / 1024', t)
    iops_r = _scalar(f'sum(rate(node_disk_reads_completed_total{{instance="{instance}"}}[1m]))', t)
    iops_w = _scalar(f'sum(rate(node_disk_writes_completed_total{{instance="{instance}"}}[1m]))', t)
    util = _scalar(f'max(rate(node_disk_io_time_seconds_total{{instance="{instance}"}}[1m])) * 100', t)

    lines.append(f'吞吐: 读 {read_mb:.2f} / 写 {write_mb:.2f} MB/s')
    lines.append(f'IOPS: 读 {iops_r:.0f} / 写 {iops_w:.0f}')
    lines.append(f'繁忙度 %util: {util:.1f}%')

    if util > 80:
        lines.append('⚠️ 磁盘繁忙度 > 80%，磁盘是真瓶颈')
    if iops_w > 500 and write_mb < 5:
        lines.append('⚠️ IOPS 高但吞吐低，是海量小文件写入场景')
    if write_mb > 50:
        lines.append('⚠️ 吞吐高，是大文件顺序写入场景')

    # 分区使用率（只列 > 50% 的）
    parts = _query(
        f'(1 - node_filesystem_avail_bytes{{instance="{instance}",{_FS_FILTER}}}'
        f' / node_filesystem_size_bytes{{instance="{instance}",{_FS_FILTER}}}) * 100',
        t,
    )
    hot = []
    for p in parts:
        try:
            pct = float(p['value'][1])
        except (KeyError, ValueError):
            continue
        if pct > 50:
            hot.append((p['metric'].get('mountpoint', '?'), pct))

    if hot:
        lines.append('')
        lines.append('分区使用率 (>50%):')
        for mp, pct in hot[:5]:
            lines.append(f'  {mp} {pct:.0f}%')

    # inode
    inode_pct = _scalar(
        f'max((1 - node_filesystem_files_free{{instance="{instance}",{_FS_FILTER}}}'
        f' / node_filesystem_files{{instance="{instance}",{_FS_FILTER}}}) * 100)',
        t,
    )
    if inode_pct:
        lines.append('')
        lines.append(f'inode 使用率: {inode_pct:.1f}%')
        if inode_pct > 80:
            lines.append('⚠️ inode > 80%，可能是海量小文件')

    return '\n'.join(lines)


# ============ 通用附加信息：网络流量 ============

_NETWORK_FILTER = (
    'device!~"lo|veth.*|docker.*|br-.*|virbr.*|vnet.*|tap.*|cali.*|flannel.*"'
)


def _network_snapshot(instance: str, t: float) -> str:
    """所有场景默认附带网络吞吐，便于判断是否是流量型压力。"""
    rx_res = _query(
        f'sum(rate(node_network_receive_bytes_total'
        f'{{instance="{instance}",{_NETWORK_FILTER}}}[1m])) / 1024 / 1024',
        t,
    )
    tx_res = _query(
        f'sum(rate(node_network_transmit_bytes_total'
        f'{{instance="{instance}",{_NETWORK_FILTER}}}[1m])) / 1024 / 1024',
        t,
    )
    if not rx_res and not tx_res:
        return ''

    rx = _first_value(rx_res)
    tx = _first_value(tx_res)
    if rx is None and tx is None:
        return ''

    rx_text = f'{rx:.2f}' if rx is not None else '未知'
    tx_text = f'{tx:.2f}' if tx is not None else '未知'
    lines = [
        '【网络流量】',
        f'接收: {rx_text} MB/s  发送: {tx_text} MB/s',
    ]
    if rx is not None and tx is not None:
        lines.append(f'合计: {rx + tx:.2f} MB/s')
    return '\n'.join(lines)


# ============ 对外接口 ============

_SCENARIO_FUNCS = {
    'cpu': _cpu_snapshot,
    'memory': _mem_snapshot,
    'disk': _disk_snapshot,
}

VALID_SCENARIOS = set(_SCENARIO_FUNCS.keys())


def get_snapshots(
    instance: str,
    scenario: str,
    n: int | None = None,
    step: int | None = None,
    offsets: tuple[int, ...] | None = None,
) -> list[dict]:
    func = _SCENARIO_FUNCS.get(scenario)
    if not func:
        return []

    now = time.time()

    if offsets:
        # 显式时间点：offsets 是“多少秒前”，按从旧到新查询。
        query_times = [
            now - offset
            for offset in sorted({int(item) for item in offsets}, reverse=True)
        ]
    elif scenario in ('cpu', 'memory') and n is None and step is None:
        # CPU/内存默认：10 分钟前、5 分钟前、3 分钟前、1 分钟前、30 秒前和当前。
        query_times = [
            now - offset
            for offset in settings.SNAPSHOT_CPU_MEM_OFFSETS
        ]
    else:
        # 兼容显式传入 n/step 的调用，以及磁盘的均匀窗口。
        if scenario == 'disk':
            n = n or settings.SNAPSHOT_DISK_N
            step = step or settings.SNAPSHOT_DISK_STEP
        else:
            n = n or len(settings.SNAPSHOT_CPU_MEM_OFFSETS)
            step = step or 60

        end = now - settings.SNAPSHOT_DELAY
        query_times = [
            end - (n - 1 - i) * step
            for i in range(n)
        ]

    snapshots = []
    for t in query_times:
        ts = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(t))
        try:
            content = func(instance, t)
        except Exception as e:
            content = f'[采集异常: {e}]'

        # 网络吞吐是所有场景的公共上下文，默认附带
        network = _network_snapshot(instance, t)
        if network:
            content = f'{content}\n\n{network}'

        snapshots.append({'timestamp': ts, 'content': content})

    return snapshots