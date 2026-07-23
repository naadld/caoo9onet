#!/usr/bin/env python3
"""
O9O.NET Telegram Bot Command Listener (Topic 3953 Enabled)
Supports full suite of manual control commands:
  - /step 1 start           (Default scraper sequence, day small -> big)
  - /step 1 XX              (Scrape all missing videos for Grade XX)
  - /step 1 XX.yyy          (Scrape specific Grade XX, Day yyy - skips existing)
  - /step 1 force XX.yyy    (Force re-download Grade XX, Day yyy - overwrites)
  - /step 3                 (Run Git Publish & Google Doc logger)
  - /step 4                 (Run AI Subtitles & Interactive JSON generator)
  - /step 5 start           (Resume default GDrive copy - skips existing)
  - /step 5 link1-link2     (Copy custom GDrive folder link1/ID1 -> link2/ID2)
  - /step 6                 (Run GDrive folder comparator & report)
  - /help                   (Show interactive command guide)
"""

import os
import sys
import re
import json
import time
import subprocess
import urllib.request
import urllib.parse
from datetime import datetime, timezone, timedelta

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OFFSET_FILE = os.path.join(BASE_DIR, ".telegram_offset")

PRIMARY_BOT_TOKEN = "8525129998:AAG6-Ib_AfqEGc7jwroo58reg5UVYlRZ-3A"
FALLBACK_BOT_TOKEN = "8733078949:AAEX6WGeGasyVHXEYqgadgE8RFovyr64lBg"
DEFAULT_CHAT_ID = "-1003954353565"
DEFAULT_THREAD_ID = 3953

def normalize_grade(val):
    if not val:
        return None
    val = str(val).strip().upper()
    mapping = {
        "01": "Grade 1", "1": "Grade 1", "G1": "Grade 1", "GRADE 1": "Grade 1", "GRADE1": "Grade 1",
        "02": "Grade 2", "2": "Grade 2", "G2": "Grade 2", "GRADE 2": "Grade 2", "GRADE2": "Grade 2",
        "03": "Grade 3", "3": "Grade 3", "G3": "Grade 3", "GRADE 3": "Grade 3", "GRADE3": "Grade 3",
        "04": "Grade 4", "4": "Grade 4", "G4": "Grade 4", "GRADE 4": "Grade 4", "GRADE4": "Grade 4",
        "05": "Grade 5", "5": "Grade 5", "G5": "Grade 5", "GRADE 5": "Grade 5", "GRADE5": "Grade 5",
        "06": "Grade 6", "6": "Grade 6", "G6": "Grade 6", "GRADE 6": "Grade 6", "GRADE6": "Grade 6",
        "07": "Grade 7", "7": "Grade 7", "G7": "Grade 7", "GRADE 7": "Grade 7", "GRADE7": "Grade 7",
        "08": "Grade 8", "8": "Grade 8", "G8": "Grade 8", "GRADE 8": "Grade 8", "GRADE8": "Grade 8",
        "09": "Grade 9", "9": "Grade 9", "G9": "Grade 9", "GRADE 9": "Grade 9", "GRADE9": "Grade 9",
        "10": "Grade 10", "G10": "Grade 10", "GRADE 10": "Grade 10", "GRADE10": "Grade 10",
        "11": "Grade 11", "G11": "Grade 11", "GRADE 11": "Grade 11", "GRADE11": "Grade 11",
        "12": "Grade 12", "G12": "Grade 12", "GRADE 12": "Grade 12", "GRADE12": "Grade 12",
        "K4": "K4", "K4.": "K4",
        "K5": "K5", "K5.": "K5"
    }
    return mapping.get(val, val)

def send_telegram_reply(text, chat_id=DEFAULT_CHAT_ID, thread_id=DEFAULT_THREAD_ID):
    token = os.getenv("TELEGRAM_BOT_TOKEN") or PRIMARY_BOT_TOKEN
    tokens_to_try = [token]
    if token != FALLBACK_BOT_TOKEN:
        tokens_to_try.append(FALLBACK_BOT_TOKEN)

    for tok in tokens_to_try:
        url = f"https://api.telegram.org/bot{tok}/sendMessage"
        payload = {
            "chat_id": chat_id,
            "text": text
        }
        if thread_id:
            payload["message_thread_id"] = thread_id

        data = urllib.parse.urlencode(payload).encode("utf-8")
        try:
            req = urllib.request.Request(url, data=data)
            with urllib.request.urlopen(req, timeout=10) as resp:
                if resp.status == 200:
                    return True
        except Exception as e:
            print(f"⚠️ Reply error ({tok[:10]}...): {e}")
    return False

