/* ============================================================
   ABEKA LIVE WORKFLOW OPERATIONS DASHBOARD - JAVASCRIPT LOGIC
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
  }, 6000); // Poll every 6 seconds
}

async function fetchLiveData() {
  const statusElem = document.getElementById('lastUpdatedTime');
  try {
    const res = await fetch('data/workflow_live_status.json?t=' + Date.now());
    if (res.ok) {
      currentStatusData = await res.json();
      renderDashboard(currentStatusData);
      if (statusElem) statusElem.innerText = currentStatusData.last_updated || 'Just now';
    }
  } catch (err) {
    console.error('Error fetching live workflow status:', err);
    if (statusElem) statusElem.innerText = 'Offline / Retrying...';
  }
}

function renderDashboard(data) {
  renderGitHubRuns(data.github_runs || []);
  renderDaemons(data.running_daemons || {});
  renderActiveLocks(data.active_locks || []);
  renderLogs(data.log_tails || {});
}

function renderGitHubRuns(runs) {
  const container = document.getElementById('workflowRunsGrid');
  if (!container) return;

  if (runs.length === 0) {
    container.innerHTML = `<div style="grid-column: 1/-1; padding: 20px; text-align: center; color: var(--text-muted);">No active workflow runs found.</div>`;
    return;
  }

  container.innerHTML = '';
  runs.forEach(run => {
    const card = document.createElement('div');
    
    let statusClass = 'in_progress';
    let statusLabel = run.status;

    if (run.status === 'completed') {
      if (run.conclusion === 'success') {
        statusClass = 'completed_success';
        statusLabel = 'SUCCESS';
      } else {
        statusClass = 'completed_failure';
        statusLabel = run.conclusion ? run.conclusion.toUpperCase() : 'FAILED';
      }
    } else if (run.status === 'in_progress') {
      statusClass = 'in_progress';
      statusLabel = 'IN PROGRESS 🟢';
    } else if (run.status === 'pending' || run.status === 'queued') {
      statusClass = 'pending';
      statusLabel = 'QUEUED 🟡';
    }

    const pillClass = run.status === 'completed' 
      ? (run.conclusion === 'success' ? 'success' : 'failure') 
      : (run.status === 'in_progress' ? 'in_progress' : 'pending');

    card.className = `run-card ${statusClass}`;
    card.innerHTML = `
      <div class="run-header">
        <div class="run-name">${escapeHtml(run.name)}</div>
        <span class="status-pill ${pillClass}">${statusLabel}</span>
      </div>
      <div class="run-details">
        <div><strong>Run ID:</strong> #${run.id} (Run #${run.run_number})</div>
        <div><strong>Created:</strong> ${formatTime(run.created_at)}</div>
        ${run.commit_message ? `<div class="run-commit">💬 ${escapeHtml(run.commit_message)}</div>` : ''}
      </div>
      <div class="run-footer">
        <span>Cloud Execution</span>
        <a href="${run.html_url}" target="_blank" rel="noopener" class="run-link-btn">
          <span>🔗 View Logs on GitHub</span>
        </a>
      </div>
    `;
    container.appendChild(card);
  });
}

function renderDaemons(daemons) {
  const container = document.getElementById('daemonsList');
  if (!container) return;

  const daemonNames = {
    telegram_bot: '🤖 Telegram Listener & Bot',
    appscript_relay: '📡 AppScript Telegram Relay Server (Port 8088)',
    watchdog: '🛡️ Local Watchdog Monitor Daemon',
    active_scraper_local: '⚡ Local Python Scraper Instance'
  };

  container.innerHTML = '';
  Object.keys(daemonNames).forEach(key => {
    const isRunning = daemons[key];
    const item = document.createElement('div');
    item.className = 'daemon-item';
    item.innerHTML = `
      <span>${daemonNames[key]}</span>
      <span class="${isRunning ? 'badge-on' : 'badge-off'}">
        ${isRunning ? '● ACTIVE RUNNING' : '○ IDLE / INACTIVE'}
      </span>
    `;
    container.appendChild(item);
  });
}

function renderActiveLocks(locks) {
  const container = document.getElementById('locksList');
  if (!container) return;

  if (!locks || locks.length === 0) {
    container.innerHTML = `<span style="color: var(--text-dim); font-size: 0.85rem;">No active process lock files (.lock). System clear.</span>`;
    return;
  }

  container.innerHTML = locks.map(l => `<span class="lock-badge">🔒 ${escapeHtml(l)}</span>`).join('');
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
  return d.toLocaleTimeString() + ' (' + d.toLocaleDateString() + ')';
}

function escapeHtml(str) {
  if (!str) return '';
  return str.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
}
