"""
AI.py — DeepSeek 大模型分析模块

职责:
  - 把告警信息 + 现场快照 + 历史数据组装成 Prompt
  - 调用 DeepSeek API 生成排查建议
  - 兼容 deepseek-chat 的 content 和 deepseek-reasoner 的 reasoning_content
"""
import os
from openai import OpenAI


def ai_monitor(resource, current_value, threshold, context_data, snapshot=""):
    """
    参数:
        resource: 资源类型（CPU/内存/磁盘）
        current_value: 当前值
        threshold: 阈值
        context_data: 历史数据字符串
        snapshot: 场景化现场快照字符串
    """
    api_key = os.getenv('API_KEY')
    if not api_key:
        return None

    prompt = f"""
你是资深 Linux 系统运维专家，现在需要对一条监控告警给出快速、可执行的排查建议。

【告警信息】
- 资源类型：{resource}
- 当前使用率：{current_value}%
- 告警阈值：{threshold}%

【现场快照】
{snapshot}

【最近历史数据】
{context_data}

【你的任务】
1. 结合"现场快照"判断根因，特别注意：
   - CPU 告警：若 wa 高，是 IO 问题不是 CPU；若某单核满，可能是单线程程序
   - 内存告警：若 Swap > 0 且 available 低，是真实不足；若 available 充足，是缓存
   - 磁盘告警：若 IOPS 高吞吐低，是小文件写入；若吞吐高 IOPS 低，是大文件
2. 给出最可能的 1~2 个原因，说清依据。
3. 给出可直接复制的排查命令（用代码块，按顺序编号）。
4. 给出临时缓解方案（立刻能做）和长期解决方向（各 1 条）。

【输出要求】
- 用中文，Markdown 格式
- 直接进入正题，不要复述告警内容
- 每个排查命令后面用一句话说明目的
- 总长度控制在 400 字以内，宁短勿长
"""

    client = OpenAI(api_key=api_key, base_url=os.getenv('API_URL', 'https://api.deepseek.com/v1'))
    try:
        response = client.chat.completions.create(
            model=os.getenv('MODEL_NAME', 'deepseek-chat'),
            messages=[{"role": "user", "content": prompt}],
            max_tokens=2048,
            timeout=20
        )
        msg = response.choices[0].message
        content = msg.content
        if not content:
            content = getattr(msg, 'reasoning_content', None)
        print(f"[AI 调试] content长度={len(msg.content or '')}, "
              f"reasoning长度={len(getattr(msg, 'reasoning_content', '') or '')}")
        return content
    except Exception as e:
        print(f"LLM 分析失败: {e}")
        return None