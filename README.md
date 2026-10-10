# System Monitor

一个基于 Prometheus 的智能系统告警处理服务，支持自动采集指标快照、AI 智能分析告警，并通过企业微信发送告警通知。

## 功能特性

- 📥 **Webhook 告警接收**：接收来自 Prometheus 或其他监控系统的告警 webhook
- 📊 **智能指标采集**：自动获取告警实例的 CPU、内存、磁盘快照
- 🤖 **AI 智能分析**：利用 LLM 分析告警原因并提供处理建议
- 🛰️ **企业微信通知**：支持将告警信息推送至企业微信
- 🔄 **去重与冷却**：内置告警去重和冷却机制，避免重复告警
- ☸️ **Kubernetes 部署**：提供完整的 K8s 部署配置文件

## 快速开始

### 本地运行

```bash
# 1. 安装依赖
pip install -r requirements.txt

# 2. 配置环境变量
cp .env.example .env
# 编辑 .env 文件，配置 Prometheus 地址、企业微信 webhook 等

# 3. 启动服务
uvicorn main:app --host 0.0.0.0 --port 8080
```

### Docker 运行

```bash
docker build -t system_monitor .
docker run -d -p 8080:8080 --env-file .env system_monitor
```

### Kubernetes 部署

```bash
kubectl apply -f k8s/
```

## 配置说明

| 环境变量 | 说明 | 默认值 |
|---------|------|-------|
| `PROMETHEUS_URL` | Prometheus 服务器地址 | `http://prometheus:9090` |
| `WECOM_WEBHOOK` | 企业微信机器人 Webhook URL | - |
| `AI_API_KEY` | AI API 密钥 | - |
| `AI_BASE_URL` | AI API 基础地址 | - |
| `AI_MODEL` | 使用的 AI 模型 | - |
| `COOLDOWN_SECONDS` | 告警冷却时间（秒） | `3600` |

## API 接口

### 告警 Webhook

```
POST /webhook
```

接收 Prometheus Alertmanager 推送的告警数据。

### 健康检查

```
GET /healthz
```

返回服务健康状态。

## 项目结构

```
system_monitor/
├── src/
│   ├── main.py          # FastAPI 应用入口
│   ├── config.py        # 配置管理
│   ├── models.py        # 数据模型定义
│   ├── webhook.py       # Webhook 处理逻辑
│   ├── prom_client.py   # Prometheus 客户端
│   ├── prompt.py        # AI 提示词构建
│   ├── ai.py            # AI 分析模块
│   ├── notifier.py      # 企业微信通知
│   └── dedup.py         # 去重与冷却逻辑
├── k8s/                 # Kubernetes 部署配置
├── Dockerfile
├── requirements.txt
└── .env.example
```

## 告警流程

1. **接收告警**：通过 `/webhook` 接口接收 Prometheus Alertmanager 推送的告警
2. **去重检查**：检查告警是否在冷却期内，避免重复处理
3. **指标采集**：从 Prometheus 查询告警实例的 CPU、内存、磁盘指标快照
4. **AI 分析**：将告警信息和指标快照发送给 AI 获取分析建议
5. **发送通知**：将告警信息和 AI 建议通过企业微信发送

## 许可证

MIT 许可证
