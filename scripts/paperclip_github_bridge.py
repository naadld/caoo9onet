#!/usr/bin/env python3
"""
Paperclip -> GitHub Actions Cloud Interactive Controller & Bridge.
Allows triggering GitHub Actions Cloud workflows directly from Paperclip Agent Actions / Issues.
Supports Step 1, Step 3, Step 4, Step 5, Step 6.
"""

import os
import sys
import json
import urllib.request
import urllib.parse

GITHUB_REPO = "naadld/caoo9onet"
GITHUB_PAT = os.getenv("GITHUB_PAT") or os.getenv("GH_PAT") or ""

def trigger_github_workflow(workflow_file, inputs_dict):
    if not GITHUB_PAT:
        print("⚠️ GITHUB_PAT not set. Please provide GitHub Personal Access Token.")
        return False

    url = f"https://api.github.com/repos/{GITHUB_REPO}/actions/workflows/{workflow_file}/dispatches"
    payload = {
        "ref": "main",
        "inputs": inputs_dict
    }
    data = json.dumps(payload).encode("utf-8")
    headers = {
        "Accept": "application/vnd.github+json",
        "Authorization": f"Bearer {GITHUB_PAT}",
        "User-Agent": "Paperclip-GitHub-Bridge",
        "X-GitHub-Api-Version": "2022-11-28"
    }

    try:
        req = urllib.request.Request(url, data=data, headers=headers, method="POST")
        with urllib.request.urlopen(req, timeout=10) as resp:
            if resp.status in (200, 201, 204):
                print(f"🚀 [PAPERCLIP -> GITHUB API SUCCESS] Triggered workflow {workflow_file} with inputs: {inputs_dict}")
                return True
    except Exception as e:
        print(f"❌ [PAPERCLIP -> GITHUB API ERROR] Failed to trigger {workflow_file}: {e}")

    return False

def parse_paperclip_command(command_str):
    text = command_str.strip().lower()
    
    # /step 1
    if "step 1" in text or "step1" in text:
        if "start" in text:
            return ("1_scraper_stream.yml", {"max_days": "170"})
        m_grade = urllib.parse.parse_qs(text).get("grade")
        if "05" in text or "grade 5" in text or "5" in text:
            return ("1_scraper_stream.yml", {"grade": "Grade 5", "max_days": "170"})
        return ("1_scraper_stream.yml", {"max_days": "170"})

    # /step 4
    if "step 4" in text or "step4" in text:
        return ("4_generate_subtitles.yml", {"target_folder": "Grade 5"})

    # /step 5
    if "step 5" in text or "step5" in text:
        return ("5_gdrive_copier.yml", {})

    # /step 6
    if "step 6" in text or "step6" in text:
        return ("6_folder_comparator.yml", {})

    return (None, {})

if __name__ == "__main__":
    if len(sys.argv) > 1:
        cmd = " ".join(sys.argv[1:])
        wf, inputs = parse_paperclip_command(cmd)
        if wf:
            trigger_github_workflow(wf, inputs)
        else:
            print(f"⚠️ Unrecognized Paperclip command: {cmd}")
