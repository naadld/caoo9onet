/* ============================================================
   ABEKA KANBAN LIVE WORKFLOW DASHBOARD - JAVASCRIPT LOGIC
   ============================================================ */

let currentStatusData = null;
let autoRefreshInterval = null;
let activeLogTab = 'stream.log';

document.addEventListener('DOMContentLoaded', () => {
  fetchLiveData();
  startAutoRefresh();

  document.getElementById('refreshBtn')?.addEventListener('click', () => {
    fetchLiveData();
  });
});

function startAutoRefresh() {
  if (autoRefreshInterval) clearInterval(autoRefreshInterval);
  autoRefreshInterval = setInterval(() => {
    fetchLiveData();
  }, 5000); // 5s polling
}

async function fetchLiveData() {
  const statusElem = document.getElementById('lastUpdatedTime');
  try {
    const res = await fetch('data/workflow_live_status.json?t=' + Date.now());
    if (res.ok) {
      currentStatusData = await res.json();
      renderKanbanBoard(currentStatusData);
      if (statusElem) statusElem.innerText = currentStatusData.last_updated || 'Just now';
    }
  } catch (err) {
    console.error('Error fetching live workflow status:', err);
    if (statusElem) statusElem.innerText = 'Offline / Retrying...';
  }
}

function renderKanbanBoard(data) {
  const queuedCol = document.getElementById('cardsQueued');
  const progressCol = document.getElementById('cardsProgress');
  const completedCol = document.getElementById('cardsCompleted');
  const failedCol = document.getElementById('cardsFailed');

  if (!queuedCol || !progressCol || !completedCol || !failedCol) return;

  queuedCol.innerHTML = '';
  progressCol.innerHTML = '';
  completedCol.innerHTML = '';
  failedCol.innerHTML = '';

  let countQueued = 0;
  let countProgress = 0;
  let countCompleted = 0;
  let countFailed = 0;

  // 1. Sort & Render GitHub Action Runs into Kanban Columns
  const runs = data.github_runs || [];
  runs.forEach(run => {
    const card = createGitHubRunCard(run);

    if (run.status === 'in_progress') {
      progressCol.appendChild(card);
      countProgress++;
    } else if (run.status === 'pending' || run.status === 'queued') {
      queuedCol.appendChild(card);
      countQueued++;
    } else if (run.status === 'completed') {
      if (run.conclusion === 'success') {
        completedCol.appendChild(card);
        countCompleted++;
      } else {
        failedCol.appendChild(card);
        countFailed++;
      }
    }
  });

  // 2. Render Active Target Pairs into In Progress
  const activePairs = data.active_pairs || [];
  activePairs.forEach(pair => {
    const pairCard = document.createElement('div');
    pairCard.className = 'kanban-card';
    pairCard.style.borderLeft = '3px solid var(--accent-blue)';
    pairCard.innerHTML = `
      <span class="card-tag tag-grade">⚡ Active Scraping Pair</span>
      <div class="card-title">Scraping ${pair.join(' & ')}</div>
      <div class="card-step" style="color: var(--accent-green);">▶️ Executing Multi-Thread Direct Stream</div>
      <div class="card-body">Tải video từ o9o.net, remux MP4 H.264 và rclone copyto sang GDrive.</div>
      <div class="card-footer">
        <span>SOP Sequence 04-06</span>
        <span style="color: var(--accent-green); font-weight: bold;">● Active Stream</span>
      </div>
    `;
    progressCol.appendChild(pairCard);
    countProgress++;
  });

  // 3. Render Lock Files into In Progress
  const locks = data.active_locks || [];
  locks.forEach(lock => {
    const lockCard = document.createElement('div');
    lockCard.className = 'kanban-card';
    lockCard.style.borderLeft = '3px solid var(--accent-yellow)';
    lockCard.innerHTML = `
      <span class="card-tag tag-lock">🔒 Process Lock Active</span>
      <div class="card-title">${escapeHtml(lock)}</div>
      <div class="card-step" style="color: var(--accent-yellow);">🔒 Lock Occupied by Local Process</div>
      <div class="card-body">Tránh ghi đè file rác khi đang cào dữ liệu ngầm.</div>
      <div class="card-footer">
        <span>Local VPS Process</span>
        <span style="color: var(--accent-yellow); font-weight: bold;">Locked</span>
      </div>
    `;
    progressCol.appendChild(lockCard);
    countProgress++;
  });

  // 4. Render 100% Completed Grades into Completed Column
  const completedGrades = data.completed_grades || [];
  completedGrades.forEach(grade => {
    const gradeCard = document.createElement('div');
    gradeCard.className = 'kanban-card';
    gradeCard.style.borderLeft = '3px solid var(--accent-green)';
    gradeCard.innerHTML = `
      <span class="card-tag tag-grade">✅ 100% Verified Grade</span>
      <div class="card-title">${escapeHtml(grade)}</div>
      <div class="card-step" style="color: var(--accent-green);">✅ Verified 170/170 Days Complete</div>
      <div class="card-body">Tất cả bài học đầy đủ môn, video chuẩn MP4 >100KB, xem bình thường.</div>
      <div class="card-footer">
        <span>Abeka Curriculum</span>
        <span style="color: var(--accent-green); font-weight: bold;">Exemption List</span>
      </div>
    `;
    completedCol.appendChild(gradeCard);
    countCompleted++;
  });

  // Update Column Badge Counts
  document.getElementById('countQueued').innerText = countQueued;
  document.getElementById('countProgress').innerText = countProgress;
  document.getElementById('countCompleted').innerText = countCompleted;
  document.getElementById('countFailed').innerText = countFailed;

  // 5. Render Log Terminal Output
  renderLogs(data.log_tails || {});
}

