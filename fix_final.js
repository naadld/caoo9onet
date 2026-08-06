const fs = require('fs');
let text = fs.readFileSync('scripts/cloudflare_worker.js', 'utf8');

// Remove step 5 block
text = text.replace(/\/\/ \/step 5[\s\S]*?(?=\/\/ \/step 6)/g, '');
// Remove step 6 block
text = text.replace(/\/\/ \/step 6[\s\S]*?(?=\/\/ \/step 7)/g, '');
// Remove step 7 block
text = text.replace(/\/\/ \/step 7[\s\S]*?(?=\}\n\nasync function triggerGitHubWorkflow)/g, '');

// Update sendHelp function to remove step 5, 6, 7
const helpRegex = /async function sendHelp.*?const helpMsg = `📖.*?ℹ️ Gõ \/help bất kỳ lúc nào để hiển thị danh sách này\.`;\n  await sendTelegramReply\(helpMsg, chatId, threadId, null, botTok\);\n}/s;
const newHelp = `async function sendHelp(chatId, threadId, botTok) {
  const helpMsg = \`📖 [BẢNG HƯỚNG DẪN LỆNH BOT TELEGRAM O9O.NET (SERVERLESS CLOUD)]\\n━━━━━━━━━━━━━━━━━━━━━━\\n🎬 STEP 1 - CÀO VIDEO:\\n▪️ /step 1 start\\n   👉 Chạy tiến trình cào mặc định (từng Grade từ ngày nhỏ -> lớn)\\n▪️ /step 1 XX\\n   👉 Cào bài học chưa có của Grade XX (Ví dụ: /step 1 05)\\n▪️ /step 1 XX.yyy\\n   👉 Cào bài học cụ thể (Ví dụ: /step 1 01.010 - Bỏ qua bài đã có)\\n▪️ /step 1 force XX.yyy\\n   👉 Cào ép buộc bài cụ thể (Ví dụ: /step 1 force K4.150 - Ghi đè file)\\n\\n📝 STEP 3 - ĐỒNG BỘ GIT & GOOGLE DOC:\\n▪️ /step 3\\n   👉 Chạy đồng bộ log & Git commit/push\\n\\n🎙️ STEP 4 - TẠO PHỤ ĐỀ AI WHISPER:\\n▪️ /step 4\\n   👉 Khởi chạy tạo phụ đề AI & file JSON tương tác\\n\\n🤖 CHẾ ĐỘ TỰ ĐỘNG (AUTO CRON):\\n▪️ /auto\\n   👉 Kích hoạt chế độ chạy tự động Step 1 & Step 4 mỗi 30 phút\\n▪️ /auto off\\n   👉 Tắt chế độ chạy tự động\\n\\n⚡ KIỂM TRA HỆ THỐNG:\\n▪️ /status\\n   👉 Kiểm tra trạng thái các tiến trình Cloud đang chạy\\n\\nℹ️ Gõ /help bất kỳ lúc nào để hiển thị danh sách này.\`;
  await sendTelegramReply(helpMsg, chatId, threadId, null, botTok);
}`;
text = text.replace(helpRegex, newHelp);

// Remove step 7 from scheduled auto (line 661 onwards)
text = text.replace(/\/\/ Step 7 check & trigger.*?actionsSkipped\.push\("🧹 Step 7.*?Bỏ qua\)"\);\n  \}/gs, '');

fs.writeFileSync('scripts/cloudflare_worker.js', text);
