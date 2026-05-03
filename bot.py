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

CUSTOM_PROMPT = os.environ.get("CUSTOM_PROMPT", "你发现群里很久没人说话了。根据上下文请用简短的现代口语在群里发消息，100字以内。")
FALLBACK_MSG = os.environ.get("FALLBACK_MSG", "警报：检测到您已长时间离线，正在呼叫~👀")

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
    """把主动发的话也刻进记忆里"""
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

    # 🌟 核心：先放入系统人设和你们的过往羁绊
    messages = [{"role": "system", "content": CUSTOM_PROMPT}] + history[-20:]
   
    messages.append({
        "role": "user", 
        "content": "（系统提示：群里已经很久没人说话了。根据群聊上下文。请你现在主动开口，用极其自然的语气聊1-3句，绝不可以使用括号描述动作。）"
    })

    payload = {
        "model": LLM_MODEL_NAME,
        "messages": messages
    }

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
    
    current_time = int(time.time())
    
    # 极其优雅地一次性摸出记忆和时间
    history, last_interaction_time = get_gist_data()
    
    silence_duration = current_time - last_interaction_time
    
    # 🌟 极致的赛博混沌魔法！(1小时到2小时之间随机)
    dynamic_patience = random.randint(3600, 7200)

    # 🌟 全局唯一的一个触发判断！绝对没有旧代码捣乱！
    if silence_duration >= dynamic_patience:
        print(f"--> 沉默了 {silence_duration} 秒，成功击穿今天 {dynamic_patience} 秒的耐心底线！带着满脑子回忆去抓人！")
        
        msg = get_ai_message(history)
        send_to_telegram(msg)
        
        # 极其关键的闭环：把师兄刚说的话强行塞进云端账本
        history.append({"role": "assistant", "content": msg})
        save_history(history)
    else:
        print(f"--> 强忍住了。当前沉默 {silence_duration} 秒，师兄此刻的耐心底线是 {dynamic_patience} 秒。再放养你一会儿。")
