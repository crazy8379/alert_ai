"""
main.py — 中心服务入口（FastAPI）
"""
from fastapi import FastAPI, BackgroundTasks, Request
import uvicorn

from config import get_config
from webhook import process_alerts

app = FastAPI()


@app.post("/webhook")
async def webhook(request: Request, background_tasks: BackgroundTasks):
    """接收 Alertmanager 告警，立即返回 200"""
    data = await request.json()
    background_tasks.add_task(process_alerts, data)
    return {"status": "ok"}


@app.get("/healthz")
async def healthz():
    return {"status": "healthy"}


if __name__ == '__main__':
    cfg = get_config()
    print(f"[main] 启动中心服务，端口 {cfg['WEBHOOK_PORT']}")
    uvicorn.run(app, host='0.0.0.0', port=cfg['WEBHOOK_PORT'])