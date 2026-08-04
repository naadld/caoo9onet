#!/usr/bin/env python3
import os
import time
import urllib.request
import urllib.parse
import subprocess
import json
import shutil

BASE_DIR = "/media/vpsg24gb/DATA/o9o"
PRIMARY_BOT_TOKEN = "8525129998:AAH9PfSY-lIieT0T0Rbewa7_8LqQHoKEy7k"
FALLBACK_BOT_TOKEN = ""
DEFAULT_CHAT_ID = "-1003954353565"
DEFAULT_THREAD_ID = 4455

def send_telegram_msg(message):
    token = os.getenv("TELEGRAM_BOT_TOKEN") or PRIMARY_BOT_TOKEN
    chat_id = os.getenv("TELEGRAM_CHAT_ID") or DEFAULT_CHAT_ID
    thread_id = os.getenv("TELEGRAM_THREAD_ID") or DEFAULT_THREAD_ID

    tokens_to_try = [token]
    if token != FALLBACK_BOT_TOKEN and FALLBACK_BOT_TOKEN:
        tokens_to_try.append(FALLBACK_BOT_TOKEN)

    sent = False
    for tok in tokens_to_try:
        if not tok: continue
        url = f"https://api.telegram.org/bot{tok}/sendMessage"
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
                if resp.status == 200:
                    print(f"Telegram notification sent via {tok[:5]}...")
                    sent = True
                    break
        except Exception as e:
            pass

def get_status():
    try:
        res = subprocess.run(["ps", "aux"], capture_output=True, text=True)
        
        # Kiểm tra step 1
        is_step1 = "step1_direct_stream.py" in res.stdout
        status_msg = "🟢 Đang chạy" if is_step1 else "🔴 Đang dừng"
        
        # Lấy tiến độ
        prog_file = os.path.join(BASE_DIR, "progress_SongSong.json")
        prog_info = ""
        if os.path.exists(prog_file):
            try:
                with open(prog_file, "r") as f:
                    data = json.load(f)
                    pairs = data.get("active_pairs", [])
                    day = data.get("day_num", 1)
                    prog_info = f"\n📚 Cặp đang làm: {pairs}\n📅 Vị trí ngày: {day}"
            except:
                pass
                
        msg = f"📊 [BÁO CÁO TIẾN ĐỘ HÀNG GIỜ]\nTrạng thái Step 1: {status_msg}{prog_info}"
        
        # Check size of tmp_stream
        tmp_dir = os.path.join(BASE_DIR, ".tmp_stream")
        if os.path.exists(tmp_dir):
            sz = subprocess.run(["du", "-sh", tmp_dir], capture_output=True, text=True)
            if sz.returncode == 0:
                msg += f"\n📁 Dung lượng .tmp_stream: {sz.stdout.split()[0]}"
                
        return msg
    except Exception as e:
        return f"Lỗi lấy báo cáo: {e}"

if __name__ == "__main__":
    print("Khởi động trình báo cáo hàng giờ qua Telegram...")
    # Gửi luôn báo cáo đầu tiên
    send_telegram_msg(get_status())
    while True:
        time.sleep(3600)
        msg = get_status()
        send_telegram_msg(msg)
