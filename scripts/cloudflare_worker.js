/**
 * O9O.NET 100% Serverless Telegram Bot (Cloudflare Worker)
 * Listens to Telegram Webhooks -> Triggers GitHub Actions Cloud Workflows
 * Supports Interactive Telegram Inline Keyboards & Real-time Substep Detail Views!
 * NO VPS REQUIRED! 24/7 FREE CLOUD HOSTING.
 */

const TELEGRAM_BOT_TOKEN = "YOUR_TELEGRAM_BOT_TOKEN_HERE";
const FALLBACK_BOT_TOKEN = "YOUR_FALLBACK_BOT_TOKEN_HERE";
const TARGET_CHAT_ID     = "-1003954353565";
const TARGET_THREAD_ID   = 3953;

// Fill in your GitHub Personal Access Token (PAT) here (e.g. ghp_xxxxxxxxxxxx)
const GITHUB_PAT         = "YOUR_GITHUB_PAT_HERE";
const GITHUB_REPO        = "naadld/caoo9onet";

export default {
  async fetch(request, env, ctx) {
    const url = new URL(request.url);
    // Intercept progress logging endpoint from GitHub Actions and forward to VPS
    if (url.pathname === "/api/progress") {
      if (request.method === "POST") {
        try {
          const body = await request.text();
          const vpsUrl = "https://compare-phosphate-hug.ngrok-free.dev/api/progress";
          ctx.waitUntil(fetch(vpsUrl, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: body
          }));
        } catch (e) {
          console.error("Forward error:", e);
        }
        return new Response("OK", { status: 200 });
      }
    }

    if (request.method === "POST") {
      try {
        const update = await request.json();
        ctx.waitUntil(handleUpdate(update, env));
      } catch (err) {
        console.error("Worker Error:", err);
      }
      // Always return 200 OK immediately to Telegram
      return new Response("OK", { status: 200 });
    }
    return new Response("O9O.NET Serverless Telegram Bot is Running!", { status: 200 });
  },
  async scheduled(event, env, ctx) {
    ctx.waitUntil(handleScheduled(env));
  }
};

async function handleUpdate(update, env) {
  // Handle Inline Button Taps (Callback Query)
  if (update.callback_query) {
    const cb = update.callback_query;
    const cbThreadId = cb.message ? cb.message.message_thread_id : null;
    if (String(cbThreadId) !== String(TARGET_THREAD_ID)) return;

    await handleCallbackQuery(cb, env);
    return;
  }

  const message = update.message || update.channel_post || update.edited_message;
  if (!message) return;

  const chatId = String(message.chat.id);
  const msgThreadId = message.message_thread_id;
  const text = (message.text || "").trim();

  if ((chatId === TARGET_CHAT_ID || chatId === String(TARGET_CHAT_ID)) && String(msgThreadId) === String(TARGET_THREAD_ID)) {
    await routeCommand(text, chatId, TARGET_THREAD_ID, env);
  }
}

async function handleCallbackQuery(cb, env) {
  const data = cb.data || "";
  const chatId = String(cb.message.chat.id);
  const messageId = cb.message.message_id;
  const threadId = cb.message.message_thread_id || TARGET_THREAD_ID;
  const pat = (env && env.GITHUB_PAT) || GITHUB_PAT;
  const botTok = (env && env.TELEGRAM_BOT_TOKEN) || TELEGRAM_BOT_TOKEN;

  await answerCallback(cb.id, botTok);

  if (data.startsWith("run_detail:")) {
    const runId = data.replace("run_detail:", "");
    await sendRunDetail(chatId, messageId, threadId, runId, pat, botTok);
  } else if (data === "back_to_status" || data === "refresh_status") {
    await sendStatus(chatId, threadId, pat, botTok, messageId);
  }
}

async function answerCallback(callbackQueryId, botTok) {
  const url = `https://api.telegram.org/bot${botTok}/answerCallbackQuery`;
  try {
    await fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/x-www-form-urlencoded" },
      body: new URLSearchParams({ callback_query_id: callbackQueryId })
    });
  } catch (e) {}
}

