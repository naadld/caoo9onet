import subprocess
from collections import defaultdict

grades = ["K4 (Age 4)", "K5 (Age 5)", "Grade 1", "Grade 2", "Grade 3", "Grade 4", "Grade 5", "Grade 6"]
REMOTE_BASE = "vpsg24gb.aleron,root_folder_id=11fQ8VYTmwRX9fMJFXeTrTTeZGDqki6dh:"

for grade in grades:
    print(f"Scanning {grade}...")
    cmd = ["rclone", "lsf", "--format", "p", "--dirs-only", f"{REMOTE_BASE}{grade}/"]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"Failed to scan {grade}: {result.stderr}")
        continue
    
    lines = result.stdout.splitlines()
    counts = defaultdict(int)
    for line in lines:
        name = line.strip().rstrip('/')
        if name:
            counts[name] += 1
            
    duplicates = {name: count for name, count in counts.items() if count > 1}
    if duplicates:
        print(f"  [!] Found duplicates in {grade}:")
        for name, count in duplicates.items():
            print(f"      - '{name}': {count} folders")
    else:
        print(f"  No duplicates found in {grade}.")

