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
import urllib.request
import subprocess
import argparse
import threading
import shutil
from concurrent.futures import ThreadPoolExecutor, as_completed
from bs4 import BeautifulSoup
import fcntl

BASE_URL = "https://www.o9o.net"
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOCK_FILE = os.path.join(BASE_DIR, "step1_scraper.lock")

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
    ["Grade 2", "Grade 5"],
    ["Grade 1", "Grade 4"],
    ["Grade 3", "Grade 6"],
    ["K5"]
]

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
            [RCLONE_BIN, "--config", RCLONE_CONF, "lsf", "-R", "--format", "ps", "--separator", ";", GDrive_REMOTE],
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
    ytdlp_cmd = [
        YTDLP_BIN,
        "--add-header", f"Referer:{BASE_URL}/",
        "-o", "-",
        m3u8_url
    ]
    
    rclone_cmd = [
        RCLONE_BIN, "--config", RCLONE_CONF, "rcat",
        f"{GDrive_REMOTE}{gdrive_target_path}"
    ]
    
    try:
        p1 = subprocess.Popen(ytdlp_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        p2 = subprocess.Popen(rclone_cmd, stdin=p1.stdout, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        p1.stdout.close()
        
        out2, err2 = p2.communicate()
        out1, err1 = p1.communicate()
        
        success1 = (p1.returncode == 0)
        success2 = (p2.returncode == 0)
        
        if not success1:
            print(f"    ❌ yt-dlp failed (code {p1.returncode}). Stderr: {err1.decode('utf-8', errors='ignore').strip()}")
        if not success2:
            print(f"    ❌ rclone failed (code {p2.returncode}). Stderr: {err2.decode('utf-8', errors='ignore').strip()}")
            
        return success1 and success2
    except Exception as e:
        print(f"    ❌ Pipe streaming failed: {e}")
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
        if success:
            with gdrive_index_lock:
                gdrive_index[gdrive_rel_path.lower()] = 999999999
                
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
    print("=" * 60)
    print(f"🚀 O9O.NET DIRECT PIPE STREAMING DOWNLOADER (Grade 2 & Grade 5 Top Priority - 2 Parallel Streams)")
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

    processed_days_count = 0
    for p_idx in range(start_pair_idx, len(pairs_to_run)):
        pair = pairs_to_run[p_idx]
        print(f"\n{'#'*60}\nPROCESSING PAIR: {' & '.join(pair)}\n{'#'*60}")

        current_start_day = start_day_num if p_idx == start_pair_idx else 1

        for day_num in range(current_start_day, 171):
            if max_days and processed_days_count >= max_days:
                print(f"\n✋ Reached max_days limit ({max_days}). Stopping Step 1.")
                return

            day = f"{day_num:03d}"
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

            # 2. Process tasks concurrently with ThreadPoolExecutor (max_workers=2)
            day_success = True
            if day_tasks:
                print(f"\n⚡ Processing {len(day_tasks)} videos concurrently (Max 2 parallel streams)...")
                with ThreadPoolExecutor(max_workers=2) as executor:
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

def main():
    parser = argparse.ArgumentParser(description="Direct Pipe Streaming Downloader for Abeka Videos.")
    parser.add_argument("--max-days", type=int, default=None, help="Maximum number of days to process in this run")
    parser.add_argument("--grade2-5-only", action="store_true", help="Process only Grade 2 and Grade 5 pair")
    args = parser.parse_args()
    
    pairs = [["Grade 2", "Grade 5"]] if args.grade2_5_only else TARGET_PAIRS
    run_direct_streaming(pairs_to_run=pairs, max_days=args.max_days)

if __name__ == "__main__":
    main()
