/**
 * O9O.NET Telegram Bot Controller via Google Apps Script (Serverless 24/7)
 * Webhook Endpoint: Telegram -> Apps Script -> GitHub Actions API & Google Docs
 */

const TELEGRAM_BOT_TOKEN = "YOUR_TELEGRAM_BOT_TOKEN_HERE";
const FALLBACK_BOT_TOKEN = "YOUR_FALLBACK_BOT_TOKEN_HERE";
const TARGET_CHAT_ID     = "-1003954353565";
const TARGET_THREAD_ID   = 3953;

// Paste your GitHub Personal Access Token (PAT) here or set in Script Properties
const GITHUB_PAT         = "YOUR_GITHUB_PAT_HERE"; 
const GITHUB_REPO        = "naadld/caoo9onet";

/**
 * Main Webhook POST Handler
 */
function doPost(e) {
  try {
    if (!e || !e.postData || !e.postData.contents) {
      return ContentService.createTextOutput("OK");
    }

    const update = JSON.parse(e.postData.contents);
    const message = update.message || update.channel_post || update.edited_message;
    if (!message) return ContentService.createTextOutput("OK");

    const chatId = String(message.chat.id);
    const threadId = message.message_thread_id;
    const text = (message.text || "").trim();

    // Verify Chat ID (-1003954353565)
    if (chatId === TARGET_CHAT_ID || chatId === String(TARGET_CHAT_ID)) {
      routeCommand(text, chatId, TARGET_THREAD_ID);
    }
  } catch (err) {
    Logger.log("doPost Error: " + err);
  }
  return ContentService.createTextOutput("OK");
}

function doGet(e) {
  return ContentService.createTextOutput("O9O.NET Telegram Apps Script Webhook is Active!");
}

/**
 * Command Router
 */
