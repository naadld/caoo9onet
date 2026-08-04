import subprocess
import os

grades = ["K4 (Age 4)", "K5 (Age 5)", "Grade 1", "Grade 2", "Grade 3", "Grade 4", "Grade 5", "Grade 6"]
REMOTE_BASE = "vpsg24gb.aleron,root_folder_id=11fQ8VYTmwRX9fMJFXeTrTTeZGDqki6dh:"

print("Bắt đầu quá trình dọn dẹp và gộp thư mục trên Google Drive...")

for grade in grades:
    print(f"\n[{grade}] Đang xử lý dedupe...")
    cmd = [
        "rclone", "dedupe", "largest",
        "--dedupe-mode", "largest",
        "--tpslimit", "4",
        "--tpslimit-burst", "4",
        f"{REMOTE_BASE}{grade}",
        "-v"
    ]
    
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode == 0:
        print(f"[{grade}] Hoàn tất dedupe!")
        for line in result.stderr.splitlines():
            if "Deleted" in line or "renamed" in line or "merge duplicate directories" in line or "Skipped" in line:
                print("  ->", line)
    else:
        print(f"[{grade}] Lỗi khi chạy dedupe: {result.stderr}")

print("\nĐã hoàn tất dọn dẹp trên Google Drive!")
print("Tiến hành cập nhật database cục bộ...")
step2_cmd = ["python3", "scripts/step2_link_database.py"]
subprocess.run(step2_cmd)
print("Database cập nhật xong!")
