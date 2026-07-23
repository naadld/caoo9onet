#!/usr/bin/env python3
"""
Sync live scraping & system progress for Step 1 to Step 6 to Paperclip AI Dashboard (PostgreSQL DB).
Maps each Step to its corresponding Department under NAADLD CEO.
"""

import os
import sys
import glob
import json
import shutil
import argparse
import subprocess
import time
import urllib.request

COMPANY_ID = "d244b5e9-4326-45c5-aea7-5f802940d68a"
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

STEP_DEPT_MAP = {
    "step1": {
        "key": "STEP-1",
        "role": "dept_media_scrapping",
        "name": "Step 1 - Media Scrapping Dept"
    },
    "step2": {
        "key": "STEP-2",
        "role": "dept_website_indexing",
        "name": "Step 2 - Website Indexing Dept"
    },
    "step3": {
        "key": "STEP-3",
        "role": "dept_playlist_fetching",
        "name": "Step 3 - Playlist Fetching Dept"
    },
    "step4": {
        "key": "STEP-4",
        "role": "dept_subtitle_building",
        "name": "Step 4 - Subtitle Building Dept"
    },
    "step5": {
        "key": "STEP-5",
        "role": "dept_storage_copying",
        "name": "Step 5 - Storage Copying Dept"
    },
    "step6": {
        "key": "STEP-6",
        "role": "dept_gdrive_comparision",
        "name": "Step 6 - Gdrive Comparision Dept"
    }
}

def send_to_cloudflare(step_name, status_str, detail_msg):
    url = "https://gentle-darkness-4028.hothihuong113.workers.dev/api/progress"
    payload = {
        "step": step_name,
        "status": status_str,
        "msg": detail_msg
    }
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"}, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            if resp.status == 200:
                print(f"✅ Synced progress back to Cloudflare Worker -> VPS: {step_name} ({status_str})")
                return True
    except Exception as e:
        print(f"❌ Failed to sync progress to Cloudflare Worker: {e}")
    return False

def run_sql(sql):
    if shutil.which("docker"):
        cmd = [
            "docker", "exec", "-i", "docker-db-1",
            "psql", "-U", "paperclip", "-d", "paperclip", "-c", sql
        ]
        try:
            res = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            if res.returncode == 0:
                return res.stdout
        except Exception:
            pass

    if shutil.which("psql"):
        cmd = ["psql", "-h", "docker-db-1", "-U", "paperclip", "-d", "paperclip", "-c", sql]
        try:
            env = {**os.environ, "PGPASSWORD": "paperclip_password"}
            res = subprocess.run(cmd, capture_output=True, text=True, env=env, timeout=10)
            if res.returncode == 0:
                return res.stdout
        except Exception:
            pass

    return ""

def get_agent_id(role):
    sql = f"SELECT id FROM agents WHERE company_id = '{COMPANY_ID}' AND role = '{role}' LIMIT 1;"
    out = run_sql(sql)
    for line in out.splitlines():
        line = line.strip()
        if len(line) == 36 and "-" in line:
            return line
    return None

def get_issue_id(identifier):
    sql = f"SELECT id FROM issues WHERE company_id = '{COMPANY_ID}' AND identifier = '{identifier}' LIMIT 1;"
    out = run_sql(sql)
    for line in out.splitlines():
        line = line.strip()
        if len(line) == 36 and "-" in line:
            return line
    return None

def post_comment(issue_id, agent_id, comment_body):
    if not issue_id or not agent_id:
        return
    body_escaped = comment_body.replace("'", "''")
    sql = f"""
    INSERT INTO issue_comments (id, company_id, issue_id, author_agent_id, author_type, body, created_at, updated_at)
    VALUES (gen_random_uuid(), '{COMPANY_ID}', '{issue_id}', '{agent_id}', 'agent', '{body_escaped}', NOW(), NOW());
    """
    run_sql(sql)

def update_paperclip_dept(step_name, status_str, detail_msg):
    if os.getenv("GITHUB_ACTIONS") == "true":
        send_to_cloudflare(step_name, status_str, detail_msg)
        return

    step_key = str(step_name).lower().strip()
    if step_key not in STEP_DEPT_MAP:
        step_key = "step1"

    dept_info = STEP_DEPT_MAP[step_key]
    role = dept_info["role"]
    issue_key = dept_info["key"]
    dept_name = dept_info["name"]

    agent_id = get_agent_id(role)
    issue_id = get_issue_id(issue_key)

    now_str = time.strftime("%Y-%m-%d %H:%M:%S")
    formatted_msg = f"""🏢 [{dept_name.upper()} - {status_str}]
━━━━━━━━━━━━━━━━━━━━━━
⏰ Thời gian: {now_str}
📌 Trạng thái: {status_str}
📝 Chi tiết:
{detail_msg}
"""

    if issue_id and agent_id:
        post_comment(issue_id, agent_id, formatted_msg)
        print(f"✅ Posted real-time activity update to Paperclip UI for [{dept_name}].")
    else:
        print(f"⚠️ Could not resolve agent ({agent_id}) or issue ({issue_id}) for [{dept_name}].")

def main():
    parser = argparse.ArgumentParser(description="Sync GitHub Actions & System Activity to Paperclip AI Dashboard")
    parser.add_argument("--step", choices=["step1", "step2", "step3", "step4", "step5", "step6"], default="step1", help="Step/Dept to update")
    parser.add_argument("--status", default="RUNNING", help="Status string (e.g. START, RUNNING, SUCCESS, ERROR)")
    parser.add_argument("--msg", default="Processing step...", help="Detailed message for Paperclip live feed")

    args = parser.parse_args()
    update_paperclip_dept(args.step, args.status, args.msg)

if __name__ == "__main__":
    main()
