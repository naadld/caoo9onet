#!/usr/bin/env python3
"""
Sync live scraping & system progress to Paperclip AI Dashboard (PostgreSQL DB).
Works seamlessly whether executed directly on Host or inside Docker Container.
"""

import os
import glob
import json
import shutil
import subprocess
import time

COMPANY_ID = "d244b5e9-4326-45c5-aea7-5f802940d68a"
BASE_DIR = "/media/vpsg24gb/DATA1/o9o"
STREAM_LOG = os.path.join(BASE_DIR, "stream.log")

def run_sql(sql):
    # Try docker exec if running on host
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

    # Try psql directly if running inside container
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

def main():
    # 1. Count completed videos
    total_videos = 0
    grade_counts = {}
    for f in glob.glob(os.path.join(BASE_DIR, "database_*.json")):
        try:
            name = os.path.basename(f).replace("database_", "").replace(".json", "")
            data = json.load(open(f, "r", encoding="utf-8"))
            count = len(data)
            grade_counts[name] = count
            total_videos += count
        except Exception:
            pass

    # 2. Get last 5 lines from stream log
    last_log_lines = []
    if os.path.exists(STREAM_LOG):
        try:
            with open(STREAM_LOG, "r", encoding="utf-8", errors="ignore") as f:
                lines = f.readlines()
                last_log_lines = [l.strip() for l in lines[-5:] if l.strip()]
        except Exception:
            pass

    log_summary = "\n".join(last_log_lines) if last_log_lines else "Stream log active."

    # 3. Format progress message
    grade_details = ", ".join([f"{k}: {v} video" for k, v in grade_counts.items()])
    now_str = time.strftime("%Y-%m-%d %H:%M:%S")

    comment_msg = f"""⚡ [Paperclip Live Activity Log - {now_str}]
🎬 Tổng số video đã hoàn tất & Upload GDrive: {total_videos} video
📊 Chi tiết: {grade_details}
⚙️ Quy tắc cào: ĐƠN LUỒNG 1 VIDEO / LẦN (Chế độ Lock Single-Instance Active)
📌 Nhật ký cào mới nhất:
{log_summary}
"""

    try:
        pipe_agent_id = get_agent_id("pipe_streamer")
        pri1_issue_id = get_issue_id("PRI-1")

        if pri1_issue_id and pipe_agent_id:
            post_comment(pri1_issue_id, pipe_agent_id, comment_msg)
            print(f"✅ Posted live activity update to Paperclip UI (Total: {total_videos} videos).")
    except Exception as e:
        print(f"⚠️ Live sync info: {e}")

if __name__ == "__main__":
    main()