function routeCommand(rawText, chatId, threadId) {
  const text = rawText.trim();
  const clean = text.toLowerCase();
  const nowStr = getVNNowString();

  // /help
  if (clean === "/help" || clean === "help" || clean.indexOf("/help@") === 0 || clean.indexOf("/start") === 0) {
    sendHelp(chatId, threadId);
    return;
  }

  // /status
  if (clean === "/status" || clean === "status" || clean.indexOf("/status@") === 0) {
    sendStatus(chatId, threadId);
    return;
  }

  // /step 1
  if (clean.indexOf("/step 1") === 0 || clean.indexOf("/step1") === 0 || clean.indexOf("step 1") === 0) {
    // 1. /step 1 force XX.yyy or /step 1 XX.yyy
    const mDay = text.match(/step\s*1\s+(?:(force)\s+)?([a-zA-Z0-9]+)[\._](\d+)/i);
    if (mDay) {
      const isForce = !!mDay[1];
      const rawGrade = mDay[2];
      const dayNum = mDay[3];
      const grade = normalizeGrade(rawGrade);
      const modeText = isForce ? "FORCE (Ghi đè file cũ)" : "THƯỜNG (Bỏ qua bài đã có)";

      sendTelegramReply(`📥 [ĐÃ NHẬN LỆNH /step 1 ${rawGrade}.${dayNum}]\n━━━━━━━━━━━━━━━━━━━━━━\n📚 Grade: ${grade}\n📅 Ngày: Ngày ${dayNum}\n⚡ Chế độ: ${modeText}\n⏰ Thời gian: ${nowStr}\n🚀 Đang kích hoạt GitHub Actions Cloud...`, chatId, threadId);

      const res = triggerGitHubWorkflow("1_scraper_stream.yml", {
        "max_days": "1",
        "grade": String(grade),
        "day": String(parseInt(dayNum, 10)),
        "force": isForce ? "true" : "false"
      });
      sendTelegramReply(res.success ? `✅ [KÍCH HOẠT THÀNH CÔNG]\n${res.info}\n🔗 Theo dõi tại: https://github.com/${GITHUB_REPO}/actions` : `❌ ${res.info}`, chatId, threadId);
      return;
    }

    // 2. /step 1 start
    if (clean.indexOf("start") !== -1) {
      sendTelegramReply(`🚀 [ĐÃ NHẬN LỆNH /step 1 start]\n━━━━━━━━━━━━━━━━━━━━━━\n📚 Tiến trình cào mặc định toàn bộ các Grade\n📅 Quét từ ngày nhỏ đến ngày lớn (Day 001 -> Day 170)\n⏰ Thời gian: ${nowStr}\n🚀 Đang khởi chạy GitHub Actions Cloud...`, chatId, threadId);
      const res = triggerGitHubWorkflow("1_scraper_stream.yml", { "max_days": "170" });
      sendTelegramReply(res.success ? `✅ [KÍCH HOẠT THÀNH CÔNG]\n${res.info}\n🔗 Theo dõi tại: https://github.com/${GITHUB_REPO}/actions` : `❌ ${res.info}`, chatId, threadId);
      return;
    }

    // 3. /step 1 XX
    const mGrade = text.match(/step\s*1\s+([a-zA-Z0-9]+)/i);
    if (mGrade && mGrade[1].toLowerCase() !== "start") {
      const rawGrade = mGrade[1];
      const grade = normalizeGrade(rawGrade);
      sendTelegramReply(`🚀 [ĐÃ NHẬN LỆNH /step 1 ${rawGrade}]\n━━━━━━━━━━━━━━━━━━━━━━\n📚 Cào toàn bộ bài học chưa có của ${grade}\n📅 Quét từ Day 001 đến Day 170 (Bỏ qua bài đã có)\n⏰ Thời gian: ${nowStr}\n🚀 Đang khởi chạy GitHub Actions Cloud...`, chatId, threadId);
      const res = triggerGitHubWorkflow("1_scraper_stream.yml", { "grade": String(grade), "max_days": "170" });
      sendTelegramReply(res.success ? `✅ [KÍCH HOẠT THÀNH CÔNG]\n${res.info}\n🔗 Theo dõi tại: https://github.com/${GITHUB_REPO}/actions` : `❌ ${res.info}`, chatId, threadId);
      return;
    }
  }

  // /step 3
  if (clean.indexOf("/step 3") === 0 || clean.indexOf("/step3") === 0 || clean === "step 3") {
    sendTelegramReply(`🚀 [ĐÃ NHẬN LỆNH /step 3]\n━━━━━━━━━━━━━━━━━━━━━━\n📝 Đồng bộ Git Commit & Ghi Log Google Doc...\n⏰ Thời gian: ${nowStr}`, chatId, threadId);
    sendTelegramReply(`✅ [STEP 3] Đã ghi nhận lệnh thành công!`, chatId, threadId);
    return;
  }

  // /step 4
  if (clean.indexOf("/step 4") === 0 || clean.indexOf("/step4") === 0 || clean === "step 4") {
    sendTelegramReply(`🚀 [ĐÃ NHẬN LỆNH /step 4]\n━━━━━━━━━━━━━━━━━━━━━━\n🎙️ Khởi chạy Tạo Phụ đề AI Whisper & Interactive JSON...\n⏰ Thời gian: ${nowStr}`, chatId, threadId);
    const res = triggerGitHubWorkflow("4_generate_subtitles.yml", { "target_folder": "Grade 4" });
    sendTelegramReply(res.success ? `✅ [KÍCH HOẠT THÀNH CÔNG]\n${res.info}\n🔗 Theo dõi tại: https://github.com/${GITHUB_REPO}/actions` : `❌ ${res.info}`, chatId, threadId);
    return;
  }

  // /step 5
  if (clean.indexOf("/step 5") === 0 || clean.indexOf("/step5") === 0 || clean.indexOf("step 5") === 0) {
    const mLinks = text.match(/step\s*5\s+([^\s-]+)[\s-]+([^\s]+)/i);
    if (mLinks && mLinks[1].toLowerCase() !== "start") {
      const src = mLinks[1].trim();
      const dst = mLinks[2].trim();
      sendTelegramReply(`🚀 [ĐÃ NHẬN LỆNH /step 5 CUSTOM COPY]\n━━━━━━━━━━━━━━━━━━━━━━\n📁 Nguồn: ${src}\n📂 Đích:  ${dst}\n⏰ Thời gian: ${nowStr}\n🚀 Đang khởi chạy GitHub Actions Cloud...`, chatId, threadId);
      const res = triggerGitHubWorkflow("5_gdrive_copier.yml", { "src_folder": src, "dst_folder": dst });
      sendTelegramReply(res.success ? `✅ [KÍCH HOẠT THÀNH CÔNG]\n${res.info}\n🔗 Theo dõi tại: https://github.com/${GITHUB_REPO}/actions` : `❌ ${res.info}`, chatId, threadId);
      return;
    }

    sendTelegramReply(`🚀 [ĐÃ NHẬN LỆNH /step 5 start]\n━━━━━━━━━━━━━━━━━━━━━━\n📂 Tiếp tục Copy thư mục GDrive dở dang (Nguồn -> Đích)\n⚡ Chế độ: Bỏ qua các file đã có\n⏰ Thời gian: ${nowStr}\n🚀 Đang khởi chạy GitHub Actions Cloud...`, chatId, threadId);
    const res = triggerGitHubWorkflow("5_gdrive_copier.yml", {});
    sendTelegramReply(res.success ? `✅ [KÍCH HOẠT THÀNH CÔNG]\n${res.info}\n🔗 Theo dõi tại: https://github.com/${GITHUB_REPO}/actions` : `❌ ${res.info}`, chatId, threadId);
    return;
  }

  // /step 6
  if (clean.indexOf("/step 6") === 0 || clean.indexOf("/step6") === 0 || clean.indexOf("step 6") === 0) {
    const mLinks = text.match(/step\s*6\s+([^\s-]+)[\s-]+([^\s]+)/i);
    if (mLinks && mLinks[1].toLowerCase() !== "start") {
      const src = mLinks[1].trim();
      const dst = mLinks[2].trim();
      sendTelegramReply(`🚀 [ĐÃ NHẬN LỆNH /step 6 CUSTOM COMPARE]\n━━━━━━━━━━━━━━━━━━━━━━\n📁 Nguồn: ${src}\n📂 Đích:  ${dst}\n⏰ Thời gian: ${nowStr}\n📊 Đang khởi chạy tiến trình đối chiếu & so sánh...`, chatId, threadId);
      const res = triggerGitHubWorkflow("6_folder_comparator.yml", { "src_folder": src, "dst_folder": dst });
      sendTelegramReply(res.success ? `✅ [KÍCH HOẠT THÀNH CÔNG]\n${res.info}\n🔗 Theo dõi tại: https://github.com/${GITHUB_REPO}/actions` : `❌ ${res.info}`, chatId, threadId);
      return;
    }

    sendTelegramReply(`🚀 [ĐÃ NHẬN LỆNH /step 6]\n━━━━━━━━━━━━━━━━━━━━━━\n📊 Khởi chạy Step 6: Báo cáo đối chiếu & so sánh thư mục GDrive...\n⏰ Thời gian: ${nowStr}`, chatId, threadId);
    const res = triggerGitHubWorkflow("6_folder_comparator.yml", {});
    sendTelegramReply(res.success ? `✅ [KÍCH HOẠT THÀNH CÔNG]\n${res.info}\n🔗 Theo dõi tại: https://github.com/${GITHUB_REPO}/actions` : `❌ ${res.info}`, chatId, threadId);
    return;
  }
}

