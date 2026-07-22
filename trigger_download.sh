#!/bin/bash
# ============================================================
# Abeka Video Scraper Cloud Trigger Snippet
# Execute via Terminus / SSH to dispatch GitHub Cloud Scraper
# ============================================================

TOKEN=$(grep -oP 'github\.com' ~/.git-credentials 2>/dev/null | head -n 1)
PAT=$(grep -oP 'https://[^:]+:\K[^@]+' ~/.git-credentials 2>/dev/null | head -n 1)
PAT="${PAT:-$GITHUB_PAT}"

if [ -z "$PAT" ]; then
  echo "❌ Không tìm thấy GitHub PAT Token trong ~/.git-credentials hoặc môi trường."
  exit 1
fi

curl -s -X POST \
  -H "Accept: application/vnd.github+json" \
  -H "Authorization: Bearer $PAT" \
  -H "X-GitHub-Api-Version: 2022-11-28" \
  https://api.github.com/repos/naadld/caoo9onet/actions/workflows/1_scraper_stream.yml/dispatches \
  -d '{"ref":"main"}'

echo "✅ Đã gửi lệnh kích hoạt cào video thành công!"
echo "🔗 Theo dõi tiến trình trực tiếp tại: https://github.com/naadld/caoo9onet/actions"
