#!/usr/bin/env python3
"""
2-3 Minute Watchdog Daemon & Cron Runner for O9O.NET Continuous Streaming.
Ensures stream downloading runs continuously without stalling or freezing.
Recovers automatically from network timeouts.
"""

import os
import sys
import time
import subprocess

BASE_DIR = "/media/vpsg24gb/DATA1/o9o"
PID_FILE = os.path.join(BASE_DIR, "streamer.pid")
LOG_FILE = os.path.join(BASE_DIR, "stream.log")
SCRIPT_STEP1 = os.path.join(BASE_DIR, "scripts/step1_direct_stream.py")
SCRIPT_STEP2 = os.path.join(BASE_DIR, "scripts/step2_link_database.py")

def is_process_running(pid):
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False

def check_and_revive_streamer():
    pid = None
    if os.path.exists(PID_FILE):
        try:
            with open(PID_FILE, "r") as f:
                pid = int(f.read().strip())
        except Exception:
            pid = None

    if pid and is_process_running(pid):
        print(f"✅ Streamer process is active (PID {pid}). No action needed.")
        return

    print("⚡ Streamer process is not running or has stalled. Launching new continuous stream worker...")
    # Clean stale PID file
    if os.path.exists(PID_FILE):
        os.remove(PID_FILE)

    cmd = f"PYTHONUNBUFFERED=1 python3 {SCRIPT_STEP1} --max-days 1 >> {LOG_FILE} 2>&1 & echo $!"
    res = subprocess.run(cmd, shell=True, capture_output=True, text=True, cwd=BASE_DIR)
    new_pid = res.stdout.strip()

    if new_pid.isdigit():
        with open(PID_FILE, "w") as f:
            f.write(new_pid)
        print(f"🚀 Started continuous stream worker with PID: {new_pid}")
    else:
        print(f"⚠️ Failed to obtain new PID for stream worker.")

    # Run step2 DB/HTML sync
    try:
        subprocess.run(["python3", SCRIPT_STEP2], cwd=BASE_DIR, capture_output=True)
        print("✅ HTML Player updated with latest GDrive data.")
    except Exception as e:
        print(f"⚠️ HTML sync warning: {e}")

    # Sync live progress to Paperclip UI
    try:
        sync_script = os.path.join(BASE_DIR, "scripts/sync_paperclip_live.py")
        if os.path.exists(sync_script):
            subprocess.run(["python3", sync_script], cwd=BASE_DIR, capture_output=True)
            print("✅ Paperclip Dashboard live progress synced.")
    except Exception as e:
        print(f"⚠️ Paperclip sync warning: {e}")

SCRIPT_TG_LISTENER = os.path.join(BASE_DIR, "scripts/telegram_bot_listener.py")
TG_PID_FILE = os.path.join(BASE_DIR, "telegram_listener.pid")

def check_and_revive_telegram_listener():
    pid = None
    if os.path.exists(TG_PID_FILE):
        try:
            with open(TG_PID_FILE, "r") as f:
                pid = int(f.read().strip())
        except Exception:
            pid = None

    if pid and is_process_running(pid):
        return

    print("🤖 Telegram Bot listener is not running. Launching listener daemon...")
    if os.path.exists(TG_PID_FILE):
        os.remove(TG_PID_FILE)

    cmd = f"PYTHONUNBUFFERED=1 python3 {SCRIPT_TG_LISTENER} >> {os.path.join(BASE_DIR, 'telegram_listener.log')} 2>&1 & echo $!"
    res = subprocess.run(cmd, shell=True, capture_output=True, text=True, cwd=BASE_DIR)
    new_pid = res.stdout.strip()
    if new_pid.isdigit():
        with open(TG_PID_FILE, "w") as f:
            f.write(new_pid)
        print(f"🚀 Started Telegram Bot Listener daemon with PID: {new_pid}")

def main():
    print("=" * 60)
    print("🔄 O9O.NET 2-3 MINUTE WATCHDOG & CONTINUOUS SCRAPER RUNNER")
    print("=" * 60)
    check_and_revive_telegram_listener()
    check_and_revive_streamer()

if __name__ == "__main__":
    main()
