#!/usr/bin/env python3
"""
Automated Abeka Video Downloader.
Downloads next pending lessons to local temporary folder.
"""

import os
import json
import subprocess
import argparse
import sys
sys.path.append("/media/vpsg24gb/DATA1/o9o/scripts")
from telegram_notifier import send_telegram_notification
import time

BASE_DIR = "/media/vpsg24gb/DATA1/o9o"
STATUS_JSON_PATH = os.path.join(BASE_DIR, "Video Processing/status.json")
DATA_DIR = os.path.join(BASE_DIR, "data")

GRADES = ["k4", "k5", "g1", "g2", "g3", "g4", "g5", "g6", "g7", "g8", "g9", "g10", "g11", "g12"]

def load_status():
    if os.path.exists(STATUS_JSON_PATH):
        try:
            with open(STATUS_JSON_PATH, "r", encoding="utf-8") as f:
                status = json.load(f)
                # Ensure downloaded_lessons key exists for each grade
                for grade in GRADES:
                    if grade not in status:
                        status[grade] = {"completed_lessons": [], "downloaded_lessons": [], "total_lessons": 170}
                    if "downloaded_lessons" not in status[grade]:
                        status[grade]["downloaded_lessons"] = []
                return status
        except Exception as e:
            print(f"Error reading status.json: {e}")
            
    # Default initial status
    status = {}
    for grade in GRADES:
        grade_dir = os.path.join(DATA_DIR, grade)
        total_lessons = 0
        if os.path.isdir(grade_dir):
            total_lessons = len([f for f in os.listdir(grade_dir) if f.endswith(".json")])
        status[grade] = {
            "completed_lessons": [],
            "downloaded_lessons": [],
            "total_lessons": total_lessons or 170
        }
    return status

def save_status(status):
    with open(STATUS_JSON_PATH, "w", encoding="utf-8") as f:
        json.dump(status, f, indent=2, ensure_ascii=False)

def find_next_lessons(status, batch_size):
    pending = []
    for grade in GRADES:
        data = status.get(grade, {"completed_lessons": [], "downloaded_lessons": [], "total_lessons": 170})
        completed = set(data.get("completed_lessons", []))
        downloaded = set(data.get("downloaded_lessons", []))
        tot = data.get("total_lessons", 170)
        
        for lesson_num in range(1, tot + 1):
            if lesson_num not in completed and lesson_num not in downloaded:
                pending.append((grade, lesson_num))
                if len(pending) >= batch_size:
                    return pending
    return pending

def run_cmd(cmd, cwd=BASE_DIR):
    print(f"Executing: {' '.join(cmd)}")
    res = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
    if res.returncode != 0:
        print(f"Error output: {res.stderr}")
    return res.returncode == 0

def main():
    try:
        parser = argparse.ArgumentParser(description="Run batch downloader only.")
        parser.add_argument("--batch-size", type=int, default=3, help="Number of lessons to download")
        args = parser.parse_args()
        
        status = load_status()
        pending = find_next_lessons(status, args.batch_size)
        
        if not pending:
            print("🎉 No pending lessons to download.")
            return
            
        pending_str = ", ".join([f"{g.upper()} L{n}" for g, n in pending])
        send_telegram_notification(f"Bắt đầu tải {len(pending)} bài học: {pending_str}...", agent_name="Downloader")
        
        processed_any = False
        failed_lessons = []
        for grade, num in pending:
            print(f"\n🎬 Starting local download for {grade.upper()} Lesson {num}...")
            cmd_dl = [
                "python3", "scripts/download_to_gdrive.py",
                "--grade", grade,
                "--start", str(num),
                "--end", str(num),
                "--download-only"
            ]
            if run_cmd(cmd_dl):
                print(f"✅ Successfully downloaded {grade.upper()} Lesson {num}!")
                status[grade]["downloaded_lessons"].append(num)
                save_status(status)
                processed_any = True
            else:
                print(f"❌ Failed to download {grade.upper()} Lesson {num}.")
                failed_lessons.append(f"{grade.upper()} L{num}")
                
        if processed_any:
            save_status(status)
            
        if failed_lessons:
            send_telegram_notification(f"⚠️ Hoàn tất lượt tải. Lỗi tại các bài: {', '.join(failed_lessons)}", agent_name="Downloader")
        else:
            send_telegram_notification(f"✅ Tải thành công {len(pending)} bài học về VPS.", agent_name="Downloader")
    except Exception as e:
        send_telegram_notification(f"❌ Lỗi nghiêm trọng: {e}", agent_name="Downloader")
        raise e

if __name__ == "__main__":
    main()
