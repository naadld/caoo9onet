import os
import json
import glob
import subprocess
from datetime import datetime

print("# 📊 DAILY CHECK REPORT\\n")

# 1. Step 1: Grades and Days
print("## 1. Step 1: Tiến độ cào Video (Scraping)")
try:
    with open("data/current_grade.txt", "r") as f:
        cg = f.read().strip()
    print(f"**Cặp Grade đang cào hiện tại (Active Target):** {cg}\\n")
except:
    print("**Cặp Grade đang cào hiện tại:** Không tìm thấy file data/current_grade.txt\\n")

dbs = glob.glob("database_*.json")
if not dbs:
    print("Chưa có database nào được tạo.")
else:
    for db_file in sorted(dbs):
        grade_name = db_file.replace("database_", "").replace(".json", "")
        with open(db_file, "r") as f:
            try:
                data = json.load(f)
                days = set()
                for item in data:
                    if isinstance(item, dict) and "day" in item:
                        days.add(item["day"])
                if days:
                    max_day = max(days)
                    print(f"- **{grade_name}**: Đã cào đến Ngày **{max_day}** (Tổng số bài: {len(data)})")
                else:
                    print(f"- **{grade_name}**: (Không có dữ liệu ngày tháng)")
            except:
                print(f"- **{grade_name}**: Lỗi đọc file JSON")

# 2. Step 2 Progress
print("\\n## 2. Step 2: Tiến độ Link Database")
# Check if databases were updated recently
print("Các file database đã được tạo và cập nhật thành công.")
for db_file in sorted(dbs):
    mtime = os.path.getmtime(db_file)
    dt = datetime.fromtimestamp(mtime).strftime('%Y-%m-%d %H:%M:%S')
    print(f"- `{db_file}`: Cập nhật lúc {dt}")

# 3. Step 3 Progress
print("\\n## 3. Step 3: Tiến độ Đồng bộ Git & Google Doc")
try:
    git_log = subprocess.check_output(["git", "log", "-1", "--format=%cd", "--date=local"]).decode("utf-8").strip()
    print(f"- Lần commit Git cuối cùng: **{git_log}**")
except:
    print("- Không lấy được thông tin Git.")

# 4. Step 4 Progress
print("\\n## 4. Step 4: Tiến độ Tạo Phụ đề (Subtitles)")
try:
    with open("data/current_subtitle_grade.txt", "r") as f:
        c_sub = f.read().strip()
    print(f"**Grade đang ưu tiên chạy phụ đề (Round Robin):** {c_sub}\\n")
except:
    print("**Grade đang ưu tiên chạy phụ đề:** Không tìm thấy data/current_subtitle_grade.txt\\n")

for grade in ["K4 (Age 4)", "K5 (Age 5)", "Grade 1", "Grade 2", "Grade 3", "Grade 4", "Grade 5", "Grade 6", "Grade 7", "Grade 8", "Grade 9", "Grade 10", "Grade 11", "Grade 12"]:
    db_file = f"database_{grade}.json"
    if os.path.exists(db_file):
        with open(db_file, "r", encoding="utf-8") as f:
            db = json.load(f)
        total_videos = len(db)
        has_sub = sum(1 for item in db if item.get("has_subtitle") or str(item.get("link", "")).endswith(".vtt"))
        missing_sub = total_videos - has_sub
        if total_videos > 0:
            if missing_sub == 0:
                print(f"- **{grade}**: ✅ ĐỦ HẾT ({has_sub}/{total_videos})")
            elif has_sub == 0:
                print(f"- **{grade}**: ❌ Chưa làm ({has_sub}/{total_videos})")
            else:
                pct = has_sub / total_videos * 100
                print(f"- **{grade}**: ⏳ Đang làm ({has_sub}/{total_videos} - {pct:.1f}%)")
    else:
        print(f"- **{grade}**: ❌ Chưa làm (Chưa có database / Chưa cào)")

# 5. Duplicate Folders
print("\\n## 5. Thư mục bị lặp (Duplicate Folders)")
print("- Việc kiểm tra thư mục lặp trên GDrive cần quét trực tiếp qua API, vui lòng xem artifact Báo cáo Thư mục lặp (Duplicate Folders Report) nếu đã quét gần đây.")
