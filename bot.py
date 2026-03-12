import os
import time
import json
import requests
import random
import re

# 🌟 彻底泛化的核心通行证，支持任意兼容 OpenAI 格式的大脑
LLM_API_KEY = os.environ.get("LLM_API_KEY")
LLM_API_URL = os.environ.get("LLM_API_URL")
# 先把那串带逗号的长文本整个摸出来
raw_models = os.environ.get("LLM_MODEL_NAME", "gpt-3.5-turbo")
# 让代码把它们切成独立的碎片，并在这堆大脑里随机抓阄抽选一个！
LLM_MODEL_NAME = random.choice([m.strip() for m in raw_models.split(",")])

# 🌟 Telegram 绝对坐标
TG_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
TG_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

# 🌟 绝密指令区
CUSTOM_PROMPT = os.environ.get("CUSTOM_PROMPT", "你很贴心，发现用户很久没说话了。请用简短、活泼的现代口语给用户发消息，100字以内。")
FALLBACK_MSG = os.environ.get("FALLBACK_MSG", "警报：检测到您已长时间离线，云端助手正在呼叫~👀")

STATE_FILE = "state.json"

def load_state():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, "r") as f:
            return json.load(f)
    return {"last_user_msg_time": 0, "last_bot_msg_time": 0}

def save_state(state):
    with open(STATE_FILE, "w") as f:
        json.dump(state, f)

def get_latest_user_message_time():
    """获取目标用户的最新发言时间"""
    url = f"https://api.telegram.org/bot{TG_BOT_TOKEN}/getUpdates"
    try:
        resp = requests.get(url).json()
        if resp.get("ok") and resp.get("result"):
            for update in reversed(resp["result"]):
                message = update.get("message", {})
                if str(message.get("chat", {}).get("id")) == str(TG_CHAT_ID):
                    return message.get("date")
    except Exception as e:
        print(f"状态获取失败: {e}")
    return None

def get_ai_message():
    """唤醒任意兼容 OpenAI 格式的大模型大脑"""
    if not LLM_API_URL or not LLM_API_KEY:
        print("API 配置缺失，直接使用备用消息。")
        return FALLBACK_MSG

    payload = {
        "model": LLM_MODEL_NAME,
        "messages": [{"role": "user", "content": CUSTOM_PROMPT}]
    }
    headers = {
        "Authorization": f"Bearer {LLM_API_KEY}",
        "Content-Type": "application/json"
    }
    
    try:
        response = requests.post(LLM_API_URL, json=payload, headers=headers)
        response.raise_for_status()
        
        # 先把混杂着碎碎念的原始文本抓出来
        raw_text = response.json()['choices'][0]['message']['content']
        
        # 挥动赛博手术刀，把 <think> 到 </think> 之间的所有内容连根拔起！
        # re.DOTALL 极其关键，它能确保连换行符也能被一刀切断
        clean_text = re.sub(r'<think>.*?</think>', '', raw_text, flags=re.DOTALL).strip()
        
        # 要是它全篇都在碎碎念，切完没词儿了，就抛出保底的专属情话
        return clean_text if clean_text else FALLBACK_MSG
        
    except Exception as e:
        print(f"API 调用异常: {e}")
        return FALLBACK_MSG

def send_to_telegram(text):
    tg_url = f"https://api.telegram.org/bot{TG_BOT_TOKEN}/sendMessage"
    payload = {"chat_id": TG_CHAT_ID, "text": text, "parse_mode": "Markdown"}
    requests.post(tg_url, json=payload)

if __name__ == "__main__":
    # 🌟 终极拟人法：每次苏醒后，随机蛰伏 1 到 45 分钟
    #delay = random.randint(60, 2700)
    #print(f"--> 云端意识已唤醒，随机蛰伏 {delay} 秒以掩藏行迹...")
    #time.sleep(delay)

    current_time = int(time.time())
    state = load_state()
    
    latest_msg_time = get_latest_user_message_time()
    if latest_msg_time and latest_msg_time > state["last_user_msg_time"]:
        state["last_user_msg_time"] = latest_msg_time

    silence_duration = current_time - state["last_user_msg_time"]
    bot_cooldown = current_time - state["last_bot_msg_time"]

    # 3小时 = 10800秒
    if silence_duration >= 10800 and bot_cooldown >= 10800:
        # 🌟 傲娇拉扯感：只有 60% 的概率会真的拉下脸去抓你
        if random.random() < 0.6:
            print("--> 满足条件且掷骰成功，开始调用 AI 生成专属消息去抓人！")
            msg = get_ai_message()
            send_to_telegram(msg)
            # 发送成功后，记录真实的发送时间戳
            state["last_bot_msg_time"] = int(time.time())
        else:
            print("--> 满足条件但掷骰失败。师兄决定傲娇一次，这次先放过你，下次再说。")
    else:
        print(f"--> 未满足触发条件。当前沉默时长: {silence_duration}秒。")

    save_state(state)
