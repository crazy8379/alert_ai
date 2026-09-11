import prometheus_client

cpu_use_gauge = prometheus_client.Gauge("cpu_use_gauge","cpu使用率")
mem_use_gauge = prometheus_client.Gauge("mem_use_gauge","mem使用率")
disk_use_gauge = prometheus_client.Gauge("disk_use_gauge","disk使用率")

def port_num(port=8000):
    prometheus_client.start_http_server(port)
    print(f"promethues端口已启动:{port}")