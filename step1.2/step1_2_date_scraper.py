#!/usr/bin/env python3
"""
Step 1.2: Targeted Single-Grade & Single-Day Downloader for Abeka Videos (o9o.net)
Author: Antigravity AI Agent
Description:
    Downloads video lessons specifically for a target Grade and Day (date) on demand
    to prevent missing data or re-stream specific lessons without running a full batch.
"""

import os
import sys
import re
import json
import time
import uuid
import urllib.request
import urllib.parse
import subprocess
import argparse
import threading
import shutil
from datetime import datetime, timezone, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed
from bs4 import BeautifulSoup
import fcntl

# Path definitions
STEP1_2_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.dirname(STEP1_2_DIR)
SCRIPTS_DIR = os.path.join(BASE_DIR, "scripts")

BASE_URL = "https://www.o9o.net"

# Telegram Bot Credentials
PRIMARY_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
FALLBACK_BOT_TOKEN = os.getenv("TELEGRAM_FALLBACK_BOT_TOKEN", "")
DEFAULT_CHAT_ID = "-1003954353565"
DEFAULT_THREAD_ID = 4455

# Executable locations
RCLONE_BIN = shutil.which("rclone") or "rclone"
RCLONE_CONF = os.getenv("RCLONE_CONFIG") or os.path.expanduser("~/.config/rclone/rclone.conf")
if not os.path.exists(RCLONE_CONF) and os.path.exists("/home/vpsg24gb/.config/rclone/rclone.conf"):
    RCLONE_CONF = "/home/vpsg24gb/.config/rclone/rclone.conf"

YTDLP_BIN = shutil.which("yt-dlp") or "yt-dlp"
REMOTE_BASE = "vpsg24gb.aleron,root_folder_id=11fQ8VYTmwRX9fMJFXeTrTTeZGDqki6dh:"

# Threading locks
db_lock = threading.Lock()
gdrive_index_lock = threading.Lock()
gdrive_index = {}

def send_telegram_msg(message):
    token = os.getenv("TELEGRAM_BOT_TOKEN") or PRIMARY_BOT_TOKEN
    chat_id = os.getenv("TELEGRAM_CHAT_ID") or DEFAULT_CHAT_ID
    thread_id = os.getenv("TELEGRAM_THREAD_ID") or DEFAULT_THREAD_ID

    tokens_to_try = [token]
    if token != FALLBACK_BOT_TOKEN:
        tokens_to_try.append(FALLBACK_BOT_TOKEN)

    sent = False
    for tok in tokens_to_try:
        if not tok:
            continue
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
                    print(f"📱 [Telegram Notification Sent] Token: {tok[:12]}...")
                    sent = True
                    break
        except Exception as e:
            print(f"⚠️ Telegram send attempt failed for token {tok[:12]}...: {e}")

    if not sent:
        print("ℹ️ Telegram notification skipped or failed.")

def acquire_step1_2_lock(grade, day):
    clean_g = re.sub(r'[^a-zA-Z0-9]', '_', str(grade or 'all')).lower()
    clean_d = str(day)
    lock_file_path = os.path.join(BASE_DIR, f"step1_2_{clean_g}_{clean_d}.lock")
    try:
        fd = open(lock_file_path, "w")
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        print(f"🔒 [LOCK ACQUIRED] Step 1.2 Lock acquired for Grade [{grade}] Day [{day}] -> {os.path.basename(lock_file_path)}")
        return fd
    except (IOError, OSError):
        print(f"⚠️ Another instance of Step 1.2 for Grade [{grade}] Day [{day}] is running. Skipping duplicate execution.")
        sys.exit(0)

def clean_private_key(info):
    if "private_key" in info:
        pk = str(info["private_key"]).strip()
        pk = pk.replace("\\n", "\n").replace("\r", "")
        while "\\n" in pk:
            pk = pk.replace("\\n", "\n")
        info["private_key"] = pk
    return info

