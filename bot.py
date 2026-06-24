import os
import time
import json
import requests
import random
import re
from datetime import datetime, timezone

# ---------------------------------------------------------------------------
# Configuration — all values come from environment variables
# ---------------------------------------------------------------------------

LLM_API_KEY = os.environ.get("LLM_API_KEY")
LLM_API_URL = os.environ.get("LLM_API_URL")
raw_models = os.environ.get("LLM_MODEL_NAME", "gpt-3.5-turbo")
LLM_MODEL_NAME = random.choice([m.strip() for m in raw_models.split(",")])

TG_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
TG_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

# Gist credentials for persisting chat history across CI runs
GIST_ID = os.environ.get("GIST_ID")
GIST_TOKEN = os.environ.get("GIST_TOKEN")
GIST_FILENAME = "chat_history.json"

CUSTOM_PROMPT = os.environ.get(
    "CUSTOM_PROMPT",
    "You notice the group has been quiet for a while. Based on the conversation "
    "context, send a short message in the group in natural modern language (under 100 characters)."
)
FALLBACK_MSG = os.environ.get(
    "FALLBACK_MSG",
    "Heads up — it's been quiet here for a while. Everything okay? 👀"
)


def get_gist_data():
    """Fetch chat history and last modified timestamp from the Gist."""
    if not GIST_ID or not GIST_TOKEN:
        print("Gist credentials missing, skipping history fetch.")
        return [], int(time.time())

    headers = {"Authorization": f"token {GIST_TOKEN}"}
    try:
        resp = requests.get(f"https://api.github.com/gists/{GIST_ID}", headers=headers)
        resp.raise_for_status()

        # Use the Gist's last-updated timestamp for silence calculation
        updated_at_str = resp.json()["updated_at"]
        dt = datetime.strptime(updated_at_str, "%Y-%m-%dT%H:%M:%SZ").replace(
            tzinfo=timezone.utc
        )
        last_time = int(dt.timestamp())

        # Parse stored conversation history
        content = resp.json()["files"][GIST_FILENAME]["content"]
        data = json.loads(content)
        if isinstance(data, dict):
            data = []

        return data, last_time
    except Exception as e:
        print(f"Failed to read Gist: {e}")
        return [], int(time.time())


def save_history(history):
    """Persist conversation history back to the Gist."""
    if not GIST_ID or not GIST_TOKEN:
        return

    if len(history) > 20:
        history = history[-20:]

    headers = {
        "Authorization": f"token {GIST_TOKEN}",
        "Accept": "application/vnd.github.v3+json",
    }
    payload = {
        "files": {GIST_FILENAME: {"content": json.dumps(history, ensure_ascii=False)}}
    }
    try:
        requests.patch(
            f"https://api.github.com/gists/{GIST_ID}", json=payload, headers=headers
        )
    except Exception as e:
        print(f"Failed to write Gist: {e}")


def get_ai_message(history):
    """Call the LLM API to generate a reply based on conversation history."""
    if not LLM_API_URL or not LLM_API_KEY:
        return FALLBACK_MSG

    # Build message list: system prompt + recent history + trigger instruction
    messages = [{"role": "system", "content": CUSTOM_PROMPT}] + history[-20:]

    messages.append({
        "role": "user",
        "content": (
            "The group has been silent for a while. Based on the conversation "
            "context above, proactively say something in a natural tone "
            "(1–3 sentences). Do NOT use parentheses to describe actions."
        ),
    })

    payload = {
        "model": LLM_MODEL_NAME,
        "messages": messages,
    }
    headers = {
        "Authorization": f"Bearer {LLM_API_KEY}",
        "Content-Type": "application/json",
    }
    try:
        response = requests.post(LLM_API_URL, json=payload, headers=headers)
        response.raise_for_status()

        raw_text = response.json()["choices"][0]["message"]["content"]
        clean_text = re.sub(r"<think>.*?</think>", "", raw_text, flags=re.DOTALL).strip()

        return clean_text if clean_text else FALLBACK_MSG
    except Exception as e:
        print(f"API call failed: {e}")
        if "response" in locals():
            print(f"API response body: {response.text}")
        return FALLBACK_MSG


def send_to_telegram(text):
    """Send a message to the configured Telegram chat."""
    tg_url = f"https://api.telegram.org/bot{TG_BOT_TOKEN}/sendMessage"
    payload = {"chat_id": TG_CHAT_ID, "text": text, "parse_mode": "Markdown"}
    requests.post(tg_url, json=payload)


if __name__ == "__main__":
    current_time = int(time.time())

    history, last_interaction_time = get_gist_data()
    silence_duration = current_time - last_interaction_time

    # Random threshold between 1–2 hours so the bot doesn't fire at the same time every cycle
    dynamic_patience = random.randint(3600, 7200)

    if silence_duration >= dynamic_patience:
        print(
            f"Silence {silence_duration}s exceeds threshold {dynamic_patience}s "
            f"— sending AI message."
        )

        msg = get_ai_message(history)
        send_to_telegram(msg)

        # Append this reply to history and persist
        history.append({"role": "assistant", "content": msg})
        save_history(history)
    else:
        print(
            f"Silence {silence_duration}s within threshold {dynamic_patience}s "
            f"— waiting."
        )
