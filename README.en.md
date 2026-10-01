# System Monitor

An intelligent system alert processing service based on Prometheus, supporting automatic metric snapshot collection, AI-powered alert analysis, and sending alert notifications via WeCom.

## Features

- 📥 **Webhook Alert Reception**: Receive alert webhooks from Prometheus or other monitoring systems
- 📊 **Intelligent Metric Collection**: Automatically capture CPU, memory, and disk snapshots for alerted instances
- 🤖 **AI Intelligent Analysis**: Utilize LLMs to analyze alert causes and provide handling suggestions
- 🛰️ **WeCom Notification**: Support pushing alert information to WeCom
- 🔄 **Deduplication & Cooldown**: Built-in alert deduplication and cooldown mechanisms to avoid repeated alerts
- ☸️ **Kubernetes Deployment**: Provides complete K8s deployment configuration files

## Quick Start

### Local Run

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Configure environment variables
cp .env.example .env
# Edit the .env file, configure Prometheus address, WeCom webhook, etc.

# 3. Start the service
uvicorn main:app --host 0.0.0.0 --port 8080
```

### Docker Run

```bash
docker build -t system_monitor .
docker run -d -p 8080:8080 --env-file .env system_monitor
```

### Kubernetes Deployment

```bash
kubectl apply -f k8s/
```

## Configuration

| Environment Variable | Description | Default Value |
|---------|------|-------|
| `PROMETHEUS_URL` | Prometheus server address | `http://prometheus:9090` |
| `WECOM_WEBHOOK` | WeCom Bot Webhook URL | - |
| `AI_API_KEY` | AI API Key | - |
| `AI_BASE_URL` | AI API Base URL | - |
| `AI_MODEL` | AI Model used | - |
| `COOLDOWN_SECONDS` | Alert cooldown time (seconds) | `3600` |

## API Endpoints

### Alert Webhook

```
POST /webhook
```

Receives alert data pushed by Prometheus Alertmanager.

### Health Check

```
GET /healthz
```

Returns the service health status.

## Project Structure

```
system_monitor/
├── src/
│   ├── main.py          # FastAPI app entry point
│   ├── config.py        # Configuration management
│   ├── models.py        # Data model definitions
│   ├── webhook.py       # Webhook processing logic
│   ├── prom_client.py   # Prometheus client
│   ├── prompt.py        # AI prompt construction
│   ├── ai.py            # AI analysis module
│   ├── notifier.py      # WeCom notifier
│   └── dedup.py         # Deduplication and cooldown logic
├── k8s/                 # Kubernetes deployment configuration
├── Dockerfile
├── requirements.txt
└── .env.example
```

## Alert Workflow

1. **Receive Alerts**: Receive alerts pushed by Prometheus Alertmanager via the `/webhook` endpoint
2. **Deduplication Check**: Check if the alert is within the cooldown period to avoid duplicate processing
3. **Metric Collection**: Query CPU, memory, and disk metric snapshots for the alerted instance from Prometheus
4. **AI Analysis**: Send alert information and metric snapshots to AI to obtain analysis suggestions
5. **Send Notification**: Send alert information and AI suggestions via WeCom

## License

MIT License