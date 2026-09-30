"""
snapshot_server.py — 按场景返回快照

职责:
  - 端口 9101 提供 GET /snapshot?scenario=cpu&n=5
  - 维护 3 个环形缓冲（各保留 10 次）
  - 每 30 秒采一次
"""
import json
import time
import threading
from collections import deque
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

from diagnose import snapshot_cpu, snapshot_memory, snapshot_disk


_BUFFERS = {
    'cpu':    deque(maxlen=10),
    'memory': deque(maxlen=10),
    'disk':   deque(maxlen=10),
}
_LOCK = threading.Lock()

_SNAPSHOT_FUNCS = {
    'cpu':    snapshot_cpu,
    'memory': snapshot_memory,
    'disk':   snapshot_disk,
}


def _collector(interval=30):
    while True:
        for scenario, func in _SNAPSHOT_FUNCS.items():
            try:
                data = {
                    'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
                    'content': func(),
                }
                with _LOCK:
                    _BUFFERS[scenario].append(data)
            except Exception as e:
                print(f"[snapshot] {scenario} 采集失败: {e}")
        time.sleep(interval)


def _get_recent(scenario, n=5):
    with _LOCK:
        items = list(_BUFFERS.get(scenario, []))
    return items[-n:] if len(items) > n else items


class SnapshotHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path != '/snapshot':
            self.send_response(404)
            self.end_headers()
            return

        query = parse_qs(parsed.query)
        scenario = query.get('scenario', ['cpu'])[0].lower()
        try:
            n = int(query.get('n', ['5'])[0])
        except ValueError:
            n = 5
        n = max(1, min(n, 10))

        if scenario not in _BUFFERS:
            self.send_response(400)
            self.end_headers()
            self.wfile.write(json.dumps({'error': f'未知场景: {scenario}'}).encode('utf-8'))
            return

        try:
            items = _get_recent(scenario, n)
            if not items:
                func = _SNAPSHOT_FUNCS[scenario]
                items = [{
                    'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
                    'content': func(),
                }]

            body = json.dumps({
                'scenario': scenario,
                'count': len(items),
                'snapshots': items,
            }, ensure_ascii=False).encode('utf-8')

            self.send_response(200)
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self.send_header('Content-Length', str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        except Exception as e:
            self.send_response(500)
            self.end_headers()
            self.wfile.write(f'{{"error": "{e}"}}'.encode('utf-8'))

    def log_message(self, *args):
        pass


def start_snapshot_server_async(port=9101):
    threading.Thread(target=_collector, args=(30,), daemon=True).start()
    server = HTTPServer(('0.0.0.0', port), SnapshotHandler)
    print(f"[snapshot] 端口已启动: {port}")
    threading.Thread(target=server.serve_forever, daemon=True).start()