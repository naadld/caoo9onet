#!/bin/bash
# ============================================================
# Abeka Video Scraper Cloud Trigger Snippet
# Execute via Terminus / SSH to dispatch GitHub Cloud Scraper
# ============================================================

echo "🚀 Kích hoạt tiến trình cào video Abeka trên GitHub Cloud..."

curl -s -X POST \
  -H "Accept: application/vnd.github+json" \
  -H "Authorization: Bearer YOUR_GITHUB_PAT" \
  -H "X-GitHub-Api-Version: 2022-11-28" \
  https://api.github.com/repos/naadld/caoo9onet/actions/workflows/1_scraper_stream.yml/dispatches \
  -d '{"ref":"main"}'

echo "✅ Đã gửi lệnh kích hoạt cào video thành công!"
echo "🔗 Theo dõi tiến trình trực tiếp tại: https://github.com/naadld/caoo9onet/actions"
