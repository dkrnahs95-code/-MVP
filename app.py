import json
import os
import time
import datetime
import requests
import feedparser
from flask import Flask, jsonify, request
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

DATA_FILE = 'data.json'

# ==========================================
# 🔴 配置区域 (请在此处填入你的飞书应用信息)
# ==========================================
FEISHU_APP_ID = "cli_a9bd09639db91bef"      # 在飞书开发者后台获取
FEISHU_APP_SECRET = "PuCyJKV7INLp934czIQvPeJPOKEuUSE3"  # 在飞书开发者后台获取  
FEISHU_CALENDAR_ID = "feishu.cn_QtxRQxvJnNM8DXWFVUXyJe@group.calendar.feishu.cn" # 如果已修改为真实ID请保留你的修改

# ==========================================
# 🛠️ 基础数据读写
# ==========================================
def load_data():
    # 默认结构：todos列表，cards列表
    if not os.path.exists(DATA_FILE):
        return {"todos": [], "cards": []}
    with open(DATA_FILE, 'r', encoding='utf-8') as f:
        data = json.load(f)
        # 兼容性处理：如果 old data.json 里没有 cards 字段
        if 'cards' not in data:
            data['cards'] = []
        return data

def save_data(data):
    with open(DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

# ==========================================
# 🤖 功能模块：AI 新闻 / 飞书 (逻辑优化版)
# ==========================================
def fetch_ai_news():
    rss_url = "https://techcrunch.com/category/artificial-intelligence/feed/"
    feed = feedparser.parse(rss_url)
    new_cards = []
    
    for entry in feed.entries[:5]: 
        title = entry.title
        link = entry.link
        # 生成带 ID 的对象结构
        card = {
            "id": int(time.time() * 1000) + len(new_cards), # 防止ID重复
            "content": f"<strong>[AI热点]</strong> <a href='{link}' target='_blank'>{title}</a>",
            "type": "ai", # 标记类型，方便前端变色
            "created_at": time.time()
        }
        new_cards.append(card)
    return new_cards

def get_feishu_token():
    url = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
    headers = {"Content-Type": "application/json; charset=utf-8"}
    payload = {"app_id": FEISHU_APP_ID, "app_secret": FEISHU_APP_SECRET}
    try:
        resp = requests.post(url, json=payload)
        return resp.json().get("tenant_access_token")
    except:
        return None

def sync_feishu_calendar():
    token = get_feishu_token()
    if not token: return []
    
    url = f"https://open.feishu.cn/open-apis/calendar/v4/calendars/{FEISHU_CALENDAR_ID}/events"
    headers = {"Authorization": f"Bearer {token}"}
    now = datetime.datetime.now()
    start_time = int(now.replace(hour=0, minute=0, second=0).timestamp())
    end_time = int(now.replace(hour=23, minute=59, second=59).timestamp())

    try:
        resp = requests.get(url, headers=headers, params={"start_time": str(start_time), "end_time": str(end_time)})
        events = []
        if resp.status_code == 200:
            data = resp.json()
            if 'data' in data and 'items' in data['data']:
                for item in data['data']['items']:
                    start_ts = int(item['start_time']['timestamp'])
                    dt_object = datetime.datetime.fromtimestamp(start_ts)
                    events.append({
                        "id": int(time.time() * 1000) + start_ts,
                        "time": dt_object.strftime("%H:%M"),
                        "desc": f"[飞书] {item['summary']}"
                    })
        return events
    except:
        return []

# ==========================================
# 🌐 API 接口路由
# ==========================================

@app.route('/api/data', methods=['GET'])
def get_data():
    return jsonify(load_data())

# --- 待办事项 (Todos) ---
@app.route('/api/todos', methods=['POST'])
def add_todo():
    new_task = request.json
    new_task['id'] = int(time.time() * 1000)
    data = load_data()
    data['todos'].append(new_task)
    save_data(data)
    return jsonify({"message": "OK"})

@app.route('/api/todos/<int:task_id>', methods=['DELETE'])
def delete_todo(task_id):
    data = load_data()
    data['todos'] = [t for t in data['todos'] if t['id'] != task_id]
    save_data(data)
    return jsonify({"message": "Deleted"})

# --- 信息卡片 (Cards) 新增接口 ---
@app.route('/api/cards', methods=['POST'])
def add_card():
    # 前端发来 {content: "xxx"}
    req_data = request.json
    new_card = {
        "id": int(time.time() * 1000),
        "content": req_data.get('content'),
        "type": "memo", # 默认为手动备忘
        "created_at": time.time()
    }
    data = load_data()
    # 把新卡片插到最前面
    data['cards'].insert(0, new_card)
    save_data(data)
    return jsonify({"message": "Card Added"})

@app.route('/api/cards/<int:card_id>', methods=['DELETE'])
def delete_card(card_id):
    data = load_data()
    # 过滤掉要删除的卡片
    data['cards'] = [c for c in data['cards'] if c['id'] != card_id]
    save_data(data)
    return jsonify({"message": "Card Deleted"})

# --- Agent 触发器 ---
@app.route('/api/agent/news', methods=['POST'])
def trigger_news_agent():
    try:
        news_cards = fetch_ai_news()
        data = load_data()
        # 将新闻合并到开头
        for card in reversed(news_cards):
            data['cards'].insert(0, card)
        save_data(data)
        return jsonify({"message": f"已抓取 {len(news_cards)} 条新闻"})
    except Exception as e:
        return jsonify({"message": "抓取失败"}), 500

@app.route('/api/sync/feishu', methods=['POST'])
def trigger_feishu_sync():
    events = sync_feishu_calendar()
    data = load_data()
    for event in events:
        # 简单去重：如果ID不存在才添加 (实际可能需要更复杂的逻辑)
        if not any(t['desc'] == event['desc'] for t in data['todos']):
            data['todos'].append(event)
    data['todos'].sort(key=lambda x: x['time'])
    save_data(data)
    return jsonify({"message": f"同步完成"})

if __name__ == '__main__':
    print("🚀 服务器运行中...")
    app.run(debug=True, port=5000)