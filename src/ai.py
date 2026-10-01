"""ai.py — 调 DeepSeek"""
import json
import requests

from config import settings


def analyze(prompt: str) -> str | None:
    if not settings.API_KEY:
        print('[ai] 未配置 API_KEY')
        return None

    payload = {
        'model': settings.MODEL_NAME,
        'messages': [{'role': 'user', 'content': prompt}],
        'max_tokens': settings.AI_MAX_TOKENS,
        'temperature': settings.AI_TEMPERATURE,
    }
    body = json.dumps(payload, ensure_ascii=False).encode('utf-8')

    try:
        resp = requests.post(
            f'{settings.API_URL}/chat/completions',
            headers={
                'Authorization': f'Bearer {settings.API_KEY}',
                'Content-Type': 'application/json; charset=utf-8',
            },
            data=body,
            timeout=settings.AI_TIMEOUT,
        )
        if resp.status_code != 200:
            print(f'[ai] 请求失败: {resp.status_code} {resp.text[:200]}')
            return None

        data = resp.json()
        msg = data['choices'][0]['message']
        content = msg.get('content') or msg.get('reasoning_content') or ''
        print(f'[ai] content 长度={len(content)}')
        return content
    except Exception as e:
        print(f'[ai] 失败: {e}')
        return None