import json
import os
import time
import datetime
import random
import requests
import feedparser
from flask import Flask, jsonify, request
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

DATA_FILE = 'data.json'

# ==========================================
# 🔴 配置区域
# ==========================================
FEISHU_APP_ID = "cli_a9bd09639db91bef"      
FEISHU_APP_SECRET = "PuCyJKV7INLp934czIQvPeJPOKEuUSE3"
FEISHU_CALENDAR_ID = "feishu.cn_QtxRQxvJnNM8DXWFVUXyJe@group.calendar.feishu.cn"

# 📚 激励语录库 (每一次刷新随机挑一个，除非你有自定义的)
QUOTE_LIBRARY = [
    "种一棵树最好的时间是十年前，其次是现在。",
    "流水不争先，争的是滔滔不绝。",
    "道阻且长，行则将至。",
    "悲观者正确，乐观者成功。",
    "保持饥饿，保持愚蠢。",
    "也就是现在的你，才能定义未来的你。",
    "效率是把事情做对，效能是做对的事情。",
    "我们的绳子上已经打了太多人的结。",
    "你走的每一步，都算数。",
    "我不怕孤单，只怕习惯了有人陪。",
    "人一旦有了梦想，怎么活都是有灵魂的。",
    "见好就收，不行就撤。",
    "平芜尽处是春山。",
    "少年当有落子无悔的勇气。",
    "牛羊成群，猛虎独行。",
    "人生当如蜡烛一样，从头燃烧到尾，始终光明。",
    "攀一座山，看一场雪，追一个梦。",
    "离群索居者，不是神明，就是野兽。",
    "过了河的悍卒，沾了血，就不能回头了。无关利弊。那是勇气。",
    "永远年轻，永远赤诚，永远热泪盈眶，永远渴望踏上新的征程。",
    "当殊死搏杀的最后时刻，那种从底层拼搏上来的小人物才最可怕。",
    "你活得简单，这世界就能简单。",
    "永远少年"

]

# ==========================================
# 🛠️ 基础数据读写
# ==========================================
def load_data():
    default_data = {
        "todos": [], 
        "cards": [], 
        "settings": {
            "progress": 30,        # 默认进度
            "custom_quote": ""     # 用户自定义语录，如果有值则优先显示
        }
    }
    
    if not os.path.exists(DATA_FILE):
        return default_data
        
    with open(DATA_FILE, 'r', encoding='utf-8') as f:
        data = json.load(f)
        # 兼容性补丁：防止旧文件没有 settings 字段报错
        if 'settings' not in data:
            data['settings'] = default_data['settings']
        return data

