import time
import psutil
import AI

from history import get_history
from alter import log_alter
from mysql_config import insert_data
from Prometheus_config import cpu_use_gauge, mem_use_gauge, disk_use_gauge, port_num
from load_config import load_config

cfg=load_config()
port_num(8000)
print("开始采集数据")
print(f"[配置] ALTER_INTERVAL = {cfg['ALTER_INTERVAL']}")

last_alert_time={'cpu':0.0,'mem':0.0,'disk':0.0}
while True:
    system_time = time.strftime('%Y-%m-%d %H:%M:%S')
    cpu=psutil.cpu_percent(interval=1)
    mem=psutil.virtual_memory().percent
    disk=psutil.disk_usage(cfg['DISK_PATH']).percent

    cpu_use_gauge.set(cpu)
    mem_use_gauge.set(mem)
    disk_use_gauge.set(disk)

    if cfg.get('cursor'):
        data={
            'timestamp': system_time,
            'cpu_use': cpu,
            'mem_use': mem,
            'disk_use': disk

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
        log_alter(cfg.get('URL'), system_time, 'CPU', cpu, cfg['CPU_MAXUSE'], advice)
        last_alert_time['cpu'] = time.time()

    if mem >= cfg['MEMORY_MAXUSE'] and (current_time - last_alert_time['mem']) >= cfg['ALTER_INTERVAL']:
        print(f"触发 内存 告警: 当前 {mem}%，阈值 {cfg['MEMORY_MAXUSE']}%")
        history_data = get_history(cfg.get('cursor'), 'mem_use')  # 数据库字段是 mem_use
        advice = AI.ai_monitor('内存', mem, cfg['MEMORY_MAXUSE'], history_data)
        log_alter(cfg.get('URL'), system_time, '内存', mem, cfg['MEMORY_MAXUSE'], advice)
        last_alert_time['mem'] = time.time()

    if disk >= cfg['DISK_MAXUSE'] and (current_time - last_alert_time['disk']) >= cfg['ALTER_INTERVAL']:
        print(f"触发 磁盘 告警: 当前 {disk}%，阈值 {cfg['DISK_MAXUSE']}%")
        history_data = get_history(cfg.get('cursor'), 'disk_use') # 数据库字段是 disk_use
        advice = AI.ai_monitor('磁盘', disk, cfg['DISK_MAXUSE'], history_data)
        log_alter(cfg.get('URL'), system_time, '磁盘', disk, cfg['DISK_MAXUSE'], advice)
        last_alert_time['disk'] = time.time()

    print(f"CPU: {cpu}% | 内存: {mem}% | 磁盘: {disk}%")
    time.sleep(cfg['INTERVAL'])


