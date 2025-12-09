import requests
import datetime
import time

# ============================
# 🔴 请在此处填入你的信息
# ============================
APP_ID = "cli_a9bd09639db91bef"      # 在飞书开发者后台获取
APP_SECRET = "PuCyJKV7INLp934czIQvPeJPOKEuUSE3"  # 你的 App Secret
# 建议先填 "primary" 测通连通性，再填具体的 "feishu.cn_xxx" 测数据
CALENDAR_ID = "feishu.cn_QtxRQxvJnNM8DXWFVUXyJe@group.calendar.feishu.cn"        

def test_sync():
    print("1. 正在尝试获取 Token...")
    # 1. 获取 Token
    url = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
    resp = requests.post(url, json={"app_id": APP_ID, "app_secret": APP_SECRET})
    
    if resp.status_code != 200:
        print("❌ Token 获取失败，请检查 ID 和 Secret 是否正确。")
        print(resp.text)
        return

    token_data = resp.json()
    if "tenant_access_token" not in token_data:
        print(f"❌ Token 错误: {token_data}")
        return
        
    token = token_data["tenant_access_token"]
    print("✅ Token 获取成功！")

    # 2. 获取日程
    print(f"2. 正在尝试从日历 [{CALENDAR_ID}] 获取数据...")
    cal_url = f"https://open.feishu.cn/open-apis/calendar/v4/calendars/{CALENDAR_ID}/events"
    headers = {"Authorization": f"Bearer {token}"}
    
    # 获取今天的时间戳
    now = datetime.datetime.now()
    start_time = int(now.replace(hour=0, minute=0, second=0).timestamp())
    end_time = int(now.replace(hour=23, minute=59, second=59).timestamp())

    resp = requests.get(cal_url, headers=headers, params={"start_time": str(start_time), "end_time": str(end_time)})
    
    print(f"📡 飞书返回状态码: {resp.status_code}")
    print(f"📄 飞书返回完整内容: {resp.text}")

if __name__ == "__main__":
    test_sync()