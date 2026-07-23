#!/usr/bin/env python3
"""
Direct Pipe Streaming Downloader for Abeka Videos (Multi-Machine Anti-Duplicate Enabled).
Streams video bytes directly from o9o.net to Google Drive using yt-dlp and rclone rcat,
with zero local disk space usage and instant multi-machine duplicate prevention.
Prioritizes Grade 2 & Grade 5 first.
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

BASE_URL = "https://www.o9o.net"
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOCK_FILE = os.path.join(BASE_DIR, "step1_scraper.lock")

# Telegram Bot Credentials (matched from Step 5-6)
PRIMARY_BOT_TOKEN = "8525129998:AAG6-Ib_AfqEGc7jwroo58reg5UVYlRZ-3A"
FALLBACK_BOT_TOKEN = "8733078949:AAEX6WGeGasyVHXEYqgadgE8RFovyr64lBg"
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
                    print(f"📱 [Telegram Notification Sent Success] Token: {tok[:12]}...")
                    sent = True
                    break
        except Exception as e:
            print(f"⚠️ Telegram send attempt failed for token {tok[:12]}...: {e}")

    if not sent:
        print("❌ Could not send Telegram report to specified chat/bot.")

# Enforce strict single-instance execution across system
try:
    lock_file_fd = open(LOCK_FILE, "w")
    fcntl.flock(lock_file_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
except (IOError, OSError):
    print("⚠️ Another instance of step1_direct_stream.py is currently actively streaming a video in the background.")
    sys.exit(0)

# Resolve executables dynamically
RCLONE_BIN = shutil.which("rclone") or "rclone"

RCLONE_CONF = os.getenv("RCLONE_CONFIG") or os.path.expanduser("~/.config/rclone/rclone.conf")
if not os.path.exists(RCLONE_CONF) and os.path.exists("/home/vpsg24gb/.config/rclone/rclone.conf"):
    RCLONE_CONF = "/home/vpsg24gb/.config/rclone/rclone.conf"

YTDLP_BIN = shutil.which("yt-dlp") or "yt-dlp"

REMOTE_BASE = "vpsg24gb.aleron,root_folder_id=11fQ8VYTmwRX9fMJFXeTrTTeZGDqki6dh:"
TARGET_PAIRS = [
    ["Grade 2", "Grade 5"]
]

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
        from datetime import datetime, timezone, timedelta

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

        formatted_entry = f"{now_str}: {entry_text}\n"

        requests = [{
            'insertText': {
                'location': {'index': end_index},
                'text': formatted_entry
            }
        }]
        docs_service.documents().batchUpdate(documentId=doc_id, body={'requests': requests}).execute()
        print(f"📝 [Doc Log Success] {formatted_entry.strip()}")
    except Exception as e:
        print(f"⚠️ Doc Logger Error: {e}")

GDRIVE_LOCK_PATH = f"{REMOTE_BASE}.scraper_lock"

def check_and_acquire_gdrive_lock():
    try:
        res = subprocess.run(
            [RCLONE_BIN, "--config", RCLONE_CONF, "cat", GDRIVE_LOCK_PATH],
            capture_output=True, text=True, timeout=15
        )
        if res.returncode == 0 and res.stdout.strip():
            try:
                lock_time = float(res.stdout.strip())
                age_seconds = time.time() - lock_time
                if age_seconds < 2700: # Fresh lock (< 45 mins)
                    print("=" * 60)
                    print(f"⚠️ Another Cloud Scraper instance is currently actively streaming on GDrive (Lock age: {age_seconds/60:.1f} mins).")
                    print("🚀 SKIPPING Step 1 immediately so only 1 scraping job runs. Subsequent indexer & dashboard steps will continue.")
                    print("=" * 60)
                    sys.exit(0)
                else:
                    print(f"ℹ️ Stale GDrive lock detected ({age_seconds/3600:.1f} hours old). Overwriting lock...")
            except ValueError:
                pass
    except Exception as e:
        print(f"⚠️ Lock check warning: {e}")

    try:
        p = subprocess.Popen([RCLONE_BIN, "--config", RCLONE_CONF, "rcat", GDRIVE_LOCK_PATH], stdin=subprocess.PIPE)
        p.communicate(input=str(time.time()).encode("utf-8"))
        print("🔒 GDrive distributed scraper lock acquired.")
    except Exception as e:
        print(f"⚠️ Lock creation warning: {e}")

def release_gdrive_lock():
    try:
        subprocess.run(
            [RCLONE_BIN, "--config", RCLONE_CONF, "deletefile", GDRIVE_LOCK_PATH],
            capture_output=True, timeout=15
        )
        print("🔓 GDrive distributed scraper lock released.")
    except Exception as e:
        print(f"⚠️ Lock release warning: {e}")

# Threading locks for synchronization
db_lock = threading.Lock()
gdrive_index_lock = threading.Lock()

# Global state
gdrive_index = {}

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

def get_progress_file(script_id):
    return os.path.join(BASE_DIR, f"progress_{script_id}.json")

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

def save_database(grade, db):
    db_file = get_db_file(grade)
    with db_lock:
        with open(db_file, 'w', encoding='utf-8') as f:
            json.dump(db, f, ensure_ascii=False, indent=4)

def load_progress(script_id="SongSong"):
    prog_file = get_progress_file(script_id)
    if os.path.exists(prog_file):
        try:
            with open(prog_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            pass
    return {"pair_idx": 0, "day_num": 1}

def save_progress(script_id, pair_idx, day_num):
    prog_file = get_progress_file(script_id)
    with open(prog_file, 'w', encoding='utf-8') as f:
        json.dump({"pair_idx": pair_idx, "day_num": day_num}, f)

def fetch_live_gdrive_index():
    print("🔍 Fetching live GDrive index to prevent multi-machine duplicates...")
    g_files = {}  # path.lower() -> size in bytes
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
    # Ensure zero empty folders are created on Google Drive if stream fails.
    # Download to temporary staging file first, verify 100% completion, then copy to Google Drive.
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

        # File is 100% complete! Copy directly to Google Drive
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

def process_single_video(item_info):
    actual_g_name = item_info["actual_g_name"]
    day = item_info["day"]
    subject = item_info["subject"]
    link = item_info["link"]
    gdrive_rel_path = item_info["gdrive_rel_path"]
    
    print(f"  🎬 [{subject}] Target: {gdrive_rel_path}")
    
    # Thread-safe check in database
    db = load_database(actual_g_name)
    record_exists = any(r['day'] == day and r['subject'] == subject for r in db)
    
    # Thread-safe check in live GDrive index
    with gdrive_index_lock:
        file_on_gdrive = gdrive_rel_path.lower() in gdrive_index
        gdrive_size = gdrive_index.get(gdrive_rel_path.lower(), 0) if file_on_gdrive else 0
        
    is_valid_on_gdrive = file_on_gdrive and gdrive_size > 100000
    
    success = False
    if is_valid_on_gdrive:
        print(f"    -> ⏭️ File already uploaded & valid ({gdrive_size / 1024 / 1024:.2f} MB). Skipping.")
        success = True
        if not record_exists:
            db = load_database(actual_g_name)
            db.append({
                "grade": actual_g_name,
                "day": day,
                "subject": subject,
                "link": gdrive_rel_path
            })
            save_database(actual_g_name, db)
            print(f"    -> Restored missing database record for {subject}.")
    else:
        if file_on_gdrive:
            print(f"    -> ⚠️ File is invalid/empty on Google Drive ({gdrive_size} bytes). Re-streaming...")
        else:
            print(f"    -> ⚡ Direct pipe streaming from o9o.net to Google Drive for: {subject}")
            
        if record_exists:
            db = load_database(actual_g_name)
            db = [r for r in db if not (r['day'] == day and r['subject'] == subject)]
            save_database(actual_g_name, db)
            
        success = direct_stream_to_gdrive(link, gdrive_rel_path)
        from datetime import datetime, timezone, timedelta
        vn_tz = timezone(timedelta(hours=7))
        now_str = datetime.now(vn_tz).strftime("%Y-%m-%d %H:%M:%S")
        if success:
            with gdrive_index_lock:
                gdrive_index[gdrive_rel_path.lower()] = 999999999
            log_to_google_doc(f"{now_str}: Hoàn thành {actual_g_name}, {day}, {subject}")
        else:
            log_to_google_doc(f"{now_str}: Lỗi cào video {subject} ({actual_g_name}, {day})")
                
    if success:
        db = load_database(actual_g_name)
        if not any(r['day'] == day and r['subject'] == subject for r in db):
            db.append({
                "grade": actual_g_name,
                "day": day,
                "subject": subject,
                "link": gdrive_rel_path
            })
            save_database(actual_g_name, db)
            print(f"    -> Updated database record for: {subject}")
        return True
    else:
        return False

def run_direct_streaming(pairs_to_run=TARGET_PAIRS, max_days=None, script_id="SongSong"):
    global gdrive_index
    check_and_acquire_gdrive_lock()
    try:
        print("=" * 60)
        print(f"🚀 O9O.NET DIRECT PIPE STREAMING DOWNLOADER (Active Pairs: {pairs_to_run})")
        print(f"Target GDrive Remote: {REMOTE_BASE}")
        print("=" * 60)

        gdrive_index = fetch_live_gdrive_index()

        print("\n1. Accessing main menu to map grades...")
        html = fetch(BASE_URL)
        soup = BeautifulSoup(html, 'html.parser')
        menu = soup.find('ul', id='menu-menu')
        
        all_grade_links = {}
        if menu:
            for a in menu.find_all('a'):
                name = a.text.strip()
                if "Home" not in name:
                    all_grade_links[name] = a['href']
                    
        print("2. Mapping lesson days for grade pairs...")
        grade_days_map = {}
        for pair in pairs_to_run:
            for g_name_short in pair:
                actual_g_name = next((k for k in all_grade_links.keys() if g_name_short.lower() in k.lower()), None)
                if not actual_g_name or actual_g_name in grade_days_map:
                    continue
                    
                grade_days_map[actual_g_name] = {}
                g_html = fetch(all_grade_links[actual_g_name])
                g_soup = BeautifulSoup(g_html, 'html.parser')
                lichhoc = g_soup.find('ul', class_='lichhoc')
                if lichhoc:
                    for lesson in lichhoc.find_all('a'):
                        grade_days_map[actual_g_name][lesson.text.strip()] = lesson['href']

        progress = load_progress(script_id)
        start_pair_idx = progress.get("pair_idx", 0)
        start_day_num = progress.get("day_num", 1)

        print(f"\n[SYSTEM] Resuming from PAIR {start_pair_idx + 1}, DAY {start_day_num:03d}")

        start_pair_str = " & ".join(pairs_to_run[start_pair_idx]) if start_pair_idx < len(pairs_to_run) else "N/A"
        start_day_str = f"Ngày {start_day_num:03d}"

        vn_tz = timezone(timedelta(hours=7))
        start_time_str = datetime.now(vn_tz).strftime("%Y-%m-%d %H:%M:%S")

        start_msg = (
            f"🚀 [STEP 1: BẮT ĐẦU CÀO VIDEO]\n"
            f"━━━━━━━━━━━━━━━━━━━━━━\n"
            f"📚 Grade cào: {start_pair_str}\n"
            f"📅 Ngày sẽ cào: {start_day_str}\n"
            f"⏰ Giờ bắt đầu (GMT+7): {start_time_str}"
        )
        print("\n" + start_msg + "\n")
        send_telegram_msg(start_msg)
        log_to_google_doc(f"Step 1 Bắt đầu cào: Grade [{start_pair_str}], {start_day_str}")

        last_scraped_grade = start_pair_str
        last_scraped_day = start_day_str

        processed_days_count = 0
        try:
            for p_idx in range(start_pair_idx, len(pairs_to_run)):
                pair = pairs_to_run[p_idx]
                print(f"\n{'#'*60}\nPROCESSING PAIR: {' & '.join(pair)}\n{'#'*60}")

                current_start_day = start_day_num if p_idx == start_pair_idx else 1

                for day_num in range(current_start_day, 171):
                    if max_days and processed_days_count >= max_days:
                        print(f"\n✋ Reached max_days limit ({max_days}). Stopping Step 1.")
                        break

                    day = f"{day_num:03d}"
                    last_scraped_grade = " & ".join(pair)
                    last_scraped_day = f"Ngày {day}"

                    print(f"\n{'='*50}\nPROCESSING DAY: {day}\n{'='*50}")

                    day_tasks = []

                    # 1. Gather all tasks for this day across both grades
                    for g_name_short in pair:
                        actual_g_name = next((k for k in grade_days_map.keys() if g_name_short.lower() in k.lower()), None)
                        if not actual_g_name:
                            continue

                        day_url = grade_days_map[actual_g_name].get(day)
                        if not day_url:
                            continue

                        print(f"---> [{actual_g_name}] Fetching Day {day} playlist...")
                        l_html = fetch(day_url)
                        data_match = re.search(r'const playlistData = (\[.*?\]);', l_html, re.DOTALL)
                        if not data_match:
                            continue

                        try:
                            playlist = json.loads(data_match.group(1))
                        except Exception:
                            continue

                        for item in playlist:
                            subject = item.get('title', 'Unknown')
                            safe_subject = subject.replace('/', '-').replace(':', '').replace('?', '')
                            link = item.get('file', '')
                            if link.startswith('/'):
                                link = BASE_URL + link

                            file_name = f"{actual_g_name} - {day} - {safe_subject}.mp4"
                            gdrive_rel_path = f"{actual_g_name}/Ngày {day}/{safe_subject}/{file_name}"
                            
                            day_tasks.append({
                                "actual_g_name": actual_g_name,
                                "day": day,
                                "subject": subject,
                                "link": link,
                                "gdrive_rel_path": gdrive_rel_path
                            })

                    # 2. Process tasks concurrently with ThreadPoolExecutor (max_workers=5)
                    day_success = True
                    if day_tasks:
                        print(f"\n⚡ Processing {len(day_tasks)} videos concurrently (Max 5 parallel streams)...")
                        with ThreadPoolExecutor(max_workers=5) as executor:
                            futures = {executor.submit(process_single_video, t): t for t in day_tasks}
                            for future in as_completed(futures):
                                res = future.result()
                                if not res:
                                    day_success = False
                    else:
                        print(f"ℹ️ No tasks to process for Day {day}.")

                    if day_success:
                        save_progress(script_id, p_idx, day_num + 1)
                        processed_days_count += 1
                    else:
                        print(f"\n⚠️ Day {day} had stream errors. Will retry next run.")

            print("\n🎉 Completed processing all grade pairs!")
        finally:
            stop_time_str = datetime.now(vn_tz).strftime("%Y-%m-%d %H:%M:%S")
            stop_msg = (
                f"🛑 [STEP 1: THÔNG BÁO DỪNG CÀO]\n"
                f"━━━━━━━━━━━━━━━━━━━━━━\n"
                f"📚 Grade cuối cùng: {last_scraped_grade}\n"
                f"📅 Ngày cuối cùng đã cào được: {last_scraped_day}\n"
                f"⏰ Giờ dừng (GMT+7): {stop_time_str}"
            )
            print("\n" + stop_msg + "\n")
            send_telegram_msg(stop_msg)
            log_to_google_doc(f"Step 1 Thông báo dừng: Grade cuối [{last_scraped_grade}], Ngày cuối [{last_scraped_day}]")
    finally:
        release_gdrive_lock()

def main():
    parser = argparse.ArgumentParser(description="Direct Pipe Streaming Downloader for Abeka Videos.")
    parser.add_argument("--max-days", type=int, default=None, help="Maximum number of days to process in this run")
    parser.add_argument("--grade2-5-only", action="store_true", help="Process only Grade 2 and Grade 5 pair")
    parser.add_argument("--force-local", action="store_true", help="Force running on local machine/VPS")
    args = parser.parse_args()
    
    is_github_actions = os.getenv("GITHUB_ACTIONS") == "true"
    if not is_github_actions and not args.force_local:
        print("=" * 60)
        print("⛔ [VPS EXECUTION BLOCKED]")
        print("Theo nguyên tắc hệ thống, tiến trình cào chỉ được phép chạy 100% trên GitHub Cloud (GitHub Actions).")
        print("Tiến trình trên VPS đã bị chặn để không tốn CPU/RAM/băng thông VPS.")
        print("Vui lòng kích hoạt cào trên GitHub Actions Cloud hoặc chờ lịch tự động.")
        print("=" * 60)
        sys.exit(0)

    pairs = [["Grade 2", "Grade 5"]] if args.grade2_5_only else TARGET_PAIRS
    run_direct_streaming(pairs_to_run=pairs, max_days=args.max_days)

if __name__ == "__main__":
    main()
