#!/usr/bin/env python3
"""
Scan cached JSON playlists in data/ for relative '/streaming-media/' HLS links.
For each link, download the master and variant .m3u8 files from o9o.net
and save them locally in the data/ folder.
Update the JSON playlists to point to the local master .m3u8 file.
"""

import os
import re
import json
import urllib.request
import time

BASE_URL = "https://www.o9o.net"
DATA_DIR = "/media/vpsg24gb/DATA1/o9o/data"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120",
    "Referer": "https://www.o9o.net/"
}

def download_file(url, out_path):
    req = urllib.request.Request(url, headers=HEADERS)
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            content = r.read()
        os.makedirs(os.path.dirname(out_path), exist_ok=True)
        with open(out_path, "wb") as f:
            f.write(content)
        return content.decode("utf-8", errors="ignore")
    except Exception as e:
        print(f"    Error downloading {url}: {e}")
        return None

def process_playlist_file(grade, filename):
    json_path = os.path.join(DATA_DIR, grade, filename)
    lesson_code = filename[:-5] # strip .json

    with open(json_path, "r", encoding="utf-8") as f:
        try:
            items = json.load(f)
        except Exception as e:
            print(f"Error loading JSON {json_path}: {e}")
            return

    modified = False

    for idx, item in enumerate(items):
        file_path = item.get("file", "")
        if file_path.startswith("/streaming-media/"):
            print(f"  🎬 {lesson_code} Video {idx}: {file_path}")
            
            # Paths setup
            base_url_dir = os.path.dirname(file_path) # e.g. /streaming-media/2023/k5/K5PH002D
            master_filename = os.path.basename(file_path) # e.g. K5PH002D.m3u8
            
            lesson_local_dir = os.path.join(DATA_DIR, grade, lesson_code)
            variant_local_dir = os.path.join(lesson_local_dir, str(idx))
            
            # Master output path: data/{grade}/{lesson_code}/{idx}_master.m3u8
            master_local_path = os.path.join(lesson_local_dir, f"{idx}_master.m3u8")
            
            # Download master m3u8
            master_url = f"{BASE_URL}{file_path}"
            master_content = download_file(master_url, master_local_path)
            
            if master_content:
                # Find all variants inside master content
                variants = re.findall(r'^[^#\s].*?\.m3u8', master_content, re.MULTILINE)
                print(f"    Downloaded master. Found {len(variants)} variants.")
                
                for variant in variants:
                    variant_url = f"{BASE_URL}{base_url_dir}/{variant}"
                    variant_local_path = os.path.join(variant_local_dir, variant)
                    download_file(variant_url, variant_local_path)
                
                # Rewrite master content relative paths to point to variant subfolder
                rewritten_lines = []
                for line in master_content.splitlines():
                    line = line.strip()
                    if line and not line.startswith("#"):
                        # Relative variant file is inside the subdirectory named after the video index
                        rewritten_lines.append(f"{idx}/{line}")
                    else:
                        rewritten_lines.append(line)
                
                with open(master_local_path, "w", encoding="utf-8") as f_out:
                    f_out.write("\n".join(rewritten_lines))
                
                # Update item file path in JSON
                # This path is relative to the grade HTML page (e.g. k5/index.html)
                item["file"] = f"../data/{grade}/{lesson_code}/{idx}_master.m3u8"
                modified = True
                
                # Sleep to be nice to o9o server
                time.sleep(0.3)
            else:
                print(f"    Failed to download master {master_url}")

    if modified:
        with open(json_path, "w", encoding="utf-8") as f_out:
            json.dump(items, f_out, ensure_ascii=False, separators=(",", ":"))
        print(f"  💾 Updated JSON {json_path}")

def main():
    print("🚀 Starting download_m3u8s process...")
    prioritized_grades = ["k5", "g1", "g2", "g3", "g4", "g5", "g6", "g7", "g8", "g9", "g10", "g11", "g12", "k4"]
    for grade in prioritized_grades:
        grade_dir = os.path.join(DATA_DIR, grade)
        if not os.path.isdir(grade_dir):
            continue
            
        print(f"\n📂 Scanning grade {grade}...")
        files = sorted([f for f in os.listdir(grade_dir) if f.endswith(".json")])
        for f in files:
            process_playlist_file(grade, f)

if __name__ == "__main__":
    main()
