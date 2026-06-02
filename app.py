"""
财经新闻分析工具 - Flask 主应用
两阶段加载：先展示新闻，再异步分析
"""

import os
import sys
from flask import Flask, render_template, jsonify
import threading
import time

from fetcher import fetch_all
from analyzer import analyze_news

app = Flask(__name__)

# 缓存
cache = {
    'data': None,        # 新闻数据
    'analysis': None,     # AI 分析结果
    'timestamp': None,
    'loading_fetch': False,   # 正在采集新闻
    'loading_analysis': False, # 正在分析
}


@app.route('/')
def index():
    """首页"""
    ctx = {
        'has_data': cache['data'] is not None,
        'timestamp': cache['timestamp'] or '',
        'loading_fetch': cache['loading_fetch'],
        'loading_analysis': cache['loading_analysis'],
    }
    return render_template('index.html', **ctx)


@app.route('/api/status')
def api_status():
    """API 状态轮询"""
    return jsonify({
        'loading_fetch': cache['loading_fetch'],
        'loading_analysis': cache['loading_analysis'],
        'has_data': cache['data'] is not None,
        'has_analysis': cache['analysis'] is not None,
        'timestamp': cache['timestamp'],
    })


@app.route('/api/data')
def api_data():
    """获取完整数据"""
    if cache['loading_fetch']:
        return jsonify({'status': 'loading_fetch'})
    if not cache['data']:
        return jsonify({'status': 'empty', 'data': None, 'analysis': None})

    return jsonify({
        'status': 'ready',
        'data': cache['data'],
        'analysis': cache['analysis'],
        'loading_analysis': cache['loading_analysis'],
        'timestamp': cache['timestamp'],
    })


@app.route('/refresh')
def refresh():
    """手动触发刷新 — 分两阶段"""
    if cache['loading_fetch']:
        return jsonify({'status': 'already_loading'})

    # 清除旧缓存
    cache['data'] = None
    cache['analysis'] = None
    cache['timestamp'] = None

    # 启动采集线程（阶段1）
    thread = threading.Thread(target=_do_fetch, daemon=True)
    thread.start()

    return jsonify({'status': 'started'})


def _do_fetch():
    """阶段1: 只采集新闻，完成后立即展示"""
    cache['loading_fetch'] = True
    cache['loading_analysis'] = False

    try:
        print('=' * 50)
        print('Phase 1: Fetching news...')
        print('=' * 50)
        news_data = fetch_all()

        # 立即缓存新闻数据
        cache['data'] = _format_news_for_display(news_data)
        cache['loading_fetch'] = False
        cache['timestamp'] = time.strftime('%Y-%m-%d %H:%M:%S')
        print('=' * 50)
        print('News ready! Starting AI analysis...')
        print('=' * 50)

        # 阶段2: AI 分析（异步，不阻塞页面）
        cache['loading_analysis'] = True
        t2 = threading.Thread(target=_do_analysis, args=(news_data,), daemon=True)
        t2.start()

    except Exception as e:
        print(f'[Error] Fetch failed: {e}')
        cache['data'] = {'error': str(e)}
        cache['loading_fetch'] = False


def _do_analysis(news_data):
    """阶段2: 后台执行 AI 分析"""
    try:
        analysis = analyze_news(news_data)
        cache['analysis'] = analysis
        print(f'Analysis complete: {len(analysis.get("analysis", ""))} chars')
    except Exception as e:
        print(f'[Error] Analysis failed: {e}')
        cache['analysis'] = {'error': str(e)}
    finally:
        cache['loading_analysis'] = False


def _format_news_for_display(raw):
    """格式化新闻数据用于前端展示"""
    formatted = {}
    for category in ['financial', 'figures', 'china']:
        items = raw.get(category, [])
        groups = {}
        for item in items:
            src = item.get('source', '其他')
            if src not in groups:
                groups[src] = []
            groups[src].append(item)
        formatted[category] = groups
    formatted['fetched_at'] = raw.get('fetched_at', '')
    return formatted


if __name__ == '__main__':
    # 启动时自动采集
    print('Starting auto-fetch on startup...')
    threading.Thread(target=_do_fetch, daemon=True).start()

    app.run(host='127.0.0.1', port=5000, debug=False, threaded=True)
