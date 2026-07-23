#!/usr/bin/env python3
"""
Step 6: Folder Comparator & Telegram Reporter
Compares Source Google Drive Folder vs Destination Google Drive Folder:
- Number of Subfolders
- Number of Files
- Total Size (Bytes & Human-Readable GB/MB)
Calculates completeness percentage and reports results to Telegram Bot (8525129998:AAG6-Ib_AfqEGc7jwroo58reg5UVYlRZ-3A) and Google Doc.
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
from datetime import datetime, timezone, timedelta

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DOC_ID = "1Ew8UPThE2yN9S7EEzeeToUxZCMNpWbkNqhOfpsqXPBw"

DEFAULT_SRC_FOLDER = "1ZY-penoxRJgLHZ5i41hb7e0UqfFwt3YR"
DEFAULT_DST_FOLDER = "1kti0VyCp93sL49pn3JkyU2gBa-tr33Iz"

PRIMARY_BOT_TOKEN = "8525129998:AAG6-Ib_AfqEGc7jwroo58reg5UVYlRZ-3A"
FALLBACK_BOT_TOKEN = "8733078949:AAEX6WGeGasyVHXEYqgadgE8RFovyr64lBg"
DEFAULT_CHAT_ID = "-1003954353565"
DEFAULT_THREAD_ID = 4049

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

    if not sent:
        print("❌ Could not send Telegram report to specified chat/bot.")

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

def format_bytes(size):
    if size < 1024:
        return f"{size} B"
    elif size < 1024 ** 2:
        return f"{size / 1024:.2f} KB"
    elif size < 1024 ** 3:
        return f"{size / (1024 ** 2):.2f} MB"
    else:
        return f"{size / (1024 ** 3):.2f} GB"

def inspect_folder(folder_val):
    folder_id = extract_folder_id(folder_val)
    remote_path = f"vpsg24gb.aleron,root_folder_id={folder_id}:"

    # List items recursively using rclone lsf -R
    cmd_lsf = [RCLONE_BIN, "--config", RCLONE_CONF, "lsf", "-R", remote_path]
    res_lsf = subprocess.run(cmd_lsf, capture_output=True, text=True, timeout=300)
    
    folders = []
    files = []
    if res_lsf.returncode == 0:
        lines = [line.strip() for line in res_lsf.stdout.splitlines() if line.strip()]
        folders = [l for l in lines if l.endswith('/')]
        files = [l for l in lines if not l.endswith('/')]

    # Get size using rclone size
    cmd_size = [RCLONE_BIN, "--config", RCLONE_CONF, "size", remote_path]
    res_size = subprocess.run(cmd_size, capture_output=True, text=True, timeout=120)

    total_bytes = 0
    total_objects = len(files)

    if res_size.returncode == 0:
        out = res_size.stdout
        # Match "(14582442200 Byte)"
        m_bytes = re.search(r'\(([\d]+)\s*Byte', out)
        if m_bytes:
            total_bytes = int(m_bytes.group(1))

        m_objs = re.search(r'Total objects:\s*([\d]+)', out)
        if m_objs:
            total_objects = int(m_objs.group(1))

    return {
        "id": folder_id,
        "remote": remote_path,
        "folder_count": len(folders),
        "file_count": total_objects,
        "bytes": total_bytes,
        "folders_list": set(folders),
        "files_list": set(files)
    }

def compare_folders(src_val, dst_val):
    print("=" * 60)
    print("🚀 STEP 6: GDRIVE FOLDER COMPARATOR")
    print("=" * 60)

    src_id = extract_folder_id(src_val)
    dst_id = extract_folder_id(dst_val)

    print(f"📊 Inspecting Source Folder [{src_id}]...")
    src_info = inspect_folder(src_id)

    print(f"📊 Inspecting Target Folder [{dst_id}]...")
    dst_info = inspect_folder(dst_id)

    # Calculation
    src_fcount = src_info["folder_count"]
    dst_fcount = dst_info["folder_count"]

    src_files = src_info["file_count"]
    dst_files = dst_info["file_count"]

    src_bytes = src_info["bytes"]
    dst_bytes = dst_info["bytes"]

    folder_pct = (dst_fcount / src_fcount * 100.0) if src_fcount > 0 else (100.0 if dst_fcount >= src_fcount else 0.0)
    file_pct = (dst_files / src_files * 100.0) if src_files > 0 else (100.0 if dst_files >= src_files else 0.0)
    bytes_pct = (dst_bytes / src_bytes * 100.0) if src_bytes > 0 else (100.0 if dst_bytes >= src_bytes else 0.0)

    missing_files = src_info["files_list"] - dst_info["files_list"]
    missing_folders = src_info["folders_list"] - dst_info["folders_list"]

    is_complete = (dst_files >= src_files and dst_bytes >= src_bytes) if src_files > 0 else True

    status_icon = "✅" if is_complete else "⚠️"
    status_text = "HOÀN TOÀN ĐẦY ĐỦ (100% SUCCESS)" if is_complete else f"CHƯA ĐỒNG BỘ ĐỦ (Thiếu {len(missing_files)} files / {len(missing_folders)} folders)"

    vn_tz = timezone(timedelta(hours=7))
    now_str = datetime.now(vn_tz).strftime("%Y-%m-%d %H:%M:%S")

    # Formatted Telegram Report
    report = (
        f"📊 [STEP 6: BÁO CÁO SO SÁNH FOLDER]\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"📁 Nguồn: https://drive.google.com/drive/folders/{src_id}\n"
        f"📂 Đích:  https://drive.google.com/drive/folders/{dst_id}\n\n"
        f"📋 KẾT QUẢ ĐỐI CHIẾU:\n"
        f"▪️ Thư mục (Folders): {dst_fcount} / {src_fcount} ({folder_pct:.1f}%)\n"
        f"▪️ Số tệp (Files):    {dst_files} / {src_files} ({file_pct:.1f}%)\n"
        f"▪️ Dung lượng (Size): {format_bytes(dst_bytes)} / {format_bytes(src_bytes)} ({bytes_pct:.1f}%)\n\n"
        f"{status_icon} TRẠNG THÁI: {status_text}\n"
        f"⏰ Giờ kiểm tra (GMT+7): {now_str}"
    )

    print("\n" + report + "\n")

    # Log to Google Doc
    doc_msg = f"Step 6 So sánh [{src_id}] -> [{dst_id}]: Folders ({dst_fcount}/{src_fcount}), Files ({dst_files}/{src_files}), Size ({format_bytes(dst_bytes)}/{format_bytes(src_bytes)}) - {status_text}"
    log_to_google_doc(doc_msg)

    # Send Telegram Notification
    send_telegram_msg(report)

    return is_complete

def main():
    parser = argparse.ArgumentParser(description="Step 6: Folder Comparator & Telegram Reporter")
    parser.add_argument("--src", type=str, default=DEFAULT_SRC_FOLDER, help="Source GDrive Folder URL or ID")
    parser.add_argument("--dst", type=str, default=DEFAULT_DST_FOLDER, help="Target GDrive Folder URL or ID")
    args = parser.parse_args()

    compare_folders(args.src, args.dst)

if __name__ == "__main__":
    main()
