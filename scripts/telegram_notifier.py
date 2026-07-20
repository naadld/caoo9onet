import os
import json
import urllib.request
import urllib.parse

BASE_DIR = "/media/vpsg24gb/DATA1/o9o"
STATUS_JSON_PATH = os.path.join(BASE_DIR, "Video Processing/status.json")

def send_telegram_notification(msg, agent_name="System"):
    if not os.path.exists(STATUS_JSON_PATH):
        return
    try:
        with open(STATUS_JSON_PATH, "r", encoding="utf-8") as f:
            status = json.load(f)
    except Exception as e:
        print(f"Error reading status.json for telegram config: {e}")
        return

    tg = status.get("telegram", {})
    if not tg.get("enabled", False):
        return

    token = tg.get("bot_token")
    chat_id = tg.get("chat_id")
    if not token or not chat_id:
        print("Telegram configuration is incomplete.")
        return

    # Auto-format using the requested template
    formatted_msg = f"[NAADLD] Updates:\n[{agent_name}]: {msg}"

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": formatted_msg
    }
    
    thread_id = tg.get("message_thread_id")
    if thread_id:
        payload["message_thread_id"] = thread_id

    data = urllib.parse.urlencode(payload).encode("utf-8")
    try:
        req = urllib.request.Request(url, data=data)
        with urllib.request.urlopen(req, timeout=10) as response:
            print("Telegram notification sent successfully.")
    except Exception as e:
        print(f"Failed to send Telegram notification: {e}")