def get_github_pat():
    pat = os.getenv("GITHUB_PAT")
    if pat:
        return pat
    cred_file = os.path.expanduser("~/.git-credentials")
    if os.path.exists(cred_file):
        try:
            with open(cred_file, "r") as f:
                content = f.read()
                m = re.search(r'https://[^:]+:([^@]+)@github\.com', content)
                if m:
                    return m.group(1).strip()
        except Exception:
            pass
    return ""

def trigger_github_generic_workflow(workflow_file, inputs_dict):
    pat = get_github_pat()
    if not pat:
        return False, "Không tìm thấy GitHub PAT token."

    url = f"https://api.github.com/repos/naadld/caoo9onet/actions/workflows/{workflow_file}/dispatches"
    headers = {
        "Accept": "application/vnd.github+json",
        "Authorization": f"Bearer {pat}",
        "X-GitHub-Api-Version": "2022-11-28",
        "Content-Type": "application/json"
    }

    payload = {
        "ref": "main",
        "inputs": inputs_dict
    }

    data = json.dumps(payload).encode("utf-8")
    try:
        req = urllib.request.Request(url, data=data, headers=headers, method="POST")
        with urllib.request.urlopen(req, timeout=15) as resp:
            if resp.status in (204, 200, 201):
                return True, "Đã gửi lệnh kích hoạt GitHub Actions Cloud thành công!"
            return False, f"GitHub API trả về HTTP {resp.status}"
    except Exception as e:
        return False, f"Lỗi gọi GitHub API: {e}"

def load_offset():
    if os.path.exists(OFFSET_FILE):
        try:
            with open(OFFSET_FILE, "r") as f:
                return int(f.read().strip())
        except Exception:
            pass
    return None

def save_offset(offset):
    try:
        with open(OFFSET_FILE, "w") as f:
            f.write(str(offset))
    except Exception as e:
        print(f"⚠️ Cannot save offset: {e}")

def check_vps_processes():
    try:
        output = subprocess.check_output(["ps", "aux"], text=True)
    except Exception:
        output = ""

    status_dict = {
        "listener": [],
        "step1": [],
        "step3": [],
        "step4": [],
        "step5": [],
        "step6": []
    }

    for line in output.splitlines():
        if "python" in line:
            m = line.split()
            if len(m) > 1:
                pid = m[1]
                if "telegram_bot_listener.py" in line:
                    status_dict["listener"].append(pid)
                elif "step1_direct_stream.py" in line:
                    status_dict["step1"].append(pid)
                elif "step3_git_publish.py" in line:
                    status_dict["step3"].append(pid)
                elif "step4_generate_subtitles.py" in line:
                    status_dict["step4"].append(pid)
                elif "step5_gdrive_copier.py" in line:
                    status_dict["step5"].append(pid)
                elif "step6_compare_folders.py" in line:
                    status_dict["step6"].append(pid)

    return status_dict

def get_github_active_runs():
    pat = get_github_pat()
    if not pat:
        return []

    url = "https://api.github.com/repos/naadld/caoo9onet/actions/runs?status=in_progress"
    headers = {
        "Accept": "application/vnd.github+json",
        "Authorization": f"Bearer {pat}",
        "X-GitHub-Api-Version": "2022-11-28"
    }

    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            active_runs = []
            for run in data.get("workflow_runs", []):
                name = run.get("name")
                run_id = run.get("id")
                html_url = run.get("html_url")
                active_runs.append({"name": name, "id": run_id, "url": html_url})
            return active_runs
    except Exception as e:
        print(f"⚠️ Error fetching GitHub active runs: {e}")
        return []

