"""
新闻采集模块
- 全球财经媒体头条
- 名人最新言论 (马斯克/特朗普/黄仁勋)
- 中国官媒要闻
"""

import feedparser
import requests
import re
import time
import random
from datetime import datetime
from bs4 import BeautifulSoup


# ===== 配置 =====
REQUEST_TIMEOUT = 15
USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:126.0) Gecko/20100101 Firefox/126.0',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.5 Safari/605.1.15',
]

HEADERS = {
    'User-Agent': USER_AGENTS[0],
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
}


# ===== 财经媒体源 =====
FINANCIAL_FEEDS = [
    {
        'name': 'Reuters',
        'url': 'https://www.reutersagency.com/feed/',
        'fallback': 'https://news.google.com/rss/search?q=site:reuters.com+finance&hl=en-US&gl=US&ceid=US:en',
    },
    {
        'name': 'CNBC',
        'url': 'https://search.cnbc.com/rs/search/combinedcms/view.xml?partnerId=wrss01&id=100003114',
    },
    {
        'name': 'Yahoo Finance',
        'url': 'https://finance.yahoo.com/news/rssindex',
    },
    {
        'name': 'MarketWatch',
        'url': 'https://feeds.marketwatch.com/marketwatch/topstories',
    },
    {
        'name': 'Bloomberg',
        'url': 'https://news.google.com/rss/search?q=site:bloomberg.com+markets&hl=en-US&gl=US&ceid=US:en',
    },
    {
        'name': 'Financial Times',
        'url': 'https://news.google.com/rss/search?q=site:ft.com+finance&hl=en-US&gl=US&ceid=US:en',
    },
    {
        'name': 'WSJ',
        'url': 'https://news.google.com/rss/search?q=site:wsj.com+markets&hl=en-US&gl=US&ceid=US:en',
    },
]

# 中国官媒
CHINA_FEEDS = [
    {
        'name': '新华社',
        'url': 'http://www.xinhuanet.com/rss/news_world.xml',
    },
    {
        'name': '央视新闻',
        'url': 'http://www.xinhuanet.com/rss/news_world.xml',  # 备用
        'search': 'https://news.google.com/rss/search?q=site:cctv.com+%E6%96%B0%E9%97%BB&hl=zh-CN&gl=CN&ceid=CN:zh-Hans',
    },
    {
        'name': '人民日报',
        'url': '',  # 通过搜索获取
        'search': 'https://news.google.com/rss/search?q=site:people.com.cn+%E9%87%8D%E8%A6%81%E6%96%B0%E9%97%BB&hl=zh-CN&gl=CN&ceid=CN:zh-Hans',
    },
]

# 名人搜索
FIGURE_SEARCHES = [
    {
        'name': 'Elon Musk',
        'keywords': 'Elon Musk',
        'url': 'https://news.google.com/rss/search?q=Elon+Musk&hl=en-US&gl=US&ceid=US:en',
    },
    {
        'name': 'Donald Trump',
        'keywords': 'Donald Trump',
        'url': 'https://news.google.com/rss/search?q=Donald+Trump&hl=en-US&gl=US&ceid=US:en',
    },
    {
        'name': 'Jensen Huang',
        'keywords': 'Jensen Huang',
        'url': 'https://news.google.com/rss/search?q=Jensen+Huang&hl=en-US&gl=US&ceid=US:en',
    },
]


def get_headers():
    """随机 UA 和通用请求头"""
    return {
        **HEADERS,
        'User-Agent': random.choice(USER_AGENTS),
    }


def get_session():
    """获取不经过系统代理的 requests session"""
    s = requests.Session()
    s.trust_env = False
    return s


