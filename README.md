

# System Monitor

一个基于AI智能分析的系统监控项目，支持实时资源监控、Prometheus集成、MySQL数据存储和智能告警功能。

## 功能特点

- **AI智能监控**：利用人工智能技术分析系统资源状态，提供智能监控建议
- **实时监控**：持续监控CPU、内存、磁盘、网络等关键系统资源
- **Prometheus集成**：支持Prometheus指标暴露，便于与现有监控系统集成
- **历史数据查询**：支持查询历史监控数据，便于趋势分析
- **智能告警**：根据AI分析结果生成智能告警和建议
- **灵活配置**：支持通过配置文件自定义监控参数和阈值

## 项目结构

```
system_monitor/
├── src/
│   ├── AI.py              # AI智能监控分析模块
│   ├── Prometheus_config.py # Prometheus配置模块
│   ├── alter.py           # 告警日志模块
│   ├── history.py         # 历史数据查询模块
│   ├── load_config.py     # 配置加载模块
│   ├── monitor.py         # 系统监控模块
│   └── mysql_config.py    # MySQL数据存储模块
├── .env.example           # 环境变量示例
├── .gitignore             # Git忽略规则
├── requirements.txt       # 依赖包列表
├── Dockerfile             # Docker构建文件
└── k8s/                   # Kubernetes部署配置
    ├── configmap.yaml
    ├── daemonset.yaml
    ├── mysql-secret.yaml
    ├── mysql-service.yaml
    ├── mysql-statefulset.yaml
    ├── mysql-svc-clusterip.yaml
    ├── secret.yaml
    └── configmap.yaml
```

## 核心模块说明

### AI监控模块 (AI.py)
```python
ai_monitor(resource, current_value, threshold, context_data)
```
AI智能分析系统资源状态，提供智能监控建议。

### Prometheus配置模块 (Prometheus_config.py)
```python
port_num(port=8000)              # 配置Prometheus服务端口
start_health_server(port=8001)   # 启动健康检查服务器
start_health_server_async(port=8001) # 异步启动健康检查服务器
```
配置Prometheus指标暴露和健康检查服务。

### 告警模块 (alter.py)
```python
log_alter(url, system_time, resource, current_value, threshold, advice=None)
```
记录系统告警信息，包括资源名称、当前值、阈值和AI建议。

### 历史数据模块 (history.py)
```python
get_history(cursor, resource, mi=10)
```
查询指定资源的监控历史数据，默认获取最近10分钟数据。

### 配置加载模块 (load_config.py)
```python
load_config()
```
加载并解析项目配置，包括数据库连接、监控阈值等参数。

### 监控模块 (monitor.py)
```python
get_host_info()
```
获取主机系统信息，包括硬件配置和运行状态。

### 数据存储模块 (mysql_config.py)
```python
insert_data(cursor, conn, data)
```
将监控数据存储到MySQL数据库。

## 快速开始

### 环境要求

- Python 3.7+
- MySQL数据库
- 必要的Python依赖包

### 安装步骤

1. 克隆项目到本地：
```bash
git clone https://gitee.com/crayz123/system_monitor.git
cd system_monitor
```

2. 安装依赖：
```bash
pip install -r requirements.txt
```

3. 配置环境变量：
```bash
cp .env.example .env
# 编辑.env文件，配置数据库连接和其他参数
```

4. 启动监控服务：
```bash
python src/monitor.py
```

### Docker部署

```bash
docker build -t system-monitor .
docker run -d -p 8000:8000 -p 8001:8001 --name monitor system-monitor
```

### Kubernetes部署

项目提供了完整的Kubernetes部署配置：

```bash
kubectl apply -f k8s/
```

## 配置说明

### 环境变量配置 (.env)

参考`.env.example`文件配置以下环境变量：

- 数据库连接信息（主机、端口、用户名、密码、数据库名）
- AI分析相关配置
- 告警通知设置
- Prometheus服务端口

### 监控参数配置

通过`load_config()`函数加载自定义监控阈值和参数。

## 监控指标

系统支持监控以下资源类型：

- CPU使用率
- 内存使用情况
- 磁盘空间和I/O
- 网络带宽和连接数
- 进程状态
- 自定义应用指标

## 告警规则

当资源使用量超过预设阈值时，系统将：

1. 触发告警并记录日志
2. 调用AI分析模块生成处理建议
3. 可选的主动通知机制

## Prometheus集成

项目内置Prometheus配置支持，默认端口8000，可通过以下方式暴露指标：

```python
from src.Prometheus_config import port_num
port_num(8000)  # 自定义端口
```

健康检查服务默认端口8001。

## 数据存储

监控数据默认存储在MySQL数据库中，支持：

- 实时数据插入
- 历史数据查询
- 数据备份和恢复

## API参考

### AI监控
```python
from src.AI import ai_monitor
result = ai_monitor(resource, current_value, threshold, context_data)
```

### Prometheus配置
```python
from src.Prometheus_config import port_num, start_health_server
port_num(8000)
start_health_server(8001)
```

### 告警日志
```python
from src.alter import log_alter
log_alter(url, system_time, resource, current_value, threshold, advice)
```

### 获取历史数据
```python
from src.history import get_history
history_data = get_history(cursor, resource, mi=10)
```

### 系统监控
```python
from src.monitor import get_host_info
host_info = get_host_info()
```

### 数据存储
```python
from src.mysql_config import insert_data
insert_data(cursor, conn, data)
```

### 配置加载
```python
from src.load_config import load_config
config = load_config()
```

## 依赖包

主要依赖包括：

- 数据库连接库
- 系统监控库
- AI/机器学习库
- Web服务框架

详情请查看`requirements.txt`文件。

## 许可证

本项目遵循开源许可证协议。

## 贡献指南

欢迎通过以下方式贡献代码：

- 提交Issue反馈问题
- 发送Pull Request贡献代码
- 完善项目文档

## 联系方式

- 项目地址：https://gitee.com/crayz123/system_monitor