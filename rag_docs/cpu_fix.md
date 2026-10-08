# CPU 告警处理方案

## 场景一：wa 高，us 低
说明是 IO 瓶颈，不是 CPU 问题。
排查命令：`iostat -x 1`、`iotop -o`。
处置：检查磁盘 IO 队列，考虑升级 SSD 或拆分热点文件。

## 场景二：us 高，sy 低
说明是用户态代码在跑循环。
排查命令：`ps aux --sort=-%cpu | head -10`。
处置：Java 用 `jstack` 看线程栈，Python 用 `py-spy dump`。

## 场景三：sy 高，us 低
说明是内核态开销，可能是系统调用频繁或上下文切换过高。
排查命令：`vmstat 1`、`pidstat -w 1`。
处置：检查是否有进程频繁创建/销毁。