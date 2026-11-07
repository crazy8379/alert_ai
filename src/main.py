
# main.py
from fastapi import FastAPI, Request
import uvicorn
from config import settings
from webhook import process_alerts

app = FastAPI(title='Alert AI 诊断中心')

@app.post('/webhook')
async def webhook(request: Request):
    """接收 Alertmanager 告警，快速入队后返回。"""
    data = await request.json()
    accepted = process_alerts(data)
    return {'status': 'accepted', 'accepted': accepted}


@app.get('/healthz')
async def healthz():
    return {'status': 'healthy'}


if __name__ == '__main__':
    print(f'[main] 启动中心服务，端口 {settings.WEBHOOK_PORT}')
    print(f'[main] Prometheus: {settings.PROM_URL}')
    uvicorn.run(app, host='0.0.0.0', port=settings.WEBHOOK_PORT)