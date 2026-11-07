# Alert AI — 告警智能诊断服务

位于 Alertmanager 下游的 AIOps 服务：接收 Alertmanager Webhook，**先发基础告警**，再异步采集 Prometheus 指标快照交给 LLM 分析，**补发一条根因与处置建议**。

目标不是替代 Alertmanager 做降噪，而是解决值班时"告警响了，但不知道是不是误报、该从哪里查"的问题。

## 架构

```text
Prometheus 规则 → Alertmanager → POST /webhook
                                      │
                                      ├─ 解析 labels，匹配 cpu / memory / disk
                                      │
                        ┌─────────────┴─────────────┐
                        │ 匹配到                     │ 未匹配到
                        ▼                           ▼
                通知线程池：发【告警】          直发【告警】
                        │                     （服务存活、探测类告警，
                        ▼                      不查指标、不调 AI）
                分析线程池：查快照 → 调 LLM
                        │
                        ▼
                补发【AI 分析】
```

- **两段式通知**：基础告警与分析结果使用独立线程池（默认 4 / 2），AI 慢调用不会阻塞告警送达
- **按需采集**：只采集 labels 中实际出现的场景，不多拉也不少拉
- **非资源告警直发**：`InstanceDown`、`MySQLDown`、`WebsiteDown` 等不接 AI，但保证通知到人

## 处理流程

1. Alertmanager 推送 `POST /webhook`，接口解析后立即返回 `{"status":"accepted"}`
2. 遍历每条告警的 `labels`，匹配 `cpu` / `mem` / `disk` 关键词
3. **未匹配**：走直发分支，推一条事实通知（含 `description`），结束
4. **匹配到**：先发【告警】占位消息；发送成功后进入第二阶段
5. 采集指标快照：CPU / 内存取 `10m / 5m / 3m / 1m / 30s / now` 六个点，磁盘取最近 1 小时 7 个点
6. 每个快照点自动附带网络收发速率，便于判断是否为流量型压力
7. 组装 Prompt（固定五段式输出：紧急程度 / 关联分析 / 可能原因 / 排查命令 / 处置建议），调用 LLM
8. 以企业微信 markdown 消息补发【AI 分析】

## 快速开始

### 本地运行

```bash
pip install -r requirements.txt
cp .env.example .env      # 填入 Prometheus 地址、API Key、企微机器人地址

cd src
python main.py            # 或 uvicorn main:app --host 0.0.0.0 --port 8080
```

### Docker

```bash
docker build -t alert-ai:1.0 .

docker run -d --name alert-ai --restart unless-stopped \
  --network host \
  --env-file .env \
  -v /etc/localtime:/etc/localtime:ro \
  --memory 256m \
  alert-ai:1.0
```

`--network host` 让容器直接用宿主机网络，容器内 `127.0.0.1:9090` 即可访问本机 Prometheus。
若使用桥接网络，需改为 `-p 8080:8080` 并把 `PROM_URL` 指向宿主机地址（如 `http://172.17.0.1:9090`）。

### Kubernetes

```bash
kubectl apply -f k8s/
```

注意：`k8s/3-deployment.yaml` 使用 `imagePullPolicy: Never`，需要先把镜像导入节点。

### 对接 Alertmanager

```yaml
receivers:
  - name: alert-ai
    webhook_configs:
      - url: 'http://127.0.0.1:8080/webhook'
        # 当前代码未处理 resolved，先关闭恢复通知
        send_resolved: false
```

## 配置

| 环境变量 | 说明 | 默认值 |
|---|---|---|
| `PROM_URL` | Prometheus 地址 | `http://prometheus:9090` |
| `PROM_TIMEOUT` | 单次 PromQL 超时（秒） | `10` |
| `API_KEY` | LLM API Key | - |
| `API_URL` | OpenAI 兼容接口地址 | `https://api.deepseek.com/v1` |
| `MODEL_NAME` | 模型名 | `deepseek-chat` |
| `AI_TIMEOUT` | LLM 请求超时（秒） | `30` |
| `AI_MAX_TOKENS` | 输出上限 | `2048` |
| `AI_TEMPERATURE` | 采样温度 | `0.3` |
| `WECOM_URL` | 企业微信机器人 Webhook | - |
| `WEBHOOK_PORT` | 服务端口（仅 `python main.py` 生效） | `8080` |
| `NOTIFY_WORKERS` | 基础通知并发 | `4` |
| `ANALYSIS_WORKERS` | AI 分析并发 | `2` |
| `SNAPSHOT_CPU_MEM_OFFSETS` | CPU/内存采样点（秒前，逗号分隔） | `600,300,180,60,30,0` |
| `SNAPSHOT_DISK_N` | 磁盘采样点数 | `7` |
| `SNAPSHOT_DISK_STEP` | 磁盘采样间隔（秒） | `600` |

## 接口

| 方法 | 路径 | 说明 |
|---|---|---|
| `POST` | `/webhook` | 接收 Alertmanager 告警，返回 `accepted` 数量 |
| `GET` | `/healthz` | 健康检查 |

## 目录结构

```text
src/
├── main.py          # FastAPI 入口
├── config.py        # 环境变量配置
├── models.py        # Alert 数据模型
├── webhook.py       # 告警编排：标签匹配、线程池、直发分支
├── prom_client.py   # Prometheus 查询与快照生成
├── prompt.py        # Prompt 模板
├── ai.py            # LLM 调用
└── notifier.py      # 企业微信通知（text / markdown）
```

## 设计取舍

- **降噪交给 Alertmanager**：服务端不做去重和抑制，`group_by` / `repeat_interval` / `silence` 统一在 Alertmanager 配置
- **AI 不参与拦截**：模型只补充分析，告警是否发送不由模型决定，避免误判导致 P0 漏报
- **两段式而非同步**：先保证告警到达，再花时间做分析
- **采集窗口按场景区分**：CPU/内存覆盖告警规则 `for` 的持续时间，磁盘用更长窗口估算增长率

## 已知限制

- 线程池与队列在进程内，重启会丢失排队任务；多副本部署需换成 Redis 或消息队列
- 未处理 `resolved` 状态，恢复通知需保持 `send_resolved: false`
- Prometheus 查询失败与真实 0 值目前无法区分
- Webhook 无鉴权，生产部署应限制来源

## License

MIT
