#!/usr/bin/env python3
"""
Step 5: GDrive Copier with Column D (Status), Column E (Source files #), Column F (Destination files #)
Reads Google Sheet (ID: 1yLPYbiPhV50fZVBMxzDnKrBJ9J7i8oWZJgQcKBLYSl8) via Rclone CSV Export,
extracts Source Folder (Column B) and Target Folder (Column C).
Cleans URL parameters (e.g. ?fbclid=..., ?usp=drive_link) for 100% accurate Folder ID resolution.
Copies files via rclone copy, verifies file counts in Source (Col E) vs Destination (Col F) to prevent missing files,
and logs progress to Google Doc.
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
from datetime import datetime, timezone, timedelta

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REMOTE_BASE = "vpsg24gb.aleron,root_folder_id=11fQ8VYTmwRX9fMJFXeTrTTeZGDqki6dh:"
PARENT_FOLDER_ID = "11fQ8VYTmwRX9fMJFXeTrTTeZGDqki6dh"
SPREADSHEET_ID = "1yLPYbiPhV50fZVBMxzDnKrBJ9J7i8oWZJgQcKBLYSl8"
DOC_ID = "1Ew8UPThE2yN9S7EEzeeToUxZCMNpWbkNqhOfpsqXPBw"

RCLONE_BIN = shutil.which("rclone") or "rclone"
RCLONE_CONF = os.getenv("RCLONE_CONFIG") or os.path.expanduser("~/.config/rclone/rclone.conf")
if not os.path.exists(RCLONE_CONF) and os.path.exists("/home/vpsg24gb/.config/rclone/rclone.conf"):
    RCLONE_CONF = "/home/vpsg24gb/.config/rclone/rclone.conf"

def clean_private_key(info):
    if "private_key" in info:
        pk = str(info["private_key"]).strip()
        pk = pk.replace("\\n", "\n").replace("\r", "")
        while "\\n" in pk:
            pk = pk.replace("\\n", "\n")
        info["private_key"] = pk
    return info

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

def fetch_copy_pairs_from_gdrive_export():
    print("📖 Exporting Google Sheet via rclone...")
    tmp_dir = os.path.join(BASE_DIR, ".tmp_sheet_export")
    if os.path.exists(tmp_dir):
        shutil.rmtree(tmp_dir, ignore_errors=True)
    os.makedirs(tmp_dir, exist_ok=True)

    cmd = [
        RCLONE_BIN, "--config", RCLONE_CONF, "copy",
        "--drive-export-formats", "csv",
        f"vpsg24gb.aleron,root_folder_id={PARENT_FOLDER_ID}:",
        tmp_dir,
        "--max-depth", "1"
    ]
    res = subprocess.run(cmd, capture_output=True, text=True)

    csv_file = None
    for root, dirs, files in os.walk(tmp_dir):
        for f in files:
            if f.endswith('.csv') and ("link" in f.lower() or "drive" in f.lower() or "sheet" in f.lower()):
                csv_file = os.path.join(root, f)
                break
        if csv_file:
            break

    if not csv_file:
        for root, dirs, files in os.walk(tmp_dir):
            for f in files:
                if f.endswith('.csv'):
                    csv_file = os.path.join(root, f)
                    break
            if csv_file:
                break

    if not csv_file or not os.path.exists(csv_file):
        print(f"❌ Could not find exported CSV file in GDrive parent folder. Stderr: {res.stderr.strip()}")
        shutil.rmtree(tmp_dir, ignore_errors=True)
        return []

    print(f"📄 Found exported Google Sheet CSV: {os.path.basename(csv_file)}")
    pairs = []

    try:
        with open(csv_file, 'r', encoding='utf-8-sig', errors='ignore') as f:
            reader = csv.reader(f)
            for idx, row in enumerate(reader, start=1):
                if not row or len(row) < 3:
                    continue
                name_col = row[0].strip()
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
                    "name": name_col,
                    "src": src,
                    "dst": dst,
                    "status": status,
                    "src_files_count": src_files_count,
                    "dst_files_count": dst_files_count
                })
        print(f"📊 [Rclone Sheet Export] Successfully read {len(pairs)} folder copy pairs!")
    except Exception as e:
        print(f"❌ Error parsing exported CSV: {e}")
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)

    return pairs

def extract_folder_id(val):
    if not val:
        return ""
    val = str(val).strip()
    # Strip URL parameters starting with ? (e.g., ?fbclid=..., ?usp=drive_link)
    if '?' in val:
        val = val.split('?')[0]
    m = re.search(r'folders/([a-zA-Z0-9_-]+)', val)
    if m:
        return m.group(1)
    return val.strip()

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

    # Use rclone copy with high parallel transfers and real-time output streaming
    cmd = [
        RCLONE_BIN, "--config", RCLONE_CONF, "copy",
        src_remote, dst_remote,
        "--transfers", "12",
        "--checkers", "24",
        "--fast-list",
        "--stats", "10s", "-v"
    ]

    try:
        p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1)
        for line in iter(p.stdout.readline, ''):
            if line:
                sys.stdout.write("    " + line)
                sys.stdout.flush()
        p.wait()

        if p.returncode == 0:
            print("  ✅ Copy completed successfully.")
            return True, src_remote, dst_remote
        else:
            print(f"  ❌ Copy failed (code {p.returncode})")
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

    pairs = fetch_copy_pairs_from_gdrive_export()

    if not pairs:
        print("ℹ️ No copy pairs found to process.")
        return

    success_count = 0
    fail_count = 0
    skipped_count = 0

    for idx, item in enumerate(pairs, 1):
        row_num = item['row']
        status = item['status']
        existing_src_c = item['src_files_count']
        existing_dst_c = item['dst_files_count']
        pair_name = item.get('name', f"Row {row_num}")

        print(f"\n[{idx}/{len(pairs)}] Processing [{pair_name}] Row {row_num} (Status: '{status}'):")

        src_remote = resolve_rclone_remote(item['src'])
        dst_remote = resolve_rclone_remote(item['dst'])

        # If marked completed, verify if file counts match
        if is_already_completed(status):
            if existing_src_c and existing_dst_c and existing_src_c == existing_dst_c:
                print(f"  ⏭️ Row {row_num} [{pair_name}] already completed and file counts match ({existing_dst_c}/{existing_src_c}). Skipping.")
                skipped_count += 1
                continue
            else:
                # Count files to verify
                src_c = count_remote_files(src_remote)
                dst_c = count_remote_files(dst_remote)
                if src_c > 0 and src_c == dst_c:
                    print(f"  ⏭️ Row {row_num} [{pair_name}] verified match ({dst_c}/{src_c}). Skipping.")
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
            print(f"  📝 [Progress Logged] [{pair_name}] -> Col D: 'Hoàn thành' | Col E (Src): {src_c} | Col F (Dst): {dst_c}")
            log_to_google_doc(f"{now_str}: Hoàn thành Step 5 Copy [{pair_name}] từ [{item['src']}] sang [{item['dst']}] (Đủ {dst_c}/{src_c} files)")
        elif ok and src_c != dst_c:
            fail_count += 1
            print(f"  ⚠️ [File Count Mismatch] [{pair_name}] -> Src: {src_c} vs Dst: {dst_c}")
            log_to_google_doc(f"{now_str}: ⚠️ Cảnh báo Step 5 Lệch file [{pair_name}] từ [{item['src']}] sang [{item['dst']}] (Đích: {dst_c} / Nguồn: {src_c})")
        else:
            fail_count += 1
            print(f"  ❌ [Copy Error] [{pair_name}] Copy failed.")
            log_to_google_doc(f"{now_str}: Lỗi Step 5 Copy [{pair_name}] từ [{item['src']}] sang [{item['dst']}]")

    print("\n" + "=" * 60)
    print(f"🎉 STEP 5 SUMMARY: {success_count} succeeded, {skipped_count} skipped, {fail_count} failed out of {len(pairs)} total pairs.")
    print("=" * 60)

def main():
    run_gdrive_copier()

if __name__ == "__main__":
    main()
