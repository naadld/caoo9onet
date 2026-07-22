#!/usr/bin/env python3
"""
Step 5: GDrive Copier
Reads Google Sheet (ID: 1yLPYbiPhV50fZVBMxzDnKrBJ9J7i8oWZJgQcKBLYSl8),
extracts Source Folder (Column B) and Target Folder (Column C),
and uses rclone copy to safely copy all contents from Source to Target on Google Drive.
"""

import os
import sys
import re
import json
import time
import shutil
import argparse
import subprocess
from datetime import datetime, timezone, timedelta

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REMOTE_BASE = "vpsg24gb.aleron,root_folder_id=11fQ8VYTmwRX9fMJFXeTrTTeZGDqki6dh:"
RCLONE_BIN = shutil.which("rclone") or "rclone"

RCLONE_CONF = os.getenv("RCLONE_CONFIG") or os.path.expanduser("~/.config/rclone/rclone.conf")
if not os.path.exists(RCLONE_CONF) and os.path.exists("/home/vpsg24gb/.config/rclone/rclone.conf"):
    RCLONE_CONF = "/home/vpsg24gb/.config/rclone/rclone.conf"

SPREADSHEET_ID = "1yLPYbiPhV50fZVBMxzDnKrBJ9J7i8oWZJgQcKBLYSl8"
DOC_ID = "1Ew8UPThE2yN9S7EEzeeToUxZCMNpWbkNqhOfpsqXPBw"

def log_to_google_doc(entry_text):
    try:
        from google.oauth2 import service_account
        from googleapiclient.discovery import build

        vn_tz = timezone(timedelta(hours=7))
        now_str = datetime.now(vn_tz).strftime("%Y-%m-%d %H:%M:%S")

        creds_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS") or os.path.join(BASE_DIR, "credentials.json")
        if not os.path.exists(creds_path):
            return

        with open(creds_path, 'r', encoding='utf-8') as f:
            info = json.load(f)

        if "private_key" in info:
            info["private_key"] = str(info["private_key"]).replace("\\n", "\n").replace("\r", "")

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
        print(f"⚠️ Doc Logger Error: {e}")

def get_google_creds():
    from google.oauth2 import service_account

    creds_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS") or os.path.join(BASE_DIR, "credentials.json")
    env_creds = os.getenv("GCP_SERVICE_ACCOUNT_JSON")

    info = None
    if env_creds:
        try:
            info = json.loads(env_creds)
        except Exception:
            pass

    if not info and os.path.exists(creds_path):
        with open(creds_path, 'r', encoding='utf-8') as f:
            info = json.load(f)

    if not info:
        raise RuntimeError("No Google Service Account credentials found.")

    if "private_key" in info:
        info["private_key"] = str(info["private_key"]).replace("\\n", "\n").replace("\r", "")

    scopes = [
        'https://www.googleapis.com/auth/spreadsheets.readonly',
        'https://www.googleapis.com/auth/drive'
    ]
    return service_account.Credentials.from_service_account_info(info, scopes=scopes)

def fetch_copy_pairs_from_sheets():
    from googleapiclient.discovery import build

    creds = get_google_creds()
    sheets_service = build('sheets', 'v4', credentials=creds)

    print(f"📖 Reading Google Sheet (ID: {SPREADSHEET_ID})...")
    
    # Try reading range B2:C from Sheet1 or first sheet
    try:
        sheet_metadata = sheets_service.spreadsheets().get(spreadsheetId=SPREADSHEET_ID).execute()
        sheets = sheet_metadata.get('sheets', [])
        first_sheet_title = sheets[0]['properties']['title'] if sheets else "Sheet1"
        range_name = f"'{first_sheet_title}'!B2:C"
    except Exception as e:
        print(f"⚠️ Could not fetch sheet metadata ({e}). Defaulting to 'Sheet1!B2:C'...")
        range_name = "Sheet1!B2:C"

    result = sheets_service.spreadsheets().values().get(
        spreadsheetId=SPREADSHEET_ID,
        range=range_name
    ).execute()

    rows = result.get('values', [])
    pairs = []

    for idx, row in enumerate(rows, start=2):
        if not row or len(row) < 2:
            continue
        src = row[0].strip()
        dst = row[1].strip()

        if not src or not dst:
            continue
            
        # Ignore header if row 2 contains header labels
        if src.lower() in ["folder gốc", "source", "folder goc", "nội dung gốc"] or dst.lower() in ["folder đích", "target", "destination", "folder dich"]:
            continue

        pairs.append({"row": idx, "src": src, "dst": dst})

    print(f"📊 Found {len(pairs)} folder copy pairs in Google Sheet.")
    return pairs

