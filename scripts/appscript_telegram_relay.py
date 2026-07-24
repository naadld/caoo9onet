#!/usr/bin/env python3
"""
O9O.NET Telegram Webhook -> Google Apps Script Relay (with Ngrok / Cloudflare Tunnel)
Receives Telegram Webhook POST -> Follows HTTP 302 Redirect to Google Apps Script -> Returns HTTP 200 OK to Telegram.
Also intercepts /api/progress endpoint to sync Cloud logging directly to local Paperclip!
"""

import os
import sys
import json
import requests
import subprocess
from http.server import HTTPServer, BaseHTTPRequestHandler

APPS_SCRIPT_URL = "https://script.google.com/macros/s/AKfycby1ZNXnIdywl3xUX2dQSrdPQmLe2I0Qsh1d-_K-LU2vuJWC7HYuB1VOIi8nycLMSh1M/exec"
DEFAULT_PORT = 8088

class RelayHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/plain; charset=utf-8')
        self.end_headers()
        self.wfile.write(b"O9O.NET Telegram -> Google Apps Script Relay Active!")

    def do_POST(self):
        content_length = int(self.headers.get('Content-Length', 0))
        post_data = self.rfile.read(content_length)
        
        # Intercept /api/progress for live dashboard feed updates
        if self.path == "/api/progress":
            try:
                payload = json.loads(post_data.decode('utf-8'))
                step = payload.get("step", "step1")
                status = payload.get("status", "RUNNING")
                msg = payload.get("msg", "")
                print(f"📥 [Live Progress] step={step}, status={status}, msg={msg[:60]}...")
                
                # Execute local sync script to write to Postgres
                cmd = [
                    "python3", "/media/vpsg24gb/DATA1/o9o/scripts/sync_paperclip_live.py",
                    "--step", step,
                    "--status", status,
                    "--msg", msg
                ]
                res = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
                print(f"✅ Sync Script Exit Code: {res.returncode}")
            except Exception as e:
                print(f"⚠️ Live Progress Sync Error: {e}")
            
            self.send_response(200)
            self.send_header('Content-type', 'text/plain')
            self.end_headers()
            self.wfile.write(b"OK")
            return

        try:
            payload = json.loads(post_data.decode('utf-8'))
            print(f"📥 Received Telegram Webhook -> Forwarding to Google Apps Script...")
            
            # Forward POST payload to Google Apps Script following HTTP 302 redirects
            res = requests.post(APPS_SCRIPT_URL, json=payload, allow_redirects=True, timeout=15)
            print(f"✅ Google Apps Script Executed! Status: {res.status_code}")
        except Exception as e:
            print(f"⚠️ Relay Forwarding Error: {e}")

        # Always return HTTP 200 OK directly to Telegram
        self.send_response(200)
        self.send_header('Content-type', 'text/plain')
        self.end_headers()
        self.wfile.write(b"OK")

    def log_message(self, format, *args):
        pass

def main():
    port = int(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_PORT
    server_address = ('0.0.0.0', port)
    httpd = HTTPServer(server_address, RelayHandler)
    print(f"🚀 Telegram -> Google Apps Script Relay running on port {port}...")
    httpd.serve_forever()

if __name__ == '__main__':
    main()
