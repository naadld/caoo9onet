#!/usr/bin/env python3
"""
Legacy TS to Native MP4 Converter & Fixer for Google Drive.
Scans uploaded videos on Google Drive, inspects container format via ffprobe,
and remuxes any MPEG-TS files into true native ISO MP4 files using ffmpeg -c copy.
"""

import os
import sys
import shutil
import subprocess
import json

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REMOTE_BASE = "vpsg24gb.aleron,root_folder_id=11fQ8VYTmwRX9fMJFXeTrTTeZGDqki6dh:"
RCLONE_BIN = shutil.which("rclone") or "rclone"
RCLONE_CONF = os.getenv("RCLONE_CONFIG") or "/home/vpsg24gb/.config/rclone/rclone.conf"
FFPROBE_BIN = shutil.which("ffprobe") or "ffprobe"
FFMPEG_BIN = shutil.which("ffmpeg") or "ffmpeg"

def check_is_native_mp4(file_path):
    """Checks if a local file is a true native MP4 container."""
    try:
        cmd = [
            FFPROBE_BIN, "-v", "error",
            "-show_entries", "format=format_name",
            "-of", "default=noprintwrappers=1:nokey=1",
            file_path
        ]
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
        fmt = res.stdout.strip()
        # True MP4 format string in ffprobe is 'mov,mp4,m4a,3gp,3g2,mj2'
        return "mp4" in fmt and "mpegts" not in fmt
    except Exception:
        return False

def remux_to_native_mp4(input_path, output_path):
    """Remuxes video container to native MP4 using ffmpeg stream copy (0% re-encode, ultra fast)."""
    try:
        cmd = [
            FFMPEG_BIN, "-y", "-loglevel", "error",
            "-i", input_path,
            "-c", "copy",
            "-bsf:a", "aac_adtstoasc",
            "-movflags", "+faststart",
            output_path
        ]
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        return res.returncode == 0 and os.path.exists(output_path) and os.path.getsize(output_path) > 100000
    except Exception as e:
        print(f"    ❌ FFmpeg remux error: {e}")
        return False

def main():
    import argparse
    parser = argparse.ArgumentParser(description="Fix legacy TS files to native MP4 format.")
    parser.add_argument("--folder", default="", help="Subfolder to target on Google Drive (e.g. 'Grade 4')")
    args = parser.parse_args()

    print("=" * 60)
    print("🛠️ ABEKA GDRIVE LEGACY TS TO NATIVE MP4 CONVERTER")
    print("=" * 60)

    target_remote = f"{REMOTE_BASE}{args.folder}".rstrip('/') + '/' if args.folder else REMOTE_BASE

    # 1. Fetch file list from Google Drive
    print(f"🔍 Fetching MP4 files from Google Drive remote: {target_remote}...")
    cmd = [RCLONE_BIN, "--config", RCLONE_CONF, "lsf", "-R", "--files-only", target_remote]
    res = subprocess.run(cmd, capture_output=True, text=True)
    all_files_raw = [f.strip() for f in res.stdout.splitlines() if f.strip().endswith(".mp4")]
    
    all_files = [f"{args.folder.rstrip('/')}/{f}" if args.folder else f for f in all_files_raw]

    print(f"📊 Found {len(all_files)} total MP4 files on Google Drive.")

    tmp_dir = os.path.join(BASE_DIR, ".tmp_fix_mp4")
    os.makedirs(tmp_dir, exist_ok=True)

    fixed_count = 0
    already_good_count = 0

    for idx, rel_path in enumerate(all_files, 1):
        print(f"\n[{idx}/{len(all_files)}] Checking container format: {rel_path}")
        
        local_in = os.path.join(tmp_dir, "input.mp4")
        local_out = os.path.join(tmp_dir, "output_native.mp4")
        
        if os.path.exists(local_in):
            os.remove(local_in)
        if os.path.exists(local_out):
            os.remove(local_out)

        # Download sample chunk / header to check
        dl_cmd = [
            RCLONE_BIN, "--config", RCLONE_CONF, "copyto",
            f"{REMOTE_BASE}{rel_path}", local_in
        ]
        
        try:
            p = subprocess.run(dl_cmd, capture_output=True, text=True, timeout=300)
            if p.returncode != 0 or not os.path.exists(local_in):
                print("    ⚠️ Failed to fetch file from Drive. Skipping.")
                continue

            if check_is_native_mp4(local_in):
                print("    ✅ Already a true native MP4 container. Skipping.")
                already_good_count += 1
                os.remove(local_in)
                continue

            print("    ⚠️ Detected legacy MPEG-TS container! Remuxing to native MP4 with FFmpeg...")
            if remux_to_native_mp4(local_in, local_out):
                orig_size = os.path.getsize(local_in)
                new_size = os.path.getsize(local_out)
                print(f"    🎉 Remuxed successfully ({orig_size / 1024 / 1024:.1f} MB -> {new_size / 1024 / 1024:.1f} MB).")
                print("    📤 Uploading true native MP4 back to Google Drive...")

                up_cmd = [
                    RCLONE_BIN, "--config", RCLONE_CONF, "copyto",
                    local_out, f"{REMOTE_BASE}{rel_path}"
                ]
                subprocess.run(up_cmd, check=True)
                print("    ✅ Successfully updated file on Google Drive!")
                fixed_count += 1
            else:
                print("    ❌ Remux failed.")

        except Exception as e:
            print(f"    ❌ Error processing {rel_path}: {e}")
        finally:
            if os.path.exists(local_in):
                try:
                    os.remove(local_in)
                except Exception:
                    pass
            if os.path.exists(local_out):
                try:
                    os.remove(local_out)
                except Exception:
                    pass

    shutil.rmtree(tmp_dir, ignore_errors=True)
    print("\n" + "=" * 60)
    print(f"🎉 COMPLETED! Fixed: {fixed_count} files | Already native MP4: {already_good_count} files.")
    print("=" * 60)

if __name__ == "__main__":
    main()
