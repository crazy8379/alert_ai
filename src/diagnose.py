"""
diagnose.py — 场景化现场快照采集

职责:
  - CPU 告警：每核使用率 + us/sy/wa 分布 + Load + 上下文切换 + Top CPU 进程
  - 内存告警：内存详情 + Swap + Top 内存进程
  - 磁盘告警：吞吐 + IOPS + %util + 分区使用率
  - 全部基于 psutil，不依赖 top/iostat 等外部工具

注意: 依赖 monitor.py 已设置 psutil.PROCFS_PATH 指向 /host/proc
"""
import os
import time
import psutil


# ========== 进程 Top N ==========

def _top_procs_by_cpu(n=5):
    procs = []
    for p in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent']):
        try:
            info = p.info
            procs.append({
                'name': info.get('name') or f"pid{info['pid']}",
                'pid': info['pid'],
                'cpu': info.get('cpu_percent') or 0.0,
                'mem': info.get('memory_percent') or 0.0,
            })
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    procs.sort(key=lambda x: x['cpu'], reverse=True)
    return procs[:n]


def _top_procs_by_mem(n=5):
    procs = []
    for p in psutil.process_iter(['pid', 'name', 'memory_percent']):
        try:
            info = p.info
            procs.append({
                'name': info.get('name') or f"pid{info['pid']}",
                'pid': info['pid'],
                'mem': info.get('memory_percent') or 0.0,
            })
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    procs.sort(key=lambda x: x['mem'], reverse=True)
    return procs[:n]


# ========== 磁盘 IO 差值 ==========

_prev_disk_io = None
_prev_disk_time = None


def _collect_disk_detail():
    """每次调用时重新采样（sleep 1 秒做两次差值）"""
    result = {'iops_read': 0, 'iops_write': 0, 'util': 0, 'read_mb': 0, 'write_mb': 0}
    try:
        io1 = psutil.disk_io_counters()
        t1 = time.time()
        if io1 is None:
            return result

        time.sleep(1)   # 等 1 秒

        io2 = psutil.disk_io_counters()
        t2 = time.time()
        if io2 is None:
            return result

        interval = t2 - t1
        if interval > 0:
            result['iops_read'] = (io2.read_count - io1.read_count) / interval
            result['iops_write'] = (io2.write_count - io1.write_count) / interval
            result['read_mb'] = (io2.read_bytes - io1.read_bytes) / 1024 / 1024 / interval
            result['write_mb'] = (io2.write_bytes - io1.write_bytes) / 1024 / 1024 / interval
            if hasattr(io2, 'busy_time') and hasattr(io1, 'busy_time'):
                busy_ms = io2.busy_time - io1.busy_time
                result['util'] = min(busy_ms / (interval * 1000) * 100, 100)
    except Exception:
        pass
    return result


# ========== 三种场景快照 ==========

def snapshot_cpu():
    lines = ["【CPU 现场】"]
    try:
        percpu = psutil.cpu_percent(percpu=True, interval=None)
        lines.append(f"每核使用率: {', '.join(f'{c:.0f}%' for c in percpu)}")

        times = psutil.cpu_times_percent(interval=None)
        iowait = getattr(times, 'iowait', 0.0)
        lines.append(f"用户态 us: {times.user:.1f}%  内核态 sy: {times.system:.1f}%  "
                     f"IO等待 wa: {iowait:.1f}%  空闲 id: {times.idle:.1f}%")
        if iowait > 20:
            lines.append("⚠️ wa 高，可能不是 CPU 问题，是 IO 瓶颈")

        try:
            l1, l5, l15 = os.getloadavg()
            cpu_count = psutil.cpu_count() or 1
            load_pct = l1 / cpu_count * 100
            lines.append(f"Load: {l1:.2f} / {l5:.2f} / {l15:.2f}  "
                         f"(CPU核数 {cpu_count}，负载率 {load_pct:.0f}%)")
        except (AttributeError, OSError):
            pass

        stats = psutil.cpu_stats()
        lines.append(f"上下文切换: {stats.ctx_switches} 次  中断: {stats.interrupts} 次")
    except Exception as e:
        lines.append(f"[采集异常: {e}]")

    try:
        top = _top_procs_by_cpu(5)
        if top:
            lines.append("\nTop 5 CPU 进程:")
            for p in top:
                lines.append(f"  {p['name']}(pid {p['pid']})  CPU {p['cpu']:.1f}%  MEM {p['mem']:.1f}%")
    except Exception:
        pass

    return "\n".join(lines)


