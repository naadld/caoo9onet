#!/usr/bin/env python3
"""
Upload/Overwrite the index_songsong.html directly to GDrive File ID: 17-iAoi4fK8DuxX7ucDBEvJbtLj4Q2rkX.
Uses the GCP Service Account credentials from credentials.json or GCP_SERVICE_ACCOUNT_JSON.
"""

import os
import sys
import json
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CREDENTIALS_PATH = os.path.join(BASE_DIR, "credentials.json")
LOCAL_FILE = os.path.join(BASE_DIR, "index_songsong.html")
FILE_ID = "17-iAoi4fK8DuxX7ucDBEvJbtLj4Q2rkX"

def get_creds():
    env_creds = os.environ.get("GCP_SERVICE_ACCOUNT_JSON")
    if env_creds:
        try:
            info = json.loads(env_creds)
            if "private_key" in info:
                info["private_key"] = str(info["private_key"]).replace("\\n", "\n").replace("\r", "")
            return Credentials.from_service_account_info(
                info,
                scopes=["https://www.googleapis.com/auth/drive"]
            )
        except Exception as e:
            print(f"⚠️ Error parsing GCP_SERVICE_ACCOUNT_JSON: {e}")

    if os.path.exists(CREDENTIALS_PATH):
        try:
            return Credentials.from_service_account_file(
                CREDENTIALS_PATH,
                scopes=["https://www.googleapis.com/auth/drive"]
            )
        except Exception as e:
            print(f"⚠️ Error reading local credentials.json: {e}")

    return None

def upload_dashboard():
    print("=" * 60)
    print("📤 GOOGLE DRIVE HTML DASHBOARD UPLOADER")
    print("=" * 60)

    if not os.path.exists(LOCAL_FILE):
        print(f"❌ ERROR: Local file not found at: {LOCAL_FILE}")
        return False

    creds = get_creds()
    if not creds:
        print("ℹ️ Service Account credentials not found. Falling back to rclone upload...")
        import subprocess, shutil
        rclone_bin = shutil.which("rclone") or "rclone"
        rclone_conf = os.getenv("RCLONE_CONFIG") or "/home/vpsg24gb/.config/rclone/rclone.conf"
        target_remote = "vpsg24gb.aleron,root_folder_id=11fQ8VYTmwRX9fMJFXeTrTTeZGDqki6dh:index_songsong.html"
        cmd = [rclone_bin, "--config", rclone_conf, "copyto", LOCAL_FILE, target_remote]
        res = subprocess.run(cmd, capture_output=True, text=True)
        if res.returncode == 0:
            print("🎉 Dashboard successfully uploaded via rclone!")
            return True
        else:
            print(f"❌ rclone upload failed: {res.stderr}")
            return False

    try:
        service = build("drive", "v3", credentials=creds)
        
        # Overwrite file metadata & content by ID
        media = MediaFileUpload(LOCAL_FILE, mimetype="text/html", resumable=True)
        print(f"📤 Overwriting GDrive File ID '{FILE_ID}' with latest dashboard data...")
        
        updated_file = service.files().update(
            fileId=FILE_ID,
            media_body=media,
            fields="id,name,webViewLink"
        ).execute()
        
        print("🎉 Dashboard successfully uploaded!")
        print(f"🔗 WebView Link: {updated_file.get('webViewLink')}")
        return True
    except Exception as e:
        print(f"❌ Error uploading dashboard: {e}")
        print("📌 Please make sure the target File ID is shared with your Service Account email (Editor role).")
        return False

if __name__ == "__main__":
    upload_dashboard()
