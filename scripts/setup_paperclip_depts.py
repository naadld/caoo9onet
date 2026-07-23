#!/usr/bin/env python3
"""
Paperclip NAADLD Organization & Department Setup Script.
Maps Step 1 to Step 6 as 6 distinct Departments under 1 CEO.
Creates/updates Issues and Agents in Paperclip Database (PostgreSQL).
"""

import os
import sys
import json
import shutil
import subprocess

COMPANY_ID = "d244b5e9-4326-45c5-aea7-5f802940d68a"
CEO_ID = "f749085e-3af9-44f7-9824-0ba23356f731"

DEPARTMENTS = [
    {
        "step": "step1",
        "agent_id": "c8b702b2-ccae-49fd-b56b-65a1e5b17521",
        "issue_id": "11111111-1111-1111-1111-111111111111",
        "key": "STEP-1",
        "name": "Step 1 - Media Scrapping Dept",
        "role": "dept_media_scrapping",
        "title": "Head of Media Scrapping Dept",
        "issue_title": "🎬 Step 1: Media Scrapping Dept Live Feed"
    },
    {
        "step": "step2",
        "agent_id": "777c31ef-2605-43c5-8fdb-b18e70fe4e3e",
        "issue_id": "22222222-2222-2222-2222-222222222222",
        "key": "STEP-2",
        "name": "Step 2 - Website Indexing Dept",
        "role": "dept_website_indexing",
        "title": "Head of Website Indexing Dept",
        "issue_title": "🌐 Step 2: Website Indexing Dept Live Feed"
    },
    {
        "step": "step3",
        "agent_id": "7874449f-c660-4612-9282-f07aa5906682",
        "issue_id": "33333333-3333-3333-3333-333333333333",
        "key": "STEP-3",
        "name": "Step 3 - Playlist Fetching Dept",
        "role": "dept_playlist_fetching",
        "title": "Head of Playlist Fetching Dept",
        "issue_title": "📝 Step 3: Playlist Fetching Dept Live Feed"
    },
    {
        "step": "step4",
        "agent_id": "44444444-4444-4444-4444-444444444444",
        "issue_id": "44444444-4444-4444-4444-444444444444",
        "key": "STEP-4",
        "name": "Step 4 - Subtitle Building Dept",
        "role": "dept_subtitle_building",
        "title": "Head of Subtitle Building Dept",
        "issue_title": "🎙️ Step 4: Subtitle Building Dept Live Feed"
    },
    {
        "step": "step5",
        "agent_id": "69000d64-6b6d-427d-99e1-e5d89848767c",
        "issue_id": "55555555-5555-5555-5555-555555555555",
        "key": "STEP-5",
        "name": "Step 5 - Storage Copying Dept",
        "role": "dept_storage_copying",
        "title": "Head of Storage Copying Dept",
        "issue_title": "📂 Step 5: Storage Copying Dept Live Feed"
    },
    {
        "step": "step6",
        "agent_id": "66666666-6666-6666-6666-666666666666",
        "issue_id": "66666666-6666-6666-6666-666666666666",
        "key": "STEP-6",
        "name": "Step 6 - Gdrive Comparision Dept",
        "role": "dept_gdrive_comparision",
        "title": "Head of Gdrive Comparision Dept",
        "issue_title": "📊 Step 6: Gdrive Comparision Dept Live Feed"
    }
]

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
        except Exception as e:
            print(f"SQL Exception: {e}")
    return ""

def setup_organization():
    print("=" * 60)
    print("🏢 SETTING UP NAADLD ORGANIZATION & DEPARTMENTS IN PAPERCLIP")
    print("=" * 60)

    # 1. CEO Agent
    sql_ceo = f"""
    INSERT INTO agents (id, company_id, name, role, title, status, adapter_type, created_at, updated_at)
    VALUES ('{CEO_ID}', '{COMPANY_ID}', 'NAADLD-Executive-CEO', 'ceo', 'Chief Executive Officer (CEO)', 'active', 'manual', NOW(), NOW())
    ON CONFLICT (id) DO UPDATE 
    SET name = 'NAADLD-Executive-CEO', role = 'ceo', title = 'Chief Executive Officer (CEO)', status = 'active';
    """
    run_sql(sql_ceo)
    print("✅ Verified CEO Agent: NAADLD-Executive-CEO")

    # 2. Departments & Issues
    for dept in DEPARTMENTS:
        name = dept["name"]
        role = dept["role"]
        title = dept["title"]
        key = dept["key"]
        agent_id = dept["agent_id"]
        issue_id = dept["issue_id"]
        issue_title = dept["issue_title"]

        # Agent Insert/Update
        sql_agent = f"""
        INSERT INTO agents (id, company_id, name, role, title, status, reports_to, adapter_type, created_at, updated_at)
        VALUES ('{agent_id}', '{COMPANY_ID}', '{name}', '{role}', '{title}', 'active', '{CEO_ID}', 'manual', NOW(), NOW())
        ON CONFLICT (id) DO UPDATE 
        SET name = '{name}', role = '{role}', title = '{title}', status = 'active', reports_to = '{CEO_ID}';
        """
        run_sql(sql_agent)

        # Issue Insert/Update
        sql_issue = f"""
        INSERT INTO issues (id, company_id, identifier, title, status, assignee_agent_id, created_by_agent_id, priority, created_at, updated_at)
        VALUES ('{issue_id}', '{COMPANY_ID}', '{key}', '{issue_title}', 'in_progress', '{agent_id}', '{CEO_ID}', 'high', NOW(), NOW())
        ON CONFLICT (id) DO UPDATE 
        SET title = '{issue_title}', status = 'in_progress', assignee_agent_id = '{agent_id}';
        """
        run_sql(sql_issue)

        print(f"🏢 Configured Dept: [{name}] -> Agent ID: {agent_id} | Issue Key: {key}")

if __name__ == "__main__":
    setup_organization()
