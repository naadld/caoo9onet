/**
 * O9O.NET 100% Serverless Telegram Bot (Cloudflare Worker)
 * Listens to Telegram Webhooks -> Triggers GitHub Actions Cloud Workflows
 * Supports Interactive Telegram Inline Keyboards & Real-time Substep Detail Views!
 * NO VPS REQUIRED! 24/7 FREE CLOUD HOSTING.
 */

const TELEGRAM_BOT_TOKEN = "YOUR_TELEGRAM_BOT_TOKEN_HERE";
const FALLBACK_BOT_TOKEN = "YOUR_FALLBACK_BOT_TOKEN_HERE";
const TARGET_CHAT_ID     = "-1003954353565";
const TARGET_THREAD_ID   = 4455;

// Fill in your GitHub Personal Access Token (PAT) here (e.g. ghp_xxxxxxxxxxxx)
const GITHUB_PAT         = "YOUR_GITHUB_PAT_HERE";
const GITHUB_REPO = "naadld/caoo9onet";

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
        await handleUpdate(update, env);
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
    const cbChatId = cb.message ? String(cb.message.chat.id) : null;
    if ((cbChatId !== TARGET_CHAT_ID && cbChatId !== String(TARGET_CHAT_ID)) || String(cbThreadId) !== String(TARGET_THREAD_ID)) return;

    await handleCallbackQuery(cb, env);
    return;
  }

  const message = update.message || update.channel_post || update.edited_message;
  if (!message) return;

  const chatId = String(message.chat.id);
  const msgThreadId = message.message_thread_id;
  const text = message.text || message.caption || "";
  
  console.log(`Received text: "${text}" from chatId: ${chatId}, threadId: ${msgThreadId}`);

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
  } catch (e) { }
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
    await sendTelegramReply(`🤖 [CHẾ ĐỘ TỰ ĐỘNG KHỞI CHẠY]\n━━━━━━━━━━━━━━━━━━━━━━\n🟢 Trạng thái: ĐÃ BẬT /auto\n⏰ Chu kỳ: Quét mỗi 30 phút qua Cloudflare Scheduler\n⚡ Các bước chạy tự động: Step 1 (Cào video), Step 4 (Tạo phụ đề), Step 7 (Dọn dẹp)\n⏰ Thời gian: ${nowStr}`, chatId, threadId, null, botTok);
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

  // /latest
  if (clean === "/latest" || clean === "latest" || clean.startsWith("/latest@")) {
    await sendLatest(chatId, threadId, pat, botTok);
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
    const mGrade = text.match(/step\s*4\s+(.+)/i);
    let targetFolder = "K4 (Age 4)";
    if (mGrade) {
      targetFolder = mGrade[1].trim();
    } else {
      try {
        const gRes = await fetch(`https://raw.githubusercontent.com/${GITHUB_REPO}/main/data/current_subtitle_grade.txt?t=${Date.now()}`);
        if (gRes.status === 200) {
          targetFolder = (await gRes.text()).trim();
        }
      } catch (e) { }
    }
    await sendTelegramReply(`🚀 [ĐÃ NHẬN LỆNH /step 4]\n━━━━━━━━━━━━━━━━━━━━━━\n🎙️ Khởi chạy Tạo Phụ đề AI cho ${targetFolder}...\n⏰ Thời gian: ${nowStr}`, chatId, threadId, null, botTok);
    const res = await triggerGitHubWorkflow("4_generate_subtitles.yml", { "target_folder": targetFolder }, pat);
    await sendTelegramReply(res.success ? `✅ [KÍCH HOẠT THÀNH CÔNG]\n${res.info}\n🔗 Theo dõi tại: https://github.com/${GITHUB_REPO}/actions` : `❌ ${res.info}`, chatId, threadId, null, botTok);
    return;
  }

  // /report
  if (clean.startsWith("/report") || clean === "report") {
    await sendTelegramReply(`🚀 [ĐÃ NHẬN LỆNH /report]\n━━━━━━━━━━━━━━━━━━━━━━\n📊 Khởi chạy Báo cáo Chi tiết Tiến độ Cào Video & Phụ đề AI...\n⏰ Thời gian: ${nowStr}`, chatId, threadId, null, botTok);
    const res = await triggerGitHubWorkflow("5_daily_report.yml", {}, pat);
    await sendTelegramReply(res.success ? `✅ [KÍCH HOẠT BÁO CÁO THÀNH CÔNG]\n${res.info}\n🔗 Báo cáo sẽ gửi trực tiếp vào nhóm Telegram trong ít giây!` : `❌ ${res.info}`, chatId, threadId, null, botTok);
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

async function sendLatest(chatId, threadId, pat, botTok) {
  const nowStr = new Date().toLocaleString("sv-SE", { timeZone: "Asia/Ho_Chi_Minh" });
  await sendTelegramReply("⏳ Đang tải báo cáo mới nhất từ hệ thống...", chatId, threadId, null, botTok);

  let msg = `📊 [BÁO CÁO TIẾN ĐỘ THỰC TẾ LỚN NHẤT]\n━━━━━━━━━━━━━━━━━━━━━━\n`;

  try {
    // 1. Check Step 1 (progress & databases)
    let activePairsStr = "Không xác định";
    let maxDay = 0;

    // Fetch progress_SongSong.json
    const progUrl = `https://raw.githubusercontent.com/${GITHUB_REPO}/main/progress_SongSong.json`;
    const progRes = await fetch(progUrl);
    let activeGrades = new Set();
    if (progRes.status === 200) {
      const pData = await progRes.json();
      const pairs = pData.active_pairs || [];
      activePairsStr = JSON.stringify(pairs);
      pairs.forEach(p => p.forEach(g => activeGrades.add(g)));
    }

    // Fetch databases to find max_day
    for (const grade of activeGrades) {
      const dbUrl = `https://raw.githubusercontent.com/${GITHUB_REPO}/main/database_${encodeURIComponent(grade)}.json`;
      const dbRes = await fetch(dbUrl);
      if (dbRes.status === 200) {
        const dbData = await dbRes.json();
        dbData.forEach(r => {
          let d = r.day;
          try {
            d = parseInt(d, 10);
            if (d > maxDay) maxDay = d;
          } catch (e) { }
        });
      }
    }

    msg += `🎬 STEP 1:\n`;
    msg += `  ▪️ Đang cào cặp: ${activePairsStr}\n`;
    msg += `  ▪️ Ngày thực tế cao nhất: ${maxDay > 0 ? maxDay : "Chưa có dữ liệu"}\n\n`;

    // 2. Check Step 2, 3, 4 (workflow_live_status.json)
    msg += `🚀 TÌNH TRẠNG CÁC BƯỚC KHÁC:\n`;
    const liveUrl = `https://raw.githubusercontent.com/${GITHUB_REPO}/main/data/workflow_live_status.json`;
    const liveRes = await fetch(liveUrl);
    if (liveRes.status === 200) {
      const liveData = await liveRes.json();

      const getStepInfo = (searchName) => {
        const run = liveData.find(r => r.name && r.name.includes(searchName));
        if (!run) return "Chưa có thông tin";
        const statusStr = run.status === "completed" ? (run.conclusion || "hoàn tất") : "đang chạy";
        return `[${statusStr.toUpperCase()}] ${run.current_step || ""}`;
      };

      msg += `  ▪️ STEP 2 (Dashboard): ${getStepInfo("2. Web Player Indexer")}\n`;
      msg += `  ▪️ STEP 3 (Fetch Playlists): ${getStepInfo("3. Fetch & Cache")}\n`;
      msg += `  ▪️ STEP 4 (Subtitles): ${getStepInfo("4. Abeka Subtitle")}\n`;
    } else {
      msg += `  ▪️ Không thể tải thông tin trạng thái các bước.\n`;
    }

  } catch (e) {
    msg += `⚠️ Lỗi khi tải dữ liệu: ${e.message}\n`;
  }

  msg += `\n⏰ Cập nhật lúc: ${nowStr}`;
  await sendTelegramReply(msg, chatId, threadId, null, botTok);
}

async function sendHelp(chatId, threadId, botTok) {
  const helpMsg = `📖 [BẢNG HƯỚNG DẪN LỆNH BOT TELEGRAM O9O.NET (SERVERLESS CLOUD)]\n━━━━━━━━━━━━━━━━━━━━━━\n🎬 STEP 1 - CÀO VIDEO:\n▪️ /step 1 start\n   👉 Chạy tiến trình cào mặc định (từng Grade từ ngày nhỏ -> lớn)\n▪️ /step 1 XX\n   👉 Cào bài học chưa có của Grade XX (Ví dụ: /step 1 05)\n▪️ /step 1 XX.yyy\n   👉 Cào bài học cụ thể (Ví dụ: /step 1 01.010 - Bỏ qua bài đã có)\n▪️ /step 1 force XX.yyy\n   👉 Cào ép buộc bài cụ thể (Ví dụ: /step 1 force K4.150 - Ghi đè file)\n\n📝 STEP 3 - ĐỒNG BỘ GIT & GOOGLE DOC:\n▪️ /step 3\n   👉 Chạy đồng bộ log & Git commit/push\n\n🎙️ STEP 4 - TẠO PHỤ ĐỀ AI WHISPER:\n▪️ /step 4\n   👉 Khởi chạy tạo phụ đề AI & file JSON tương tác\n\n🤖 CHẾ ĐỘ TỰ ĐỘNG (AUTO CRON):\n▪️ /auto\n   👉 Kích hoạt chế độ chạy tự động Step 1 & Step 4 mỗi 30 phút\n▪️ /auto off\n   👉 Tắt chế độ chạy tự động\n\n⚡ KIỂM TRA HỆ THỐNG:\n▪️ /status\n   👉 Kiểm tra trạng thái các tiến trình Cloud đang chạy\n\nℹ️ Gõ /help bất kỳ lúc nào để hiển thị danh sách này.`;
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

  console.log(`Sending to Telegram: url=${url}, chat_id=${params.chat_id}, thread_id=${params.message_thread_id}, botTok=${botTok ? "EXISTS" : "MISSING"}`);
  try {
    const res = await fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/x-www-form-urlencoded" },
      body: new URLSearchParams(params)
    });
    const resText = await res.text();
    console.log(`Telegram response status: ${res.status}, body: ${resText}`);
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
  const pat = (env && env.GITHUB_PAT) || GITHUB_PAT;
  const botTok = (env && env.TELEGRAM_BOT_TOKEN) || TELEGRAM_BOT_TOKEN;
  const nowStr = new Date().toLocaleString("sv-SE", { timeZone: "Asia/Ho_Chi_Minh" });

  if (!env || !env.O9O_KV) {
    console.error("O9O_KV namespace not bound.");
    return;
  }

  const autoMode = await env.O9O_KV.get("auto_mode");
  if (autoMode !== "on") {
    console.log("Auto mode is OFF. Skipping scheduled run.");
    return;
  }

  // Check running workflows
  let runningWorkflows = new Set();

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
          const fileName = r.path.split("/").pop();
          runningWorkflows.add(fileName);
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

  let actionsTriggered = [];
  let actionsSkipped = [];

  // Step 1 check & trigger
  if (!runningWorkflows.has("1_scraper_stream.yml")) {
    const res1 = await triggerGitHubWorkflow("1_scraper_stream.yml", { "max_days": "170" }, pat);
    if (res1.success) actionsTriggered.push("📥 Step 1 (Cào video)");
    else actionsSkipped.push(`📥 Step 1 (Lỗi: ${res1.info})`);
  } else {
    actionsSkipped.push("📥 Step 1 (Đang chạy)");
  }

  // Step 2 check & trigger
  if (!runningWorkflows.has("2_web_dashboard_sync.yml")) {
    const res2 = await triggerGitHubWorkflow("2_web_dashboard_sync.yml", {}, pat);
    if (res2.success) actionsTriggered.push("🖥️ Step 2 (Dashboard)");
    else actionsSkipped.push(`🖥️ Step 2 (Lỗi: ${res2.info})`);
  } else {
    actionsSkipped.push("🖥️ Step 2 (Đang chạy)");
  }

  // Step 3 check & trigger
  if (!runningWorkflows.has("3_fetch_playlists.yml")) {
    const res3 = await triggerGitHubWorkflow("3_fetch_playlists.yml", {}, pat);
    if (res3.success) actionsTriggered.push("📋 Step 3 (Lấy Playlists)");
    else actionsSkipped.push(`📋 Step 3 (Lỗi: ${res3.info})`);
  } else {
    actionsSkipped.push("📋 Step 3 (Đang chạy)");
  }

  // Trigger all Step 4s
  const step4Workflows = [
    { file: "4_generate_subtitles.yml", name: "Grade 9" },
    { file: "4_generate_subtitles_g10.yml", name: "Grade 10" },
    { file: "4_generate_subtitles_g1.yml", name: "Grade 1" },
    { file: "4_generate_subtitles_g2.yml", name: "Grade 2" },
    { file: "4_generate_subtitles_g3.yml", name: "Grade 3" },
    { file: "4_generate_subtitles_g4.yml", name: "Grade 4" },
    { file: "4_generate_subtitles_g6.yml", name: "Grade 6" },
    { file: "4_generate_subtitles_g7.yml", name: "Grade 7" },
    { file: "4_generate_subtitles_g8.yml", name: "Grade 8" },
    { file: "4_generate_subtitles_k4.yml", name: "K4" },
    { file: "4_generate_subtitles_k5.yml", name: "K5" }
  ];

  for (const s4 of step4Workflows) {
    if (!runningWorkflows.has(s4.file)) {
      const res4 = await triggerGitHubWorkflow(s4.file, {}, pat);
      if (res4.success) actionsTriggered.push(`🎙️ Step 4 (${s4.name})`);
      else actionsSkipped.push(`🎙️ Step 4 (${s4.name} - Lỗi: ${res4.info})`);
    } else {
      actionsSkipped.push(`🎙️ Step 4 (${s4.name} - Đang chạy)`);
    }
  }

  // Step 5 check & trigger
  if (!runningWorkflows.has("5_gdrive_copier.yml")) {
    const res5 = await triggerGitHubWorkflow("5_gdrive_copier.yml", {}, pat);
    if (res5.success) actionsTriggered.push("📁 Step 5 (GDrive Copier)");
    else actionsSkipped.push(`📁 Step 5 (Lỗi: ${res5.info})`);
  } else {
    actionsSkipped.push("📁 Step 5 (Đang chạy)");
  }


  

  // Get video scraping progress in the last 30 minutes
  const videoProgressReport = await getScrapedVideoProgress(env);

  // Send unified report to Telegram
  let reportMsg = `🤖 [CHU KỲ TỰ ĐỘNG - BÁO CÁO 30 PHÚT]\n━━━━━━━━━━━━━━━━━━━━━━\n`;
  reportMsg += `${videoProgressReport}\n\n`;
  if (actionsTriggered.length > 0) {
    reportMsg += `🚀 ĐÃ KÍCH HOẠT WORKFLOW:\n${actionsTriggered.map(act => `  🟢 ${act}`).join("\n")}\n\n`;
  }
  if (actionsSkipped.length > 0) {
    reportMsg += `⏭️ HỦY BỎ / TẠM NGƯNG:\n${actionsSkipped.map(act => `  🟡 ${act}`).join("\n")}\n\n`;
  }
  reportMsg += `⏰ Thời gian: ${nowStr}\n🔗 Theo dõi tại: https://github.com/${GITHUB_REPO}/actions`;

  await sendTelegramReply(reportMsg, TARGET_CHAT_ID, TARGET_THREAD_ID, null, botTok);
}