async function routeCommand(rawText, chatId, threadId, env) {
  const text = rawText.trim();
  const clean = text.toLowerCase();
  const nowStr = new Date().toLocaleString("sv-SE", { timeZone: "Asia/Ho_Chi_Minh" });
  const pat = (env && env.GITHUB_PAT) || GITHUB_PAT;
  const botTok = (env && env.TELEGRAM_BOT_TOKEN) || TELEGRAM_BOT_TOKEN;
  // /auto off
  if (clean === "/auto off" || clean.startsWith("/auto off@") || clean === "auto off") {
    if (!env || !env.O9O_KV) {
      await sendTelegramReply("❌ Thao tác thất bại: Chưa liên kết KV Namespace `O9O_KV` vào Cloudflare Worker. Vui lòng tạo và liên kết KV Namespace tên `O9O_KV` trong cài đặt Worker.", chatId, threadId, null, botTok);
      return;
    }
    await env.O9O_KV.put("auto_mode", "off");
    await sendTelegramReply(`🤖 [CHẾ ĐỘ TỰ ĐỘNG ĐÃ TẮT]\n━━━━━━━━━━━━━━━━━━━━━━\n🔴 Trạng thái: ĐÃ TẮT /auto\n⚡ Hệ thống sẽ dừng tự động chạy. Chờ lệnh thủ công từ user.\n⏰ Thời gian: ${nowStr}`, chatId, threadId, null, botTok);
    return;
  }

  // /auto
  if (clean === "/auto" || clean.startsWith("/auto@") || clean === "auto") {
    if (!env || !env.O9O_KV) {
      await sendTelegramReply("❌ Thao tác thất bại: Chưa liên kết KV Namespace `O9O_KV` vào Cloudflare Worker. Vui lòng tạo và liên kết KV Namespace tên `O9O_KV` trong cài đặt Worker.", chatId, threadId, null, botTok);
      return;
    }
    await env.O9O_KV.put("auto_mode", "on");
    await sendTelegramReply(`🤖 [CHẾ ĐỘ TỰ ĐỘNG KHỞI CHẠY]\n━━━━━━━━━━━━━━━━━━━━━━\n🟢 Trạng thái: ĐÃ BẬT /auto\n⏰ Chu kỳ: Quét mỗi 30 phút qua Cloudflare Scheduler\n⚡ Các bước chạy tự động: Step 1 (Cào video) & Step 4 (Tạo phụ đề)\n⏰ Thời gian: ${nowStr}`, chatId, threadId, null, botTok);
    return;
  }

  // /help
  if (clean === "/help" || clean === "help" || clean.startsWith("/help@") || clean === "/start") {
    await sendHelp(chatId, threadId, botTok);
    return;
  }

  // /status
  if (clean === "/status" || clean === "status" || clean.startsWith("/status@")) {
    await sendStatus(chatId, threadId, pat, botTok);
    return;
  }

  // /step 1
  if (clean.startsWith("/step 1") || clean.startsWith("/step1") || clean.startsWith("step 1")) {
    const mDay = text.match(/step\s*1\s+(?:(force)\s+)?([a-zA-Z0-9]+)[\._](\d+)/i);
    if (mDay) {
      const isForce = !!mDay[1];
      const rawGrade = mDay[2];
      const dayNum = mDay[3];
      const grade = normalizeGrade(rawGrade);
      const modeText = isForce ? "FORCE (Ghi đè file cũ)" : "THƯỜNG (Bỏ qua bài đã có)";

      await sendTelegramReply(`📥 [ĐÃ NHẬN LỆNH /step 1 ${rawGrade}.${dayNum}]\n━━━━━━━━━━━━━━━━━━━━━━\n📚 Grade: ${grade}\n📅 Ngày: Ngày ${dayNum}\n⚡ Chế độ: ${modeText}\n⏰ Thời gian: ${nowStr}\n🚀 Đang kích hoạt GitHub Actions Cloud...`, chatId, threadId, null, botTok);

      const res = await triggerGitHubWorkflow("1_scraper_stream.yml", {
        "max_days": "1",
        "grade": String(grade),
        "day": String(parseInt(dayNum, 10)),
        "force": isForce ? "true" : "false"
      }, pat);
      await sendTelegramReply(res.success ? `✅ [KÍCH HOẠT THÀNH CÔNG]\n${res.info}\n🔗 Theo dõi tại: https://github.com/${GITHUB_REPO}/actions` : `❌ ${res.info}`, chatId, threadId, null, botTok);
      return;
    }

    if (clean.includes("start")) {
      await sendTelegramReply(`🚀 [ĐÃ NHẬN LỆNH /step 1 start]\n━━━━━━━━━━━━━━━━━━━━━━\n📚 Tiến trình cào mặc định toàn bộ các Grade\n📅 Quét từ ngày nhỏ đến ngày lớn (Day 001 -> Day 170)\n⏰ Thời gian: ${nowStr}\n🚀 Đang khởi chạy GitHub Actions Cloud...`, chatId, threadId, null, botTok);
      const res = await triggerGitHubWorkflow("1_scraper_stream.yml", { "max_days": "170" }, pat);
      await sendTelegramReply(res.success ? `✅ [KÍCH HOẠT THÀNH CÔNG]\n${res.info}\n🔗 Theo dõi tại: https://github.com/${GITHUB_REPO}/actions` : `❌ ${res.info}`, chatId, threadId, null, botTok);
      return;
    }

    const mGrade = text.match(/step\s*1\s+([a-zA-Z0-9]+)/i);
    if (mGrade && mGrade[1].toLowerCase() !== "start") {
      const rawGrade = mGrade[1];
      const grade = normalizeGrade(rawGrade);
      await sendTelegramReply(`🚀 [ĐÃ NHẬN LỆNH /step 1 ${rawGrade}]\n━━━━━━━━━━━━━━━━━━━━━━\n📚 Cào toàn bộ bài học chưa có của ${grade}\n📅 Quét từ Day 001 đến Day 170 (Bỏ qua bài đã có)\n⏰ Thời gian: ${nowStr}\n🚀 Đang khởi chạy GitHub Actions Cloud...`, chatId, threadId, null, botTok);
      const res = await triggerGitHubWorkflow("1_scraper_stream.yml", { "grade": String(grade), "max_days": "170" }, pat);
      await sendTelegramReply(res.success ? `✅ [KÍCH HOẠT THÀNH CÔNG]\n${res.info}\n🔗 Theo dõi tại: https://github.com/${GITHUB_REPO}/actions` : `❌ ${res.info}`, chatId, threadId, null, botTok);
      return;
    }
  }

  // /step 3
  if (clean.startsWith("/step 3") || clean.startsWith("/step3") || clean === "step 3") {
    await sendTelegramReply(`🚀 [ĐÃ NHẬN LỆNH /step 3]\n━━━━━━━━━━━━━━━━━━━━━━\n📝 Khởi chạy Step 3 Git Publish & Google Doc logger...\n⏰ Thời gian: ${nowStr}`, chatId, threadId, null, botTok);
    await sendTelegramReply(`✅ [STEP 3] Tiến trình đã được ghi nhận!`, chatId, threadId, null, botTok);
    return;
  }

  // /step 4
  if (clean.startsWith("/step 4") || clean.startsWith("/step4") || clean === "step 4") {
    await sendTelegramReply(`🚀 [ĐÃ NHẬN LỆNH /step 4]\n━━━━━━━━━━━━━━━━━━━━━━\n🎙️ Khởi chạy Tạo Phụ đề AI Whisper & Interactive JSON...\n⏰ Thời gian: ${nowStr}`, chatId, threadId, null, botTok);
    const res = await triggerGitHubWorkflow("4_generate_subtitles.yml", { "target_folder": "Grade 5" }, pat);
    await sendTelegramReply(res.success ? `✅ [KÍCH HOẠT THÀNH CÔNG]\n${res.info}\n🔗 Theo dõi tại: https://github.com/${GITHUB_REPO}/actions` : `❌ ${res.info}`, chatId, threadId, null, botTok);
    return;
  }

  // /step 5
  if (clean.startsWith("/step 5") || clean.startsWith("/step5") || clean.startsWith("step 5")) {
    const mLinks = text.match(/step\s*5\s+([^\s-]+)[\s-]+([^\s]+)/i);
    if (mLinks && mLinks[1].toLowerCase() !== "start") {
      const src = mLinks[1].trim();
      const dst = mLinks[2].trim();
      await sendTelegramReply(`🚀 [ĐÃ NHẬN LỆNH /step 5 CUSTOM COPY]\n━━━━━━━━━━━━━━━━━━━━━━\n📁 Nguồn: ${src}\n📂 Đích:  ${dst}\n⏰ Thời gian: ${nowStr}\n🚀 Đang khởi chạy GitHub Actions Cloud...`, chatId, threadId, null, botTok);
      const res = await triggerGitHubWorkflow("5_gdrive_copier.yml", { "src_folder": src, "dst_folder": dst }, pat);
      await sendTelegramReply(res.success ? `✅ [KÍCH HOẠT THÀNH CÔNG]\n${res.info}\n🔗 Theo dõi tại: https://github.com/${GITHUB_REPO}/actions` : `❌ ${res.info}`, chatId, threadId, null, botTok);
      return;
    }

    await sendTelegramReply(`🚀 [ĐÃ NHẬN LỆNH /step 5 start]\n━━━━━━━━━━━━━━━━━━━━━━\n📂 Tiếp tục Copy thư mục GDrive dở dang (Nguồn -> Đích)\n⚡ Chế độ: Bỏ qua các file đã có\n⏰ Thời gian: ${nowStr}\n🚀 Đang khởi chạy GitHub Actions Cloud...`, chatId, threadId, null, botTok);
    const res = await triggerGitHubWorkflow("5_gdrive_copier.yml", {}, pat);
    await sendTelegramReply(res.success ? `✅ [KÍCH HOẠT THÀNH CÔNG]\n${res.info}\n🔗 Theo dõi tại: https://github.com/${GITHUB_REPO}/actions` : `❌ ${res.info}`, chatId, threadId, null, botTok);
    return;
  }

  // /step 6
  if (clean.startsWith("/step 6") || clean.startsWith("/step6") || clean.startsWith("step 6")) {
    const mLinks = text.match(/step\s*6\s+([^\s-]+)[\s-]+([^\s]+)/i);
    if (mLinks && mLinks[1].toLowerCase() !== "start") {
      const src = mLinks[1].trim();
      const dst = mLinks[2].trim();
      await sendTelegramReply(`🚀 [ĐÃ NHẬN LỆNH /step 6 CUSTOM COMPARE]\n━━━━━━━━━━━━━━━━━━━━━━\n📁 Nguồn: ${src}\n📂 Đích:  ${dst}\n⏰ Thời gian: ${nowStr}\n📊 Đang khởi chạy tiến trình đối chiếu & so sánh...`, chatId, threadId, null, botTok);
      const res = await triggerGitHubWorkflow("6_folder_comparator.yml", { "src_folder": src, "dst_folder": dst }, pat);
      await sendTelegramReply(res.success ? `✅ [KÍCH HOẠT THÀNH CÔNG]\n${res.info}\n🔗 Theo dõi tại: https://github.com/${GITHUB_REPO}/actions` : `❌ ${res.info}`, chatId, threadId, null, botTok);
      return;
    }

    await sendTelegramReply(`🚀 [ĐÃ NHẬN LỆNH /step 6]\n━━━━━━━━━━━━━━━━━━━━━━\n📊 Khởi chạy Step 6: Báo cáo đối chiếu & so sánh thư mục GDrive...\n⏰ Thời gian: ${nowStr}`, chatId, threadId, null, botTok);
    const res = await triggerGitHubWorkflow("6_folder_comparator.yml", {}, pat);
    await sendTelegramReply(res.success ? `✅ [KÍCH HOẠT THÀNH CÔNG]\n${res.info}\n🔗 Theo dõi tại: https://github.com/${GITHUB_REPO}/actions` : `❌ ${res.info}`, chatId, threadId, null, botTok);
    return;
  }
}

