#!/usr/bin/env python3
"""
Step 3: Update Progress Status & Git Publisher.
Generates status.json and status.md visual progress badges,
commits changes and pushes to GitHub Pages repository.
"""

import os
import json
import time
import subprocess

BASE_DIR = "/media/vpsg24gb/DATA1/o9o"
STATUS_JSON_PATH = os.path.join(BASE_DIR, "Video Processing/status.json")
STATUS_MD_PATH = os.path.join(BASE_DIR, "Video Processing/status.md")
DATA_DIR = os.path.join(BASE_DIR, "data")

GRADES = ["k4", "k5", "g1", "g2", "g3", "g4", "g5", "g6", "g7", "g8", "g9", "g10", "g11", "g12"]

def load_status():
if os.path.exists(STATUS_JSON_PATH):
try:
with open(STATUS_JSON_PATH, "r", encoding="utf-8") as f:
return json.load(f)
except Exception:
pass

status = {}
for grade in GRADES:
grade_dir = os.path.join(DATA_DIR, grade)
total_lessons = len([f for f in os.listdir(grade_dir) if f.endswith(".json")]) if os.path.isdir(grade_dir) else 170
status[grade] = {
"completed_lessons": [2] if grade == "k5" else [],
"total_lessons": total_lessons or 170
}
return status

def save_status(status):
os.makedirs(os.path.dirname(STATUS_JSON_PATH), exist_ok=True)
with open(STATUS_JSON_PATH, "w", encoding="utf-8") as f:
json.dump(status, f, indent=2, ensure_ascii=False)
generate_status_report(status)

def generate_status_report(status):
total_completed = 0
total_all = 0

table_rows = []
for grade in GRADES:
data = status.get(grade, {"completed_lessons": [], "total_lessons": 170})
comp = len(data["completed_lessons"])
tot = data["total_lessons"]
total_completed += comp
total_all += tot

pct = (comp / tot * 100) if tot > 0 else 0
progress_bar = f"![Progress](https://geps.dev/progress/{int(pct)})"

comp_list_str = ", ".join(map(str, sorted(data["completed_lessons"])))
if len(comp_list_str) > 40:
comp_list_str = comp_list_str[:37] + "..."

table_rows.append(
f"| {grade.upper()} | {comp}/{tot} | {pct:.1f}% | {progress_bar} | {comp_list_str or 'None'} |"
)

overall_pct = (total_completed / total_all * 100) if total_all > 0 else 0

md_content = f"""# Abeka Video Processing Status

This file is automatically updated by the automated cron batch processor.
It tracks the video download and upload status for each grade to Google Drive (**11fQ8VYTmwRX9fMJFXeTrTTeZGDqki6dh**).

## Overall Progress: {total_completed} / {total_all} lessons ({overall_pct:.1f}%)
![Overall Progress](https://geps.dev/progress/{int(overall_pct)}?c=00ff00)

| Grade | Completed | Progress % | Visual Progress | Completed Lesson Days |
|---|---|---|---|---|
""" + "\n".join(table_rows) + f"""

---
*Last updated: {time.strftime('%Y-%m-%d %H:%M:%S %Z')}*
"""

with open(STATUS_MD_PATH, "w", encoding="utf-8") as f:
f.write(md_content)

def run_cmd(cmd, cwd=BASE_DIR, timeout=60):
print(f"Executing: {' '.join(cmd)}")
env = {**os.environ, "GIT_TERMINAL_PROMPT": "0"}
try:
res = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, env=env, timeout=timeout)
if res.returncode != 0:
print(f"Stderr: {res.stderr}")
return res.returncode == 0
except subprocess.TimeoutExpired as e:
print(f"Command timed out after {timeout}s: {' '.join(cmd)}")
if e.stderr:
print(f"Stderr: {e.stderr}")
return False

def main():
print("🚀 Updating progress status report...")
status = load_status()
save_status(status)

print("\n📤 Committing and pushing changes to GitHub Pages...")
run_cmd(["git", "stash"])
run_cmd(["git", "pull", "--rebase", "origin", "main"])
run_cmd(["git", "stash", "pop"])
run_cmd(["git", "add", "-A"])
run_cmd(["git", "commit", "-m", f"Automated Pipeline Sync: {time.strftime('%Y-%m-%d %H:%M:%S')}"])
run_cmd(["git", "push", "origin", "main"])
print("\n🎉 GitHub Pages publish completed successfully!")

if __name__ == "__main__":
main()
