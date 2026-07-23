#!/usr/bin/env python3
"""
Step 5: GDrive Copier with Column D (Status), Column E (Source files #), Column F (Destination files #)
Reads Google Sheet (ID: 1yLPYbiPhV50fZVBMxzDnKrBJ9J7i8oWZJgQcKBLYSl8),
extracts Source Folder (Column B) and Target Folder (Column C).
Copies files via rclone copy, verifies file counts in Source (Col E) vs Destination (Col F) to prevent missing files,
and updates status in Column D upon completion.
Uses rclone OAuth token to read Google Sheet CSV directly for 100% reliability.
"""

import os
import sys
import re
import csv
import json
import time
import shutil
import argparse
import subprocess
import configparser
import urllib.request
from datetime import datetime, timezone, timedelta

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REMOTE_BASE = "vpsg24gb.aleron,root_folder_id=11fQ8VYTmwRX9fMJFXeTrTTeZGDqki6dh:"
RCLONE_BIN = shutil.which("rclone") or "rclone"

RCLONE_CONF = os.getenv("RCLONE_CONFIG") or os.path.expanduser("~/.config/rclone/rclone.conf")
if not os.path.exists(RCLONE_CONF) and os.path.exists("/home/vpsg24gb/.config/rclone/rclone.conf"):
    RCLONE_CONF = "/home/vpsg24gb/.config/rclone/rclone.conf"

SPREADSHEET_ID = "1yLPYbiPhV50fZVBMxzDnKrBJ9J7i8oWZJgQcKBLYSl8"
DOC_ID = "1Ew8UPThE2yN9S7EEzeeToUxZCMNpWbkNqhOfpsqXPBw"

def fix_pem_private_key(private_key_str):
    if not private_key_str:
        return ""
    key = str(private_key_str).strip().strip('"').strip("'").strip()
    key = key.replace("\\n", "\n").replace("\r", "")
    while "\\n" in key:
        key = key.replace("\\n", "\n")
    if "-----BEGIN PRIVATE KEY-----" in key:
        header = "-----BEGIN PRIVATE KEY-----"
        footer = "-----END PRIVATE KEY-----"
        parts = key.split(header)
        if len(parts) > 1:
            body_and_footer = parts[-1].split(footer)
            body = body_and_footer[0].strip().replace(" ", "\n")
            lines = [l.strip() for l in body.split("\n") if l.strip()]
            key = f"{header}\n" + "\n".join(lines) + f"\n{footer}\n"
    return key

def get_service_account_info():
    creds_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS") or os.path.join(BASE_DIR, "credentials.json")
    env_creds = os.getenv("GCP_SERVICE_ACCOUNT_JSON")

    info = None
    if env_creds:
        try:
            info = json.loads(env_creds, strict=False)
        except Exception:
            pass

    if not info and os.path.exists(creds_path):
        with open(creds_path, 'r', encoding='utf-8') as f:
            content = f.read()
            info = json.loads(content, strict=False)

    if info and "private_key" in info:
        info["private_key"] = fix_pem_private_key(info["private_key"])

    return info

def get_rclone_oauth_access_token():
    if not os.path.exists(RCLONE_CONF):
        return None
    try:
        config = configparser.ConfigParser()
        config.read(RCLONE_CONF)
        for s in config.sections():
            if "token" in config[s]:
                tdata = json.loads(config[s]["token"])
                token = tdata.get("access_token")
                if token:
                    return token
    except Exception as e:
        print(f"⚠️ Error reading rclone OAuth token: {e}")
    return None

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

