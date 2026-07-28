#!/usr/bin/env python3
"""
Generate Live Workflow & Process Status JSON for Web UI Dashboard.
Executes periodically or on-demand to populate data/workflow_live_status.json.
"""

import os
import json
import glob
import time
import subprocess
from datetime import datetime, timezone, timedelta

BASE_DIR = "/media/vpsg24gb/DATA1/o9o"
OUTPUT_JSON = os.path.join(BASE_DIR, "data", "workflow_live_status.json")

def get_git_credentials():
    pat = os.environ.get("GITHUB_PAT", "")
    git_cred_file = os.path.expanduser("~/.git-credentials")
    if not pat and os.path.exists(git_cred_file):
        try:
            with open(git_cred_file, "r") as f:
                content = f.read()
                import re
                m = re.search(r"https://[^:]+:([^@]+)@", content)
                if m:
                    pat = m.group(1)
        except Exception:
            pass
    return pat

def fetch_github_workflows():
    pat = get_git_credentials()
    cmd = [
        "curl", "-s",
        "-H", "Accept: application/vnd.github+json",
        "https://api.github.com/repos/naadld/caoo9onet/actions/runs?per_page=10"
    ]
    if pat:
        cmd.insert(2, "-H")
        cmd.insert(3, f"Authorization: Bearer {pat}")

    try:
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        if res.returncode == 0:
            data = json.loads(res.stdout)
            runs = []
            for r in data.get("workflow_runs", []):
                runs.append({
                    "id": r.get("id"),
                    "name": r.get("name"),
                    "status": r.get("status"),
                    "conclusion": r.get("conclusion"),
                    "html_url": r.get("html_url"),
                    "created_at": r.get("created_at"),
                    "run_number": r.get("run_number"),
                    "commit_message": r.get("head_commit", {}).get("message", "") if r.get("head_commit") else ""
                })
            return runs
    except Exception as e:
        print(f"Error fetching GitHub workflows: {e}")
    return []

def get_active_locks():
    locks = glob.glob(os.path.join(BASE_DIR, "*.lock"))
    return [os.path.basename(l) for l in locks]

def get_log_tails():
    logs = {}
    for log_name in ["stream.log", "watchdog.log", "relay.log", "telegram_listener.log"]:
        log_path = os.path.join(BASE_DIR, log_name)
        if os.path.exists(log_path):
            try:
                with open(log_path, "r", encoding="utf-8", errors="ignore") as f:
                    lines = f.readlines()
                    logs[log_name] = "".join(lines[-15:])
            except Exception:
                logs[log_name] = "Unable to read log."
        else:
            logs[log_name] = "Log file not created yet."
    return logs

def get_running_daemons():
    try:
        res = subprocess.run(["ps", "aux"], capture_output=True, text=True, timeout=5)
        out = res.stdout
        daemons = {
            "telegram_bot": "telegram_bot.py" in out or "telegram_listener.js" in out,
            "appscript_relay": "appscript_telegram_relay.py" in out,
            "watchdog": "watchdog" in out,
            "active_scraper_local": "step1_direct_stream.py" in out or "step1_2_date_scraper.py" in out
        }
        return daemons
    except Exception:
        return {}

def main():
    tz_gmt7 = timezone(timedelta(hours=7))
    now_str = datetime.now(tz_gmt7).strftime("%Y-%m-%d %H:%M:%S GMT+7")

    github_runs = fetch_github_workflows()
    active_locks = get_active_locks()
    log_tails = get_log_tails()
    daemons = get_running_daemons()

    status_payload = {
        "last_updated": now_str,
        "active_pairs": [["Grade 1", "Grade 3"]],
        "completed_grades": ["K4", "K5", "Grade 2", "Grade 5"],
        "github_runs": github_runs,
        "active_locks": active_locks,
        "running_daemons": daemons,
        "log_tails": log_tails
    }

    os.makedirs(os.path.dirname(OUTPUT_JSON), exist_ok=True)
    with open(OUTPUT_JSON, "w", encoding="utf-8") as f:
        json.dump(status_payload, f, indent=2, ensure_ascii=False)

    print(f"✅ Generated {OUTPUT_JSON} successfully at {now_str}")

if __name__ == "__main__":
    main()