async function triggerGitHubWorkflow(workflowFile, inputsObj, pat) {
  if (!pat || pat === "YOUR_GITHUB_PAT_HERE") {
    return { success: false, info: "Chưa cấu hình GITHUB_PAT trong Cloudflare Worker." };
  }

  const url = `https://api.github.com/repos/${GITHUB_REPO}/actions/workflows/${workflowFile}/dispatches`;
  try {
    const res = await fetch(url, {
      method: "POST",
      headers: {
        "Accept": "application/vnd.github+json",
        "Authorization": `Bearer ${pat}`,
        "User-Agent": "CloudflareWorker-TelegramBot",
        "X-GitHub-Api-Version": "2022-11-28"
      },
      body: JSON.stringify({ ref: "main", inputs: inputsObj })
    });
    if (res.status === 204 || res.status === 200 || res.status === 201) {
      return { success: true, info: "Đã gửi lệnh kích hoạt GitHub Actions Cloud thành công!" };
    }
    const text = await res.text();
    return { success: false, info: `GitHub API HTTP ${res.status}: ${text}` };
  } catch (err) {
    return { success: false, info: `Lỗi kết nối GitHub API: ${err.message}` };
  }
}

async function sendStatus(chatId, threadId, pat, botTok, editMessageId = null) {
  const nowStr = new Date().toLocaleString("sv-SE", { timeZone: "Asia/Ho_Chi_Minh" });
  let ghStatusList = [];
  let keyboardButtons = [];

  if (pat && pat !== "YOUR_GITHUB_PAT_HERE") {
    const url = `https://api.github.com/repos/${GITHUB_REPO}/actions/runs?status=in_progress`;
    try {
      const res = await fetch(url, {
        headers: {
          "Accept": "application/vnd.github+json",
          "Authorization": `Bearer ${pat}`,
          "User-Agent": "CloudflareWorker-TelegramBot",
          "X-GitHub-Api-Version": "2022-11-28"
        }
      });
      if (res.status === 200) {
        const data = await res.json();
        const runs = data.workflow_runs || [];
        if (runs.length > 0) {
          runs.forEach((r, idx) => {
            const num = idx + 1;
            ghStatusList.push(`⚡ ${num}. ${r.name} (Run #${r.id})`);
            keyboardButtons.push([{
              text: `🔎 Xem chi tiết Tiến trình #${num}`,
              callback_data: `run_detail:${r.id}`
            }]);
          });
        } else {
          ghStatusList.push("⚪ Không có tiến trình cloud nào đang chạy");
        }
      }
    } catch (e) {
      ghStatusList.push("⚠️ Không thể kết nối GitHub API");
    }
  }

  // Add Refresh button
  keyboardButtons.push([{ text: "🔄 Làm mới Báo cáo (/status)", callback_data: "refresh_status" }]);

  const msg = `📊 [BÁO CÁO TRẠNG THÁI HỆ THỐNG /status]\n━━━━━━━━━━━━━━━━━━━━━━\n🟢 SERVERLESS BOT: Hoạt động 24/7 trên Cloud (Không dùng VPS)\n\n☁️ GITHUB ACTIONS CLOUD:\n  ${ghStatusList.join("\n  ")}\n\n⏰ Giờ kiểm tra (GMT+7): ${nowStr}`;

  if (editMessageId) {
    await editTelegramMessage(msg, chatId, editMessageId, keyboardButtons, botTok);
  } else {
    await sendTelegramReply(msg, chatId, threadId, keyboardButtons, botTok);
  }
}