def fetch_copy_pairs_from_sheets():
    print(f"📖 Reading Google Sheet (ID: {SPREADSHEET_ID})...")
    pairs = []

    # 1. Try reading via Rclone OAuth access_token via Drive API v3 CSV export
    access_token = get_rclone_oauth_access_token()
    if access_token:
        try:
            url = f"https://www.googleapis.com/drive/v3/files/{SPREADSHEET_ID}/export?mimeType=text/csv"
            req = urllib.request.Request(url, headers={'Authorization': f'Bearer {access_token}'})
            with urllib.request.urlopen(req) as resp:
                csv_text = resp.read().decode('utf-8-sig')

            reader = csv.reader(csv_text.splitlines())
            for idx, row in enumerate(reader, start=1):
                if not row or len(row) < 3:
                    continue
                src = row[1].strip()  # Col B
                dst = row[2].strip()  # Col C
                status = row[3].strip() if len(row) >= 4 else ""
                src_files_count = row[4].strip() if len(row) >= 5 else ""
                dst_files_count = row[5].strip() if len(row) >= 6 else ""

                if not src or not dst:
                    continue
                if src.lower() in ["folder gốc", "source", "folder goc", "nội dung gốc", "sources"]:
                    continue

                pairs.append({
                    "row": idx,
                    "sheet_title": "Sheet1",
                    "src": src,
                    "dst": dst,
                    "status": status,
                    "src_files_count": src_files_count,
                    "dst_files_count": dst_files_count
                })
            print(f"📊 [Rclone OAuth Export] Successfully read {len(pairs)} folder copy pairs!")
            return None, pairs
        except Exception as e:
            print(f"⚠️ Rclone OAuth CSV export warning: {e}")

    # 2. Fallback to Service Account Sheets API v4
    info = get_service_account_info()
    if info:
        try:
            from google.oauth2 import service_account
            from googleapiclient.discovery import build

            creds = service_account.Credentials.from_service_account_info(
                info,
                scopes=['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']
            )
            sheets_service = build('sheets', 'v4', credentials=creds)

            first_sheet_title = "Sheet1"
            try:
                sheet_metadata = sheets_service.spreadsheets().get(spreadsheetId=SPREADSHEET_ID).execute()
                sheets = sheet_metadata.get('sheets', [])
                if sheets:
                    first_sheet_title = sheets[0]['properties']['title']
            except Exception:
                pass

            range_name = f"'{first_sheet_title}'!B2:F"
            result = sheets_service.spreadsheets().values().get(spreadsheetId=SPREADSHEET_ID, range=range_name).execute()
            rows = result.get('values', [])

            for idx, row in enumerate(rows, start=2):
                if not row or len(row) < 2:
                    continue
                src = row[0].strip()
                dst = row[1].strip()
                status = row[2].strip() if len(row) >= 3 else ""
                src_files_count = row[3].strip() if len(row) >= 4 else ""
                dst_files_count = row[4].strip() if len(row) >= 5 else ""

                if not src or not dst or src.lower() in ["folder gốc", "source", "sources"]:
                    continue

                pairs.append({
                    "row": idx,
                    "sheet_title": first_sheet_title,
                    "src": src,
                    "dst": dst,
                    "status": status,
                    "src_files_count": src_files_count,
                    "dst_files_count": dst_files_count
                })
            print(f"📊 [Sheets API v4] Successfully read {len(pairs)} folder copy pairs!")
            return sheets_service, pairs
        except Exception as e:
            print(f"⚠️ Sheets API v4 warning: {e}")

    print("❌ Could not read Google Sheet copy pairs.")
    return None, []

def update_sheet_row_details(sheets_service, sheet_title, row_num, status_text, src_count, dst_count):
    """Updates Column D (Status), Column E (Source Files #), and Column F (Destination Files #)."""
    updated = False
    if sheets_service:
        try:
            range_name = f"'{sheet_title}'!D{row_num}:F{row_num}"
            body = {'values': [[status_text, src_count, dst_count]]}
            sheets_service.spreadsheets().values().update(
                spreadsheetId=SPREADSHEET_ID,
                range=range_name,
                valueInputOption='USER_ENTERED',
                body=body
            ).execute()
            print(f"  📝 [Sheet Updated via API] Row {row_num} -> Col D: '{status_text}' | Col E (Src): {src_count} | Col F (Dst): {dst_count}")
            updated = True
        except Exception as e:
            print(f"  ⚠️ Sheet update warning: {e}")

    if not updated:
        print(f"  📝 [Summary Log] Row {row_num} -> Col D: '{status_text}' | Col E (Src): {src_count} | Col F (Dst): {dst_count}")

def extract_folder_id(val):
    m = re.search(r'folders/([a-zA-Z0-9_-]+)', val)
    if m:
        return m.group(1)
    return val

def resolve_rclone_remote(folder_val):
    folder_id_or_path = extract_folder_id(folder_val)
    if re.match(r'^[a-zA-Z0-9_-]{25,50}$', folder_id_or_path) and '/' not in folder_id_or_path:
        return f"vpsg24gb.aleron,root_folder_id={folder_id_or_path}:"
    else:
        clean_path = folder_id_or_path.strip('/')
        return f"{REMOTE_BASE}{clean_path}"

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
            return True, src_remote, dst_remote
        else:
            print(f"  ❌ Copy failed (code {p.returncode}): {p.stderr.strip()}")
            return False, src_remote, dst_remote
    except Exception as e:
        print(f"  ❌ Copy exception: {e}")
        return False, src_remote, dst_remote

