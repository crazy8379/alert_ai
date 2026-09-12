# System Monitor

An AI-powered system monitoring project supporting real-time resource monitoring, Prometheus integration, MySQL data storage, and intelligent alerting functions.

## Features

- **AI Intelligent Monitoring**: Utilizes artificial intelligence technology to analyze system resource status
- **Real-time Monitoring**: Continuously monitors key system resources such as CPU, memory, disk, and network
- **Prometheus Integration**: Supports Prometheus metric exposure for easy integration with existing monitoring systems
- **Historical Data Query**: Supports querying historical monitoring data for trend analysis
- **Intelligent Alerting**: Generates intelligent alerts and suggestions based on AI analysis results
- **Flexible Configuration**: Supports customizing monitoring parameters and thresholds via configuration files

## Project Structure

```
system_monitor/
├── src/
│   ├── AI.py              # AI intelligent monitoring analysis module
│   ├── Prometheus_config.py # Prometheus configuration module
│   ├── alter.py           # Alert logging module
│   ├── history.py         # Historical data query module
│   ├── load_config.py     # Configuration loading module
│   ├── monitor.py         # System monitoring module
│   └── mysql_config.py    # MySQL data storage module
├── .env.example           # Environment variable example
├── .gitignore            # Git ignore rules
└── requirements.txt      # Dependencies list
```

## Core Module Description

### AI Monitoring Module (AI.py)
```python
ai_monitor(resource, current_value, threshold, context_data)
```
Performs AI intelligent analysis of system resource status and provides intelligent monitoring suggestions.

### Alert Module (alter.py)
```python
log_alter(url, system_time, resource, current_value, threshold, advice=None)
```
Records system alert information, including resource name, current value, threshold, and AI suggestions.

### Historical Data Module (history.py)
```python
get_history(cursor, resource, mi=10)
```
Queries monitoring historical data for specified resources; defaults to retrieving data from the last 10 minutes.

### Monitoring Module (monitor.py)
```python
get_host_info()
```
Retrieves host system information, including hardware configuration and operational status.

### Data Storage Module (mysql_config.py)
```python
insert_data(cursor, conn, data)
```
Stores monitoring data into the MySQL database.

### Configuration Module
- **Prometheus_config.py**: Configures the Prometheus service port (default 8000)
- **load_config.py**: Loads and parses project configurations

## Quick Start

### Environment Requirements

- Python 3.7+
- MySQL Database
- Necessary Python dependencies

### Installation Steps

1. Clone the project locally:
```bash
git clone https://gitee.com/crayz123/system_monitor.git
cd system_monitor
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Configure environment variables:
```bash
cp .env.example .env
# Edit the .env file to configure database connections and other parameters
```

4. Start the monitoring service:
```bash
python src/monitor.py
```

## Configuration Instructions

### Environment Variable Configuration (.env)

Refer to the `.env.example` file to configure the following environment variables:

- Database connection information (host, port, username, password, database name)
- AI analysis related configuration
- Alert notification settings
- Prometheus service port

### Monitoring Parameter Configuration

Load custom monitoring thresholds and parameters via the `load_config()` function.

## Monitoring Metrics

The system supports monitoring the following resource types:
- CPU Usage
- Memory Usage
- Disk Space and I/O
- Network Bandwidth and Connections
- Process Status
- Custom Application Metrics

## Alert Rules

When resource usage exceeds preset thresholds, the system will:
1. Trigger an alert and record logs
2. Call the AI analysis module to generate processing suggestions
3. Optional active notification mechanism

## Prometheus Integration

The project includes built-in Prometheus configuration support with a default port of 8000. Metrics can be exposed via the following method:

```python
from src.Prometheus_config import port_num
port_num(8000)  # Custom port
```

## Data Storage

Monitoring data is stored by default in a MySQL database, supporting:
- Real-time data insertion
- Historical data queries
- Data backup and restoration

## API Reference

### AI Monitoring
```python
from src.AI import ai_monitor
result = ai_monitor(resource, current_value, threshold, context_data)
```

### Get Historical Data
```python
from src.history import get_history
history_data = get_history(cursor, resource, mi=10)
```

### System Monitoring
```python
from src.monitor import get_host_info
host_info = get_host_info()
```

## Dependencies

Key dependencies include:
- Database connection libraries
- System monitoring libraries
- AI/Machine Learning libraries
- Web service frameworks

Please refer to the `requirements.txt` file for details.

## License

This project follows an open-source license agreement.

## Contribution Guidelines

Welcome to contribute code via the following methods:
- Submit Issues to report problems
- Send Pull Requests to contribute code
- Improve project documentation

## Contact Information

- Project Address: https://gitee.com/crayz123/system_monitor