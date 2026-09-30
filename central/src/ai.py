"""
ai.py — 调 DeepSeek 分析（用 requests，UTF-8 手动编码）
"""
import os
import json
import requests


def analyze(prompt):
    api_key = os.getenv('API_KEY')
    if not api_key:
        print("[ai] 未配置 API_KEY")
        return None

    base_url = os.getenv('API_URL', 'https://api.deepseek.com/v1')
    model = os.getenv('MODEL_NAME', 'deepseek-chat')

    payload = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": 2048,
    }
    body = json.dumps(payload, ensure_ascii=False).encode('utf-8')

    try:
        resp = requests.post(
            f"{base_url}/chat/completions",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json; charset=utf-8",
            },
            data=body,
            timeout=30
        )

        if resp.status_code != 200:
            print(f"[ai] 请求失败: {resp.status_code} {resp.text[:200]}")
            return None

        data = resp.json()
        msg = data['choices'][0]['message']
        content = msg.get('content', '') or msg.get('reasoning_content', '')

        print(f"[ai] content长度={len(content or '')}")
        return content
    except Exception as e:
        print(f"[ai] 失败: {e}")
        return None