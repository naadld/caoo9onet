#!/usr/bin/env python3
"""
Step 5: GDrive Copier Script
Copies contents from Source Google Drive Folder to Target Google Drive Folder using rclone.
Default Source: https://drive.google.com/drive/folders/1ZY-penoxRJgLHZ5i41hb7e0UqfFwt3YR
Default Target: https://drive.google.com/drive/folders/1kti0VyCp93sL49pn3JkyU2gBa-tr33Iz
"""

import os
import sys
import re
import json
import time
import shutil
import argparse
import subprocess
import urllib.request
import urllib.parse
import fcntl
from datetime import datetime, timezone, timedelta

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOCK_FILE = os.path.join(BASE_DIR, "step5_copier.lock")

# Enforce strict single-instance execution
try:
    lock_file_fd = open(LOCK_FILE, "w")
    fcntl.flock(lock_file_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
except (IOError, OSError):
    print("⚠️ Another instance of step5_gdrive_copier.py is currently running. Skipping.")
    sys.exit(0)

DOC_ID = "1Ew8UPThE2yN9S7EEzeeToUxZCMNpWbkNqhOfpsqXPBw"

DEFAULT_SRC_FOLDER = "1ZY-penoxRJgLHZ5i41hb7e0UqfFwt3YR"
DEFAULT_DST_FOLDER = "1kti0VyCp93sL49pn3JkyU2gBa-tr33Iz"

PRIMARY_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
FALLBACK_BOT_TOKEN = os.getenv("TELEGRAM_FALLBACK_BOT_TOKEN", "")
DEFAULT_CHAT_ID = "-1003954353565"
DEFAULT_THREAD_ID = 3953

def send_telegram_msg(message):
    token = os.getenv("TELEGRAM_BOT_TOKEN") or PRIMARY_BOT_TOKEN
    chat_id = os.getenv("TELEGRAM_CHAT_ID") or DEFAULT_CHAT_ID
    thread_id = os.getenv("TELEGRAM_THREAD_ID") or DEFAULT_THREAD_ID

    tokens_to_try = [token]
    if token != FALLBACK_BOT_TOKEN:
        tokens_to_try.append(FALLBACK_BOT_TOKEN)

    sent = False
    for tok in tokens_to_try:
        url = f"https://api.telegram.org/bot{tok}/sendMessage"
        payload = {
            "chat_id": chat_id,
            "text": message
        }
        if thread_id:
            payload["message_thread_id"] = thread_id

        data = urllib.parse.urlencode(payload).encode("utf-8")
        try:
            req = urllib.request.Request(url, data=data)
            with urllib.request.urlopen(req, timeout=10) as resp:
                if resp.status == 200:
                    print(f"📱 [Telegram Report Sent Success] Token: {tok[:12]}...")
                    sent = True
                    break
        except Exception as e:
            print(f"⚠️ Telegram send attempt failed for token {tok[:12]}...: {e}")

    def sync_paperclip(step_name, status, detail):
        try:
            script_path = os.path.join(BASE_DIR, "scripts/sync_paperclip_live.py")
            if os.path.exists(script_path):
                subprocess.run(["python3", script_path, "--step", step_name, "--status", status, "--msg", detail], cwd=BASE_DIR, capture_output=True, timeout=10)
        except Exception:
            pass

    if not sent:
        print("❌ Could not send Telegram report to specified chat/bot.")

RCLONE_BIN = shutil.which("rclone") or "rclone"
RCLONE_CONF = os.getenv("RCLONE_CONFIG") or os.path.expanduser("~/.config/rclone/rclone.conf")
if not os.path.exists(RCLONE_CONF) and os.path.exists("/home/vpsg24gb/.config/rclone/rclone.conf"):
    RCLONE_CONF = "/home/vpsg24gb/.config/rclone/rclone.conf"

def clean_private_key(info):
    if isinstance(info, dict) and "private_key" in info:
        pk = str(info["private_key"]).strip()
        while "\\n" in pk:
            pk = pk.replace("\\n", "\n")
        pk = pk.replace("\r", "")
        if "-----BEGIN PRIVATE KEY-----" in pk and "-----END PRIVATE KEY-----" in pk:
            header = "-----BEGIN PRIVATE KEY-----"
            footer = "-----END PRIVATE KEY-----"
            body = pk.split(header)[1].split(footer)[0].strip()
            body_clean = "".join(body.split())
            lines = [body_clean[i:i+64] for i in range(0, len(body_clean), 64)]
            pk = f"{header}\n" + "\n".join(lines) + f"\n{footer}\n"
        info["private_key"] = pk
    return info

def get_service_account_info():
    env_creds = os.getenv("GCP_SERVICE_ACCOUNT_JSON")
    creds_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS") or os.path.join(BASE_DIR, "credentials.json")

    info = None
    if env_creds:
        try:
            cleaned_env = env_creds.strip()
            if cleaned_env.startswith("'") and cleaned_env.endswith("'"):
                cleaned_env = cleaned_env[1:-1]
            info = json.loads(cleaned_env, strict=False)
        except Exception as e:
            print(f"⚠️ Notice: GCP_SERVICE_ACCOUNT_JSON parse notice: {e}")

    if not info and os.path.exists(creds_path):
        try:
            with open(creds_path, 'r', encoding='utf-8') as f:
                content = f.read()
                info = json.loads(content, strict=False)
        except Exception as e:
            print(f"⚠️ Notice: credentials.json read notice: {e}")

    if info and isinstance(info, dict) and "private_key" in info:
        info = clean_private_key(info)

    return info

def log_to_google_doc(entry_text):
    try:
        info = get_service_account_info()
        if not info:
            print("ℹ️ Skipping Google Doc log: Service account info unavailable.")
            return
        from google.oauth2 import service_account
        from googleapiclient.discovery import build

        vn_tz = timezone(timedelta(hours=7))
        now_str = datetime.now(vn_tz).strftime("%Y-%m-%d %H:%M:%S")

        creds = service_account.Credentials.from_service_account_info(
            info,
            scopes=['https://www.googleapis.com/auth/documents']
        )
        docs_service = build('docs', 'v1', credentials=creds)

        doc = docs_service.documents().get(documentId=DOC_ID).execute()
        end_index = doc.get('body').get('content')[-1].get('endIndex') - 1

        formatted_entry = f"{now_str}: {entry_text}\n"

        requests = [{
            'insertText': {
                'location': {'index': end_index},
                'text': formatted_entry
            }
        }]
        docs_service.documents().batchUpdate(documentId=DOC_ID, body={'requests': requests}).execute()
        print(f"📝 [Doc Log Success] {formatted_entry.strip()}")
    except Exception as e:
        print(f"⚠️ Doc Logger Notice: {e}")

def extract_folder_id(val):
    if not val:
        return ""
    val = str(val).strip()
    if '?' in val:
        val = val.split('?')[0]
    m = re.search(r'folders/([a-zA-Z0-9_-]+)', val)
    if m:
        return m.group(1)
    return val.strip()

def resolve_rclone_remote(folder_val):
    folder_id = extract_folder_id(folder_val)
    return f"vpsg24gb.aleron,root_folder_id={folder_id}:"

def count_remote_files(remote_path):
    try:
        cmd = [
            RCLONE_BIN, "--config", RCLONE_CONF, "lsf", "-R", "--files-only", remote_path
        ]
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        if res.returncode == 0:
            files = [line.strip() for line in res.stdout.splitlines() if line.strip()]
            return len(files)
        return 0
    except Exception as e:
        print(f"  ⚠️ File counting warning for {remote_path}: {e}")
        return 0

def execute_copy(src_val, dst_val):
    src_id = extract_folder_id(src_val)
    dst_id = extract_folder_id(dst_val)

    src_remote = resolve_rclone_remote(src_id)
    dst_remote = resolve_rclone_remote(dst_id)

    print(f"  📂 Source Folder ID: {src_id}")
    print(f"  📂 Source Remote:    {src_remote}")
    print(f"  📂 Target Folder ID: {dst_id}")
    print(f"  📂 Target Remote:    {dst_remote}")

    # Check files in source remote
    print("  📊 Counting source files...")
    src_count = count_remote_files(src_remote)
    print(f"  📄 Total Source Files: {src_count}")

    if src_count == 0:
        print("  ⚠️ Source folder contains no files or could not be listed.")

    # Fast Check: If target files count matches source count, skip immediately
    dst_count_pre = count_remote_files(dst_remote)
    if src_count > 0 and dst_count_pre >= src_count:
        msg = f"⏭️ [Chống trùng] Thư mục đích đã có đủ {dst_count_pre}/{src_count} files. Bỏ qua không tải lại!"
        print(f"  {msg}")
        log_to_google_doc(msg)
        return True

    print("  🚀 Starting rclone copy operation (Server-Side Direct Transfer)...")
    cmd = [
        RCLONE_BIN, "--config", RCLONE_CONF, "copy",
        src_remote, dst_remote,
        "--update",
        "--server-side-across-configs",
        "--drive-stop-on-upload-limit",
        "--transfers", "8",
        "--checkers", "16",
        "--fast-list",
        "--contimeout", "30s",
        "--timeout", "3m",
        "--retries", "3",
        "--stats", "10s", "-v"
    ]

    try:
        p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1)
        for line in iter(p.stdout.readline, ''):
            if line:
                sys.stdout.write("    " + line)
                sys.stdout.flush()
        p.wait()

        vn_tz = timezone(timedelta(hours=7))
        now_str = datetime.now(vn_tz).strftime("%Y-%m-%d %H:%M:%S")

        if p.returncode == 0:
            print("  📊 Counting target files post-copy...")
            dst_count = count_remote_files(dst_remote)
            print(f"  📄 Target Files: {dst_count} / {src_count}")

            msg = f"Hoàn thành Step 5 Copy từ [{src_id}] sang [{dst_id}] ({dst_count}/{src_count} files)"
            print(f"  🎉 {msg}")
            log_to_google_doc(msg)

            tg_msg = (
                f"🎉 [STEP 5: HOÀN THÀNH COPY FOLDER]\n"
                f"━━━━━━━━━━━━━━━━━━━━━━\n"
                f"📁 Nguồn: https://drive.google.com/drive/folders/{src_id}\n"
                f"📂 Đích:  https://drive.google.com/drive/folders/{dst_id}\n"
                f"📄 Số tệp: {dst_count} / {src_count} files\n"
                f"⏰ Giờ (GMT+7): {now_str}"
            )
            send_telegram_msg(tg_msg)
            return True
        else:
            err_detail = "Chạm giới hạn Upload 750GB/ngày của Google Drive (User Rate Limit Exceeded)" if p.returncode == 7 else f"Exit Code {p.returncode}"
            msg = f"Lỗi Step 5 Copy từ [{src_id}] sang [{dst_id}] ({err_detail})"
            print(f"  ❌ {msg}")
            log_to_google_doc(msg)

            tg_msg = (
                f"⚠️ [STEP 5: THÔNG BÁO LỖI COPY FOLDER]\n"
                f"━━━━━━━━━━━━━━━━━━━━━━\n"
                f"📁 Nguồn: https://drive.google.com/drive/folders/{src_id}\n"
                f"📂 Đích:  https://drive.google.com/drive/folders/{dst_id}\n"
                f"❌ Lỗi: {err_detail}\n"
                f"⏰ Giờ (GMT+7): {now_str}"
            )
            send_telegram_msg(tg_msg)
            return False
    except Exception as e:
        vn_tz = timezone(timedelta(hours=7))
        now_str = datetime.now(vn_tz).strftime("%Y-%m-%d %H:%M:%S")
        print(f"  ❌ Copy exception: {e}")
        log_to_google_doc(f"Lỗi Step 5 Copy exception: {e}")
        send_telegram_msg(f"⚠️ [STEP 5: LỖI EXCEPTION]\n❌ {e}\n⏰ Giờ (GMT+7): {now_str}")
        return False

def main():
    parser = argparse.ArgumentParser(description="Step 5: GDrive Copier")
    parser.add_argument("--src", type=str, default=DEFAULT_SRC_FOLDER, help="Source GDrive Folder URL or ID")
    parser.add_argument("--dst", type=str, default=DEFAULT_DST_FOLDER, help="Target GDrive Folder URL or ID")
    args = parser.parse_args()

    print("=" * 60)
    print("🚀 STEP 5: GDRIVE FOLDER COPIER")
    print("=" * 60)

    success = execute_copy(args.src, args.dst)
    if not success:
        sys.exit(1)

if __name__ == "__main__":
    main()
