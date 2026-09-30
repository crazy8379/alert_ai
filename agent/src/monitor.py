"""
monitor.py — Agent 主入口（简化版）

唯一职责:
  - 提供 /snapshot 端点（给中心服务拉快照）
  - 提供 /healthz 健康检查（给 K8s 探针）

不再暴露 /metrics（交给 node_exporter）
不再采集指标（交给 node_exporter）
"""
import time
import threading
import socket
import os
import psutil
from http.server import HTTPServer, BaseHTTPRequestHandler

from load_config import load_config
from snapshot_server import start_snapshot_server_async
from diagnose import warmup


# ========== K8s 环境下读宿主机 /proc ==========
if os.getenv('HOST_PROC'):
    psutil.PROCFS_PATH = os.getenv('HOST_PROC')
    print(f"[K8s] 已切换 psutil 读取路径为: {os.getenv('HOST_PROC')}")


# ========== 健康检查 ==========
def start_health_server(port=8001):
    class HealthHandler(BaseHTTPRequestHandler):
        def do_GET(self):
            if self.path == '/healthz':
                self.send_response(200)
                self.end_headers()
                self.wfile.write(b'ok')
            else:
                self.send_response(404)
                self.end_headers()

        def log_message(self, *args):
            pass

    HTTPServer(('0.0.0.0', port), HealthHandler).serve_forever()


def start_health_server_async(port=8001):
    threading.Thread(target=start_health_server, args=(port,), daemon=True).start()
    print(f"[health] 端口已启动: {port}")


# ========== 主机信息 ==========
def get_host_info():
    hostname = os.getenv('NODE_NAME') or socket.gethostname()
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(('8.8.8.8', 80))
        ip = s.getsockname()[0]
        s.close()
    except Exception:
        ip = '127.0.0.1'
    return hostname, ip


# ========== 启动 ==========
HOSTNAME, IP = get_host_info()

cfg = load_config()
start_health_server_async(cfg['HEALTH_PORT'])
start_snapshot_server_async(cfg['SNAPSHOT_PORT'])

print(f"[Agent] 启动完成 | 节点: {HOSTNAME} ({IP})")
print(f"[Agent] 唯一职责: 提供 /snapshot 快照")

# 预热
warmup()

# 主循环只需要保持进程活着
while True:
    time.sleep(60)