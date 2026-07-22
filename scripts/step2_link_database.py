#!/usr/bin/env python3
"""
Step 2: Link Google Drive File IDs & Regenerate HTML Player.
Scans Google Drive for uploaded MP4 files, maps GDrive file IDs to database & playlists,
and regenerates index_songsong.html with playable direct download links.
"""

import os
import re
import json
import glob
import subprocess
import shutil

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")
REMOTE_PATH = "vpsg24gb.aleron,root_folder_id=11fQ8VYTmwRX9fMJFXeTrTTeZGDqki6dh:"

RCLONE_BIN = shutil.which("rclone") or "rclone"

RCLONE_CONF = os.getenv("RCLONE_CONFIG") or os.path.expanduser("~/.config/rclone/rclone.conf")
if not os.path.exists(RCLONE_CONF) and os.path.exists("/home/vpsg24gb/.config/rclone/rclone.conf"):
    RCLONE_CONF = "/home/vpsg24gb/.config/rclone/rclone.conf"

def normalize_path(p):
    return p.replace("\\", "/").strip().lower()

def load_all_databases():
    db_files = glob.glob(os.path.join(BASE_DIR, "database_*.json"))
    all_db = []
    for db_file in db_files:
        if "backup" in db_file.lower():
            continue
        try:
            with open(db_file, 'r', encoding='utf-8') as f:
                all_db.extend(json.load(f))
        except Exception:
            pass
    return all_db