def save_data(data):
    with open(DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

# ==========================================
# 🤖 业务逻辑
# ==========================================
def fetch_ai_news():
    rss_url = "https://techcrunch.com/category/artificial-intelligence/feed/"
    try:
        feed = feedparser.parse(rss_url)
        new_cards = []
        for entry in feed.entries[:5]: 
            card = {
                "id": int(time.time() * 1000) + len(new_cards),
                "content": f"<strong>[AI热点]</strong> <a href='{entry.link}' target='_blank'>{entry.title}</a>",
                "type": "ai",
                "created_at": time.time()
            }
            new_cards.append(card)
        return new_cards
    except:
        return []

def get_feishu_token():
    url = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
    try:
        resp = requests.post(url, json={"app_id": FEISHU_APP_ID, "app_secret": FEISHU_APP_SECRET})
        return resp.json().get("tenant_access_token")
    except:
        return None

# 🎯 升级：支持传入指定日期字符串 "YYYY-MM-DD"
def sync_feishu_calendar(target_date_str=None):
    token = get_feishu_token()
    if not token: return []
    
    url = f"https://open.feishu.cn/open-apis/calendar/v4/calendars/{FEISHU_CALENDAR_ID}/events"
    headers = {"Authorization": f"Bearer {token}"}
    
    # 确定时间范围
    if target_date_str:
        # 如果用户选了日期，用选的日期
        target_date = datetime.datetime.strptime(target_date_str, "%Y-%m-%d")
    else:
        # 默认今天
        target_date = datetime.datetime.now()

    start_time = int(target_date.replace(hour=0, minute=0, second=0).timestamp())
    end_time = int(target_date.replace(hour=23, minute=59, second=59).timestamp())

    try:
        resp = requests.get(url, headers=headers, params={"start_time": str(start_time), "end_time": str(end_time)})
        events = []
        if resp.status_code == 200:
            data = resp.json()
            if 'data' in data and 'items' in data['data']:
                for item in data['data']['items']:
                    start_ts = int(item['start_time']['timestamp'])
                    dt_object = datetime.datetime.fromtimestamp(start_ts)
                    feishu_id = item['event_id']
                    task_id = abs(hash(feishu_id)) % (10 ** 9)

                    events.append({
                        "id": task_id,
                        "feishu_id": feishu_id,
                        "time": dt_object.strftime("%H:%M"),
                        "desc": item['summary'], # 获取日程名字
                        "type": "feishu",
                        "link": item.get('app_link')
                    })
        return events
    except Exception as e:
        print(f"Sync Error: {e}")
        return []

# ==========================================
# 🌐 API 接口路由
# ==========================================

@app.route('/api/data', methods=['GET'])
def get_data():
    data = load_data()
    # 逻辑：如果用户没写自定义语录，后端随机给一句发过去
    if not data['settings']['custom_quote']:
        data['random_quote'] = random.choice(QUOTE_LIBRARY)
    return jsonify(data)

# [新增] 更新设置 (进度条 & 语录)
@app.route('/api/settings', methods=['PUT'])
def update_settings():
    req = request.json
    data = load_data()
    if 'progress' in req:
        data['settings']['progress'] = req['progress']
    if 'custom_quote' in req:
        data['settings']['custom_quote'] = req['custom_quote']
    save_data(data)
    return jsonify({"message": "Settings Updated"})

# [修改] 飞书同步接口，接收日期参数
@app.route('/api/sync/feishu', methods=['POST'])
def trigger_feishu():
    req = request.json
    date_str = req.get('date') # 获取前端传来的日期 "2023-10-27"
    
    incoming_events = sync_feishu_calendar(date_str)
    data = load_data()
    
    modified_feishu_ids = {t.get('feishu_id') for t in data['todos'] if t.get('type') == 'feishu-modified'}
    
    # 删除旧的飞书镜像
    data['todos'] = [t for t in data['todos'] if t.get('type') != 'feishu']
    
    count = 0
    for event in incoming_events:
        if event.get('feishu_id') in modified_feishu_ids:
            continue
        data['todos'].append(event)
        count += 1
        
    data['todos'].sort(key=lambda x: x['time'])
    save_data(data)
    return jsonify({"message": f"同步完成，获取了 {count} 个日程"})

# --- 其他原有接口保持不变 (Todos, Cards) ---
@app.route('/api/todos', methods=['POST'])
def add_todo():
    new_task = request.json
    new_task['id'] = int(time.time() * 1000)
    new_task['type'] = 'manual'
    data = load_data()
    data['todos'].append(new_task)
    save_data(data)
    return jsonify({"message": "OK"})

@app.route('/api/todos/<int:task_id>', methods=['PUT'])
def update_todo(task_id):
    update_data = request.json 
    data = load_data()
    for task in data['todos']:
        if task['id'] == task_id:
            task['desc'] = update_data.get('desc', task['desc'])
            task['time'] = update_data.get('time', task['time'])
            if task.get('type') == 'feishu':
                task['type'] = 'feishu-modified'
            break
    save_data(data)
    return jsonify({"message": "Updated"})

@app.route('/api/todos/<int:task_id>', methods=['DELETE'])
def delete_todo(task_id):
    data = load_data()
    data['todos'] = [t for t in data['todos'] if t['id'] != task_id]
    save_data(data)
    return jsonify({"message": "Deleted"})

@app.route('/api/cards', methods=['POST'])
def add_card():
    req_data = request.json
    new_card = {"id": int(time.time()*1000), "content": req_data.get('content'), "type": "memo"}
    data = load_data()
    data['cards'].insert(0, new_card)
    save_data(data)
    return jsonify({"message": "Added"})

@app.route('/api/cards/<int:card_id>', methods=['DELETE'])
def delete_card(card_id):
    data = load_data()
    data['cards'] = [c for c in data['cards'] if c['id'] != card_id]
    save_data(data)
    return jsonify({"message": "Deleted"})

@app.route('/api/cards/<int:card_id>', methods=['PUT'])
def update_card(card_id):
    update_data = request.json
    data = load_data()
    for card in data['cards']:
        if card['id'] == card_id:
            card['content'] = update_data.get('content', card['content'])
            break
    save_data(data)
    return jsonify({"message": "Updated"})

@app.route('/api/agent/news', methods=['POST'])
def trigger_news():
    news_cards = fetch_ai_news()
    data = load_data()
    for card in reversed(news_cards):
        data['cards'].insert(0, card)
    save_data(data)
    return jsonify({"message": "OK"})

if __name__ == '__main__':
    app.run(debug=True, port=5000)