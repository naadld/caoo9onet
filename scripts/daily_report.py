#!/usr/bin/env python3
"""
Daily Automation Report Script (07:00 & 17:00 GMT+7)
Generates and sends detailed status & comparison report for Abeka Scraper & AI Subtitles via Telegram.
"""

import os
import sys
import json
import shutil
import subprocess
import urllib.request
import urllib.parse
from datetime import datetime, timezone, timedelta
from concurrent.futures import ThreadPoolExecutor

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SNAPSHOT_FILE = os.path.join(BASE_DIR, "data", "daily_report_snapshot.json")
STATUS_JSON_PATH = os.path.join(BASE_DIR, "Video Processing", "status.json")

REMOTE_BASE = "vpsg24gb.aleron,root_folder_id=11fQ8VYTmwRX9fMJFXeTrTTeZGDqki6dh:"
RCLONE_BIN = shutil.which("rclone") or "rclone"
RCLONE_CONF = os.getenv("RCLONE_CONFIG") or os.path.expanduser("~/.config/rclone/rclone.conf")
if not os.path.exists(RCLONE_CONF) and os.path.exists("/home/vpsg24gb/.config/rclone/rclone.conf"):
    RCLONE_CONF = "/home/vpsg24gb/.config/rclone/rclone.conf"

ALL_GRADES = [
    "K4 (Age 4)", "K5 (Age 5)", "Grade 1", "Grade 2", "Grade 3",
    "Grade 4", "Grade 5", "Grade 6", "Grade 7", "Grade 8",
    "Grade 9", "Grade 10", "Grade 11", "Grade 12"
]

def send_telegram_msg(message):
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = "-1003954353565"
    thread_id = 4455

    if not token and os.path.exists(STATUS_JSON_PATH):
        try:
            with open(STATUS_JSON_PATH, "r", encoding="utf-8") as f:
                st = json.load(f)
                tg = st.get("telegram", {})
                t_token = tg.get("bot_token")
                if t_token and t_token != "TELEGRAM_BOT_TOKEN_ENV":
                    token = t_token
                if tg.get("chat_id"):
                    chat_id = tg.get("chat_id")
                if tg.get("message_thread_id"):
                    thread_id = tg.get("message_thread_id")
        except Exception:
            pass

    if not token:
        print("⚠️ Warning: TELEGRAM_BOT_TOKEN not found. Skipping Telegram send.")
        print("\n--- REPORT PREVIEW ---\n")
        print(message)
        return False

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": message
    }
    if thread_id:
        payload["message_thread_id"] = thread_id

    data = urllib.parse.urlencode(payload).encode("utf-8")
    try:
        req = urllib.request.Request(url, data=data)
        with urllib.request.urlopen(req, timeout=15) as resp:
            if resp.status == 200:
                print("📱 Telegram report sent successfully!")
                return True
    except Exception as e:
        print(f"❌ Error sending Telegram report: {e}")
        return False

def scan_grade_gdrive(folder):
    cmd = [RCLONE_BIN, "--config", RCLONE_CONF, "lsf", "-R", f"{REMOTE_BASE}{folder}"]
    try:
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        lines = res.stdout.splitlines()
        mp4_files = [f for f in lines if f.endswith(".mp4")]
        srt_files = [f for f in lines if f.endswith(".srt")]
        json_files = [f for f in lines if f.endswith(".json")]

        days = set()
        folders = set()
        for f in mp4_files:
            parts = f.split("/")
            if len(parts) >= 1 and "Ngày" in parts[0]:
                days.add(parts[0])
            if len(parts) >= 2:
                folders.add("/".join(parts[:-1]))

        return {
            "folder": folder,
            "mp4_count": len(mp4_files),
            "srt_count": len(srt_files),
            "json_count": len(json_files),
            "days_count": len(days),
            "folders_count": len(folders)
        }
    except Exception as e:
        print(f"Error scanning {folder}: {e}")
        return {
            "folder": folder,
            "mp4_count": 0,
            "srt_count": 0,
            "json_count": 0,
            "days_count": 0,
            "folders_count": 0
        }

