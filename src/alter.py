import requests

def log_alter(url,system_time,resource,current_value,threshold,advice=None):
    if not url:
        print("未设置 webhook url，跳过告警")
        return

    message= f"时间:{system_time}\n资源: {resource}\n当前值: {current_value}%\n阈值: {threshold}%"

    if advice:
        message+=f"\n\nAI 建议:\n{advice}"

    data = {"msgtype":"text","text":{"content":message}}

    try:
        r =requests.post(url,json=data,timeout=10)
        if r.status_code == 200:
            print("告警成功")
        else:
            print(f"告警失败:{r.status_code}")
    except Exception as e:
        print(f"告警异常:{e}")

