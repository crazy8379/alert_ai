"""main.py — 中心服务入口"""
from fastapi import FastAPI, BackgroundTasks, Request
import uvicorn

from config import settings
from webhook import process_alerts

app = FastAPI(title='Alert AI 诊断中心')


@app.post('/webhook')
async def webhook(request: Request, background_tasks: BackgroundTasks):
    """接收 Alertmanager 告警，立即返回 200"""
    data = await request.json()
    background_tasks.add_task(process_alerts, data)
    return {'status': 'ok'}


@app.get('/healthz')
async def healthz():
    return {'status': 'healthy'}


if __name__ == '__main__':
    print(f'[main] 启动中心服务，端口 {settings.WEBHOOK_PORT}')
    print(f'[main] Prometheus: {settings.PROM_URL}')
    uvicorn.run(app, host='0.0.0.0', port=settings.WEBHOOK_PORT)