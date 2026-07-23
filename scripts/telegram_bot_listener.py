#!/usr/bin/env python3
"""
O9O.NET Telegram Bot Command Listener (Topic 3953 Enabled)
Listens for manual Telegram commands:
  - /step 1 XX.yyy         (Normal scrape for Grade XX, Day yyy - skips existing)
  - /step 1 force XX.yyy   (Force re-download Grade XX, Day yyy - overwrites existing)
"""

import os
import sys
import re
import json
import time
import subprocess
import urllib.request
import urllib.parse
from datetime import datetime, timezone, timedelta

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OFFSET_FILE = os.path.join(BASE_DIR, ".telegram_offset")

PRIMARY_BOT_TOKEN = "8525129998:AAG6-Ib_AfqEGc7jwroo58reg5UVYlRZ-3A"
FALLBACK_BOT_TOKEN = "8733078949:AAEX6WGeGasyVHXEYqgadgE8RFovyr64lBg"
DEFAULT_CHAT_ID = "-1003954353565"
DEFAULT_THREAD_ID = 3953

def normalize_grade(val):
    if not val:
        return None
    val = str(val).strip().upper()
    mapping = {
        "01": "Grade 1", "1": "Grade 1", "G1": "Grade 1", "GRADE 1": "Grade 1", "GRADE1": "Grade 1",
        "02": "Grade 2", "2": "Grade 2", "G2": "Grade 2", "GRADE 2": "Grade 2", "GRADE2": "Grade 2",
        "03": "Grade 3", "3": "Grade 3", "G3": "Grade 3", "GRADE 3": "Grade 3", "GRADE3": "Grade 3",
        "04": "Grade 4", "4": "Grade 4", "G4": "Grade 4", "GRADE 4": "Grade 4", "GRADE4": "Grade 4",
        "05": "Grade 5", "5": "Grade 5", "G5": "Grade 5", "GRADE 5": "Grade 5", "GRADE5": "Grade 5",
        "06": "Grade 6", "6": "Grade 6", "G6": "Grade 6", "GRADE 6": "Grade 6", "GRADE6": "Grade 6",
        "07": "Grade 7", "7": "Grade 7", "G7": "Grade 7", "GRADE 7": "Grade 7", "GRADE7": "Grade 7",
        "08": "Grade 8", "8": "Grade 8", "G8": "Grade 8", "GRADE 8": "Grade 8", "GRADE8": "Grade 8",
        "09": "Grade 9", "9": "Grade 9", "G9": "Grade 9", "GRADE 9": "Grade 9", "GRADE9": "Grade 9",
        "10": "Grade 10", "G10": "Grade 10", "GRADE 10": "Grade 10", "GRADE10": "Grade 10",
        "11": "Grade 11", "G11": "Grade 11", "GRADE 11": "Grade 11", "GRADE11": "Grade 11",
        "12": "Grade 12", "G12": "Grade 12", "GRADE 12": "Grade 12", "GRADE12": "Grade 12",
        "K4": "K4", "K4.": "K4",
        "K5": "K5", "K5.": "K5"
    }
    return mapping.get(val, val)

def send_telegram_reply(text, chat_id=DEFAULT_CHAT_ID, thread_id=DEFAULT_THREAD_ID):
    token = os.getenv("TELEGRAM_BOT_TOKEN") or PRIMARY_BOT_TOKEN
    tokens_to_try = [token]
    if token != FALLBACK_BOT_TOKEN:
        tokens_to_try.append(FALLBACK_BOT_TOKEN)

    for tok in tokens_to_try:
        url = f"https://api.telegram.org/bot{tok}/sendMessage"
        payload = {
            "chat_id": chat_id,
            "text": text
        }
        if thread_id:
            payload["message_thread_id"] = thread_id

        data = urllib.parse.urlencode(payload).encode("utf-8")
        try:
            req = urllib.request.Request(url, data=data)
            with urllib.request.urlopen(req, timeout=10) as resp:
                if resp.status == 200:
                    return True
        except Exception as e:
            print(f"⚠️ Reply error ({tok[:10]}...): {e}")
    return False

def get_github_pat():
    pat = os.getenv("GITHUB_PAT")
    if pat:
        return pat
    cred_file = os.path.expanduser("~/.git-credentials")
    if os.path.exists(cred_file):
        try:
            with open(cred_file, "r") as f:
                content = f.read()
                m = re.search(r'https://[^:]+:([^@]+)@github\.com', content)
                if m:
                    return m.group(1).strip()
        except Exception:
            pass
    return ""

def trigger_github_workflow(grade, day, force=False):
    pat = get_github_pat()
    if not pat:
        print("⚠️ GitHub PAT Token not found in environment or ~/.git-credentials.")
        return False, "Không tìm thấy GitHub PAT token."

    url = "https://api.github.com/repos/naadld/caoo9onet/actions/workflows/1_scraper_stream.yml/dispatches"
    headers = {
        "Accept": "application/vnd.github+json",
        "Authorization": f"Bearer {pat}",
        "X-GitHub-Api-Version": "2022-11-28",
        "Content-Type": "application/json"
    }

    payload = {
        "ref": "main",
        "inputs": {
            "max_days": "1",
            "grade": str(grade),
            "day": str(day),
            "force": "true" if force else "false"
        }
    }

    data = json.dumps(payload).encode("utf-8")
    try:
        req = urllib.request.Request(url, data=data, headers=headers, method="POST")
        with urllib.request.urlopen(req, timeout=15) as resp:
            if resp.status in (204, 200, 201):
                return True, "Đã gửi lệnh kích hoạt GitHub Actions Cloud thành công!"
            return False, f"GitHub API trả về HTTP {resp.status}"
    except Exception as e:
        return False, f"Lỗi gọi GitHub API: {e}"