def log_to_google_doc(entry_text):
    try:
        from google.oauth2 import service_account
        from googleapiclient.discovery import build

        vn_tz = timezone(timedelta(hours=7))
        now_str = datetime.now(vn_tz).strftime("%Y-%m-%d %H:%M:%S")

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

        if not info:
            return

        info = clean_private_key(info)

        creds = service_account.Credentials.from_service_account_info(
            info,
            scopes=['https://www.googleapis.com/auth/documents']
        )
        docs_service = build('docs', 'v1', credentials=creds)
        doc_id = '1Ew8UPThE2yN9S7EEzeeToUxZCMNpWbkNqhOfpsqXPBw'

        doc = docs_service.documents().get(documentId=doc_id).execute()
        end_index = doc.get('body').get('content')[-1].get('endIndex') - 1

        formatted_entry = f"{now_str}: [Step 1.2] {entry_text}\n"

        requests = [{
            'insertText': {
                'location': {'index': end_index},
                'text': formatted_entry
            }
        }]
        docs_service.documents().batchUpdate(documentId=doc_id, body={'requests': requests}).execute()
        print(f"📝 [Doc Log Success] {formatted_entry.strip()}")
    except Exception as e:
        print(f"⚠️ Doc Logger Warning: {e}")

def fetch(url):
    req = urllib.request.Request(
        url,
        headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
    )
    for _ in range(3):
        try:
            with urllib.request.urlopen(req, timeout=15) as response:
                return response.read().decode('utf-8')
        except Exception as e:
            time.sleep(2)
    return ""

def get_db_file(grade):
    return os.path.join(BASE_DIR, f"database_{grade}.json")

