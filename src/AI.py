"""
AI.py — DeepSeek 大模型分析模块

职责:
  - 把告警信息 + 现场快照 + 历史数据组装成 Prompt
  - 调用 DeepSeek API 生成排查建议
  - 兼容 deepseek-chat 的 content 和 deepseek-reasoner 的 reasoning_content
"""
import os
from openai import OpenAI

""""""
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
    你是资深 Linux 系统运维专家，正在处理一条监控告警。

    【告警信息】
    - 资源类型：{resource}
    - 当前使用率：{current_value}%
    - 告警阈值：{threshold}%

    【{resource} 现场快照】
    {snapshot}

    【最近历史数据】
    格式：每行 "时间 : 使用率%"，时间正序（越往下越新），共 30 条

    {context_data}

    【你的任务（严格按此顺序输出）】

    **一、紧急程度**
    用一句话判断：需要立即处理 / 需要关注 / 可观察。给出依据。

    **二、趋势与预测**
    - 若为磁盘告警：根据历史数据估算增长率（%/小时），预测多久达到 100% 满盘。若数据不足，说明"数据不足以预测"。
    - 若为内存告警：判断是缓慢泄漏（持续上升）还是短期波动（有升有降）。
    - 若为 CPU 告警：判断是持续高负载还是瞬时抖动，结合 Load 和 wa 判断是计算瓶颈还是 IO 瓶颈。

    **三、最可能的原因（1~2 个）**
    不要罗列所有可能，只给最可能的，每条附上判断依据。

    **四、排查命令**
    按顺序编号，每个命令用代码块包裹，命令后一句话说明目的。

    **五、处置建议**
    - 临时缓解：立刻能做什么（1~2 条），做完后预期效果
    - 长期解决：根治方向（1~2 条），预计生效时间

    【输出要求】
    - 用中文，Markdown 格式
    - 严格使用上述五个标题
    - 不复述告警信息
    - 总长度控制在 500 字以内；关键信息多时可扩展到 800 字
    - 优先保证前两部分完整
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