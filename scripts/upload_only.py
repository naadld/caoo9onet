#!/usr/bin/env python3
"""
Automated Abeka Video Uploader.
Uploads downloaded videos from local temp folder to GDrive,
runs link mapper, and updates status JSON.
"""

import os
import json
import sys
sys.path.append("/media/vpsg24gb/DATA1/o9o/scripts")
from telegram_notifier import send_telegram_notification

BASE_DIR = "/media/vpsg24gb/DATA1/o9o"
STATUS_JSON_PATH = os.path.join(BASE_DIR, "Video Processing/status.json")
DATA_DIR = os.path.join(BASE_DIR, "data")
REMOTE = "vpsg24gb.aleron,root_folder_id=1E_hq6-w6OacdDTlTCvpCC-JKPJoQdz1x:"

GRADES = ["k4", "k5", "g1", "g2", "g3", "g4", "g5", "g6", "g7", "g8", "g9", "g10", "g11", "g12"]

def load_status():
    if os.path.exists(STATUS_JSON_PATH):
        try:
            with open(STATUS_JSON_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"Error reading status.json: {e}")
    return {}

def save_status(status):
    with open(STATUS_JSON_PATH, "w", encoding="utf-8") as f:
        json.dump(status, f, indent=2, ensure_ascii=False)

def run_cmd(cmd, cwd=BASE_DIR):
    import subprocess
    print(f"Executing: {' '.join(cmd)}")
    res = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
    if res.returncode != 0:
        print(f"Error output: {res.stderr}")
    return res.returncode == 0

def check_lesson_fully_linked(grade, lesson_num):
    # Determine filename
    # e.g., 2023-k5-002.json
    grade_dir = os.path.join(DATA_DIR, grade)
    if not os.path.isdir(grade_dir):
        return False
        
    # Search for json file matching the lesson number
    files = [f for f in os.listdir(grade_dir) if f.endswith(".json")]
    matched_file = None
    for f in files:
        parts = f[:-5].split("-")
        try:
            if int(parts[-1]) == lesson_num:
                matched_file = f
                break
        except:
            continue
            
    if not matched_file:
        print(f"  ⚠️ Could not find playlist JSON for {grade.upper()} Lesson {lesson_num}")
        return False
        
    json_path = os.path.join(grade_dir, matched_file)
    try:
        with open(json_path, "r", encoding="utf-8") as file_in:
            playlist = json.load(file_in)
    except Exception as e:
        print(f"  ⚠️ Error reading JSON {json_path}: {e}")
        return False
        
    # Check if all items have "gdrive:"
    all_gdrive = True
    for item in playlist:
        file_val = item.get("file", "")
        if not file_val.startswith("gdrive:"):
            print(f"  ❌ Video '{item.get('title')}' in {matched_file} is not linked yet (value: {file_val})")
            all_gdrive = False
            
    return all_gdrive

def main():
    try:
        status = load_status()
        
        # 1. Check if we have any downloaded lessons pending upload
        pending_uploads = []
        for grade in GRADES:
            data = status.get(grade, {})
            downloaded = data.get("downloaded_lessons", [])
            for num in downloaded:
                pending_uploads.append(f"{grade.upper()} L{num}")
                
        if not pending_uploads:
            print("🎉 No pending downloaded lessons to upload.")
            return
            
        send_telegram_notification(f"Bắt đầu đẩy {len(pending_uploads)} bài lên Google Drive: {', '.join(pending_uploads)}...", agent_name="Uploader")
        
        # 2. Run Rclone move to sync and delete source files
        cmd_upload = [
            "/home/vpsg24gb/bin/rclone", "move",
            "/media/vpsg24gb/DATA1/o9o/Video Processing/tmt/",
            REMOTE,
            "--verbose"
        ]
        
        if not run_cmd(cmd_upload):
            print("❌ Rclone move failed.")
            send_telegram_notification("❌ Rclone move thất bại.", agent_name="Uploader")
            return
            
        # 3. Run linking script to map IDs back to playlists
        print("\n🔗 Linking uploaded files in JSON playlists...")
        run_cmd(["python3", "scripts/link_gdrive_files.py"])
        
        # 4. Check each downloaded lesson to verify upload and update status
        status_changed = False
        fully_linked = []
        failed_link = []
        for grade in GRADES:
            data = status.get(grade, {})
            downloaded = data.get("downloaded_lessons", [])
            completed = data.get("completed_lessons", [])
            
            still_downloaded = []
            for num in downloaded:
                print(f"🔍 Verifying upload status for {grade.upper()} Lesson {num}...")
                if check_lesson_fully_linked(grade, num):
                    print(f"✅ Verified! Moving {grade.upper()} Lesson {num} to completed.")
                    if num not in completed:
                        completed.append(num)
                    status_changed = True
                    fully_linked.append(f"{grade.upper()} L{num}")
                else:
                    print(f"⚠️ Lesson {grade.upper()} Lesson {num} is not fully linked/uploaded yet.")
                    still_downloaded.append(num)
                    failed_link.append(f"{grade.upper()} L{num}")
                    
            data["downloaded_lessons"] = still_downloaded
            data["completed_lessons"] = completed
            status[grade] = data
            if status_changed:
                save_status(status)
            
        if failed_link:
            send_telegram_notification(f"⚠️ Hoàn tất tải lên. Một số bài chưa thể map liên kết: {', '.join(failed_link)}", agent_name="Uploader")
        else:
            send_telegram_notification(f"✅ Đẩy lên Drive và ánh xạ link thành công: {', '.join(fully_linked)}.", agent_name="Uploader")
    except Exception as e:
        send_telegram_notification(f"❌ Lỗi nghiêm trọng: {e}", agent_name="Uploader")
        raise e

if __name__ == "__main__":
    main()
