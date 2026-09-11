import os
import pymysql
from dotenv import load_dotenv

load_dotenv()

conn=None
cursor=None
try:
    conn=pymysql.connect(
        host=os.getenv('MYSQL_HOST','127.0.0.1'),
        port=int(os.getenv('MYSQL_PORT', '3306')),
        user=os.getenv('MYSQL_USER', 'monitorer'),
        password=os.getenv('MYSQL_PASSWORD', '123456'),
        database=os.getenv('MYSQL_DB', 'system_monitor'),
        charset='utf8mb4',
        connect_timeout=5
    )
    cursor=conn.cursor()
    print("MYSQL连接成功")
except Exception as e:
    print(f"MYSQL连接失败:{e},将跳过数据库写入")


def load_config():

    return {

        'CPU_MAXUSE':int(os.getenv('CPU_MAXUSE','80')),
        'MEMORY_MAXUSE': int(os.getenv('MEMORY_MAXUSE', '90')),
        'DISK_MAXUSE': int(os.getenv('DISK_MAXUSE', '80')),
        'INTERVAL': int(os.getenv('INTERVAL', '3')),
        'DISK_PATH': os.getenv('DISK_PATH', 'C:\\'),
        'MYSQL_HOST': os.getenv('MYSQL_HOST', '127.0.0.1'),
        'MYSQL_PORT': int(os.getenv('MYSQL_PORT', '3306')),
        'MYSQL_USER': os.getenv('MYSQL_USER', 'monitorer'),
        'MYSQL_PASSWORD': os.getenv('MYSQL_PASSWORD', '123456'),
        'MYSQL_DB': os.getenv('MYSQL_DB', 'system_monitor'),
        'conn': conn,      # <--- 新增
        'cursor': cursor,   # <--- 新增
        'ALTER_INTERVAL': int(os.getenv('ALTER_INTERVAL', '300')),  # <--- 必须加上这行
        'URL': os.getenv('URL', '')

    }