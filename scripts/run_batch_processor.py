#!/usr/bin/env python3
"""
Automated Abeka Video Batch Processor.
Downloads a batch of lessons, uploads them to Google Drive (aleron.dt@gmail.com),
updates the local JSON playlists with GDrive File IDs,
and commits/pushes the changes to GitHub Pages.
"""

import os
import json
import subprocess
import argparse
import time

BASE_DIR = "/media/vpsg24gb/DATA1/o9o"
STATUS_JSON_PATH = os.path.join(BASE_DIR, "Video Processing/status.json")
STATUS_MD_PATH = os.path.join(BASE_DIR, "Video Processing/status.md")
DATA_DIR = os.path.join(BASE_DIR, "data")

GRADES = ["k4", "k5", "g1", "g2", "g3", "g4", "g5", "g6", "g7", "g8", "g9", "g10", "g11", "g12"]

def load_status():
    if os.path.exists(STATUS_JSON_PATH):
        try:
            with open(STATUS_JSON_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"Error reading status.json: {e}")
            
    # Default initial status
    status = {}
    for grade in GRADES:
        # Determine total lessons based on json files in data folder
        grade_dir = os.path.join(DATA_DIR, grade)
        total_lessons = 0
        if os.path.isdir(grade_dir):
            total_lessons = len([f for f in os.listdir(grade_dir) if f.endswith(".json")])
        
        # K5 Day 2 was already uploaded in our test
        completed = [2] if grade == "k5" else []
        status[grade] = {
            "completed_lessons": completed,
            "total_lessons": total_lessons or 170
        }
    return status

def save_status(status):
    with open(STATUS_JSON_PATH, "w", encoding="utf-8") as f:
        json.dump(status, f, indent=2, ensure_ascii=False)
        
    # Generate human-readable status.md report
    generate_status_report(status)

def generate_status_report(status):
    total_completed = 0
    total_all = 0
    
    table_rows = []
    for grade in GRADES:
        data = status.get(grade, {"completed_lessons": [], "total_lessons": 170})
        comp = len(data["completed_lessons"])
        tot = data["total_lessons"]
        total_completed += comp
        total_all += tot
        
        pct = (comp / tot * 100) if tot > 0 else 0
        progress_bar = f"![Progress](https://geps.dev/progress/{int(pct)})"
        
        comp_list_str = ", ".join(map(str, sorted(data["completed_lessons"])))
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

def find_next_lessons(status, batch_size):
    pending = []
    for grade in GRADES:
        data = status.get(grade, {"completed_lessons": [], "total_lessons": 170})
        completed = set(data["completed_lessons"])
        tot = data["total_lessons"]
        
        for lesson_num in range(1, tot + 1):
            if lesson_num not in completed:
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
    parser = argparse.ArgumentParser(description="Run batch video downloader and uploader.")
    parser.add_argument("--batch-size", type=int, default=3, help="Number of lessons to process in this run")
    args = parser.parse_args()
    
    status = load_status()
    pending = find_next_lessons(status, args.batch_size)
    
    if not pending:
        print("🎉 All lessons processed! No more pending lessons.")
        return

    print(f"🚀 Found {len(pending)} lessons to process in this batch:")
    for grade, num in pending:
        print(f"  - {grade.upper()} Lesson {num}")
        
    processed_any = False
    for grade, num in pending:
        print(f"\n🎬 Starting download/upload for {grade.upper()} Lesson {num}...")
        
        # 1. Download and Upload
        # Lệnh: python3 scripts/download_to_gdrive.py --grade {grade} --start {num} --end {num}
        cmd_dl = [
            "python3", "scripts/download_to_gdrive.py",
            "--grade", grade,
            "--start", str(num),
            "--end", str(num)
        ]
        
        if run_cmd(cmd_dl):
            print(f"✅ Successfully processed {grade.upper()} Lesson {num}!")
            status[grade]["completed_lessons"].append(num)
            processed_any = True
        else:
            print(f"❌ Failed to process {grade.upper()} Lesson {num}. Skipping this one.")
            
    if processed_any:
        # 2. Update local JSON link mappings
        print("\n🔗 Linking uploaded files in JSON playlists...")
        run_cmd(["python3", "scripts/link_gdrive_files.py"])
        
        # 3. Save status and regenerate report
        save_status(status)
        
        # 4. Commit and Push to GitHub Pages
        print("\n📤 Committing and pushing changes to GitHub Pages...")
        run_cmd(["git", "stash"])
        run_cmd(["git", "pull", "--rebase", "origin", "main"])
        run_cmd(["git", "stash", "pop"])
        run_cmd(["git", "add", "-A"])
        run_cmd(["git", "commit", "-m", f"Automated Batch Sync: processed {len(pending)} lessons"])
        run_cmd(["git", "push", "origin", "main"])
        print("\n🎉 Batch processing completed and pushed successfully!")
    else:
        print("\n⚠️ No lessons were successfully processed in this batch.")

if __name__ == "__main__":
    main()
