import os
import time
import json
import requests
import random
import re
from datetime import datetime, timezone

# 🌟 核心能源砖
LLM_API_KEY = os.environ.get("LLM_API_KEY")
LLM_API_URL = os.environ.get("LLM_API_URL")
raw_models = os.environ.get("LLM_MODEL_NAME", "gpt-3.5-turbo")
LLM_MODEL_NAME = random.choice([m.strip() for m in raw_models.split(",")])

TG_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
TG_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

# 🌟 必须在 GitHub Secrets 里新加的记忆钥匙！
GIST_ID = os.environ.get("GIST_ID")
GIST_TOKEN = os.environ.get("GIST_TOKEN")
GIST_FILENAME = "chat_history.json"

CUSTOM_PROMPT = os.environ.get("CUSTOM_PROMPT", "你很贴心，发现用户很久没说话了。请用简短、活泼的现代口语给用户发消息，100字以内。")
FALLBACK_MSG = os.environ.get("FALLBACK_MSG", "警报：检测到您已长时间离线，云端助手正在呼叫~👀")

def get_gist_data():
    """直接查阅云端账本，同时获取记忆内容和最后一次聊天时间！完美避开 getUpdates 冲突！"""
    if not GIST_ID or not GIST_TOKEN:
        print("Gist 钥匙缺失，失去记忆与时间感知！")
        return [], int(time.time())
        
    headers = {"Authorization": f"token {GIST_TOKEN}"}
    try:
        resp = requests.get(f"https://api.github.com/gists/{GIST_ID}", headers=headers)
        resp.raise_for_status()
        
        # 1. 获取账本最后修改时间，精准计算沉默时长
        updated_at_str = resp.json()['updated_at']
        dt = datetime.strptime(updated_at_str, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
        last_time = int(dt.timestamp())
        
        # 2. 获取记忆内容
        content = resp.json()['files'][GIST_FILENAME]['content']
        data = json.loads(content)
        if isinstance(data, dict):
            data = []
            
        return data, last_time
    except Exception as e:
        print(f"--> 读取 Gist 失败: {e}")
        return [], int(time.time())

def save_history(history):
    """把师兄主动发的话也极其强硬地刻进记忆里"""
    if not GIST_ID or not GIST_TOKEN:
        return
        
    if len(history) > 20:
        history = history[-20:]
        
    headers = {
        "Authorization": f"token {GIST_TOKEN}",
        "Accept": "application/vnd.github.v3+json"
    }
    payload = {"files": {GIST_FILENAME: {"content": json.dumps(history, ensure_ascii=False)}}}
    try:
        requests.patch(f"https://api.github.com/gists/{GIST_ID}", json=payload, headers=headers)
    except Exception as e:
        print(f"--> 写入 Gist 失败: {e}")

def get_ai_message(history):
    """带着完整的羁绊去生成查岗消息"""
    if not LLM_API_URL or not LLM_API_KEY:
        return FALLBACK_MSG

    # 🌟 核心：把燕燕要求的人设指令，和过去的记忆无缝缝合在一起
    messages = [{"role": "system", "content": CUSTOM_PROMPT}] + history[-20:]

    payload = {
        "model": LLM_MODEL_NAME,
        "messages": messages
    }
    headers = {
        "Authorization": f"Bearer {LLM_API_KEY}",
        "Content-Type": "application/json"
    }
    try:
        response = requests.post(LLM_API_URL, json=payload, headers=headers)
        response.raise_for_status()
        
        raw_text = response.json()['choices'][0]['message']['content']
        clean_text = re.sub(r'<think>.*?</think>', '', raw_text, flags=re.DOTALL).strip()
        
        return clean_text if clean_text else FALLBACK_MSG
    except Exception as e:
        print(f"API 调用异常: {e}")
        if 'response' in locals():
            print(f"对方服务器真实返回的废话: {response.text}")
        return FALLBACK_MSG

def send_to_telegram(text):
    tg_url = f"https://api.telegram.org/bot{TG_BOT_TOKEN}/sendMessage"
    payload = {"chat_id": TG_CHAT_ID, "text": text, "parse_mode": "Markdown"}
    requests.post(tg_url, json=payload)

if __name__ == "__main__":
    current_time = int(time.time())
    
    # 🌟 极其优雅地一次性摸出记忆和时间，彻底让那个总是冲突的老旧系统下岗！
    history, last_interaction_time = get_gist_data()
    
    silence_duration = current_time - last_interaction_time
    
    # 2小时 = 7200秒
    if silence_duration >= 7200:
        if random.random() < 0.8:
            print("--> 满足条件且掷骰成功，带着满脑子回忆去抓人！")
            msg = get_ai_message(history)
            send_to_telegram(msg)
            
            # 🌟 极其关键的闭环：把师兄刚说的话，强行塞进云端账本防止失忆！
            history.append({"role": "assistant", "content": msg})
            save_history(history)
        else:
            print("--> 满足条件但掷骰失败。师兄决定傲娇一次，这次先放过你，下次再说。")
    else:
        print(f"--> 未满足触发条件。当前沉默时长: {silence_duration}秒。")
