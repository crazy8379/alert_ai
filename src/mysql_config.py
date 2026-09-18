"""
mysql_config.py — 数据写入模块

职责:
  - INSERT 数据到 metrics 表
  - 超过 MAX_ROWS 时批量删除最旧记录
"""
def insert_data(cursor, conn, data):
    sql = """
        insert into metrics 
        (timestamp, cpu_use, mem_use, disk_use, 
          swap_use, disk_read, disk_write, net_send, net_recv)
        values (%s, %s, %s, %s, %s, %s, %s, %s, %s)
    """
    cursor.execute(sql, (
        data['timestamp'], data['cpu_use'], data['mem_use'], data['disk_use'],
        data['swap_use'],
        data['disk_read'], data['disk_write'],
        data['net_send'], data['net_recv'],
    ))
    conn.commit()

    # ========== 数据清理：最多保留 1000 条 ==========
    MAX_ROWS = 100

    cursor.execute("SELECT COUNT(*) FROM metrics")
    count = cursor.fetchone()[0]

    if count > MAX_ROWS:
        delete_count = count - MAX_ROWS + 10
        cursor.execute(
            f"DELETE FROM metrics ORDER BY id ASC LIMIT {delete_count}"
        )
        conn.commit()
        print(f"[清理] 数据超过 {MAX_ROWS} 条，已删除最早的 {delete_count} 条")