def generate_index_html(gdrive_map, current_status=""):
    html_output = os.path.join(BASE_DIR, "index_songsong.html")
    db = load_all_databases()

    html_content = ["<html><head><meta charset='utf-8'><title>Abeka Videos (Song Song)</title>"]
    html_content.append('''
    <style>
        body { font-family: sans-serif; background: #1e1e2e; color: #cdd6f4; margin: 0; padding: 20px; }
        h2 { color: #f5c2e7; }
        table { width: 100%; border-collapse: collapse; margin-top: 10px; background: #313244; }
        table, th, td { border: 1px solid #45475a; padding: 8px; }
        th { background-color: #45475a; color: #f5c2e7; }
        tr:hover { background-color: #585b70; }
        .tab { display: flex; flex-wrap: wrap; background-color: #11111b; padding: 5px; border-radius: 8px 8px 0 0; }
        .tab button { background: transparent; border: none; color: #cdd6f4; cursor: pointer; padding: 10px 16px; font-size: 14px; font-weight: bold; border-radius: 4px; }
        .tab button:hover { background-color: #313244; }
        .tab button.active { background-color: #cba6f7; color: #11111b; }

        .subtab { display: flex; flex-wrap: wrap; background-color: #313244; padding: 5px; }
        .subtab button { background: transparent; border: none; color: #cdd6f4; cursor: pointer; padding: 6px 10px; font-size: 13px; }
        .subtab button:hover { background-color: #45475a; }
        .subtab button.active { background-color: #a6e3a1; color: #11111b; font-weight: bold; }

        .tabcontent { display: none; background: #1e1e2e; border: 1px solid #45475a; padding: 15px; }
        .subtabcontent { display: none; }
    </style>
    <script>
        function openGrade(evt, gradeName) {
            var i, tabcontent, tablinks;
            tabcontent = document.getElementsByClassName("tabcontent");
            for (i = 0; i < tabcontent.length; i++) { tabcontent[i].style.display = "none"; }
            tablinks = document.getElementsByClassName("tablinks");
            for (i = 0; i < tablinks.length; i++) { tablinks[i].className = tablinks[i].className.replace(" active", ""); }
            document.getElementById(gradeName).style.display = "block";
            evt.currentTarget.className += " active";
        }
        function openDay(evt, dayName) {
            var i, subtabcontent, subtablinks;
            var parent = evt.currentTarget.closest('.tabcontent');
            subtabcontent = parent.getElementsByClassName("subtabcontent");
            for (i = 0; i < subtabcontent.length; i++) { subtabcontent[i].style.display = "none"; }
            subtablinks = parent.getElementsByClassName("subtablinks");
            for (i = 0; i < subtablinks.length; i++) { subtablinks[i].className = subtablinks[i].className.replace(" active", ""); }
            document.getElementById(dayName).style.display = "block";
            evt.currentTarget.className += " active";
        }
        function playVideo(videoSrc, videoTitle) {
            var videoPlayer = document.getElementById('videoPlayer');
            videoPlayer.src = videoSrc;
            videoPlayer.play();
            document.getElementById('nowPlaying').innerText = "Đang phát: " + videoTitle;
        }
    </script>
    </head><body>
    ''')

    html_content.append("<h2>🎬 Abeka Video Player (Direct GDrive Streaming)</h2>")
    if current_status:
        html_content.append(f"<h4 style='color: #89b4fa;'>{current_status}</h4>")

    unique_grades = list(dict.fromkeys(row['grade'] for row in db))
    def grade_sort_key(g):
        num = re.sub(r'\D', '', g)
        return int(num) if num else g
    unique_grades.sort(key=grade_sort_key)

    if unique_grades:
        html_content.append('<div style="display: grid; grid-template-columns: 1fr 1fr; gap: 20px; align-items: start;">')
        html_content.append('<div>')
        html_content.append('<div class="tab">')
        for idx, g in enumerate(unique_grades):
            active_class = " active" if idx == 0 else ""
            safe_id = g.replace(" ", "_").replace("(", "").replace(")", "")
            short_g = g.replace("Grade ", "G")
            html_content.append(f'''<button class="tablinks{active_class}" onclick="openGrade(event, '{safe_id}')">{short_g}</button>''')
        html_content.append('</div>')

        for idx, g in enumerate(unique_grades):
            safe_id = g.replace(" ", "_").replace("(", "").replace(")", "")
            display_style = "block" if idx == 0 else "none"
            html_content.append(f'<div id="{safe_id}" class="tabcontent" style="display:{display_style}">')

            grade_days = list(dict.fromkeys(row['day'] for row in db if row['grade'] == g))
            grade_days.sort()

            if grade_days:
                html_content.append('<div class="subtab">')
                for d_idx, day in enumerate(grade_days):
                    d_active = " active" if d_idx == 0 else ""
                    safe_day_id = f"{safe_id}_{day}"
                    short_d = str(int(day))
                    html_content.append(f'''<button class="subtablinks{d_active}" onclick="openDay(event, '{safe_day_id}')">{short_d}</button>''')
                html_content.append('</div>')

                for d_idx, day in enumerate(grade_days):
                    safe_day_id = f"{safe_id}_{day}"
                    d_display = "block" if d_idx == 0 else "none"
                    html_content.append(f'<div id="{safe_day_id}" class="subtabcontent" style="display:{d_display}">')
                    html_content.append("<table><tr><th>Lớp</th><th>Ngày</th><th>Môn Học</th><th>Trạng Thái</th><th>Xem trực tiếp</th></tr>\n")
                    
                    for row in db:
                        if row['grade'] == g and row['day'] == day:
                            rel_p = normalize_path(row['link'])
                            file_id = gdrive_map.get(rel_p)
                            
                            safe_subj = row['subject'].replace("'", "\\'")
                            if file_id:
                                # Playable direct download link
                                play_link = f"https://drive.google.com/uc?export=download&id={file_id}"
                                status_lbl = "<span style='color: #a6e3a1;'>● Sẵn sàng</span>"
                                play_btn = f"<button style='background-color:#a6e3a1; color:#11111b; border:none; padding:4px 8px; border-radius:4px; cursor:pointer;' onclick=\"playVideo('{play_link}', '{safe_subj}')\">Phát Video</button>"
                            else:
                                play_link = "#"
                                status_lbl = "<span style='color: #f38ba8;'>○ Chưa cào</span>"
                                play_btn = "<span style='color:#585b70;'>Chưa khả dụng</span>"
                                
                            html_content.append(f"<tr><td>{row['grade']}</td><td>{row['day']}</td><td>{row['subject']}</td><td>{status_lbl}</td><td>{play_btn}</td></tr>\n")
                    html_content.append("</table></div>\n")

            html_content.append("</div>\n")

        html_content.append('</div>')
        html_content.append('''
        <div style="position: sticky; top: 20px; display: flex; flex-direction: column; align-items: center; padding: 20px; background: #313244; border-radius: 8px; border: 1px solid #45475a; box-shadow: 0 4px 12px rgba(0,0,0,0.3);">
            <h3 id="nowPlaying" style="margin-top: 0; color: #f5c2e7; text-align: center;">Chọn môn học bên trái để xem video</h3>
            <video id="videoPlayer" controls style="width: 100%; border: 2px solid #cba6f7; background: #000; border-radius: 8px;">
                <source src="" type="video/mp4">
            </video>
        </div>
        </div>
        ''')

    html_content.append("</body></html>")
    with open(html_output, 'w', encoding='utf-8') as f:
        f.write("".join(html_content))
    print(f"✅ Generated index_songsong.html successfully.")

def main():
    print("🚀 Scanning Google Drive remote for file IDs...")
    gdrive_map = {}
    try:
        res = subprocess.run(
            [RCLONE_BIN, "--config", RCLONE_CONF, "lsf", "--format", "ip", "-R", REMOTE_PATH],
            capture_output=True,
            check=True
        )
        lines = res.stdout.decode("utf-8").splitlines()
        print(f"  Indexed {len(lines)} GDrive files.")
        for line in lines:
            if ";" in line:
                file_id, rel_path = line.split(";", 1)
                gdrive_map[normalize_path(rel_path)] = file_id
    except Exception as e:
        print(f"❌ Failed to scan GDrive remote: {e}")
    
    # Generate updated HTML player
    generate_index_html(gdrive_map, "Google Drive Synced Dashboard")

if __name__ == "__main__":
    main()