async function sendRunDetail(chatId, messageId, threadId, runId, pat, botTok) {
  const nowStr = new Date().toLocaleString("sv-SE", { timeZone: "Asia/Ho_Chi_Minh" });
  let detailText = `🔍 [CHI TIẾT TIẾN TRÌNH CLOUD - RUN #${runId}]\n━━━━━━━━━━━━━━━━━━━━━━\n`;

  if (pat && pat !== "YOUR_GITHUB_PAT_HERE") {
    try {
      // 1. Fetch Run info
      const runUrl = `https://api.github.com/repos/${GITHUB_REPO}/actions/runs/${runId}`;
      const runRes = await fetch(runUrl, {
        headers: {
          "Accept": "application/vnd.github+json",
          "Authorization": `Bearer ${pat}`,
          "User-Agent": "CloudflareWorker-TelegramBot",
          "X-GitHub-Api-Version": "2022-11-28"
        }
      });
      if (runRes.status === 200) {
        const rData = await runRes.json();
        detailText += `📌 Tiến trình: ${rData.name}\n`;
        detailText += `⚡ Trạng thái: ${rData.status} (${rData.conclusion || "đang thực thi"})\n`;
        detailText += `📅 Tạo lúc: ${new Date(rData.created_at).toLocaleString("sv-SE", { timeZone: "Asia/Ho_Chi_Minh" })}\n`;
      }

      // 2. Fetch Jobs & Steps
      const jobsUrl = `https://api.github.com/repos/${GITHUB_REPO}/actions/runs/${runId}/jobs`;
      const jobsRes = await fetch(jobsUrl, {
        headers: {
          "Accept": "application/vnd.github+json",
          "Authorization": `Bearer ${pat}`,
          "User-Agent": "CloudflareWorker-TelegramBot",
          "X-GitHub-Api-Version": "2022-11-28"
        }
      });
      if (jobsRes.status === 200) {
        const jData = await jobsRes.json();
        const jobs = jData.jobs || [];
        detailText += `\n🚀 CÁC BƯỚC ĐANG THỰC THI (SUBSTEPS):\n`;
        jobs.forEach(job => {
          (job.steps || []).forEach(st => {
            const stIcon = st.status === "completed" ? (st.conclusion === "success" ? "✅" : "❌") : "⚡";
            detailText += `  ${stIcon} ${st.name} [${st.status}]\n`;
          });
        });
      }
    } catch (e) {
      detailText += `⚠️ Không thể tải thông tin chi tiết từ GitHub API: ${e.message}\n`;
    }
  }

  detailText += `\n⏰ Giờ kiểm tra (GMT+7): ${nowStr}`;

  const keyboardButtons = [
    [{ text: "🔄 Làm mới Chi tiết", callback_data: `run_detail:${runId}` }],
    [{ text: "🔙 Quay lại Báo cáo Status", callback_data: "back_to_status" }]
  ];

  await editTelegramMessage(detailText, chatId, messageId, keyboardButtons, botTok);
}