def is_already_completed(status_str):
    if not status_str:
        return False
    st = status_str.lower()
    return any(kw in st for kw in ["hoàn thành", "done", "success", "completed"])

def run_gdrive_copier():
    print("=" * 60)
    print("🚀 STEP 5: GDRIVE COPIER (With Col D Status, Col E Src #, Col F Dst #)")
    print("=" * 60)

    try:
        sheets_service, pairs = fetch_copy_pairs_from_sheets()
    except Exception as e:
        print(f"❌ Failed to fetch copy pairs from Google Sheet: {e}")
        return

    if not pairs:
        print("ℹ️ No copy pairs found to process.")
        return

    success_count = 0
    fail_count = 0
    skipped_count = 0

    for idx, item in enumerate(pairs, 1):
        row_num = item['row']
        sheet_title = item['sheet_title']
        status = item['status']
        existing_src_c = item['src_files_count']
        existing_dst_c = item['dst_files_count']

        print(f"\n[{idx}/{len(pairs)}] Checking Row {row_num} (Status: '{status}'):")

        src_remote = resolve_rclone_remote(item['src'])
        dst_remote = resolve_rclone_remote(item['dst'])

        # If marked completed, verify if file counts match
        if is_already_completed(status):
            if existing_src_c and existing_dst_c and existing_src_c == existing_dst_c:
                print(f"  ⏭️ Row {row_num} already completed and file counts match ({existing_dst_c}/{existing_src_c}). Skipping.")
                skipped_count += 1
                continue
            else:
                # Count files to verify
                src_c = count_remote_files(src_remote)
                dst_c = count_remote_files(dst_remote)
                update_sheet_row_details(sheets_service, sheet_title, row_num, status, src_c, dst_c)
                if src_c > 0 and src_c == dst_c:
                    print(f"  ⏭️ Row {row_num} verified match ({dst_c}/{src_c}). Skipping.")
                    skipped_count += 1
                    continue
                else:
                    print(f"  ⚠️ File count mismatch (Src: {src_c}, Dst: {dst_c}). Re-running copy...")

        # Run copy operation
        ok, src_remote, dst_remote = execute_copy(item['src'], item['dst'])
        
        # Count files after copy operation
        print("  📊 Counting files in Source and Destination to verify completion...")
        src_c = count_remote_files(src_remote)
        dst_c = count_remote_files(dst_remote)

        vn_tz = timezone(timedelta(hours=7))
        now_str = datetime.now(vn_tz).strftime("%Y-%m-%d %H:%M:%S")

        if ok and src_c == dst_c and src_c > 0:
            success_count += 1
            status_msg = f"Hoàn thành ({now_str})"
            update_sheet_row_details(sheets_service, sheet_title, row_num, status_msg, src_c, dst_c)
            log_to_google_doc(f"{now_str}: Hoàn thành Step 5 Copy từ [{item['src']}] sang [{item['dst']}] (Đủ {dst_c}/{src_c} files)")
        elif ok and src_c != dst_c:
            fail_count += 1
            status_msg = f"Lệch file ({dst_c}/{src_c}) ({now_str})"
            update_sheet_row_details(sheets_service, sheet_title, row_num, status_msg, src_c, dst_c)
            log_to_google_doc(f"{now_str}: ⚠️ Cảnh báo Step 5 Lệch file từ [{item['src']}] sang [{item['dst']}] (Đích: {dst_c} / Nguồn: {src_c})")
        else:
            fail_count += 1
            status_msg = f"Lỗi copy ({now_str})"
            update_sheet_row_details(sheets_service, sheet_title, row_num, status_msg, src_c, dst_c)
            log_to_google_doc(f"{now_str}: Lỗi Step 5 Copy từ [{item['src']}] sang [{item['dst']}]")

    print("\n" + "=" * 60)
    print(f"🎉 STEP 5 SUMMARY: {success_count} succeeded, {skipped_count} skipped, {fail_count} failed out of {len(pairs)} total pairs.")
    print("=" * 60)

def main():
    run_gdrive_copier()

if __name__ == "__main__":
    main()