def process_status(chat_id, thread_id):
    vn_tz = timezone(timedelta(hours=7))
    now_str = datetime.now(vn_tz).strftime("%Y-%m-%d %H:%M:%S")

    # 1. Check VPS Local Processes
    proc_dict = check_vps_processes()
    
    local_status = []
    if proc_dict["listener"]:
        local_status.append(f"🤖 Bot Listener: 🟢 Đang chạy (PID {', '.join(proc_dict['listener'])})")
    else:
        local_status.append("🤖 Bot Listener: 🔴 Đang dừng")

    if proc_dict["step1"]:
        local_status.append(f"🎬 Step 1 Scraper: 🟢 Đang chạy (PID {', '.join(proc_dict['step1'])})")
    else:
        local_status.append("🎬 Step 1 Scraper: ⚪ Nhàn rỗi")

    if proc_dict["step3"]:
        local_status.append(f"📝 Step 3 Git Logger: 🟢 Đang chạy (PID {', '.join(proc_dict['step3'])})")

    if proc_dict["step4"]:
        local_status.append(f"🎙️ Step 4 Subtitles: 🟢 Đang chạy (PID {', '.join(proc_dict['step4'])})")

    if proc_dict["step5"]:
        local_status.append(f"📂 Step 5 Copier: 🟢 Đang chạy (PID {', '.join(proc_dict['step5'])})")
    else:
        local_status.append("📂 Step 5 Copier: ⚪ Nhàn rỗi")

    if proc_dict["step6"]:
        local_status.append(f"📊 Step 6 Comparator: 🟢 Đang chạy (PID {', '.join(proc_dict['step6'])})")
    else:
        local_status.append("📊 Step 6 Comparator: ⚪ Nhàn rỗi")

    # 2. Check GitHub Actions Cloud Active Workflows
    gh_runs = get_github_active_runs()
    gh_status = []
    if gh_runs:
        for r in gh_runs:
            gh_status.append(f"⚡ {r['name']} (Run #{r['id']})")
    else:
        gh_status.append("⚪ Không có tiến trình cloud nào đang chạy")

    status_msg = (
        f"📊 [BÁO CÁO TRẠNG THÁI HỆ THỐNG /status]\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"🖥️ MÁY CHỦ VPS (LOCAL):\n"
        f"  " + "\n  ".join(local_status) + "\n\n"
        f"☁️ GITHUB ACTIONS CLOUD:\n"
        f"  " + "\n  ".join(gh_status) + "\n\n"
        f"⏰ Giờ kiểm tra (GMT+7): {now_str}"
    )
    send_telegram_reply(status_msg, chat_id, thread_id)

