#!/usr/bin/env python3
import os
import time
import urllib.request
import urllib.parse
import subprocess
import json
import glob

BASE_DIR = "/media/vpsg24gb/DATA/o9o"
PRIMARY_BOT_TOKEN = "8525129998:AAH9PfSY-lIieT0T0Rbewa7_8LqQHoKEy7k"
FALLBACK_BOT_TOKEN = ""
DEFAULT_CHAT_ID = "-1003954353565"
DEFAULT_THREAD_ID = 4455
STATE_FILE = os.path.join(BASE_DIR, "hourly_state.json")

def send_telegram_msg(message):
    token = PRIMARY_BOT_TOKEN
    chat_id = DEFAULT_CHAT_ID
    thread_id = DEFAULT_THREAD_ID

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
        with urllib.request.urlopen(req, timeout=10) as resp:
            pass
    except Exception as e:
        pass

def get_current_db_items(pairs):
    items = set()
    max_day = 0
    active_grades = set()
    for p in pairs:
        for g in p:
            active_grades.add(g)
            
    for grade in active_grades:
        db_path = os.path.join(BASE_DIR, f"database_{grade}.json")
        if os.path.exists(db_path):
            try:
                with open(db_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    for r in data:
                        items.add(f"{r.get('grade')} | Ngày {r.get('day')} | {r.get('subject')}")
                        d = r.get('day')
                        try:
                            d = int(d)
                            if d > max_day:
                                max_day = d
                        except:
                            pass
            except:
                pass
    return items, max_day

def get_status():
    try:
        # Lấy tiến độ các cặp đang chạy
        prog_file = os.path.join(BASE_DIR, "progress_SongSong.json")
        pairs = []
        if os.path.exists(prog_file):
            try:
                with open(prog_file, "r") as f:
                    data = json.load(f)
                    pairs = data.get("active_pairs", [])
            except:
                pass
                
        # Load state
        old_items = set()
        if os.path.exists(STATE_FILE):
            try:
                with open(STATE_FILE, "r", encoding="utf-8") as f:
                    old_items = set(json.load(f))
            except:
                pass
                
        current_items, actual_day = get_current_db_items(pairs)
        new_items = current_items - old_items
        
        # Save new state
        with open(STATE_FILE, "w", encoding="utf-8") as f:
            json.dump(list(current_items), f, ensure_ascii=False)
            
        # Format new items
        new_items_text = ""
        if new_items:
            # Group by Grade | Day
            grouped = {}
            for item in new_items:
                parts = item.split(" | ")
                if len(parts) == 3:
                    folder = f"{parts[0]} - {parts[1]}"
                    file = parts[2]
                    if folder not in grouped:
                        grouped[folder] = []
                    grouped[folder].append(file)
            
            new_items_text = f"\n\n🆕 TRONG 1 GIỜ QUA ĐÃ CÀO ĐƯỢC {len(new_items)} BÀI:\n"
            # Sort folders for better readability
            for folder in sorted(grouped.keys()):
                files = grouped[folder]
                new_items_text += f"\n📁 {folder} ({len(files)} bài):\n"
                for idx, file in enumerate(files[:10]):
                    new_items_text += f"   + {file}\n"
                if len(files) > 10:
                    new_items_text += f"   + ... và {len(files)-10} bài khác\n"
        else:
            new_items_text = "\n\n⚠️ Trong 1 giờ qua KHÔNG có bài mới nào được cào thêm."

        # Kiểm tra step 1 trên Github hoặc Cloud (Vì đã chặn local)
        prog_info = f"\n📚 Cặp đang làm: {pairs}\n📅 Vị trí ngày thực tế: {actual_day}"
                
        msg = f"📊 [BÁO CÁO TIẾN ĐỘ HÀNG GIỜ]{prog_info}{new_items_text}"
        
        # Check size of tmp_stream
        tmp_dir = os.path.join(BASE_DIR, ".tmp_stream")
        if os.path.exists(tmp_dir):
            sz = subprocess.run(["du", "-sh", tmp_dir], capture_output=True, text=True)
            if sz.returncode == 0:
                msg += f"\n\n💽 Dung lượng .tmp_stream (trên máy chủ): {sz.stdout.split()[0]}"
                
        return msg
    except Exception as e:
        return f"Lỗi lấy báo cáo: {e}"

if __name__ == "__main__":
    print("Khởi động trình báo cáo hàng giờ qua Telegram...")
    # Lưu state đầu tiên để không báo cáo toàn bộ DB là bài mới
    try:
        prog_file = os.path.join(BASE_DIR, "progress_SongSong.json")
        pairs = []
        if os.path.exists(prog_file):
            with open(prog_file, "r") as f:
                pairs = json.load(f).get("active_pairs", [])
        current_items, _ = get_current_db_items(pairs)
        with open(STATE_FILE, "w", encoding="utf-8") as f:
            json.dump(list(current_items), f, ensure_ascii=False)
        send_telegram_msg("🟢 Trình báo cáo tự động đã khởi động. Sẽ gửi báo cáo chi tiết file/folder mới vào mỗi giờ.")
    except Exception as e:
        pass
        
    while True:
        time.sleep(3600)
        try:
            subprocess.run(["git", "pull"], cwd=BASE_DIR, capture_output=True)
        except:
            pass
        msg = get_status()
        send_telegram_msg(msg)
