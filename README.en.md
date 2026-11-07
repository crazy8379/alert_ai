# Alert AI — Alert Diagnosis Service

An AIOps service that sits downstream of Alertmanager. It receives alert webhooks, **sends the base alert first**, then asynchronously pulls Prometheus metric snapshots and asks an LLM for root-cause analysis, finally **pushing a second message with suggestions**.

It does not replace Alertmanager's grouping or silencing. It answers the on-call question: *is this alert real, and where should I look?*

## Architecture

```text
Prometheus rules → Alertmanager → POST /webhook
                                      │
                                      ├─ parse labels, match cpu / memory / disk
                                      │
                        ┌─────────────┴─────────────┐
                        │ matched                    │ not matched
                        ▼                            ▼
              notify pool: base alert        forward as-is
                        │                    (availability / probe alerts,
                        ▼                     no metrics, no LLM)
              analysis pool: snapshots → LLM
                        │
                        ▼
              follow-up: AI analysis
```

- **Two-stage notification**: separate pools for base alerts and AI analysis (default 4 / 2), so a slow LLM never blocks alert delivery
- **On-demand collection**: only the scenarios present in the alert labels are queried
- **Passthrough branch**: availability alerts (`InstanceDown`, `MySQLDown`, `WebsiteDown`) skip the LLM but are still delivered

## Flow

1. Alertmanager posts to `/webhook`; the API parses and returns `{"status":"accepted"}` immediately
2. Every label key/value is scanned for `cpu` / `mem` / `disk`
3. **No match** → forward a factual notification (including `description`) and stop
4. **Match** → send the base alert; only on success does analysis start
5. Collect snapshots: CPU/memory at `10m / 5m / 3m / 1m / 30s / now`; disk over the last hour (7 points)
6. Network throughput is appended to every snapshot to help identify traffic-driven pressure
7. Build a fixed five-section prompt (urgency / correlation / likely cause / commands / remediation) and call the LLM
8. Push the analysis as a WeCom **markdown** message

## Quick Start

### Local

```bash
pip install -r requirements.txt
cp .env.example .env      # fill in Prometheus URL, API key, WeCom webhook

cd src
python main.py            # or: uvicorn main:app --host 0.0.0.0 --port 8080
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

With `--network host`, `127.0.0.1:9090` inside the container reaches the host Prometheus.
For bridge networking, use `-p 8080:8080` and point `PROM_URL` at the host (e.g. `http://172.17.0.1:9090`).

### Kubernetes

```bash
kubectl apply -f k8s/
```

`k8s/3-deployment.yaml` uses `imagePullPolicy: Never`, so the image must be present on the node.

### Alertmanager

```yaml
receivers:
  - name: alert-ai
    webhook_configs:
      - url: 'http://127.0.0.1:8080/webhook'
        send_resolved: false   # resolved alerts are not handled yet
```

## Configuration

| Variable | Description | Default |
|---|---|---|
| `PROM_URL` | Prometheus base URL | `http://prometheus:9090` |
| `PROM_TIMEOUT` | Per-query timeout (s) | `10` |
| `API_KEY` | LLM API key | - |
| `API_URL` | OpenAI-compatible endpoint | `https://api.deepseek.com/v1` |
| `MODEL_NAME` | Model name | `deepseek-chat` |
| `AI_TIMEOUT` | LLM request timeout (s) | `30` |
| `AI_MAX_TOKENS` | Max output tokens | `2048` |
| `AI_TEMPERATURE` | Sampling temperature | `0.3` |
| `WECOM_URL` | WeCom bot webhook | - |
| `WEBHOOK_PORT` | Listen port (`python main.py` only) | `8080` |
| `NOTIFY_WORKERS` | Base notification concurrency | `4` |
| `ANALYSIS_WORKERS` | AI analysis concurrency | `2` |
| `SNAPSHOT_CPU_MEM_OFFSETS` | CPU/memory sample offsets (seconds ago) | `600,300,180,60,30,0` |
| `SNAPSHOT_DISK_N` | Disk sample count | `7` |
| `SNAPSHOT_DISK_STEP` | Disk sample interval (s) | `600` |

## Endpoints

| Method | Path | Description |
|---|---|---|
| `POST` | `/webhook` | Receive Alertmanager alerts, return accepted count |
| `GET` | `/healthz` | Health check |

## Design Notes

- **Noise reduction belongs to Alertmanager** — the service does not deduplicate or inhibit
- **The LLM never gates alerts** — it only adds context, so a model failure cannot suppress a P0
- **Two-stage by design** — delivery first, analysis second
- **Scenario-aware windows** — CPU/memory cover the rule's `for` duration; disk uses a longer window for growth estimation

## Known Limitations

- Pools and queues are in-process; a restart drops queued work, and multiple replicas need Redis or a queue
- `resolved` alerts are not handled; keep `send_resolved: false`
- Prometheus query failures are currently indistinguishable from real zero values
- The webhook has no authentication and should be restricted at the network layer

## License

MIT