def snapshot_memory():
    lines = ["【内存 现场】"]
    try:
        mem = psutil.virtual_memory()
        lines.append(f"总计: {mem.total/1024**3:.1f} GB  "
                     f"已用: {mem.used/1024**3:.1f} GB ({mem.percent:.1f}%)  "
                     f"可用: {mem.available/1024**3:.1f} GB")
        cached = getattr(mem, 'cached', 0)
        buffers = getattr(mem, 'buffers', 0)
        if cached or buffers:
            lines.append(f"缓存: {cached/1024**3:.1f} GB  缓冲: {buffers/1024**3:.1f} GB")
        avail_pct = mem.available / mem.total * 100 if mem.total else 0
        if avail_pct > 20:
            lines.append(f"⚠️ available 还有 {avail_pct:.0f}%，可能是文件缓存占用，非真实压力")
    except Exception as e:
        lines.append(f"[采集异常: {e}]")

    try:
        swap = psutil.swap_memory()
        lines.append(f"Swap: {swap.used/1024**3:.1f} GB / {swap.total/1024**3:.1f} GB "
                     f"({swap.percent:.1f}%)")
        if swap.percent > 10:
            lines.append("⚠️ Swap 使用中，说明真实内存不足")
    except Exception:
        pass

    try:
        top = _top_procs_by_mem(5)
        if top:
            lines.append("\nTop 5 内存进程:")
            for p in top:
                lines.append(f"  {p['name']}(pid {p['pid']})  MEM {p['mem']:.1f}%")
    except Exception:
        pass

    return "\n".join(lines)


def snapshot_disk():
    lines = ["【磁盘 现场】"]
    try:
        d = _collect_disk_detail()
        lines.append(f"吞吐: 读 {d['read_mb']:.2f} / 写 {d['write_mb']:.2f} MB/s")
        lines.append(f"IOPS: 读 {d['iops_read']:.0f} / 写 {d['iops_write']:.0f}")
        lines.append(f"繁忙度 %util: {d['util']:.1f}%")
        if d['util'] > 80:
            lines.append("⚠️ 磁盘繁忙度 > 80%，磁盘是真瓶颈")
        if d['iops_write'] > 500 and d['write_mb'] < 5:
            lines.append("⚠️ IOPS 高但吞吐低，是海量小文件写入场景")
        if d['write_mb'] > 50:
            lines.append("⚠️ 吞吐高，是大文件顺序写入场景")
    except Exception as e:
        lines.append(f"[采集异常: {e}]")

    try:
        parts = []
        for part in psutil.disk_partitions(all=False):
            try:
                usage = psutil.disk_usage(part.mountpoint)
                if usage.percent > 50:
                    parts.append(f"{part.mountpoint} {usage.percent:.0f}% "
                                 f"({usage.used/1024**3:.0f}G/{usage.total/1024**3:.0f}G)")
            except (PermissionError, OSError):
                continue
        if parts:
            lines.append("\n分区使用率:")
            for p in parts[:5]:
                lines.append(f"  {p}")
    except Exception:
        pass

    return "\n".join(lines)


SNAPSHOT_FUNCS = {
    'CPU': snapshot_cpu,
    '内存': snapshot_memory,
    '磁盘': snapshot_disk,
}


def collect_snapshot(resource):
    """根据资源类型采集对应场景快照"""
    func = SNAPSHOT_FUNCS.get(resource)
    if not func:
        return f"[未知资源类型: {resource}]"
    try:
        return func()
    except Exception as e:
        return f"[快照采集异常: {e}]"


def warmup():
    """预热：让第一次采集就有值"""
    try:
        psutil.cpu_percent(interval=None)
        psutil.cpu_percent(percpu=True, interval=None)
        psutil.cpu_times_percent(interval=None)
    except Exception:
        pass

    # ← 新增：预热进程 CPU
    try:
        for _ in psutil.process_iter(['cpu_percent']):
            pass
    except Exception:
        pass

    try:
        _collect_disk_detail()
    except Exception:
        pass