function createGitHubRunCard(run) {
  const card = document.createElement('div');
  card.className = 'kanban-card';
  
  let borderCol = 'var(--accent-purple)';
  let stepPrefix = '▶️';
  let stepStyle = 'color: var(--accent-green); font-weight: bold;';

  if (run.status === 'in_progress') {
    borderCol = 'var(--accent-blue)';
    stepPrefix = '⚡ RUNNING STEP:';
    stepStyle = 'color: var(--accent-blue); font-weight: bold; background: rgba(137, 180, 250, 0.15); padding: 4px 8px; border-radius: 4px; border: 1px solid rgba(137, 180, 250, 0.3);';
  } else if (run.status === 'pending' || run.status === 'queued') {
    borderCol = 'var(--accent-yellow)';
    stepPrefix = '⏳ IN QUEUE:';
    stepStyle = 'color: var(--accent-yellow);';
  } else if (run.conclusion === 'success') {
    borderCol = 'var(--accent-green)';
    stepPrefix = '✅ COMPLETED:';
    stepStyle = 'color: var(--accent-green);';
  } else if (run.conclusion === 'failure') {
    borderCol = 'var(--accent-red)';
    stepPrefix = '❌ FAILED AT:';
    stepStyle = 'color: var(--accent-red);';
  }
  
  card.style.borderLeft = `3px solid ${borderCol}`;

  const currentStep = run.current_step || (run.status === 'completed' ? 'Finished All Steps' : 'Initializing...');

  card.innerHTML = `
    <span class="card-tag tag-github">☁️ GitHub Actions Run #${run.run_number}</span>
    <div class="card-title">${escapeHtml(run.name)}</div>
    <div class="card-step" style="margin: 6px 0; font-size: 0.85rem; ${stepStyle}">
      ${stepPrefix} ${escapeHtml(currentStep)}
    </div>
    <div class="card-body">
      ${run.commit_message ? `<div class="card-commit">💬 ${escapeHtml(run.commit_message)}</div>` : ''}
    </div>
    <div class="card-footer">
      <span>${formatTime(run.created_at)}</span>
      <a href="${run.html_url}" target="_blank" rel="noopener" class="card-link">🔗 Chi Tiết GitHub Log</a>
    </div>
  `;
  return card;
}

function renderLogs(logTails) {
  const terminal = document.getElementById('logTerminal');
  if (!terminal) return;

  const content = logTails[activeLogTab] || 'No log output available for this log file.';
  terminal.innerText = content;
}

function switchLogTab(logName, btnElem) {
  activeLogTab = logName;
  document.querySelectorAll('.log-tab-btn').forEach(b => b.classList.remove('active'));
  if (btnElem) btnElem.classList.add('active');
  if (currentStatusData && currentStatusData.log_tails) {
    renderLogs(currentStatusData.log_tails);
  }
}

function formatTime(isoStr) {
  if (!isoStr) return '';
  const d = new Date(isoStr);
  return d.toLocaleTimeString();
}

function escapeHtml(str) {
  if (!str) return '';
  return str.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
}