def run_daily_report():
    vn_tz = timezone(timedelta(hours=7))
    now = datetime.now(vn_tz)
    now_str = now.strftime("%Y-%m-%d %H:%M:%S")
    hour = now.hour

    shift_title = f"📊 BÁO CÁO ĐỊNH KỲ ({hour:02d}:00)"

    print(f"🔍 Starting Daily Report Generation at {now_str} (GMT+7)...")

    # 1. Scan current state on GDrive
    with ThreadPoolExecutor(max_workers=14) as executor:
        scan_results = list(executor.map(scan_grade_gdrive, ALL_GRADES))

    current_data = {
        "timestamp": now_str,
        "shift": shift_title,
        "grades": {}
    }

    total_mp4 = 0
    total_srt = 0

    for r in scan_results:
        folder = r["folder"]
        current_data["grades"][folder] = {
            "mp4": r["mp4_count"],
            "srt": r["srt_count"],
            "json": r["json_count"],
            "days": r["days_count"],
            "folders": r["folders_count"]
        }
        total_mp4 += r["mp4_count"]
        total_srt += r["srt_count"]

    current_data["total_mp4"] = total_mp4
    current_data["total_srt"] = total_srt

    # 2. Load previous snapshot for diff comparison
    prev_snapshot = None
    if os.path.exists(SNAPSHOT_FILE):
        try:
            with open(SNAPSHOT_FILE, "r", encoding="utf-8") as f:
                prev_snapshot = json.load(f)
        except Exception as e:
            print(f"Error loading snapshot: {e}")

    # 3. Calculate diffs
    diff_text = ""
    if prev_snapshot:
        prev_time = prev_snapshot.get("timestamp", "Trước")
        prev_mp4 = prev_snapshot.get("total_mp4", 0)
        prev_srt = prev_snapshot.get("total_srt", 0)

        delta_mp4 = total_mp4 - prev_mp4
        delta_srt = total_srt - prev_srt

        diff_text += f"\n🔄 **SO SÁNH VỚI BẢN TIN TRƯỚC ({prev_time})**:\n"
        diff_text += f"• Video MP4 mới cào: **+{delta_mp4} file**\n"
        diff_text += f"• Phụ đề SRT mới tạo: **+{delta_srt} file**\n"

        grade_diffs = []
        prev_grades = prev_snapshot.get("grades", {})
        for g in ALL_GRADES:
            c_g = current_data["grades"].get(g, {})
            p_g = prev_grades.get(g, {})
            d_m = c_g.get("mp4", 0) - p_g.get("mp4", 0)
            d_s = c_g.get("srt", 0) - p_g.get("srt", 0)
            if d_m != 0 or d_s != 0:
                change_str = []
                if d_m > 0:
                    change_str.append(f"+{d_m} MP4")
                if d_s > 0:
                    change_str.append(f"+{d_s} Sub")
                grade_diffs.append(f"   ▫️ **{g}**: {', '.join(change_str)}")

        if grade_diffs:
            diff_text += "• Chi tiết biến động từng khối lớp:\n" + "\n".join(grade_diffs) + "\n"
        else:
            diff_text += "• Không có biến động về số lượng file trong ca vừa qua.\n"
    else:
        diff_text += "\nℹ️ *Bản tin đầu tiên, bắt đầu theo dõi biến động từ ca tiếp theo.*\n"

    # 4. Build Report Message
    msg = f"📢 **[ABEKA O9O SYSTEM REPORT]**\n"
    msg += f"⏰ **Thời gian:** {now_str} (GMT+7)\n"
    msg += f"🏷️ **Loại báo cáo:** {shift_title}\n"
    msg += f"{diff_text}\n"

    msg += "━━━━━━━━━━━━━━━━━━━━━━━\n"
    msg += "📹 **1. BÁO CÁO CÀO VIDEO (STEP 1)**\n"
    msg += f"• **Tổng số video MP4:** **{total_mp4:,} file**\n\n"

    for g in ALL_GRADES:
        info = current_data["grades"].get(g, {})
        m_cnt = info.get("mp4", 0)
        d_cnt = info.get("days", 0)
        f_cnt = info.get("folders", 0)
        if m_cnt > 0:
            msg += f"▫️ **{g:11s}**: {d_cnt}/170 Ngày | {f_cnt} Thư mục | **{m_cnt} file MP4**\n"
        else:
            msg += f"▫️ **{g:11s}**: Chưa cào dữ liệu (0 file)\n"

    msg += "\n━━━━━━━━━━━━━━━━━━━━━━━\n"
    msg += "📝 **2. BÁO CÁO TẠO PHỤ ĐỀ AI & JSON (STEP 4)**\n"
    msg += f"• **Tổng số phụ đề đã làm:** **{total_srt:,} / {total_mp4:,} file** ({(total_srt/total_mp4*100) if total_mp4 > 0 else 0:.1f}%)\n\n"

    for g in ALL_GRADES:
        info = current_data["grades"].get(g, {})
        m_cnt = info.get("mp4", 0)
        s_cnt = info.get("srt", 0)
        pct = (s_cnt / m_cnt * 100) if m_cnt > 0 else 0

        if m_cnt == 0:
            status_tag = "⚪ Chưa có video"
        elif s_cnt >= m_cnt and m_cnt > 0:
            status_tag = "✅ **100% HOÀN THÀNH**"
        elif s_cnt > 0:
            status_tag = f"🟡 Đã làm {s_cnt}/{m_cnt} ({pct:.1f}%) ➔ **CẦN LÀM TIẾP**"
        else:
            status_tag = f"🔴 Chưa có sub (0/{m_cnt}) ➔ **CẦN LÀM**"

        msg += f"▫️ **{g:11s}**: {status_tag}\n"

    msg += "\n━━━━━━━━━━━━━━━━━━━━━━━\n"
    msg += "📌 *Báo cáo tự động mỗi 6 tiếng/lần*"

    # 5. Send via Telegram
    send_telegram_msg(msg)

    # 6. Save current snapshot
    os.makedirs(os.path.dirname(SNAPSHOT_FILE), exist_ok=True)
    with open(SNAPSHOT_FILE, "w", encoding="utf-8") as f:
        json.dump(current_data, f, ensure_ascii=False, indent=2)

    print("✅ Daily report processed and snapshot saved successfully!")

if __name__ == "__main__":
    run_daily_report()