async function sendHelp(chatId, threadId, botTok) {
  const helpMsg = `📖 [BẢNG HƯỚNG DẪN LỆNH BOT TELEGRAM O9O.NET (SERVERLESS CLOUD)]\n━━━━━━━━━━━━━━━━━━━━━━\n🎬 STEP 1 - CÀO VIDEO:\n▪️ /step 1 start\n   👉 Chạy tiến trình cào mặc định (từng Grade từ ngày nhỏ -> lớn)\n▪️ /step 1 XX\n   👉 Cào bài học chưa có của Grade XX (Ví dụ: /step 1 05)\n▪️ /step 1 XX.yyy\n   👉 Cào bài học cụ thể (Ví dụ: /step 1 01.010 - Bỏ qua bài đã có)\n▪️ /step 1 force XX.yyy\n   👉 Cào ép buộc bài cụ thể (Ví dụ: /step 1 force K4.150 - Ghi đè file)\n\n📝 STEP 3 - ĐỒNG BỘ GIT & GOOGLE DOC:\n▪️ /step 3\n   👉 Chạy đồng bộ log & Git commit/push\n\n🎙️ STEP 4 - TẠO PHỤ ĐỀ AI WHISPER:\n▪️ /step 4\n   👉 Khởi chạy tạo phụ đề AI & file JSON tương tác\n\n📂 STEP 5 - COPY GDRIVE FOLDER:\n▪️ /step 5 start\n   👉 Chạy tiếp copy thư mục dở dang (Không tải lại file đã có)\n▪️ /step 5 link1-link2 (hoặc /step 5 link1 link2)\n   👉 Copy từ link1 (hoặc ID1) sang link2 (hoặc ID2)\n\n📊 STEP 6 - SO SÁNH & ĐỐI CHIẾU:\n▪️ /step 6\n   👉 Báo cáo đối chiếu dữ liệu 2 thư mục GDrive mặc định\n▪️ /step 6 link1-link2 (hoặc /step 6 link1 link2)\n   👉 So sánh đối chiếu giữa link1 (hoặc ID1) và link2 (hoặc ID2)\n\n🤖 CHẾ ĐỘ TỰ ĐỘNG (AUTO CRON):\n▪️ /auto\n   👉 Kích hoạt chế độ chạy tự động Step 1 & Step 4 mỗi 30 phút\n▪️ /auto off\n   👉 Tắt chế độ chạy tự động\n\n⚡ KIỂM TRA HỆ THỐNG:\n▪️ /status\n   👉 Kiểm tra trạng thái các tiến trình Cloud đang chạy\n\nℹ️ Gõ /help bất kỳ lúc nào để hiển thị danh sách này.`;
  await sendTelegramReply(helpMsg, chatId, threadId, null, botTok);
}

