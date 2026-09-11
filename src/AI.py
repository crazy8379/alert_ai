import os
from openai import OpenAI

def ai_monitor(resource, current_value, threshold, context_data):
    api_key = os.getenv('API_KEY')
    if not api_key:
        return None

    prompt = f"""
    你是资深 Linux 系统运维专家，现在需要对一条监控告警给出快速、可执行的排查建议。

    【告警信息】
    - 资源类型：{resource}
    - 当前使用率：{current_value}%
    - 告警阈值：{threshold}%

    【该资源最近历史数据】
    {context_data}

    【你的任务】
    1. 先判断趋势：根据历史数据，判断这是"持续高位"、"突增"还是"波动"，不同趋势原因方向不同。
    2. 给出最可能的 1~2 个原因（不要罗列所有可能），说清依据。
    3. 给出可直接复制的排查命令（用代码块，按顺序编号）。
    4. 给出临时缓解方案（立刻能做）和长期解决方向（各 1 条）。

    【输出要求】
    - 用中文，Markdown 格式
    - 直接进入正题，不要复述告警内容，不要写"根据告警信息"这种废话
    - 每个排查命令后面用一句话说明目的
    - 总长度控制在 400 字以内，宁短勿长
    """

    client = OpenAI(api_key=api_key, base_url=os.getenv('API_URL', 'https://api.deepseek.com/v1'))
    try:
        response = client.chat.completions.create(
            model=os.getenv('MODEL_NAME', 'deepseek-reasoner'),
            messages=[{"role": "user", "content": prompt}],
            max_tokens=2048,
            timeout=15
        )
        msg = response.choices[0].message

        # 先尝试拿 content
        content = msg.content
        # 如果 content 为空，退而求其次拿 reasoning_content
        if not content:
            content = getattr(msg, 'reasoning_content', None)

        # 打印一下调试信息，看看实际返回了什么
        print(
            f"[AI 调试] content长度={len(msg.content or '')}, reasoning长度={len(getattr(msg, 'reasoning_content', '') or '')}")

        return content
    except Exception as e:
        print(f"LLM 分析失败: {e}")
        return None