def extract_folder_id(val):
    """Extracts folder ID if val is a Google Drive URL, otherwise returns val."""
    m = re.search(r'folders/([a-zA-Z0-9_-]+)', val)
    if m:
        return m.group(1)
    return val

def resolve_rclone_remote(folder_val):
    """
    Resolves a folder value into an rclone remote path string.
    Supports:
    - Full Google Drive Folder URL (e.g., https://drive.google.com/drive/folders/1abc...)
    - Google Drive Folder ID (e.g., 1abc...)
    - Relative Path on GDrive (e.g., Grade 4/Ngày 001/Arithmetic)
    """
    folder_id_or_path = extract_folder_id(folder_val)
    
    # Check if folder_id_or_path looks like a GDrive Folder ID (alphanumeric, ~25-45 chars, no slashes)
    if re.match(r'^[a-zA-Z0-9_-]{25,50}$', folder_id_or_path) and '/' not in folder_id_or_path:
        return f"vpsg24gb.aleron,root_folder_id={folder_id_or_path}:"
    else:
        clean_path = folder_id_or_path.strip('/')
        return f"{REMOTE_BASE}{clean_path}"

def execute_copy(src_val, dst_val):
    src_remote = resolve_rclone_remote(src_val)
    dst_remote = resolve_rclone_remote(dst_val)

    print(f"  📂 Source: {src_val}  -->  Remote: {src_remote}")
    print(f"  📂 Target: {dst_val}  -->  Remote: {dst_remote}")

    # Use rclone copy (NEVER rclone move)
    cmd = [
        RCLONE_BIN, "--config", RCLONE_CONF, "copy",
        src_remote, dst_remote,
        "--stats", "10s", "-v"
    ]

    try:
        p = subprocess.run(cmd, capture_output=True, text=True)
        if p.returncode == 0:
            print("  ✅ Copy completed successfully.")
            return True
        else:
            print(f"  ❌ Copy failed (code {p.returncode}): {p.stderr.strip()}")
            return False
    except Exception as e:
        print(f"  ❌ Copy exception: {e}")
        return False

def run_gdrive_copier():
    print("=" * 60)
    print("🚀 STEP 5: GDRIVE COPIER")
    print("=" * 60)

    try:
        pairs = fetch_copy_pairs_from_sheets()
    except Exception as e:
        print(f"❌ Failed to fetch copy pairs from Google Sheet: {e}")
        return

    if not pairs:
        print("ℹ️ No copy pairs found to process.")
        return

    success_count = 0
    fail_count = 0

    for idx, item in enumerate(pairs, 1):
        print(f"\n[{idx}/{len(pairs)}] Processing Row {item['row']} in Sheet:")
        ok = execute_copy(item['src'], item['dst'])
        
        vn_tz = timezone(timedelta(hours=7))
        now_str = datetime.now(vn_tz).strftime("%Y-%m-%d %H:%M:%S")

        if ok:
            success_count += 1
            log_to_google_doc(f"{now_str}: Hoàn thành Step 5 Copy từ [{item['src']}] sang [{item['dst']}]")
        else:
            fail_count += 1
            log_to_google_doc(f"{now_str}: Lỗi Step 5 Copy từ [{item['src']}] sang [{item['dst']}]")

    print("\n" + "=" * 60)
    print(f"🎉 STEP 5 SUMMARY: {success_count} succeeded, {fail_count} failed out of {len(pairs)} total pairs.")
    print("=" * 60)

def main():
    run_gdrive_copier()

if __name__ == "__main__":
    main()