def route_command(raw_text, chat_id, thread_id):
    text = raw_text.strip()
    clean = text.lower()

    vn_tz = timezone(timedelta(hours=7))
    now_str = datetime.now(vn_tz).strftime("%Y-%m-%d %H:%M:%S")

    # HELP / START
    if clean in ["/help", "help", "/start"] or clean.startswith("/help@") or clean.startswith("/start@"):
        process_help(chat_id, thread_id)
        return

    # STATUS
    if clean in ["/status", "status"] or clean.startswith("/status@"):
        process_status(chat_id, thread_id)
        return

    # STEP 1 COMMANDS
    if clean.startswith("/step 1") or clean.startswith("/step1") or clean.startswith("step 1"):
        # 1. /step 1 force XX.yyy or /step 1 XX.yyy (specific day)
        m_day = re.search(r'step\s*1\s+(?:(force)\s+)?([a-zA-Z0-9]+)[\._](\d+)', text, re.IGNORECASE)
        if m_day:
            is_force = bool(m_day.group(1))
            raw_grade = m_day.group(2)
            raw_day = m_day.group(3)
            grade = normalize_grade(raw_grade)
            try:
                day = int(raw_day)
                mode_text = "FORCE (Ghi đè file cũ)" if is_force else "THƯỜNG (Bỏ qua bài đã có)"
                ack_msg = (
                    f"📥 [ĐÃ NHẬN LỆNH /step 1 {raw_grade}.{day:03d}]\n"
                    f"━━━━━━━━━━━━━━━━━━━━━━\n"
                    f"📚 Grade: {grade}\n"
                    f"📅 Ngày: Ngày {day:03d}\n"
                    f"⚡ Chế độ: {mode_text}\n"
                    f"⏰ Thời gian: {now_str}\n"
                    f"🚀 Đang kích hoạt tiến trình..."
                )
                send_telegram_reply(ack_msg, chat_id, thread_id)
                success, info = trigger_github_generic_workflow("1_scraper_stream.yml", {
                    "max_days": "1",
                    "grade": str(grade),
                    "day": str(day),
                    "force": "true" if is_force else "false"
                })
                if success:
                    send_telegram_reply(f"✅ [KÍCH HOẠT THÀNH CÔNG]\n{info}\n🔗 Theo dõi tại: https://github.com/naadld/caoo9onet/actions", chat_id, thread_id)
                else:
                    send_telegram_reply(f"⚠️ {info}\n⚡ Chuyển sang chạy dự phòng trên VPS...", chat_id, thread_id)
                    cmd = f"python3 {os.path.join(BASE_DIR, 'scripts/step1_direct_stream.py')} --grade \"{grade}\" --day {day} {'--force' if is_force else ''} --force-local --max-days 1 >> {os.path.join(BASE_DIR, 'stream.log')} 2>&1 &"
                    subprocess.Popen(cmd, shell=True, cwd=BASE_DIR)
                return
            except ValueError:
                pass

        # 2. /step 1 start
        if "start" in clean:
            ack_msg = (
                f"🚀 [ĐÃ NHẬN LỆNH /step 1 start]\n"
                f"━━━━━━━━━━━━━━━━━━━━━━\n"
                f"📚 Tiến trình cào mặc định toàn bộ các Grade\n"
                f"📅 Quét từ ngày nhỏ đến ngày lớn (Day 001 -> Day 170)\n"
                f"⏰ Thời gian: {now_str}\n"
                f"🚀 Đang khởi chạy tiến trình..."
            )
            send_telegram_reply(ack_msg, chat_id, thread_id)
            success, info = trigger_github_generic_workflow("1_scraper_stream.yml", {
                "max_days": "170"
            })
            if success:
                send_telegram_reply(f"✅ [KÍCH HOẠT THÀNH CÔNG]\n{info}\n🔗 Theo dõi tại: https://github.com/naadld/caoo9onet/actions", chat_id, thread_id)
            else:
                send_telegram_reply(f"⚠️ {info}\n⚡ Chuyển sang chạy dự phòng trên VPS...", chat_id, thread_id)
                cmd = f"python3 {os.path.join(BASE_DIR, 'scripts/step1_direct_stream.py')} --force-local --max-days 170 >> {os.path.join(BASE_DIR, 'stream.log')} 2>&1 &"
                subprocess.Popen(cmd, shell=True, cwd=BASE_DIR)
            return

        # 3. /step 1 XX (Grade overall)
        m_grade = re.search(r'step\s*1\s+([a-zA-Z0-9]+)', text, re.IGNORECASE)
        if m_grade:
            raw_grade = m_grade.group(1)
            grade = normalize_grade(raw_grade)
            ack_msg = (
                f"🚀 [ĐÃ NHẬN LỆNH /step 1 {raw_grade}]\n"
                f"━━━━━━━━━━━━━━━━━━━━━━\n"
                f"📚 Cào toàn bộ bài học chưa có của {grade}\n"
                f"📅 Quét từ Day 001 đến Day 170 (Bỏ qua bài đã có)\n"
                f"⏰ Thời gian: {now_str}\n"
                f"🚀 Đang khởi chạy..."
            )
            send_telegram_reply(ack_msg, chat_id, thread_id)
            success, info = trigger_github_generic_workflow("1_scraper_stream.yml", {
                "grade": str(grade),
                "max_days": "170"
            })
            if success:
                send_telegram_reply(f"✅ [KÍCH HOẠT THÀNH CÔNG]\n{info}\n🔗 Theo dõi tại: https://github.com/naadld/caoo9onet/actions", chat_id, thread_id)
            else:
                send_telegram_reply(f"⚠️ {info}\n⚡ Chuyển sang chạy dự phòng trên VPS...", chat_id, thread_id)
                cmd = f"python3 {os.path.join(BASE_DIR, 'scripts/step1_direct_stream.py')} --grade \"{grade}\" --force-local --max-days 170 >> {os.path.join(BASE_DIR, 'stream.log')} 2>&1 &"
                subprocess.Popen(cmd, shell=True, cwd=BASE_DIR)
            return

    # STEP 3 COMMAND
    if clean.startswith("/step 3") or clean.startswith("/step3") or clean == "step 3":
        ack_msg = (
            f"🚀 [ĐÃ NHẬN LỆNH /step 3]\n"
            f"━━━━━━━━━━━━━━━━━━━━━━\n"
            f"📝 Khởi chạy Step 3: Git Publish & Ghi Log Google Doc...\n"
            f"⏰ Thời gian: {now_str}"
        )
        send_telegram_reply(ack_msg, chat_id, thread_id)
        cmd = f"python3 {os.path.join(BASE_DIR, 'scripts/step3_git_publish.py')} >> {os.path.join(BASE_DIR, 'step3.log')} 2>&1 &"
        subprocess.Popen(cmd, shell=True, cwd=BASE_DIR)
        send_telegram_reply("✅ [STEP 3] Tiến trình đã được kích hoạt chạy ngầm thành công!", chat_id, thread_id)
        return

    # STEP 4 COMMAND
    if clean.startswith("/step 4") or clean.startswith("/step4") or clean == "step 4":
        ack_msg = (
            f"🚀 [ĐÃ NHẬN LỆNH /step 4]\n"
            f"━━━━━━━━━━━━━━━━━━━━━━\n"
            f"🎙️ Khởi chạy Step 4: Tạo Phụ đề AI Whisper & File JSON tương tác...\n"
            f"⏰ Thời gian: {now_str}"
        )
        send_telegram_reply(ack_msg, chat_id, thread_id)
        success, info = trigger_github_generic_workflow("4_generate_subtitles.yml", {
            "target_folder": "Grade 4"
        })
        if success:
            send_telegram_reply(f"✅ [KÍCH HOẠT THÀNH CÔNG]\n{info}\n🔗 Theo dõi tại: https://github.com/naadld/caoo9onet/actions", chat_id, thread_id)
        else:
            send_telegram_reply(f"⚠️ {info}\n⚡ Chuyển sang chạy dự phòng trên VPS...", chat_id, thread_id)
            cmd = f"python3 {os.path.join(BASE_DIR, 'scripts/step4_generate_subtitles.py')} >> {os.path.join(BASE_DIR, 'step4.log')} 2>&1 &"
            subprocess.Popen(cmd, shell=True, cwd=BASE_DIR)
        return

    # STEP 5 COMMANDS
    if clean.startswith("/step 5") or clean.startswith("/step5") or clean.startswith("step 5"):
        # 1. Check custom link1-link2 or link1 link2
        m_links = re.search(r'step\s*5\s+([^\s-]+)[\s-]+([^\s]+)', text, re.IGNORECASE)
        if m_links and m_links.group(1).lower() != "start":
            src = m_links.group(1).strip()
            dst = m_links.group(2).strip()
            ack_msg = (
                f"🚀 [ĐÃ NHẬN LỆNH /step 5 CUSTOM COPY]\n"
                f"━━━━━━━━━━━━━━━━━━━━━━\n"
                f"📁 Nguồn: {src}\n"
                f"📂 Đích:  {dst}\n"
                f"⏰ Thời gian: {now_str}\n"
                f"🚀 Đang khởi chạy tiến trình copy GDrive..."
            )
            send_telegram_reply(ack_msg, chat_id, thread_id)
            success, info = trigger_github_generic_workflow("5_gdrive_copier.yml", {
                "src_folder": src,
                "dst_folder": dst
            })
            if success:
                send_telegram_reply(f"✅ [KÍCH HOẠT THÀNH CÔNG]\n{info}\n🔗 Theo dõi tại: https://github.com/naadld/caoo9onet/actions", chat_id, thread_id)
            else:
                send_telegram_reply(f"⚠️ {info}\n⚡ Chuyển sang chạy dự phòng trên VPS...", chat_id, thread_id)
                cmd = f"python3 {os.path.join(BASE_DIR, 'scripts/step5_gdrive_copier.py')} --src \"{src}\" --dst \"{dst}\" >> {os.path.join(BASE_DIR, 'step5.log')} 2>&1 &"
                subprocess.Popen(cmd, shell=True, cwd=BASE_DIR)
            return

        # 2. /step 5 start (or default fallback)
        ack_msg = (
            f"🚀 [ĐÃ NHẬN LỆNH /step 5 start]\n"
            f"━━━━━━━━━━━━━━━━━━━━━━\n"
            f"📂 Tiếp tục Copy thư mục GDrive dở dang (Nguồn -> Đích)\n"
            f"⚡ Chế độ: Bỏ qua các file đã có\n"
            f"⏰ Thời gian: {now_str}\n"
            f"🚀 Đang khởi chạy..."
        )
        send_telegram_reply(ack_msg, chat_id, thread_id)
        success, info = trigger_github_generic_workflow("5_gdrive_copier.yml", {})
        if success:
            send_telegram_reply(f"✅ [KÍCH HOẠT THÀNH CÔNG]\n{info}\n🔗 Theo dõi tại: https://github.com/naadld/caoo9onet/actions", chat_id, thread_id)
        else:
            send_telegram_reply(f"⚠️ {info}\n⚡ Chuyển sang chạy dự phòng trên VPS...", chat_id, thread_id)
            cmd = f"python3 {os.path.join(BASE_DIR, 'scripts/step5_gdrive_copier.py')} >> {os.path.join(BASE_DIR, 'step5.log')} 2>&1 &"
            subprocess.Popen(cmd, shell=True, cwd=BASE_DIR)
        return

    # STEP 6 COMMANDS
    if clean.startswith("/step 6") or clean.startswith("/step6") or clean.startswith("step 6"):
        # Check custom link1-link2 or link1 link2
        m_links = re.search(r'step\s*6\s+([^\s-]+)[\s-]+([^\s]+)', text, re.IGNORECASE)
        if m_links and m_links.group(1).lower() != "start":
            src = m_links.group(1).strip()
            dst = m_links.group(2).strip()
            ack_msg = (
                f"🚀 [ĐÃ NHẬN LỆNH /step 6 CUSTOM COMPARE]\n"
                f"━━━━━━━━━━━━━━━━━━━━━━\n"
                f"📁 Nguồn: {src}\n"
                f"📂 Đích:  {dst}\n"
                f"⏰ Thời gian: {now_str}\n"
                f"📊 Đang khởi chạy tiến trình đối chiếu & so sánh..."
            )
            send_telegram_reply(ack_msg, chat_id, thread_id)
            success, info = trigger_github_generic_workflow("6_folder_comparator.yml", {
                "src_folder": src,
                "dst_folder": dst
            })
            if success:
                send_telegram_reply(f"✅ [KÍCH HOẠT THÀNH CÔNG]\n{info}\n🔗 Theo dõi tại: https://github.com/naadld/caoo9onet/actions", chat_id, thread_id)
            else:
                send_telegram_reply(f"⚠️ {info}\n⚡ Chuyển sang chạy dự phòng trên VPS...", chat_id, thread_id)
                cmd = f"python3 {os.path.join(BASE_DIR, 'scripts/step6_compare_folders.py')} --src \"{src}\" --dst \"{dst}\" >> {os.path.join(BASE_DIR, 'step6.log')} 2>&1 &"
                subprocess.Popen(cmd, shell=True, cwd=BASE_DIR)
            return

        # Default /step 6
        ack_msg = (
            f"🚀 [ĐÃ NHẬN LỆNH /step 6]\n"
            f"━━━━━━━━━━━━━━━━━━━━━━\n"
            f"📊 Khởi chạy Step 6: Báo cáo đối chiếu & so sánh thư mục GDrive...\n"
            f"⏰ Thời gian: {now_str}"
        )
        send_telegram_reply(ack_msg, chat_id, thread_id)
        success, info = trigger_github_generic_workflow("6_folder_comparator.yml", {})
        if success:
            send_telegram_reply(f"✅ [KÍCH HOẠT THÀNH CÔNG]\n{info}\n🔗 Theo dõi tại: https://github.com/naadld/caoo9onet/actions", chat_id, thread_id)
        else:
            send_telegram_reply(f"⚠️ {info}\n⚡ Chuyển sang chạy dự phòng trên VPS...", chat_id, thread_id)
            cmd = f"python3 {os.path.join(BASE_DIR, 'scripts/step6_compare_folders.py')} >> {os.path.join(BASE_DIR, 'step6.log')} 2>&1 &"
            subprocess.Popen(cmd, shell=True, cwd=BASE_DIR)
        return

