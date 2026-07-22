#!/usr/bin/env python3
"""
Garbage & Advanced Duplicate Cleanup Agent for O9O.NET Pipeline.
Scheduled to run daily at 05:00 AM.
Rules:
1. Scans Google Drive for duplicate files (including copy suffixes like ' (1)', ' (2)', etc.).
2. Groups duplicate files by canonical filename.
3. Keeps ONLY the single file with the LARGEST size, deleting all other duplicate copies.
4. Strips any ' (x)' copy suffix from the surviving largest file so it returns to the clean default filename.
5. Deletes incomplete/junk files (.part, .ytdl, .tmp, 0-byte MP4s) locally and on GDrive.
"""

import os
import re
import glob
import subprocess
from collections import defaultdict

BASE_DIR = "/media/vpsg24gb/DATA1/o9o"
TEMP_DIRS = [
    os.path.join(BASE_DIR, "Video Processing"),
    "/tmp"
]
GDrive_REMOTE = "vpsg24gb.aleron,root_folder_id=11fQ8VYTmwRX9fMJFXeTrTTeZGDqki6dh:"
RCLONE_BIN = "/home/vpsg24gb/bin/rclone"
RCLONE_CONF = "/home/vpsg24gb/.config/rclone/rclone.conf"

def strip_copy_suffix(filename):
    name, ext = os.path.splitext(filename)
    clean_name = re.sub(r'\s*\(\d+\)$', '', name).strip()
    return f"{clean_name}{ext}"

def cleanup_local_garbage():
    print("🧹 [05:00 AM AGENT] Cleaning local temp files...")
    cleaned_count = 0
    freed_bytes = 0

    for temp_dir in TEMP_DIRS:
        if not os.path.exists(temp_dir):
            continue

        patterns = ["*.part*", "*.ytdl*", "*.tmp*"]
        for pattern in patterns:
            for filepath in glob.glob(os.path.join(temp_dir, "**", pattern), recursive=True):
                try:
                    size = os.path.getsize(filepath)
                    os.remove(filepath)
                    cleaned_count += 1
                    freed_bytes += size
                    print(f"  🗑️ Removed local junk: {filepath} ({size / (1024*1024):.2f} MB)")
                except Exception as e:
                    print(f"  ⚠️ Failed to remove {filepath}: {e}")

        for filepath in glob.glob(os.path.join(temp_dir, "**", "*.mp4"), recursive=True):
            try:
                if os.path.getsize(filepath) == 0:
                    os.remove(filepath)
                    cleaned_count += 1
                    print(f"  🗑️ Removed 0-byte MP4: {filepath}")
            except Exception as e:
                pass

    print(f"✅ Local cleanup complete: removed {cleaned_count} files ({freed_bytes / (1024*1024):.2f} MB freed).")

def cleanup_gdrive_duplicates_and_junk():
    print("\n🧹 [05:00 AM AGENT] Scanning Google Drive for duplicates & junk files...")
    
    try:
        res = subprocess.run(
            [RCLONE_BIN, "--config", RCLONE_CONF, "lsf", "-R", "--include", "*.part*", "--include", "*.ytdl*", GDrive_REMOTE],
            capture_output=True, text=True
        )
        junk_files = res.stdout.splitlines()
        if junk_files:
            print(f"  Found {len(junk_files)} junk files (.part/.ytdl) on GDrive. Deleting...")
            subprocess.run(
                [RCLONE_BIN, "--config", RCLONE_CONF, "delete", "--include", "*.part*", "--include", "*.ytdl*", GDrive_REMOTE],
                check=True
            )
            print(f"  🗑️ Purged {len(junk_files)} junk files from Google Drive.")
        else:
            print("  ✨ Google Drive has zero junk files.")
    except Exception as e:
        print(f"  ⚠️ GDrive junk removal notice: {e}")

    print("\n🔍 Scanning for duplicate video files (matching name & copy suffixes ' (1)', ' (2)', etc.)...")
    try:
        res = subprocess.run(
            [RCLONE_BIN, "--config", RCLONE_CONF, "lsf", "--format", "sp", "-R", "--include", "*.mp4", GDrive_REMOTE],
            capture_output=True, text=True, check=True
        )
        lines = res.stdout.splitlines()
    except Exception as e:
        print(f"  ❌ Failed to scan GDrive for duplicates: {e}")
        return

    groups = defaultdict(list)
    for line in lines:
        if not line or ";" not in line:
            continue
        size_str, rel_path = line.split(";", 1)
        try:
            size = int(size_str)
        except ValueError:
            size = 0

        folder_path, filename = os.path.split(rel_path)
        canonical_filename = strip_copy_suffix(filename)

        key = (folder_path.lower(), canonical_filename.lower())
        groups[key].append({
            "rel_path": rel_path,
            "filename": filename,
            "canonical_filename": canonical_filename,
            "folder_path": folder_path,
            "size": size
        })

    duplicate_groups_found = 0
    resolved_count = 0

    for (folder_lower, canonical_lower), file_list in groups.items():
        has_copy_suffix = any(f["filename"] != f["canonical_filename"] for f in file_list)
        if len(file_list) > 1 or has_copy_suffix:
            duplicate_groups_found += 1
            file_list.sort(key=lambda x: x["size"], reverse=True)

            survivor = file_list[0]
            to_delete = file_list[1:]

            print(f"\n⚡ Resolving group: Folder '{survivor['folder_path']}' -> Base '{survivor['canonical_filename']}'")
            print(f"  🏆 Keeping LARGEST file: {survivor['filename']} ({survivor['size'] / (1024*1024):.2f} MB)")

            for item in to_delete:
                print(f"  🗑️ Deleting smaller duplicate: {item['rel_path']} ({item['size'] / (1024*1024):.2f} MB)")
                subprocess.run(
                    [RCLONE_BIN, "--config", RCLONE_CONF, "deletefile", f"{GDrive_REMOTE}{item['rel_path']}"],
                    capture_output=True
                )
                resolved_count += 1

            if survivor["filename"] != survivor["canonical_filename"]:
                clean_rel_path = os.path.join(survivor["folder_path"], survivor["canonical_filename"])
                print(f"  ✏️ Renaming survivor: '{survivor['filename']}' -> '{survivor['canonical_filename']}'")
                subprocess.run(
                    [RCLONE_BIN, "--config", RCLONE_CONF, "moveto", f"{GDrive_REMOTE}{survivor['rel_path']}", f"{GDrive_REMOTE}{clean_rel_path}"],
                    capture_output=True
                )

    print(f"\n🎉 Duplicate cleanup complete! Processed {duplicate_groups_found} duplicate groups, removed {resolved_count} duplicate files.")

def main():
    print("=" * 60)
    print("🧹 O9O.NET DAILY 05:00 AM GARBAGE & DUPLICATE CLEANUP AGENT")
    print("=" * 60)
    cleanup_local_garbage()
    cleanup_gdrive_duplicates_and_junk()

if __name__ == "__main__":
    main()
