import json
import glob
import os

grades = ["K4 (Age 4)", "K5 (Age 5)", "Grade 1", "Grade 2", "Grade 3", "Grade 4", "Grade 5", "Grade 6", "Grade 7", "Grade 8", "Grade 9", "Grade 10", "Grade 11", "Grade 12"]

for grade in grades:
    db_file = f"database_{grade}.json"
    if os.path.exists(db_file):
        with open(db_file, "r", encoding="utf-8") as f:
            db = json.load(f)
        
        total_videos = len(db)
        has_sub = sum(1 for item in db if item.get("has_subtitle") or str(item.get("link", "")).endswith(".vtt"))
        missing_sub = total_videos - has_sub
        
        print(f"[{grade}] Total: {total_videos} | Has Sub: {has_sub} | Missing: {missing_sub} | Progress: {has_sub/total_videos*100 if total_videos > 0 else 0:.1f}%")