def process_help(chat_id, thread_id):
    help_msg = (
        f"📖 [BẢNG HƯỚNG DẪN LỆNH BOT TELEGRAM O9O.NET]\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"🎬 STEP 1 - CÀO VIDEO:\n"
        f"▪️ /step 1 start\n"
        f"   👉 Chạy tiến trình cào mặc định (từng Grade từ ngày nhỏ -> lớn)\n"
        f"▪️ /step 1 XX\n"
        f"   👉 Cào bài học chưa có của Grade XX (Ví dụ: /step 1 05)\n"
        f"▪️ /step 1 XX.yyy\n"
        f"   👉 Cào bài học cụ thể (Ví dụ: /step 1 01.010 - Bỏ qua bài đã có)\n"
        f"▪️ /step 1 force XX.yyy\n"
        f"   👉 Cào ép buộc bài cụ thể (Ví dụ: /step 1 force K4.150 - Ghi đè file)\n\n"
        f"📝 STEP 3 - ĐỒNG BỘ GIT & GOOGLE DOC:\n"
        f"▪️ /step 3\n"
        f"   👉 Chạy đồng bộ log & Git commit/push\n\n"
        f"🎙️ STEP 4 - TẠO PHỤ ĐỀ AI WHISPER:\n"
        f"▪️ /step 4\n"
        f"   👉 Khởi chạy tạo phụ đề AI & file JSON tương tác\n\n"
        f"📂 STEP 5 - COPY GDRIVE FOLDER:\n"
        f"▪️ /step 5 start\n"
        f"   👉 Chạy tiếp copy thư mục dở dang (Không tải lại file đã có)\n"
        f"▪️ /step 5 link1-link2 (hoặc /step 5 link1 link2)\n"
        f"   👉 Copy từ link1 (hoặc ID1) sang link2 (hoặc ID2)\n\n"
        f"📊 STEP 6 - SO SÁNH & ĐỐI CHIẾU:\n"
        f"▪️ /step 6\n"
        f"   👉 Báo cáo đối chiếu dữ liệu 2 thư mục GDrive mặc định\n"
        f"▪️ /step 6 link1-link2 (hoặc /step 6 link1 link2)\n"
        f"   👉 So sánh đối chiếu giữa link1 (hoặc ID1) và link2 (hoặc ID2)\n\n"
        f"⚡ KIỂM TRA HỆ THỐNG:\n"
        f"▪️ /status\n"
        f"   👉 Kiểm tra trạng thái các tiến trình đang chạy (VPS & Cloud)\n\n"
        f"ℹ️ Gõ /help bất kỳ lúc nào để hiển thị danh sách này."
    )
    send_telegram_reply(help_msg, chat_id, thread_id)