def load_offset():
    if os.path.exists(OFFSET_FILE):
        try:
            with open(OFFSET_FILE, "r") as f:
                return int(f.read().strip())
        except Exception:
            pass
    return None

def save_offset(offset):
    try:
        with open(OFFSET_FILE, "w") as f:
            f.write(str(offset))
    except Exception as e:
        print(f"⚠️ Cannot save offset: {e}")

def process_command(text, chat_id, thread_id):
    pattern = r'^/step\s*1(?:\s+(force))?\s+([a-zA-Z0-9]+)[\._](\d+)'
    m = re.search(pattern, text, re.IGNORECASE)
    if not m:
        return

    is_force = bool(m.group(1))
    raw_grade = m.group(2)
    raw_day = m.group(3)

    grade = normalize_grade(raw_grade)
    try:
        day = int(raw_day)
    except ValueError:
        return

    vn_tz = timezone(timedelta(hours=7))
    now_str = datetime.now(vn_tz).strftime("%Y-%m-%d %H:%M:%S")

    mode_text = "FORCE (Ghi đè file cũ)" if is_force else "THƯỜNG (Bỏ qua bài đã có)"

    ack_msg = (
        f"📥 [ĐÃ NHẬN LỆNH THỦ CÔNG /step 1]\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"📚 Grade: {grade}\n"
        f"📅 Ngày: Ngày {day:03d}\n"
        f"⚡ Chế độ: {mode_text}\n"
        f"⏰ Thời gian: {now_str}\n"
        f"🚀 Đang khởi chạy tiến trình cào trên GitHub Actions Cloud..."
    )
    send_telegram_reply(ack_msg, chat_id, thread_id)

    success, info = trigger_github_workflow(grade, day, is_force)
    if success:
        send_telegram_reply(f"✅ [KÍCH HOẠT THÀNH CÔNG]\n{info}\n🔗 Theo dõi tại: https://github.com/naadld/caoo9onet/actions", chat_id, thread_id)
    else:
        # Fallback to local background execution if GitHub trigger fails
        send_telegram_reply(f"⚠️ {info}\n⚡ Đang chuyển sang chạy dự phòng trên VPS...", chat_id, thread_id)
        cmd = f"python3 {os.path.join(BASE_DIR, 'scripts/step1_direct_stream.py')} --grade \"{grade}\" --day {day} {'--force' if is_force else ''} --force-local --max-days 1 >> {os.path.join(BASE_DIR, 'stream.log')} 2>&1 &"
        subprocess.Popen(cmd, shell=True, cwd=BASE_DIR)

def process_help(chat_id, thread_id):
    help_msg = (
        f"📖 [HƯỚNG DẪN SỬ DỤNG LỆNH CÀO VIDEO]\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"🔹 1. CÀO THƯỜNG (Bỏ qua bài đã có):\n"
        f"   👉 Cú pháp: /step 1 XX.yyy\n"
        f"   👉 Ví dụ: /step 1 01.010\n"
        f"      (Cào bài Grade 1, Ngày 10 - chỉ tải bài chưa có)\n\n"
        f"🔹 2. CÀO ÉP BUỘC (Ghi đè bài cũ):\n"
        f"   👉 Cú pháp: /step 1 force XX.yyy\n"
        f"   👉 Ví dụ: /step 1 force K4.150\n"
        f"      (Tải lại & ghi đè Level K4, Ngày 150)\n\n"
        f"📌 MÃ GRADE (XX):\n"
        f"▪️ 01..12 tương ứng Grade 1..12\n"
        f"▪️ K4, K5 tương ứng Level K4, Level K5\n\n"
        f"ℹ️ Gõ /help bất kỳ lúc nào để hiển thị bảng hướng dẫn này."
    )
    send_telegram_reply(help_msg, chat_id, thread_id)

def poll_updates():
    offset = load_offset()
    token = os.getenv("TELEGRAM_BOT_TOKEN") or PRIMARY_BOT_TOKEN

    url = f"https://api.telegram.org/bot{token}/getUpdates?timeout=10"
    if offset:
        url += f"&offset={offset}"

    try:
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            if not data.get("ok"):
                return

            for update in data.get("result", []):
                new_offset = update["update_id"] + 1
                save_offset(new_offset)

                message = update.get("message") or update.get("channel_post")
                if not message:
                    continue

                text = message.get("text", "").strip()
                chat = message.get("chat", {})
                chat_id = str(chat.get("id", ""))
                thread_id = message.get("message_thread_id")

                # Verify target chat and topic thread 3953
                if chat_id == DEFAULT_CHAT_ID and (thread_id == DEFAULT_THREAD_ID or thread_id == str(DEFAULT_THREAD_ID) or thread_id is None):
                    if text.startswith("/step"):
                        process_command(text, chat_id, DEFAULT_THREAD_ID)
                    elif text.startswith("/help") or text.startswith("/start"):
                        process_help(chat_id, DEFAULT_THREAD_ID)

    except Exception as e:
        pass

def main():
    print("🤖 O9O.NET Telegram Bot Listener Daemon Started...")
    while True:
        poll_updates()
        time.sleep(2)

if __name__ == "__main__":
    main()
