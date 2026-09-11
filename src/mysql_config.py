def insert_data(cursor,conn,data):
    sql= """
        insert into metrics (timestamp,cpu_use,mem_use,disk_use)
        values (%s,%s,%s,%s)
    
    """

    cursor.execute(sql,(
        data['timestamp'],data['cpu_use'], data['mem_use'], data['disk_use']
    ))
    conn.commit()