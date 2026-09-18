import time
import psutil
import AI
import socket
import os

from history import get_history
from alter import log_alter
from mysql_config import insert_data
from Prometheus_config import (
    cpu_use_gauge, mem_use_gauge, disk_use_gauge,
    swap_use_gauge,
    disk_read_gauge, disk_write_gauge,
    net_send_gauge, net_recv_gauge,
    port_num, start_health_server_async
)
from load_config import load_config

# K8s 里读宿主机的 /proc，本地 Windows 没这个环境变量，跳过
if os.getenv('HOST_PROC'):
    psutil.PROCFS_PATH = os.getenv('HOST_PROC')
    print(f"[K8s] 已切换 psutil 读取路径为: {os.getenv('HOST_PROC')}")

def get_host_info():
    """获取主机名和 IP，兼容本地 Windows 和 K8s 容器"""
    # K8s 里优先用 NODE_NAME 环境变量（后面阶段 7 会用到）
    hostname = os.getenv('NODE_NAME') or socket.gethostname()
    try:
        # 获取本机 IP（不会真的发包，只是拿路由表信息）
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(('8.8.8.8', 80))
        ip = s.getsockname()[0]
        s.close()
    except Exception:
        ip = '127.0.0.1'
    return hostname, ip

HOSTNAME, IP = get_host_info()

cfg=load_config()
port_num(8000)
start_health_server_async(8001)   # ← 新增：启动健康检查端口
print("开始采集数据")
print(f"[配置] ALTER_INTERVAL = {cfg['ALTER_INTERVAL']}")

last_alert_time={'cpu':0.0,'mem':0.0,'disk':0.0}
# IO 速率需要两次采样求差，这里保存上一轮的值
_prev_disk_io = None
_prev_net_io = None
_prev_io_time = None
while True:
    system_time = time.strftime('%Y-%m-%d %H:%M:%S')
    cpu=psutil.cpu_percent(interval=1)
    mem=psutil.virtual_memory().percent
    disk=psutil.disk_usage(cfg['DISK_PATH']).percent

    # ========== 新增：Load / Swap ==========
    swap = psutil.swap_memory().percent

    # ========== 新增：磁盘 IO / 网络 IO 速率 ==========
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

    cpu_use_gauge.set(cpu)
    mem_use_gauge.set(mem)
    disk_use_gauge.set(disk)

    swap_use_gauge.set(swap)
    disk_read_gauge.set(disk_read)
    disk_write_gauge.set(disk_write)
    net_send_gauge.set(net_send)
    net_recv_gauge.set(net_recv)

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
            insert_data(cfg['cursor'],cfg['conn'],data)
        except Exception as e:
            print(f"数据库写入失败,{e}")


    # 获取当前时间戳（用于告警节流）
    current_time = time.time()

    # ========== 告警逻辑 ==========

    if cpu >= cfg['CPU_MAXUSE'] and (current_time - last_alert_time['cpu']) >= cfg['ALTER_INTERVAL']:
        print(f"触发 CPU 告警: 当前 {cpu}%，阈值 {cfg['CPU_MAXUSE']}%")
        history_data = get_history(cfg.get('cursor'), 'cpu_use')
        advice = AI.ai_monitor('CPU', cpu, cfg['CPU_MAXUSE'], history_data)
        log_alter(cfg.get('URL'), system_time, f'CPU@{HOSTNAME}({IP})', cpu, cfg['CPU_MAXUSE'], advice)
        last_alert_time['cpu'] = time.time()

    if mem >= cfg['MEMORY_MAXUSE'] and (current_time - last_alert_time['mem']) >= cfg['ALTER_INTERVAL']:
        print(f"触发 内存 告警: 当前 {mem}%，阈值 {cfg['MEMORY_MAXUSE']}%")
        history_data = get_history(cfg.get('cursor'), 'mem_use')  # 数据库字段是 mem_use
        advice = AI.ai_monitor('内存', mem, cfg['MEMORY_MAXUSE'], history_data)
        log_alter(cfg.get('URL'), system_time, f'内存@{HOSTNAME}({IP})', mem, cfg['MEMORY_MAXUSE'], advice)
        last_alert_time['mem'] = time.time()

    if disk >= cfg['DISK_MAXUSE'] and (current_time - last_alert_time['disk']) >= cfg['ALTER_INTERVAL']:
        print(f"触发 磁盘 告警: 当前 {disk}%，阈值 {cfg['DISK_MAXUSE']}%")
        history_data = get_history(cfg.get('cursor'), 'disk_use') # 数据库字段是 disk_use
        advice = AI.ai_monitor('磁盘', disk, cfg['DISK_MAXUSE'], history_data)
        log_alter(cfg.get('URL'), system_time, f'磁盘@{HOSTNAME}({IP})', disk, cfg['DISK_MAXUSE'], advice)
        last_alert_time['disk'] = time.time()

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


