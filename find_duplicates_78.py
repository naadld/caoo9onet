import subprocess
from collections import defaultdict

grades = ["Grade 7", "Grade 8"]
REMOTE_BASE = "vpsg24gb.aleron,root_folder_id=11fQ8VYTmwRX9fMJFXeTrTTeZGDqki6dh:"

for grade in grades:
    print(f"Scanning {grade} for duplicate Days...")
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
        print(f"  [!] Found duplicate days in {grade}:")
        for name, count in duplicates.items():
            print(f"      - '{name}': {count} folders")
            
            # Check inside the duplicate day for duplicated subjects
            cmd2 = ["rclone", "lsf", "--format", "p", "--dirs-only", f"{REMOTE_BASE}{grade}/{name}/"]
            res2 = subprocess.run(cmd2, capture_output=True, text=True)
            if res2.returncode == 0:
                sub_counts = defaultdict(int)
                for sl in res2.stdout.splitlines():
                    sname = sl.strip().rstrip('/')
                    if sname:
                        sub_counts[sname] += 1
                sub_dups = {k: v for k, v in sub_counts.items() if v > 1}
                if sub_dups:
                    print(f"        [!] Inside '{name}', duplicate subjects found: {sub_dups}")
    else:
        print(f"  No duplicate days found in {grade}.")
        
    # We can also check ALL subjects under ALL days for duplicates, but let's stick to days for now.
    
