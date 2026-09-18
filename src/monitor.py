"""
monitor.py — 监控程序主入口

职责:
  - 主循环：采集 CPU/内存/磁盘/Swap/IO/网络
  - 暴露 Prometheus 指标（8000）和健康检查（8001）
  - 写 MySQL
  - 阈值告警：场景化快照 + AI 分析 + Webhook（异步）
"""
import time
import threading
import socket
import os
import psutil

import AI
from history import get_history
from alter import log_alter
from mysql_config import insert_data
from diagnose import collect_snapshot, warmup
from Prometheus_config import (
    cpu_use_gauge, mem_use_gauge, disk_use_gauge,
    swap_use_gauge,
    disk_read_gauge, disk_write_gauge,
    net_send_gauge, net_recv_gauge,
    port_num, start_health_server_async
)
from load_config import load_config

""""""
# ========== K8s 环境下读宿主机 /proc ==========
if os.getenv('HOST_PROC'):
    psutil.PROCFS_PATH = os.getenv('HOST_PROC')
    print(f"[K8s] 已切换 psutil 读取路径为: {os.getenv('HOST_PROC')}")


def get_host_info():
    """获取主机名和 IP，兼容本地 Windows 和 K8s 容器"""
    hostname = os.getenv('NODE_NAME') or socket.gethostname()
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(('8.8.8.8', 80))
        ip = s.getsockname()[0]
        s.close()
    except Exception:
        ip = '127.0.0.1'
    return hostname, ip


def send_alert_async(url, system_time, resource, current_value, threshold,
                     history_data, snapshot):
    """
    异步发送告警：在后台线程里调 AI + 发 Webhook
    避免阻塞主循环
    """
    def task():
        try:
            advice = AI.ai_monitor(resource, current_value, threshold,
                                   history_data, snapshot)
            log_alter(url, system_time, resource, current_value, threshold,
                      advice=advice, diag=snapshot)
        except Exception as e:
            print(f"[异步告警异常] {e}")

    threading.Thread(target=task, daemon=True).start()


HOSTNAME, IP = get_host_info()

cfg = load_config()
port_num(8000)
start_health_server_async(8001)
print("开始采集数据")
print(f"[配置] ALTER_INTERVAL = {cfg['ALTER_INTERVAL']}")

# 预热：让 CPU 和磁盘 IO 第一次采集就有值
warmup()

last_alert_time = {'cpu': 0.0, 'mem': 0.0, 'disk': 0.0}

# IO 速率两次采样求差
_prev_disk_io = None
_prev_net_io = None
_prev_io_time = None

while True:
    system_time = time.strftime('%Y-%m-%d %H:%M:%S')

    # ========== 采集（CPU 改为非阻塞）==========
    cpu = psutil.cpu_percent(interval=None)
    mem = psutil.virtual_memory().percent
    disk = psutil.disk_usage(cfg['DISK_PATH']).percent
    swap = psutil.swap_memory().percent

    now = time.time()
    disk_io = psutil.disk_io_counters()
    net_io = psutil.net_io_counters()

    if _prev_disk_io and _prev_io_time:
        interval = now - _prev_io_time
        if interval > 0:
            disk_read = (disk_io.read_bytes - _prev_disk_io.read_bytes) / 1024 / 1024 / interval
            disk_write = (disk_io.write_bytes - _prev_disk_io.write_bytes) / 1024 / 1024 / interval
            net_send = (net_io.bytes_sent - _prev_net_io.bytes_sent) / 1024 / 1024 / interval
            net_recv = (net_io.bytes_recv - _prev_net_io.bytes_recv) / 1024 / 1024 / interval
        else:
            disk_read = disk_write = net_send = net_recv = 0.0
    else:
        disk_read = disk_write = net_send = net_recv = 0.0

    _prev_disk_io = disk_io
    _prev_net_io = net_io
    _prev_io_time = now

    # ========== 暴露给 Prometheus ==========
    cpu_use_gauge.set(cpu)
    mem_use_gauge.set(mem)
    disk_use_gauge.set(disk)
    swap_use_gauge.set(swap)
    disk_read_gauge.set(disk_read)
    disk_write_gauge.set(disk_write)
    net_send_gauge.set(net_send)
    net_recv_gauge.set(net_recv)

    # ========== 写入 MySQL ==========
    if cfg.get('cursor'):
        data = {
            'timestamp': system_time,
            'cpu_use': cpu,
            'mem_use': mem,
            'disk_use': disk,
            'swap_use': swap,
            'disk_read': round(disk_read, 2),
            'disk_write': round(disk_write, 2),
            'net_send': round(net_send, 2),
            'net_recv': round(net_recv, 2),
        }
        try:
            insert_data(cfg['cursor'], cfg['conn'], data)
        except Exception as e:
            print(f"数据库写入失败,{e}")

    # ========== 告警逻辑（异步）==========
    current_time = time.time()

    if cpu >= cfg['CPU_MAXUSE'] and (current_time - last_alert_time['cpu']) >= cfg['ALTER_INTERVAL']:
        print(f"触发 CPU 告警: 当前 {cpu}%，阈值 {cfg['CPU_MAXUSE']}%")
        history_data = get_history(cfg.get('cursor'), 'cpu_use')
        snapshot = collect_snapshot('CPU')
        send_alert_async(cfg.get('URL'), system_time, f'CPU@{HOSTNAME}({IP})',
                         cpu, cfg['CPU_MAXUSE'], history_data, snapshot)
        last_alert_time['cpu'] = current_time

    if mem >= cfg['MEMORY_MAXUSE'] and (current_time - last_alert_time['mem']) >= cfg['ALTER_INTERVAL']:
        print(f"触发 内存 告警: 当前 {mem}%，阈值 {cfg['MEMORY_MAXUSE']}%")
        history_data = get_history(cfg.get('cursor'), 'mem_use')
        snapshot = collect_snapshot('内存')
        send_alert_async(cfg.get('URL'), system_time, f'内存@{HOSTNAME}({IP})',
                         mem, cfg['MEMORY_MAXUSE'], history_data, snapshot)
        last_alert_time['mem'] = current_time

    if disk >= cfg['DISK_MAXUSE'] and (current_time - last_alert_time['disk']) >= cfg['ALTER_INTERVAL']:
        print(f"触发 磁盘 告警: 当前 {disk}%，阈值 {cfg['DISK_MAXUSE']}%")
        history_data = get_history(cfg.get('cursor'), 'disk_use')
        snapshot = collect_snapshot('磁盘')
        send_alert_async(cfg.get('URL'), system_time, f'磁盘@{HOSTNAME}({IP})',
                         disk, cfg['DISK_MAXUSE'], history_data, snapshot)
        last_alert_time['disk'] = current_time

    # ========== 控制台输出 ==========
    print(
        f"────────────────────────────────────────────────────────\n"
        f"  {system_time}   节点: {HOSTNAME}  ({IP})\n"
        f"  CPU : {cpu:>6.1f}%   (阈值 {cfg['CPU_MAXUSE']}%)    "
        f"内存: {mem:>6.1f}%   (阈值 {cfg['MEMORY_MAXUSE']}%)    "
        f"磁盘: {disk:>6.1f}%   (阈值 {cfg['DISK_MAXUSE']}%)\n"
        f"  Swap: {swap:>6.1f}%   "
        f"磁盘IO:  读 {disk_read:>5.1f} / 写 {disk_write:>5.1f} MB/s   "
        f"网络:  发 {net_send:>5.1f} / 收 {net_recv:>5.1f} MB/s"
    )

    time.sleep(cfg['INTERVAL'])