/**
 * GitHub Actions Dispatch API Call
 */
function triggerGitHubWorkflow(workflowFile, inputsObj) {
  const pat = getPAT();
  if (!pat || pat === "YOUR_GITHUB_PAT_HERE") {
    return { success: false, info: "Chưa cấu hình GITHUB_PAT trong Apps Script." };
  }

  const url = `https://api.github.com/repos/${GITHUB_REPO}/actions/workflows/${workflowFile}/dispatches`;
  const options = {
    method: "post",
    contentType: "application/json",
    headers: {
      "Accept": "application/vnd.github+json",
      "Authorization": "Bearer " + pat,
      "X-GitHub-Api-Version": "2022-11-28"
    },
    payload: JSON.stringify({
      ref: "main",
      inputs: inputsObj
    }),
    muteHttpExceptions: true
  };

  try {
    const response = UrlFetchApp.fetch(url, options);
    const code = response.getResponseCode();
    if (code === 204 || code === 200 || code === 201) {
      return { success: true, info: "Đã gửi lệnh kích hoạt GitHub Actions Cloud thành công!" };
    } else {
      return { success: false, info: `GitHub API trả về HTTP ${code}: ${response.getContentText()}` };
    }
  } catch (err) {
    return { success: false, info: "Lỗi kết nối GitHub API: " + err };
  }
}