def fetch_rss(feed_url, max_items=8):
    """获取 RSS feed 并解析"""
    if not feed_url:
        return []
    try:
        feed = feedparser.parse(feed_url)
        items = []
        for entry in feed.entries[:max_items]:
            item = {
                'title': entry.get('title', '').strip(),
                'link': entry.get('link', ''),
                'summary': '',
                'published': entry.get('published', ''),
            }
            # 提取摘要
            summary = entry.get('summary', '')
            if summary:
                soup = BeautifulSoup(summary, 'html.parser')
                item['summary'] = soup.get_text(strip=True)[:300]
            elif entry.get('description', ''):
                soup = BeautifulSoup(entry['description'], 'html.parser')
                item['summary'] = soup.get_text(strip=True)[:300]
            items.append(item)
        return items
    except Exception as e:
        print(f'  [RSS Error] {feed_url[:60]}: {e}')
        return []


def fetch_google_news_rss(url, max_items=5):
    """从 Google News RSS 获取"""
    return fetch_rss(url, max_items)


def fetch_page_headlines(url, max_items=5):
    """直接抓取页面提取标题和链接"""
    try:
        resp = requests.get(url, headers=get_headers(), timeout=REQUEST_TIMEOUT)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, 'html.parser')
        items = []

        # 尝试多种选择器
        candidates = []
        for selector in ['h3 a', 'h2 a', '.headline a', 'a.headline', 'article a']:
            candidates.extend(soup.select(selector))

        seen = set()
        for a in candidates:
            title = a.get_text(strip=True)
            href = a.get('href', '')
            if title and len(title) > 10 and title not in seen:
                if href.startswith('/'):
                    from urllib.parse import urljoin
                    href = urljoin(url, href)
                items.append({
                    'title': title,
                    'link': href,
                    'summary': '',
                    'published': '',
                })
                seen.add(title)
                if len(items) >= max_items:
                    break
        return items
    except Exception as e:
        print(f'  [Scrape Error] {url}: {e}')
        return []


# ===== 公开接口 =====

def fetch_financial_news():
    """
    获取全球财经媒体头条
    每个源取前3条，返回合并列表
    """
    print('  Fetching global financial news...')
    all_news = []

    for source in FINANCIAL_FEEDS:
        name = source['name']
        items = fetch_rss(source['url'], max_items=5)
        if not items and source.get('fallback'):
            print(f'    {name}: RSS failed, trying fallback...')
            items = fetch_google_news_rss(source['fallback'], max_items=5)
        if not items:
            print(f'    {name}: no results')
            continue
        for item in items[:3]:
            item['source'] = name
            all_news.append(item)
        print(f'    {name}: {len(items[:3])} headlines')

    # 去重
    seen = set()
    unique = []
    for item in all_news:
        key = item['title'][:40]
        if key not in seen:
            seen.add(key)
            unique.append(item)

    return unique


def fetch_figure_news():
    """
    获取马斯克、特朗普、黄仁勋的最新相关新闻
    每人取前3条
    """
    print('  Fetching figure news...')
    results = []

    for figure in FIGURE_SEARCHES:
        name = figure['name']
        items = fetch_google_news_rss(figure['url'], max_items=5)
        if not items:
            print(f'    {name}: no results')
            continue
        for item in items[:3]:
            item['source'] = name
            results.append(item)
        print(f'    {name}: {len(items[:3])} news items')

    return results


def fetch_china_media():
    """
    获取中国官媒要闻
    """
    print('  Fetching Chinese state media...')
    all_news = []

    for source in CHINA_FEEDS:
        name = source['name']
        items = []
        if source.get('url'):
            items = fetch_rss(source['url'], max_items=5)
        if not items and source.get('search'):
            items = fetch_google_news_rss(source['search'], max_items=5)
        if not items:
            print(f'    {name}: no results')
            continue
        for item in items[:3]:
            item['source'] = name
            all_news.append(item)
        print(f'    {name}: {len(items[:3])} headlines')

    return all_news


def fetch_all():
    """
    采集所有新闻数据
    Returns: dict with categories
    """
    print('=' * 50)
    print(f'News Fetch: {datetime.now().strftime("%Y-%m-%d %H:%M")}')
    print('=' * 50)

    financial = fetch_financial_news()
    figures = fetch_figure_news()
    china = fetch_china_media()

    return {
        'financial': financial,
        'figures': figures,
        'china': china,
        'fetched_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
    }
