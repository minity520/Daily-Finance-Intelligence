"""
AI 分析模块
使用 DeepSeek API 分析新闻，找出受影响的经济领域和受益股票
"""

import requests
import json
import os
from datetime import datetime


DEEPSEEK_BASE_URL = 'https://api.deepseek.com/v1'
MODEL = 'deepseek-v4-flash'
MAX_TOKENS = 2048

SYSTEM_PROMPT = """你是一位金融分析师。分析新闻找出受影响的经济领域，推荐A股。

要求：
- 仅推荐A股，格式 SH:600xxx / SZ:000xxx / SZ:300xxx
- 每个领域推荐1-3只
- 基于真实新闻分析，不编造
- 若无足够信息，如实说明"""
    分析新闻数据，生成经济领域影响和股票推荐
    news_data: fetcher.fetch_all() 返回的数据
    Returns: dict with analysis sections
    """
    # 构建新闻摘要
    sections = []

    # 财经头条
    financial = news_data.get('financial', [])
    if financial:
        text = '【全球财经头条】\n'
        for item in financial:
            text += f"- [{item['source']}] {item['title']}\n"
        sections.append(text)

    # 名人言论
    figures = news_data.get('figures', [])
    if figures:
        text = '【名人相关新闻】\n'
        for item in figures:
            text += f"- [{item['source']}] {item['title']}\n"
        sections.append(text)

    # 中国官媒
    china = news_data.get('china', [])
    if china:
        text = '【中国官媒要闻】\n'
        for item in china:
            text += f"- [{item['source']}] {item['title']}\n"
        sections.append(text)

    if not sections:
        return {
            'error': '暂无新闻数据可分析',
            'analysis': '',
            'sectors': [],
            'stocks': [],
        }

    news_summary = '\n\n'.join(sections)

    user_message = f"""请分析以下今日重要新闻，找出最可能受影响的经济领域和受益股票。

今日新闻摘要：
{news_summary}

请按以下格式输出：

## 受影响经济领域分析

### 1. [领域名称]
- **影响逻辑**: 简要说明受什么新闻影响，为什么
- **推荐股票**:
  - [股票名称] ([代码]) — 推荐理由
  - [股票名称] ([代码]) — 推荐理由

### 2. [领域名称]
...以此类推

## 风险提示
简要说明可能的投资风险和不确定性"""

    result = _call_deepseek([
        {'role': 'system', 'content': SYSTEM_PROMPT},
        {'role': 'user', 'content': user_message},
    ])

    return {
        'analysis': result.get('content', ''),
        'error': result.get('error'),
        'usage': result.get('usage'),
        'generated_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
    }