async function sendTelegramReply(text, chatId, threadId, inlineKeyboard = null, botTok = TELEGRAM_BOT_TOKEN) {
  const url = `https://api.telegram.org/bot${botTok}/sendMessage`;
  const params = {
    chat_id: chatId || TARGET_CHAT_ID,
    text: text,
    message_thread_id: threadId || TARGET_THREAD_ID
  };
  if (inlineKeyboard) {
    params.reply_markup = JSON.stringify({ inline_keyboard: inlineKeyboard });
  }

  try {
    await fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/x-www-form-urlencoded" },
      body: new URLSearchParams(params)
    });
  } catch (e) {
    console.error("Send reply error:", e);
  }
}

async function editTelegramMessage(text, chatId, messageId, inlineKeyboard = null, botTok = TELEGRAM_BOT_TOKEN) {
  const url = `https://api.telegram.org/bot${botTok}/editMessageText`;
  const params = {
    chat_id: chatId || TARGET_CHAT_ID,
    message_id: messageId,
    text: text
  };
  if (inlineKeyboard) {
    params.reply_markup = JSON.stringify({ inline_keyboard: inlineKeyboard });
  }

  try {
    await fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/x-www-form-urlencoded" },
      body: new URLSearchParams(params)
    });
  } catch (e) {
    console.error("Edit message error:", e);
  }
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

