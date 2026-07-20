#!/usr/bin/env python3
"""
Abeka Video Stream to Google Drive Downloader.
Downloads high-quality HLS streams (.m3u8) as MP4 files using FFmpeg,
then uploads them directly to Google Drive using rclone, deleting the local file after upload.
"""

import os
import re
import json
import urllib.request
import subprocess
import argparse
import time

BASE_URL = "https://www.o9o.net"
DATA_DIR = "/media/vpsg24gb/DATA1/o9o/data"
DEFAULT_REMOTE = "vpsg24gb.aleron,root_folder_id=1E_hq6-w6OacdDTlTCvpCC-JKPJoQdz1x:"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120",
    "Referer": "https://www.o9o.net/"
}

def make_safe_filename(name):
    # Keep only alphanumeric, spaces, hyphens, and underscores
    safe = re.sub(r'[^a-zA-Z0-9\s\-_]', '', name)
    return safe.strip()

def get_highest_quality_variant(master_url):
    req = urllib.request.Request(master_url, headers=HEADERS)
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            content = r.read().decode("utf-8", errors="ignore")
    except Exception as e:
        print(f"    Error reading master playlist {master_url}: {e}")
        return None
        
    # Find all variant m3u8 files
    variants = re.findall(r'^[^#\s].*?\.m3u8', content, re.MULTILINE)
    if not variants:
        return master_url # Fallback to master if no variants found
        
    # Usually the variants are listed in order of quality (lowest to highest).
    # We will pick the last one which represents the highest resolution (e.g. 720p).
    highest = variants[-1]
    base_dir = os.path.dirname(master_url)
    return f"{base_dir}/{highest}"

def download_and_upload(grade, lesson_code, video_title, m3u8_url, remote):
    local_mp4 = f"/media/vpsg24gb/DATA1/o9o/Video Processing/tmt/{safe_title}.mp4"
    os.makedirs(os.path.dirname(local_mp4), exist_ok=True)
    gdrive_path = f"{remote}{grade}/{lesson_code}/"
    
    # 1. If it's a relative path on o9o.net, resolve it and find the highest quality
    resolved_url = m3u8_url
    if m3u8_url.startswith("/streaming-media/"):
        master_url = f"{BASE_URL}{m3u8_url}"
        print(f"  🔍 Resolving highest quality variant for {safe_title}...")
        highest_url = get_highest_quality_variant(master_url)
        if highest_url:
            resolved_url = highest_url
            
    print(f"  📥 Downloading stream: {resolved_url}")
    print(f"     Save to local: {local_mp4}")
    
    # ffmpeg command
    ffmpeg_cmd = [
        "ffmpeg", "-y",
        "-headers", f"Referer: {BASE_URL}/",
        "-i", resolved_url,
        "-c", "copy",
        local_mp4
    ]
    
    start_time = time.time()
    try:
        # Run ffmpeg and hide output unless it fails
        subprocess.run(ffmpeg_cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        duration = time.time() - start_time
        file_size = os.path.getsize(local_mp4) / (1024 * 1024)
        print(f"  ✅ Download complete in {duration:.1f}s ({file_size:.2f} MB)")
    except Exception as e:
        print(f"  ❌ FFmpeg download failed: {e}")
        if os.path.exists(local_mp4):
            os.remove(local_mp4)
        return False

    # 2. Upload to Google Drive via rclone
    print(f"  📤 Uploading to Google Drive: {gdrive_path}")
    rclone_cmd = [
        "rclone", "move", local_mp4, gdrive_path,
        "--stats", "1s", "--stats-one-line"
    ]
    
    try:
        subprocess.run(rclone_cmd, check=True)
        print(f"  🎉 Successfully moved to GDrive!")
        return True
    except Exception as e:
        print(f"  ❌ Rclone upload failed: {e}")
        if os.path.exists(local_mp4):
            os.remove(local_mp4)
        return False

def process_grade(grade, start_lesson, end_lesson, remote):
    grade_dir = os.path.join(DATA_DIR, grade)
    if not os.path.isdir(grade_dir):
        print(f"❌ Grade directory not found: {grade_dir}")
        return

    print(f"\n📂 Processing {grade.upper()} (Lessons {start_lesson} to {end_lesson})...")
    files = sorted([f for f in os.listdir(grade_dir) if f.endswith(".json")])
    
    for f in files:
        # Check lesson number range
        # Filename is like 2023-k5-002.json or 2023-01-001.json
        lesson_code = f[:-5] # strip .json
        parts = lesson_code.split("-")
        try:
            lesson_num = int(parts[-1])
        except:
            continue
            
        if not (start_lesson <= lesson_num <= end_lesson):
            continue

        json_path = os.path.join(grade_dir, f)
        with open(json_path, "r", encoding="utf-8") as file_in:
            try:
                playlist = json.load(file_in)
            except Exception as e:
                print(f"  Error loading JSON {f}: {e}")
                continue

        print(f"\n📖 Lesson: {lesson_code} ({len(playlist)} videos)")
        
        for idx, item in enumerate(playlist):
            title = item.get("title", f"Video {idx}")
            # If the json has already been rewritten to point to a local file,
            # we need to find the original o9o.net URL.
            # The original URL can be reconstructed or we can skip/look up.
            # Let's see: we want to download the original HLS file.
            # If it starts with '../data/', we can reconstruct the original path!
            # Example: '../data/k5/2023-k5-002/0_master.m3u8'
            # The original was '/streaming-media/2023/k5/K5PH002D/K5PH002D.m3u8'
            # Since the original URL might not be in the rewritten JSON,
            # let's download HLS streams from the live site directly or from cache.
            # Wait, can we fetch the live page to get the playlist data if it is rewritten?
            # Yes! We can just fetch the original o9o.net page to get the true original URLs!
            # That is 100% reliable and doesn't depend on whether the JSON was rewritten or not!
            
            # Let's get the original o9o playlist data by fetching the live page:
            original_url = f"{BASE_URL}/{grade}/?lesson={lesson_code}"
            req = urllib.request.Request(original_url, headers=HEADERS)
            try:
                with urllib.request.urlopen(req, timeout=15) as resp:
                    html = resp.read().decode("utf-8")
                m = re.search(r'const playlistData = (\[.*?\]);', html, re.DOTALL)
                if m:
                    live_playlist = json.loads(m.group(1))
                    original_file_url = live_playlist[idx].get("file", "")
                else:
                    original_file_url = item.get("file", "")
            except:
                original_file_url = item.get("file", "")

            # If it's still local or invalid, skip
            if not original_file_url or original_file_url.startswith(".."):
                print(f"  ⚠️ Could not resolve original URL for: {title}")
                continue

            print(f"  🎬 [{idx+1}/{len(playlist)}] {title}")
            download_and_upload(grade, lesson_code, title, original_file_url, remote)

def main():
    parser = argparse.ArgumentParser(description="Download Abeka streams directly to Google Drive.")
    parser.add_argument("--grade", required=True, help="Grade slug, e.g. k5, k4, g1, g2")
    parser.add_argument("--start", type=int, default=1, help="Start lesson number (default: 1)")
    parser.add_argument("--end", type=int, default=170, help="End lesson number (default: 170)")
    parser.add_argument("--remote", default=DEFAULT_REMOTE, help=f"rclone remote name (default: {DEFAULT_REMOTE})")
    
    args = parser.parse_args()
    process_grade(args.grade, args.start, args.end, args.remote)

if __name__ == "__main__":
    main()
