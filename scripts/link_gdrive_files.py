#!/usr/bin/env python3
"""
Scan the Google Drive folder via rclone to find all uploaded Abeka MP4 videos.
Map the file IDs back to the local JSON playlists.
This allows the website to stream GDrive files directly instead of HLS!
"""

import os
import re
import json
import subprocess

DATA_DIR = "/media/vpsg24gb/DATA1/o9o/data"
REMOTE_PATH = "vpsg24gb.aleron,root_folder_id=1E_hq6-w6OacdDTlTCvpCC-JKPJoQdz1x:"

def normalize_title(title):
    # Normalize title for matching
    safe = re.sub(r'[^a-zA-Z0-9]', '', title)
    return safe.lower()

def main():
    print("🚀 Scanning Google Drive for uploaded videos...")
    
    # Run rclone to list all files recursively with their IDs
    # Format of rclone lsf: "id;path" (e.g. "1NE-epiVM...;k5/2023-k5-002/K5 Phonics.mp4")
    try:
        res = subprocess.run(
            ["rclone", "lsf", "--format", "ip", "-R", REMOTE_PATH],
            capture_output=True,
            check=True
        )
        lines = res.stdout.decode("utf-8").splitlines()
    except Exception as e:
        print(f"❌ Failed to scan GDrive remote: {e}")
        return

    # Map: (grade, lesson_code, normalized_video_title) -> file_id
    gdrive_map = {}
    print(f"  Found {len(lines)} files on Google Drive. Indexing...")
    
    for line in lines:
        if not line or ";" not in line:
            continue
        file_id, rel_path = line.split(";", 1)
        if not rel_path.endswith(".mp4"):
            continue
            
        # Path is like: k5/2023-k5-002/K5 Phonics.mp4
        parts = rel_path.split("/")
        if len(parts) < 3:
            continue
            
        grade = parts[0]          # k5
        lesson_code = parts[1]    # 2023-k5-002
        file_name = parts[2][:-4] # K5 Phonics (strip .mp4)
        
        key = (grade.lower(), lesson_code.lower(), normalize_title(file_name))
        gdrive_map[key] = file_id

    print(f"  Indexed {len(gdrive_map)} valid video files.")

    # Now scan local data/ directory to link them
    modified_count = 0
    
    for grade in os.listdir(DATA_DIR):
        grade_dir = os.path.join(DATA_DIR, grade)
        if not os.path.isdir(grade_dir):
            continue
            
        print(f"  Scanning local data for {grade}...")
        files = [f for f in os.listdir(grade_dir) if f.endswith(".json")]
        
        for f in files:
            json_path = os.path.join(grade_dir, f)
            lesson_code = f[:-5] # strip .json
            
            with open(json_path, "r", encoding="utf-8") as file_in:
                try:
                    playlist = json.load(file_in)
                except Exception as e:
                    print(f"    Error reading JSON {f}: {e}")
                    continue
                    
            modified = False
            for item in playlist:
                title = item.get("title", "")
                current_file = item.get("file", "")
                
                key = (grade.lower(), lesson_code.lower(), normalize_title(title))
                if key in gdrive_map:
                    file_id = gdrive_map[key]
                    new_val = f"gdrive:{file_id}"
                    if current_file != new_val:
                        item["file"] = new_val
                        modified = True
                        print(f"    🔗 Linked: {lesson_code} -> {title} (ID: {file_id})")
                    
            if modified:
                with open(json_path, "w", encoding="utf-8") as file_out:
                    json.dump(playlist, file_out, ensure_ascii=False, separators=(",", ":"))
                modified_count += 1

    print(f"\n🎉 Done! Updated {modified_count} JSON playlist files.")

if __name__ == "__main__":
    main()
