"""
history.py — 历史数据查询模块

职责:
  - 从 MySQL 查询指定资源最近 N 分钟的数据
  - 返回格式化文本，供 AI 分析用
  - 任何异常都返回字符串，绝不抛出，避免主循环崩溃
"""


def get_history(cursor, resource, mi=10):
    if not cursor:
        return "无历史数据"

    # 字段白名单，防 SQL 注入
    if resource not in {'cpu_use', 'mem_use', 'disk_use'}:
        return "非法资源字段"

    try:
        sql = (f"SELECT timestamp, {resource} FROM metrics "
               f"WHERE timestamp > NOW() - INTERVAL %s MINUTE "
               f"ORDER BY timestamp ASC LIMIT 30")
        cursor.execute(sql, (mi,))
        rows = cursor.fetchall()
        if not rows:
            return "历史数据为空"
        return "\n".join([f"{r[0]} : {r[1]}%" for r in rows])
    except Exception as e:
        print(f"[history] 查询失败: {e}")
        return f"历史数据查询失败: {e}"