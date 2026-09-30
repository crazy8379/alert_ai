"""
node_client.py — 拉 Agent 的 /snapshot
"""
import requests


def get_snapshots(node_ip, scenario, n=5, timeout=10):
    """
    从 Agent 拉指定场景的快照序列
    返回: [{'timestamp': ..., 'content': ...}, ...]
    """
    try:
        url = f'http://{node_ip}:9101/snapshot'
        resp = requests.get(
            url,
            params={'scenario': scenario, 'n': n},
            timeout=timeout
        )
        data = resp.json()
        return data.get('snapshots', [])
    except Exception as e:
        print(f"[node_client] 拉快照失败 {node_ip}: {e}")
        return []