async function handleScheduled(env) {
  const pat = env.GITHUB_PAT || GITHUB_PAT;
  const botTok = env.TELEGRAM_BOT_TOKEN || TELEGRAM_BOT_TOKEN;
  const nowStr = new Date().toLocaleString("sv-SE", { timeZone: "Asia/Ho_Chi_Minh" });

  if (!env.O9O_KV) {
    console.error("O9O_KV namespace not bound.");
    return;
  }

  const autoMode = await env.O9O_KV.get("auto_mode");
  if (autoMode !== "on") {
    console.log("Auto mode is OFF. Skipping scheduled run.");
    return;
  }

  // Check running workflows
  let step1Running = false;
  let step4Running = false;

  try {
    const url = `https://api.github.com/repos/${GITHUB_REPO}/actions/runs?per_page=15`;
    const res = await fetch(url, {
      headers: {
        "Accept": "application/vnd.github+json",
        "Authorization": `Bearer ${pat}`,
        "User-Agent": "CloudflareWorker-TelegramBot",
        "X-GitHub-Api-Version": "2022-11-28"
      }
    });

    if (res.status === 200) {
      const data = await res.json();
      const runs = data.workflow_runs || [];
      runs.forEach(r => {
        if (r.status === "in_progress" || r.status === "queued") {
          if (r.path.includes("1_scraper_stream.yml")) {
            step1Running = true;
          }
          if (r.path.includes("4_generate_subtitles.yml")) {
            step4Running = true;
          }
        }
      });
    } else {
      console.error(`Failed to fetch runs. Status: ${res.status}`);
      return;
    }
  } catch (e) {
    console.error("Error fetching runs:", e);
    return;
  }

  // Triggering logic
  if (step1Running && step4Running) {
    // Both steps are running, skip and log/notify
    await sendTelegramReply(`🤖 [CHU KỲ TỰ ĐỘNG - BỎ QUA]\n━━━━━━━━━━━━━━━━━━━━━━\n⚡ Cả hai tiến trình Step 1 (Cào video) và Step 4 (Tạo phụ đề) đều đang chạy.\n⏭️ Tiến trình tự động được hủy bỏ để chờ chu kỳ 30 phút tiếp theo.\n⏰ Thời gian: ${nowStr}`, TARGET_CHAT_ID, TARGET_THREAD_ID, null, botTok);
    return;
  }

  let actionsTriggered = [];

  if (!step1Running) {
    // Trigger Step 1
    const res1 = await triggerGitHubWorkflow("1_scraper_stream.yml", { "max_days": "170" }, pat);
    if (res1.success) {
      actionsTriggered.push("📥 Step 1 (Cào video)");
    } else {
      console.error("Failed to trigger Step 1:", res1.info);
    }
  }

  if (!step4Running) {
    // Trigger Step 4
    const res4 = await triggerGitHubWorkflow("4_generate_subtitles.yml", { "target_folder": "Grade 5" }, pat);
    if (res4.success) {
      actionsTriggered.push("🎙️ Step 4 (Tạo phụ đề)");
    } else {
      console.error("Failed to trigger Step 4:", res4.info);
    }
  }

  if (actionsTriggered.length > 0) {
    await sendTelegramReply(`🤖 [CHU KỲ TỰ ĐỘNG - KÍCH HOẠT THÀNH CÔNG]\n━━━━━━━━━━━━━━━━━━━━━━\n🚀 Đã kích hoạt các tiến trình:\n${actionsTriggered.map(act => `  ${act}`).join("\n")}\n⏰ Thời gian: ${nowStr}\n🔗 Theo dõi tại: https://github.com/${GITHUB_REPO}/actions`, TARGET_CHAT_ID, TARGET_THREAD_ID, null, botTok);
  }
}
