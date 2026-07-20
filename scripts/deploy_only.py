#!/usr/bin/env python3
"""
Automated Abeka Website Deployer.
Updates status.md, commits and pushes changes to GitHub,
and copies site configuration to GDrive.
"""

import os
import json
import subprocess
import sys
sys.path.append("/media/vpsg24gb/DATA1/o9o/scripts")
from telegram_notifier import send_telegram_notification
import time

BASE_DIR = "/media/vpsg24gb/DATA1/o9o"
STATUS_JSON_PATH = os.path.join(BASE_DIR, "Video Processing/status.json")
STATUS_MD_PATH = os.path.join(BASE_DIR, "Video Processing/status.md")
DATA_DIR = os.path.join(BASE_DIR, "data")
REMOTE = "vpsg24gb.aleron,root_folder_id=1AXyDO_l32JWrdlj0K7r6Vl65Tv5EmIAm:"

GRADES = ["k4", "k5", "g1", "g2", "g3", "g4", "g5", "g6", "g7", "g8", "g9", "g10", "g11", "g12"]

def load_status():
    if os.path.exists(STATUS_JSON_PATH):
        try:
            with open(STATUS_JSON_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"Error reading status.json: {e}")
    return {}

def generate_status_report(status):
    total_completed = 0
    total_all = 0
    
    table_rows = []
    for grade in GRADES:
        data = status.get(grade, {"completed_lessons": [], "total_lessons": 170})
        comp = len(data.get("completed_lessons", []))
        tot = data.get("total_lessons", 170)
        total_completed += comp
        total_all += tot
        
        pct = (comp / tot * 100) if tot > 0 else 0
        progress_bar = f"![Progress](https://geps.dev/progress/{int(pct)})"
        
        comp_list_str = ", ".join(map(str, sorted(data.get("completed_lessons", []))))
        if len(comp_list_str) > 40:
            comp_list_str = comp_list_str[:37] + "..."
            
        table_rows.append(
            f"| {grade.upper()} | {comp}/{tot} | {pct:.1f}% | {progress_bar} | {comp_list_str or 'None'} |"
        )
        
    overall_pct = (total_completed / total_all * 100) if total_all > 0 else 0
    
    md_content = f"""# Abeka Video Processing Status

This file is automatically updated by the automated cron batch processor.
It tracks the video download and upload status for each grade to Google Drive (**aleron.dt@gmail.com**).

## Overall Progress: {total_completed} / {total_all} lessons ({overall_pct:.1f}%)
![Overall Progress](https://geps.dev/progress/{int(overall_pct)}?c=00ff00)

| Grade | Completed | Progress % | Visual Progress | Completed Lesson Days |
|---|---|---|---|---|
""" + "\n".join(table_rows) + """

---
*Last updated: {time_str}*
""".format(time_str=time.strftime("%Y-%m-%d %H:%M:%S %Z"))

    with open(STATUS_MD_PATH, "w", encoding="utf-8") as f:
        f.write(md_content)

def run_cmd(cmd, cwd=BASE_DIR):
    print(f"Executing: {' '.join(cmd)}")
    res = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
    if res.returncode != 0:
        print(f"Error output: {res.stderr}")
    return res.returncode == 0

def main():
    try:
        status = load_status()
        if not status:
            print("❌ Status JSON is empty or invalid.")
            return
            
        send_telegram_notification("Bắt đầu tạo status.md và deploy website lên GitHub/GDrive...", agent_name="Deployer")
        
        # 1. Generate status report md
        print("📝 Generating status.md report...")
        generate_status_report(status)
        
        # 2. Commit and push to GitHub
        print("\n📤 Committing and pushing changes to GitHub Pages...")
        run_cmd(["git", "stash"])
        run_cmd(["git", "pull", "--rebase", "origin", "main"])
        run_cmd(["git", "stash", "pop"])
        run_cmd(["git", "add", "-A"])
        run_cmd(["git", "commit", "-m", "Automated Site Config Sync"])
        run_cmd(["git", "push", "origin", "main"])
        
        # 3. Copy site config back to Google Drive config folder
        print("\n☁️ Syncing site config to Google Drive...")
        cmd_sync_gdrive = [
            "/home/vpsg24gb/bin/rclone", "copy",
            BASE_DIR,
            REMOTE,
            "--exclude", ".git/**",
            "--exclude", "data/*/*/",
            "--verbose"
        ]
        run_cmd(cmd_sync_gdrive)
        
        print("\n🎉 Website deployment and GDrive sync completed successfully!")
        send_telegram_notification("✅ Hoàn tất triển khai website và đồng bộ Google Drive thành công!", agent_name="Deployer")
    except Exception as e:
        send_telegram_notification(f"❌ Lỗi nghiêm trọng: {e}", agent_name="Deployer")
        raise e

if __name__ == "__main__":
    main()