def poll_updates():
    offset = load_offset()
    token_primary = os.getenv("TELEGRAM_BOT_TOKEN") or PRIMARY_BOT_TOKEN
    tokens_to_poll = [token_primary]
    if token_primary != FALLBACK_BOT_TOKEN:
        tokens_to_poll.append(FALLBACK_BOT_TOKEN)

    for token in tokens_to_poll:
        url = f"https://api.telegram.org/bot{token}/getUpdates?timeout=5"
        if offset:
            url += f"&offset={offset}"

        try:
            req = urllib.request.Request(url)
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                if not data.get("ok"):
                    continue

                for update in data.get("result", []):
                    new_offset = update["update_id"] + 1
                    save_offset(new_offset)
                    offset = new_offset

                    message = update.get("message") or update.get("channel_post") or update.get("edited_message")
                    if not message:
                        continue

                    text = message.get("text", "").strip()
                    chat = message.get("chat", {})
                    chat_id = str(chat.get("id", ""))
                    thread_id = message.get("message_thread_id")

                    # Verify target chat (chat_id -1003954353565)
                    if chat_id == DEFAULT_CHAT_ID or chat_id == str(DEFAULT_CHAT_ID):
                        route_command(text, chat_id, DEFAULT_THREAD_ID)

        except urllib.error.HTTPError:
            pass
        except Exception:
            pass

def main():
    print("🤖 O9O.NET Telegram Bot Listener Daemon Started...")
    while True:
        poll_updates()
        time.sleep(2)

if __name__ == "__main__":
    main()