/**
 * System Status Report (/status)
 */
function sendStatus(chatId, threadId) {
  const nowStr = getVNNowString();
  const pat = getPAT();

  let ghStatusList = [];
  if (pat && pat !== "YOUR_GITHUB_PAT_HERE") {
    const url = `https://api.github.com/repos/${GITHUB_REPO}/actions/runs?status=in_progress`;
    const options = {
      method: "get",
      headers: {
        "Accept": "application/vnd.github+json",
        "Authorization": "Bearer " + pat,
        "X-GitHub-Api-Version": "2022-11-28"
      },
      muteHttpExceptions: true
    };
    try {
      const resp = UrlFetchApp.fetch(url, options);
      if (resp.getResponseCode() === 200) {
        const data = JSON.parse(resp.getContentText());
        const runs = data.workflow_runs || [];
        if (runs.length > 0) {
          runs.forEach(r => ghStatusList.push(`⚡ ${r.name} (Run #${r.id})`));
        } else {
          ghStatusList.push("⚪ Không có tiến trình cloud nào đang chạy");
        }
      }
    } catch (e) {
      ghStatusList.push("⚠️ Không thể kết nối GitHub API");
    }
  } else {
    ghStatusList.push("ℹ️ Chưa cấu hình GITHUB_PAT");
  }

  const msg = `📊 [BÁO CÁO TRẠNG THÁI HỆ THỐNG /status]\n━━━━━━━━━━━━━━━━━━━━━━\n🟢 GOOGLE APPS SCRIPT WEBHOOK: Hoạt động 24/7 (Serverless)\n\n☁️ GITHUB ACTIONS CLOUD:\n  ${ghStatusList.join("\n  ")}\n\n⏰ Giờ kiểm tra (GMT+7): ${nowStr}`;
  sendTelegramReply(msg, chatId, threadId);
}

/**
 * Interactive Help Menu (/help)
 */
function sendHelp(chatId, threadId) {
  const helpMsg = `📖 [BẢNG HƯỚNG DẪN LỆNH BOT TELEGRAM O9O.NET (APPS SCRIPT 24/7)]\n━━━━━━━━━━━━━━━━━━━━━━\n🎬 STEP 1 - CÀO VIDEO:\n▪️ /step 1 start\n   👉 Chạy tiến trình cào mặc định (từng Grade từ ngày nhỏ -> lớn)\n▪️ /step 1 XX\n   👉 Cào bài học chưa có của Grade XX (Ví dụ: /step 1 05)\n▪️ /step 1 XX.yyy\n   👉 Cào bài học cụ thể (Ví dụ: /step 1 01.010 - Bỏ qua bài đã có)\n▪️ /step 1 force XX.yyy\n   👉 Cào ép buộc bài cụ thể (Ví dụ: /step 1 force K4.150 - Ghi đè file)\n\n📝 STEP 3 - ĐỒNG BỘ GIT & GOOGLE DOC:\n▪️ /step 3\n   👉 Chạy đồng bộ log & Git commit/push\n\n🎙️ STEP 4 - TẠO PHỤ ĐỀ AI WHISPER:\n▪️ /step 4\n   👉 Khởi chạy tạo phụ đề AI & file JSON tương tác\n\n📂 STEP 5 - COPY GDRIVE FOLDER:\n▪️ /step 5 start\n   👉 Chạy tiếp copy thư mục dở dang (Không tải lại file đã có)\n▪️ /step 5 link1-link2 (hoặc /step 5 link1 link2)\n   👉 Copy từ link1 (hoặc ID1) sang link2 (hoặc ID2)\n\n📊 STEP 6 - SO SÁNH & ĐỐI CHIẾU:\n▪️ /step 6\n   👉 Báo cáo đối chiếu dữ liệu 2 thư mục GDrive mặc định\n▪️ /step 6 link1-link2 (hoặc /step 6 link1 link2)\n   👉 So sánh đối chiếu giữa link1 (hoặc ID1) và link2 (hoặc ID2)\n\n⚡ KIỂM TRA HỆ THỐNG:\n▪️ /status\n   👉 Kiểm tra trạng thái các tiến trình Cloud đang chạy\n\nℹ️ Gõ /help bất kỳ lúc nào để hiển thị danh sách me.`;
  sendTelegramReply(helpMsg, chatId, threadId);
}

