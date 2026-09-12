def insert_data(cursor,conn,data):
    sql= """
        insert into metrics (timestamp,cpu_use,mem_use,disk_use)
        values (%s,%s,%s,%s)
    """
    cursor.execute(sql,(
        data['timestamp'],data['cpu_use'], data['mem_use'], data['disk_use']
    ))
    conn.commit()

    # ========== 数据清理：最多保留 1000 条 ==========
    MAX_ROWS = 50

    # 查一下当前总条数
    cursor.execute("SELECT COUNT(*) FROM metrics")
    count = cursor.fetchone()[0]

    if count > MAX_ROWS:
        # 删除最旧的 (count - MAX_ROWS + 10) 条
        # 说明：+10 是为了"批量删除"，一次多删 10 条，减少清理频率
        delete_count = count - MAX_ROWS + 10
        cursor.execute(
            f"DELETE FROM metrics ORDER BY id ASC LIMIT {delete_count}"
        )
        conn.commit()
        print(f"[清理] 数据超过 {MAX_ROWS} 条，已删除最早的 {delete_count} 条")