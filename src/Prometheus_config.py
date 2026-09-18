import prometheus_client
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler

cpu_use_gauge = prometheus_client.Gauge("cpu_use_gauge", "cpu使用率")
mem_use_gauge = prometheus_client.Gauge("mem_use_gauge", "mem使用率")
disk_use_gauge = prometheus_client.Gauge("disk_use_gauge", "disk使用率")
swap_use_gauge = prometheus_client.Gauge("swap_use_gauge", "swap使用率")
disk_read_gauge = prometheus_client.Gauge("disk_read_gauge", "磁盘读MB/s")
disk_write_gauge = prometheus_client.Gauge("disk_write_gauge", "磁盘写MB/s")
net_send_gauge = prometheus_client.Gauge("net_send_gauge", "网络发送MB/s")
net_recv_gauge = prometheus_client.Gauge("net_recv_gauge", "网络接收MB/s")

def port_num(port=8000):
    prometheus_client.start_http_server(port)
    print(f"promethues端口已启动:{port}")

def start_health_server(port=8001):
    """独立的健康检查端口，不受主循环阻塞影响"""
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
            pass  # 不打印访问日志，避免刷屏

    HTTPServer(('0.0.0.0', port), HealthHandler).serve_forever()

def start_health_server_async(port=8001):
    """用后台线程启动健康检查服务"""
    threading.Thread(target=start_health_server, args=(port,), daemon=True).start()
    print(f"健康检查端口已启动: {port}")