/**
 * Helpers
 */
function sendTelegramReply(text, chatId, threadId) {
  const url = `https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/sendMessage`;
  const payload = {
    chat_id: chatId || TARGET_CHAT_ID,
    text: text,
    message_thread_id: threadId || TARGET_THREAD_ID
  };
  try {
    UrlFetchApp.fetch(url, {
      method: "post",
      contentType: "application/x-www-form-encoding",
      payload: payload,
      muteHttpExceptions: true
    });
  } catch (e) {
    Logger.log("Send reply error: " + e);
  }
}

function getPAT() {
  const prop = PropertiesService.getScriptProperties().getProperty("GITHUB_PAT");
  return prop || GITHUB_PAT;
}

function normalizeGrade(val) {
  if (!val) return "Grade 1";
  const str = String(val).trim().toUpperCase();
  const mapping = {
    "01": "Grade 1", "1": "Grade 1", "G1": "Grade 1", "GRADE 1": "Grade 1", "GRADE1": "Grade 1",
    "02": "Grade 2", "2": "Grade 2", "G2": "Grade 2", "GRADE 2": "Grade 2", "GRADE2": "Grade 2",
    "03": "Grade 3", "3": "Grade 3", "G3": "Grade 3", "GRADE 3": "Grade 3", "GRADE3": "Grade 3",
    "04": "Grade 4", "4": "Grade 4", "G4": "Grade 4", "GRADE 4": "Grade 4", "GRADE4": "Grade 4",
    "05": "Grade 5", "5": "Grade 5", "G5": "Grade 5", "GRADE 5": "Grade 5", "GRADE5": "Grade 5",
    "06": "Grade 6", "6": "Grade 6", "G6": "Grade 6", "GRADE 6": "Grade 6", "GRADE6": "Grade 6",
    "07": "Grade 7", "7": "Grade 7", "G7": "Grade 7", "GRADE 7": "Grade 7", "GRADE7": "Grade 7",
    "08": "Grade 8", "8": "Grade 8", "G8": "Grade 8", "GRADE 8": "Grade 8", "GRADE8": "Grade 8",
    "09": "Grade 9", "9": "Grade 9", "G9": "Grade 9", "GRADE 9": "Grade 9", "GRADE9": "Grade 9",
    "10": "Grade 10", "G10": "Grade 10", "GRADE 10": "Grade 10", "GRADE10": "Grade 10",
    "11": "Grade 11", "G11": "Grade 11", "GRADE 11": "Grade 11", "GRADE11": "Grade 11",
    "12": "Grade 12", "G12": "Grade 12", "GRADE 12": "Grade 12", "GRADE12": "Grade 12",
    "K4": "K4", "K4.": "K4", "K5": "K5", "K5.": "K5"
  };
  return mapping[str] || str;
}

function getVNNowString() {
  return Utilities.formatDate(new Date(), "GMT+7", "yyyy-MM-dd HH:mm:ss");
}