def load_database(grade):
    db_file = get_db_file(grade)
    with db_lock:
        if os.path.exists(db_file):
            try:
                with open(db_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception:
                return []
        return []

def upsert_database_record(grade, record):
    db_file = get_db_file(grade)
    with db_lock:
        db = []
        if os.path.exists(db_file):
            try:
                with open(db_file, 'r', encoding='utf-8') as f:
                    db = json.load(f)
            except Exception:
                db = []
        
        updated = False
        for r in db:
            if str(r.get('day')) == str(record.get('day')) and r.get('subject') == record.get('subject'):
                r['link'] = record.get('link')
                updated = True
                break
        
        if not updated:
            db.append(record)

        def sort_key(r):
            day_str = str(r.get('day', '000'))
            day_num = int(re.sub(r'\D', '', day_str)) if re.sub(r'\D', '', day_str) else 0
            return (day_num, r.get('subject', ''))
        
        db.sort(key=sort_key)
        
        with open(db_file, 'w', encoding='utf-8') as f:
            json.dump(db, f, ensure_ascii=False, indent=4)

def remove_database_record(grade, day, subject):
    db_file = get_db_file(grade)
    with db_lock:
        if not os.path.exists(db_file):
            return
        try:
            with open(db_file, 'r', encoding='utf-8') as f:
                db = json.load(f)
            db = [r for r in db if not (str(r.get('day')) == str(day) and r.get('subject') == subject)]
            with open(db_file, 'w', encoding='utf-8') as f:
                json.dump(db, f, ensure_ascii=False, indent=4)
        except Exception:
            pass

def fetch_live_gdrive_index():
    print("🔍 Fetching live GDrive index to check existing files...")
    g_files = {}
    try:
        res = subprocess.run(
            [RCLONE_BIN, "--config", RCLONE_CONF, "lsf", "-R", "--format", "ps", "--separator", ";", REMOTE_BASE],
            capture_output=True, text=True, timeout=60
        )
        for line in res.stdout.splitlines():
            line = line.strip()
            if ";" in line:
                parts = line.split(";", 1)
                path = parts[0].strip()
                if path.endswith(".mp4"):
                    try:
                        size = int(parts[1].strip())
                    except ValueError:
                        size = 0
                    g_files[path.lower()] = size
        print(f"  Indexed {len(g_files)} existing video files on Google Drive.")
    except Exception as e:
        print(f"  ⚠️ Live GDrive indexing warning: {e}")
    return g_files

def direct_stream_to_gdrive(m3u8_url, gdrive_target_path):
    task_tmp_dir = os.path.join(BASE_DIR, ".tmp_stream", uuid.uuid4().hex)
    os.makedirs(task_tmp_dir, exist_ok=True)
    temp_file = os.path.join(task_tmp_dir, "output.mp4")

    ytdlp_cmd = [
        YTDLP_BIN,
        "--no-warnings",
        "--referer", "https://www.o9o.net/",
        "--user-agent", "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
        "--paths", f"home:{task_tmp_dir}",
        "--paths", f"temp:{task_tmp_dir}",
        "--remux-video", "mp4",
        "--postprocessor-args", "ffmpeg:-movflags +faststart -avoid_negative_ts make_zero",
        "-o", temp_file,
        m3u8_url
    ]

    try:
        p1 = subprocess.run(ytdlp_cmd, capture_output=True, text=True)
        if p1.returncode != 0 or not os.path.exists(temp_file) or os.path.getsize(temp_file) < 100000:
            print(f"    ❌ yt-dlp download failed or empty (code {p1.returncode}). Stderr: {p1.stderr.strip()}")
            shutil.rmtree(task_tmp_dir, ignore_errors=True)
            return False

        rclone_cmd = [
            RCLONE_BIN, "--config", RCLONE_CONF, "copyto",
            temp_file,
            f"{REMOTE_BASE}{gdrive_target_path}"
        ]

        p2 = subprocess.run(rclone_cmd, capture_output=True, text=True)
        success = (p2.returncode == 0)

        if not success:
            print(f"    ❌ rclone upload failed (code {p2.returncode}). Stderr: {p2.stderr.strip()}")

        shutil.rmtree(task_tmp_dir, ignore_errors=True)
        return success
    except Exception as e:
        print(f"    ❌ Staging upload failed: {e}")
        shutil.rmtree(task_tmp_dir, ignore_errors=True)
        return False

def normalize_grade(val):
    if not val:
        return None
    val_clean = str(val).strip()
    val_upper = val_clean.upper()

    mapping = {
        "K4": "K4", "K4.": "K4", "0": "K4",
        "K5": "K5", "K5.": "K5",
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
    }
    if val_upper in mapping:
        return mapping[val_upper]
    
    m = re.search(r'(\d+)', val_clean)
    if m:
        num = int(m.group(1))
        if 1 <= num <= 12:
            return f"Grade {num}"

    return val_clean

def normalize_day(val):
    if val is None:
        return None
    val_str = str(val).strip()
    m = re.search(r'(\d+)', val_str)
    if m:
        num = int(m.group(1))
        return f"{num:03d}"
    return val_str

def process_single_video(item_info, force_overwrite=False):
    actual_g_name = item_info["actual_g_name"]
    day = item_info["day"]
    subject = item_info["subject"]
    link = item_info["link"]
    gdrive_rel_path = item_info["gdrive_rel_path"]
    
    print(f"  🎬 [{subject}] Target: {gdrive_rel_path}")
    
    with gdrive_index_lock:
        file_on_gdrive = gdrive_rel_path.lower() in gdrive_index
        gdrive_size = gdrive_index.get(gdrive_rel_path.lower(), 0) if file_on_gdrive else 0
        
    is_valid_on_gdrive = file_on_gdrive and gdrive_size > 100000
    
    success = False
    if is_valid_on_gdrive and not force_overwrite:
        print(f"    -> ⏭️ File already uploaded & valid ({gdrive_size / 1024 / 1024:.2f} MB). Skipping.")
        success = True
        upsert_database_record(actual_g_name, {
            "grade": actual_g_name,
            "day": day,
            "subject": subject,
            "link": gdrive_rel_path
        })
        print(f"    -> Restored/verified database record for {subject}.")
    else:
        if force_overwrite and file_on_gdrive:
            print(f"    -> ⚡ [FORCE OVERWRITE] Re-downloading & overwriting existing file on GDrive: {subject}")
            remove_database_record(actual_g_name, day, subject)
        elif file_on_gdrive:
            print(f"    -> ⚠️ File is invalid/empty on Google Drive ({gdrive_size} bytes). Re-streaming...")
        else:
            print(f"    -> ⚡ Direct pipe streaming from o9o.net to Google Drive for: {subject}")
            
        success = direct_stream_to_gdrive(link, gdrive_rel_path)
        vn_tz = timezone(timedelta(hours=7))
        now_str = datetime.now(vn_tz).strftime("%Y-%m-%d %H:%M:%S")
        if success:
            with gdrive_index_lock:
                gdrive_index[gdrive_rel_path.lower()] = 999999999
            log_to_google_doc(f"{now_str}: Hoàn thành {actual_g_name}, Ngày {day}, {subject}")
        else:
            log_to_google_doc(f"{now_str}: Lỗi cào video {subject} ({actual_g_name}, Ngày {day})")
                
    if success:
        upsert_database_record(actual_g_name, {
            "grade": actual_g_name,
            "day": day,
            "subject": subject,
            "link": gdrive_rel_path
        })
        print(f"    -> Updated database record for: {subject}")
        return True
    else:
        return False

def run_step1_2(grade_param, day_param, force_overwrite=False, auto_sync=True):
    global gdrive_index

    norm_grade = normalize_grade(grade_param)
    norm_day = normalize_day(day_param)

    if not norm_grade or not norm_day:
        print("❌ ERROR: Both --grade and --day arguments are required.")
        sys.exit(1)

    acquire_step1_2_lock(norm_grade, norm_day)

    print("=" * 60)
    print(f"🚀 STEP 1.2: TARGETED DATE SCRAPER")
    print(f"🎯 Target Grade: {norm_grade}")
    print(f"📅 Target Day:   Ngày {norm_day}")
    print(f"⚡ Force Mode:  {'YES (Overwrite)' if force_overwrite else 'NO (Skip existing)'}")
    print("=" * 60)

    gdrive_index = fetch_live_gdrive_index()

    print("\n1. Accessing o9o.net main menu to find Grade page...")
    html = fetch(BASE_URL)
    soup = BeautifulSoup(html, 'html.parser')
    menu = soup.find('ul', id='menu-menu')

    grade_url = None
    actual_g_name = None
    if menu:
        for a in menu.find_all('a'):
            name = a.text.strip()
            if "Home" not in name and norm_grade.lower() in name.lower():
                actual_g_name = name
                grade_url = a['href']
                break

    if not grade_url:
        # Fallback search if exact menu match failed
        print(f"⚠️ Could not find exact menu entry for {norm_grade}, attempting fallback search...")
        if menu:
            for a in menu.find_all('a'):
                name = a.text.strip()
                # Check for number match
                grade_num = re.search(r'\d+', norm_grade)
                if grade_num and grade_num.group(0) in name:
                    actual_g_name = name
                    grade_url = a['href']
                    break

    if not grade_url:
        print(f"❌ ERROR: Grade '{norm_grade}' not found on o9o.net menu.")
        sys.exit(1)

    actual_g_name = norm_grade  # Standardize name for GDrive & DB
    print(f"✅ Found Grade URL: {grade_url}")

    print(f"2. Locating Day {norm_day} link on {actual_g_name} schedule...")
    g_html = fetch(grade_url)
    g_soup = BeautifulSoup(g_html, 'html.parser')
    lichhoc = g_soup.find('ul', class_='lichhoc')

    day_url = None
    if lichhoc:
        for lesson in lichhoc.find_all('a'):
            text = lesson.text.strip()
            lesson_num = re.search(r'\d+', text)
            if lesson_num and int(lesson_num.group(0)) == int(norm_day):
                day_url = lesson['href']
                break

    if not day_url:
        print(f"❌ ERROR: Day {norm_day} not found in schedule for {actual_g_name}.")
        sys.exit(1)

    print(f"✅ Found Day URL: {day_url}")

    vn_tz = timezone(timedelta(hours=7))
    start_time_str = datetime.now(vn_tz).strftime("%Y-%m-%d %H:%M:%S")

    start_msg = (
        f"🚀 [STEP 1.2: BẮT ĐẦU CÀO BÀI THEO NGÀY]\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"📚 Grade: {actual_g_name}\n"
        f"📅 Ngày học: Ngày {norm_day}\n"
        f"⚡ Chế độ: {'Ghi đè' if force_overwrite else 'Thường (bỏ qua file đã có)'}\n"
        f"⏰ Thời gian bắt đầu: {start_time_str}"
    )
    print("\n" + start_msg + "\n")
    send_telegram_msg(start_msg)
    log_to_google_doc(f"Start Step 1.2: Grade [{actual_g_name}], Ngày [{norm_day}]")

    print(f"---> Fetching playlist for Day {norm_day}...")
    l_html = fetch(day_url)
    data_match = re.search(r'const playlistData = (\[.*?\]);', l_html, re.DOTALL)
    if not data_match:
        print(f"❌ ERROR: Could not find playlistData on page {day_url}")
        sys.exit(1)

    try:
        playlist = json.loads(data_match.group(1))
    except Exception as e:
        print(f"❌ ERROR parsing playlist JSON: {e}")
        sys.exit(1)

    day_tasks = []
    for item in playlist:
        subject = item.get('title', 'Unknown')
        safe_subject = subject.replace('/', '-').replace(':', '').replace('?', '')
        link = item.get('file', '')
        if link.startswith('/'):
            link = BASE_URL + link

        file_name = f"{actual_g_name} - {norm_day} - {safe_subject}.mp4"
        gdrive_rel_path = f"{actual_g_name}/Ngày {norm_day}/{safe_subject}/{file_name}"
        
        day_tasks.append({
            "actual_g_name": actual_g_name,
            "day": norm_day,
            "subject": subject,
            "link": link,
            "gdrive_rel_path": gdrive_rel_path
        })

    print(f"\n⚡ Found {len(day_tasks)} subjects/videos for Day {norm_day}. Processing concurrently...")
    day_success = True
    if day_tasks:
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = {executor.submit(process_single_video, t, force_overwrite): t for t in day_tasks}
            for future in as_completed(futures):
                res = future.result()
                if not res:
                    day_success = False

    stop_time_str = datetime.now(vn_tz).strftime("%Y-%m-%d %H:%M:%S")
    status_str = "THÀNH CÔNG 🎉" if day_success else "CÓ LỖI TẢI ⚠️"

    end_msg = (
        f"🛑 [STEP 1.2: HOÀN THÀNH CÀO THEO NGÀY]\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"📚 Grade: {actual_g_name}\n"
        f"📅 Ngày học: Ngày {norm_day}\n"
        f"📊 Trạng thái: {status_str}\n"
        f"⏰ Thời gian hoàn tất: {stop_time_str}"
    )
    print("\n" + end_msg + "\n")
    send_telegram_msg(end_msg)
    log_to_google_doc(f"Finished Step 1.2: Grade [{actual_g_name}], Ngày [{norm_day}] - Status: {status_str}")

    if day_success and auto_sync:
        print("\n🔄 Running Step 2 to regenerate database index & upload updated index_songsong.html...")
        step2_script = os.path.join(SCRIPTS_DIR, "step2_link_database.py")
        upload_script = os.path.join(SCRIPTS_DIR, "upload_to_gdrive.py")
        
        if os.path.exists(step2_script):
            subprocess.run([sys.executable, step2_script], cwd=BASE_DIR)
        if os.path.exists(upload_script):
            subprocess.run([sys.executable, upload_script], cwd=BASE_DIR)

        # Git commit & push if git repository is clean or modified
        try:
            subprocess.run(["git", "add", "database_*.json", "index_songsong.html"], cwd=BASE_DIR, capture_output=True)
            commit_msg = f"auto(step1.2): sync database & html for {actual_g_name} day {norm_day}"
            subprocess.run(["git", "commit", "-m", commit_msg], cwd=BASE_DIR, capture_output=True)
            subprocess.run(["git", "push", "origin", "main"], cwd=BASE_DIR, capture_output=True)
            print("🚀 Git commit & push completed.")
        except Exception as e:
            print(f"⚠️ Git sync warning: {e}")

    return day_success

def main():
    parser = argparse.ArgumentParser(description="Step 1.2 Targeted Single-Grade & Single-Day Scraper for Abeka Videos.")
    parser.add_argument("-g", "--grade", type=str, required=True, help="Target Grade (e.g. Grade 4, K4, 05, g1, 4)")
    parser.add_argument("-d", "--day", type=str, required=True, help="Target Day number (e.g. 15, 015, 120)")
    parser.add_argument("-f", "--force", action="store_true", help="Force re-download and overwrite existing files on GDrive")
    parser.add_argument("--no-sync", action="store_true", help="Disable automatic Step 2 index regeneration & git upload")

    args = parser.parse_args()

    run_step1_2(
        grade_param=args.grade,
        day_param=args.day,
        force_overwrite=args.force,
        auto_sync=not args.no_sync
    )

if __name__ == "__main__":
    main()
