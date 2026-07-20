#!/usr/bin/env python3
"""
Regenerate all grade HTML pages using Plyr.js + HLS.js player.
Each page fetches playlist JSON from /data/{grade}/{lesson}.json (static, no CORS)
then plays HLS video directly from CDN using HLS.js.
"""
import os

BASE_DIR = "/media/vpsg24gb/DATA1/o9o"

GRADES = [
    ("k4",  "K4 (Age 4)",  "2023-k4",  170, "🌱", "Pre-Kindergarten",
     "Abeka K4 video lessons for 4-year-olds. Covers phonics, numbers, and skills development."),
    ("k5",  "K5 (Age 5)",  "2023-k5",  170, "🌟", "Kindergarten",
     "Abeka K5 video lessons for 5-year-olds. Full kindergarten curriculum with reading and math."),
    ("g1",  "Grade 1",     "2023-01",  170, "1️⃣", "Elementary",
     "Abeka Grade 1 daily video lessons. Phonics, reading, arithmetic, and more."),
    ("g2",  "Grade 2",     "2023-02",  170, "2️⃣", "Elementary",
     "Abeka Grade 2 daily video lessons. Reading, writing, arithmetic, and science."),
    ("g3",  "Grade 3",     "2023-03",  170, "3️⃣", "Elementary",
     "Abeka Grade 3 daily video lessons. Reading, language arts, and math fundamentals."),
    ("g4",  "Grade 4",     "2023-04",  170, "4️⃣", "Elementary",
     "Abeka Grade 4 daily video lessons. Advanced reading, writing, and mathematics."),
    ("g5",  "Grade 5",     "2023-05",  170, "5️⃣", "Elementary",
     "Abeka Grade 5 daily video lessons. Science, history, and language arts."),
    ("g6",  "Grade 6",     "2023-06",  170, "6️⃣", "Middle School",
     "Abeka Grade 6 daily video lessons. Transition to middle school curriculum."),
    ("g7",  "Grade 7",     "2023-07",  170, "7️⃣", "Middle School",
     "Abeka Grade 7 daily video lessons. Pre-algebra, history, and literature."),
    ("g8",  "Grade 8",     "2023-08",  170, "8️⃣", "Middle School",
     "Abeka Grade 8 daily video lessons. Algebra, life science, and writing."),
    ("g9",  "Grade 9",     "2023-09",  170, "9️⃣", "High School",
     "Abeka Grade 9 daily video lessons. Algebra I, literature, and world history."),
    ("g10", "Grade 10",    "2023-10",  170, "🔟", "High School",
     "Abeka Grade 10 daily video lessons. Geometry, chemistry, and American literature."),
    ("g11", "Grade 11",    "2023-11",  170, "📘", "High School",
     "Abeka Grade 11 daily video lessons. Algebra II, physics, and American history."),
    ("g12", "Grade 12",    "2023-12",  170, "🎓", "High School",
     "Abeka Grade 12 daily video lessons. Pre-calculus, economics, and senior composition."),
]

NAV_ITEMS = [
    ("../index.html", "Home"),
    ("../k4/index.html",  "K4"), ("../k5/index.html",  "K5"),
    ("../g1/index.html",  "G1"), ("../g2/index.html",  "G2"),
    ("../g3/index.html",  "G3"), ("../g4/index.html",  "G4"),
    ("../g5/index.html",  "G5"), ("../g6/index.html",  "G6"),
    ("../g7/index.html",  "G7"), ("../g8/index.html",  "G8"),
    ("../g9/index.html",  "G9"), ("../g10/index.html", "G10"),
    ("../g11/index.html", "G11"), ("../g12/index.html", "G12"),
]

def build_nav(active_folder):
    items = []
    for href, label in NAV_ITEMS:
        folder = href.split("/")[-2]
        ac = ' class="active"' if folder == active_folder else ""
        items.append(f'        <li{ac}><a href="{href}">{label}</a></li>')
    return "\n".join(items)

def build_lesson_buttons(prefix, count):
    return "\n".join(
        f'        <button class="lesson-btn" data-lesson="{prefix}-{i:03d}" id="btn-{prefix}-{i:03d}">{i:03d}</button>'
        for i in range(1, count + 1)
    )

def generate_page(folder, display_name, prefix, count, emoji, level, description):
    nav = build_nav(folder)
    btns = build_lesson_buttons(prefix, count)
    orig = f"https://www.o9o.net/{folder}/"

    return f"""<!DOCTYPE html>
<html lang="en-US">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Abeka {display_name} Video Lessons - o9o.net</title>
  <meta name="description" content="{description}">
  <link rel="canonical" href="{orig}">
  <link rel="icon" type="image/png" sizes="32x32" href="https://www.o9o.net/images/ico/favicon-32x32.png">
  <link rel="stylesheet" href="../css/style.css">

  <!-- HLS.js — plays HLS (.m3u8) in any browser -->
  <script src="https://cdn.jsdelivr.net/npm/hls.js@1/dist/hls.min.js"></script>
  <!-- Plyr — beautiful open-source HTML5 player -->
  <link  rel="stylesheet" href="https://cdn.jsdelivr.net/npm/plyr@3/dist/plyr.css">
  <script src="https://cdn.jsdelivr.net/npm/plyr@3/dist/plyr.polyfilled.min.js"></script>

  <style>
    .player-section {{ margin: 24px 0 0; }}
    .playlist-tabs {{
      display: flex; flex-wrap: wrap; gap: 8px;
      background: var(--bg-card); border: 1px solid var(--border);
      border-radius: var(--radius); padding: 14px 16px; margin-bottom: 16px;
    }}
    .playlist-tabs h4 {{ width: 100%; margin: 0 0 10px; font-size: 13px;
      color: var(--text-muted); text-transform: uppercase; letter-spacing: .5px; }}
    .tab-btn {{
      padding: 7px 14px; border-radius: 6px; border: 1.5px solid var(--border);
      background: var(--bg); font-size: 13px; font-weight: 500;
      cursor: pointer; transition: all .15s; color: var(--text);
    }}
    .tab-btn:hover {{ border-color: var(--primary); color: var(--primary); }}
    .tab-btn.active {{ background: var(--primary); border-color: var(--primary); color: #fff; }}
    .plyr {{ border-radius: var(--radius); overflow: hidden; --plyr-color-main: #0274BE; }}
    .video-info {{ padding: 14px 20px; background: var(--bg-card);
      border: 1px solid var(--border); border-top: none;
      border-radius: 0 0 var(--radius) var(--radius); }}
    .video-info h3 {{ font-size: 16px; margin-bottom: 4px; }}
    .video-info .meta {{ font-size: 13px; color: var(--text-muted); }}
    .status-msg {{
      text-align: center; padding: 48px 20px;
      background: var(--bg-card); border-radius: var(--radius);
      border: 1px solid var(--border); color: var(--text-muted);
    }}
    .status-msg .spinner {{
      width: 36px; height: 36px; border: 3px solid var(--border);
      border-top-color: var(--primary); border-radius: 50%;
      animation: spin .8s linear infinite; margin: 0 auto 12px;
    }}
    @keyframes spin {{ to {{ transform: rotate(360deg); }} }}
  </style>
</head>
<body>

<header class="site-header">
  <div class="header-top">
    <div class="container">
      <a href="../index.html" class="site-logo">
        Prinberk HP <span>Collected ABEKA Homeschooling Video Lessons</span>
      </a>
      <button class="menu-toggle" id="menu-toggle" aria-label="Toggle menu">☰</button>
    </div>
  </div>
  <nav class="site-nav">
    <div class="container">
      <ul class="nav-list" role="list">
{nav}
      </ul>
    </div>
  </nav>
</header>

<main>
  <div class="page-header">
    <div class="container">
      <div class="breadcrumb">
        <a href="../index.html">Home</a> <span class="breadcrumb-sep">›</span>
        <span>{display_name}</span>
      </div>
      <h1>{emoji} Abeka {display_name} Video Lessons</h1>
      <p>{level} · {count} daily lessons · Free homeschool curriculum</p>
    </div>
  </div>

  <div class="container">

    <!-- ===== PLAYER ===== -->
    <div class="player-section">

      <!-- Subject tabs (loaded after lesson is selected) -->
      <div class="playlist-tabs" id="playlist-tabs" style="display:none">
        <h4>📋 Subjects in this lesson:</h4>
        <!-- populated by JS -->
      </div>

      <!-- Plyr video element -->
      <div id="player-wrap">
        <div class="status-msg" id="status-msg">
          <div>📚 Select a lesson below to start watching</div>
        </div>
        <div id="plyr-container" style="display:none">
          <video id="player" playsinline style="width:100%">
            <source src="" type="application/x-mpegURL">
          </video>
        </div>
      </div>

      <div class="video-info" id="video-info" style="display:none">
        <h3 id="video-title">—</h3>
        <div class="meta" id="video-meta"></div>
      </div>

      <!-- Prev/Next -->
      <div class="lesson-nav" style="margin-top:14px">
        <button class="btn btn-outline" id="btn-prev" disabled>◀ Previous</button>
        <button class="btn btn-primary" id="btn-next" disabled>Next ▶</button>
        <a class="btn btn-outline" id="orig-link" href="{orig}"
           target="_blank" rel="noopener" style="margin-left:auto">
          🔗 o9o.net ↗
        </a>
      </div>
    </div>

    <!-- ===== LESSON GRID ===== -->
    <section class="lessons-section">
      <h2 class="lessons-title">📅 Abeka {display_name} lessons by daily schedule:</h2>
      <div class="lesson-grid" id="lesson-grid">
{btns}
      </div>
    </section>

  </div><!-- .container -->
</main>

<footer class="site-footer">
  <div class="container">
    <div class="footer-inner">
      <span><a href="../index.html">Prinberk HP</a> — Copyright &copy; 2026</span>
      <nav class="footer-links">
        <a href="https://www.o9o.net/privacy-policy/" target="_blank">Privacy Policy</a>
        <a href="{orig}" target="_blank">Original Site</a>
      </nav>
    </div>
  </div>
</footer>

<script>
(function() {{
  // ---- Config ----
  const GRADE  = '{folder}';
  const PREFIX = '{prefix}';
  const COUNT  = {count};
  const ORIG   = '{orig}';

  // ---- Elements ----
  const buttons     = Array.from(document.querySelectorAll('.lesson-btn'));
  const statusMsg   = document.getElementById('status-msg');
  const playerEl    = document.getElementById('player');
  const plyrContainer= document.getElementById('plyr-container');
  const videoInfo   = document.getElementById('video-info');
  const videoTitle  = document.getElementById('video-title');
  const videoMeta   = document.getElementById('video-meta');
  const playlistTabs= document.getElementById('playlist-tabs');
  const prevBtn     = document.getElementById('btn-prev');
  const nextBtn     = document.getElementById('btn-next');
  const origLink    = document.getElementById('orig-link');

  let plyr = null;
  let hls  = null;
  let currentIdx = -1;
  let currentPlaylist = [];
  let currentTabIdx = 0;

  // ---- Init Plyr ----
  function initPlyr() {{
    if (plyr) return;
    plyr = new Plyr(playerEl, {{
      controls: ['play','progress','current-time','mute','volume','settings','fullscreen'],
      settings: ['quality','speed'],
      speed: {{ selected: 1, options: [0.5, 0.75, 1, 1.25, 1.5, 2] }},
    }});
  }}

  // ---- Load HLS stream ----
  function loadHLS(m3u8Url) {{
    initPlyr();
    if (hls) {{ hls.destroy(); hls = null; }}

    // Rewrite HLS url to go through our proxy
    let proxiedUrl = m3u8Url;
    if (m3u8Url.startsWith('http')) {{
      try {{
        const urlObj = new URL(m3u8Url);
        proxiedUrl = 'https://abeka-proxy.hothihuong113.workers.dev/cdn/' + urlObj.hostname + urlObj.pathname + urlObj.search;
      }} catch(e) {{
        console.error('URL parse error:', e);
      }}
    }}

    plyrContainer.style.display = 'block';

    if (Hls.isSupported()) {{
      hls = new Hls({{ enableWorker: true }});
      hls.loadSource(proxiedUrl);
      hls.attachMedia(playerEl);
      hls.on(Hls.Events.MANIFEST_PARSED, () => plyr.play());
      hls.on(Hls.Events.ERROR, (e, data) => {{
        if (data.fatal) {{
          console.error('Fatal HLS error:', data);
          showError('Video không load được. Thử mở trực tiếp trên o9o.net.');
        }}
      }});
    }} else if (playerEl.canPlayType('application/vnd.apple.mpegurl')) {{
      // Safari native HLS
      playerEl.src = proxiedUrl;
      playerEl.play();
    }} else {{
      showError('Trình duyệt không hỗ trợ HLS. Dùng Chrome hoặc Firefox.');
    }}
  }}

  // ---- Render subject tabs ----
  function renderTabs(playlist) {{
    // Clear old tabs (keep h4)
    const h4 = playlistTabs.querySelector('h4');
    playlistTabs.innerHTML = '';
    playlistTabs.appendChild(h4);
    playlistTabs.style.display = 'flex';

    playlist.forEach((item, i) => {{
      const btn = document.createElement('button');
      btn.className = 'tab-btn' + (i === currentTabIdx ? ' active' : '');
      btn.textContent = item.title;
      btn.onclick = () => {{
        currentTabIdx = i;
        document.querySelectorAll('.tab-btn').forEach((b,j) =>
          b.classList.toggle('active', j === i));
        loadHLS(item.file);
        updateVideoMeta(item);
      }};
      playlistTabs.appendChild(btn);
    }});
  }}

  function updateVideoMeta(item) {{
    videoTitle.textContent = item.title + (item.description ? ' — ' + item.description.split('-')[0] : '');
    videoMeta.textContent  = item.description || '';
    videoInfo.style.display = 'block';
  }}

  function showLoading(code) {{
    statusMsg.innerHTML = '<div class="spinner"></div><div>Loading lesson ' + code + '...</div>';
    statusMsg.style.display = 'block';
    plyrContainer.style.display = 'none';
    videoInfo.style.display = 'none';
    playlistTabs.style.display = 'none';
  }}

  function showError(msg) {{
    statusMsg.innerHTML = '❌ ' + msg;
    statusMsg.style.display = 'block';
  }}

  // ---- Activate lesson ----
  function activate(index) {{
    if (index < 0 || index >= buttons.length) return;
    currentIdx = index;
    currentTabIdx = 0;
    const btn  = buttons[index];
    const code = btn.dataset.lesson;
    const num  = btn.textContent;

    // Highlight
    buttons.forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
    btn.scrollIntoView({{ behavior: 'smooth', block: 'nearest', inline: 'nearest' }});

    // Update URL
    const url = new URL(window.location.href);
    url.searchParams.set('lesson', code);
    history.pushState({{}}, '', url);

    // Update links
    origLink.href = ORIG + '?lesson=' + code;

    // Nav buttons
    prevBtn.disabled = index === 0;
    nextBtn.disabled = index === buttons.length - 1;

    showLoading(num);

    // Fetch cached JSON playlist
    const jsonUrl = '../data/' + GRADE + '/' + code + '.json';
    fetch(jsonUrl)
      .then(r => {{
        if (!r.ok) throw new Error('HTTP ' + r.status);
        return r.json();
      }})
      .then(playlist => {{
        statusMsg.style.display = 'none';
        currentPlaylist = playlist;
        renderTabs(playlist);
        loadHLS(playlist[0].file);
        updateVideoMeta(playlist[0]);
      }})
      .catch(err => {{
        // JSON not cached yet → fallback redirect to o9o.net
        statusMsg.innerHTML =
          '⚠️ Playlist chưa được cache. <br>' +
          '<a href="' + ORIG + '?lesson=' + code + '" target="_blank" ' +
          'style="color:var(--primary);font-weight:600">Mở trực tiếp trên o9o.net ↗</a>';
        statusMsg.style.display = 'block';
      }});
  }}

  // ---- Event listeners ----
  buttons.forEach((btn, i) => btn.addEventListener('click', () => activate(i)));
  prevBtn.addEventListener('click', () => activate(currentIdx - 1));
  nextBtn.addEventListener('click', () => activate(currentIdx + 1));
  document.addEventListener('keydown', e => {{
    if (e.key === 'ArrowLeft')  activate(currentIdx - 1);
    if (e.key === 'ArrowRight') activate(currentIdx + 1);
  }});

  // Mobile nav
  const toggle  = document.getElementById('menu-toggle');
  const navList = document.querySelector('.nav-list');
  if (toggle) {{
    toggle.addEventListener('click', () => navList.classList.toggle('open'));
    document.addEventListener('click', e => {{
      if (!toggle.contains(e.target) && !navList.contains(e.target))
        navList.classList.remove('open');
    }});
  }}

  // Init from URL ?lesson=
  const initCode = new URLSearchParams(window.location.search).get('lesson');
  if (initCode) {{
    const idx = buttons.findIndex(b => b.dataset.lesson === initCode);
    if (idx >= 0) activate(idx);
  }}
}})();
</script>

</body>
</html>"""


def main():
    for folder, display_name, prefix, count, emoji, level, description in GRADES:
        out_dir = os.path.join(BASE_DIR, folder)
        os.makedirs(out_dir, exist_ok=True)
        content = generate_page(folder, display_name, prefix, count, emoji, level, description)
        with open(os.path.join(out_dir, "index.html"), "w", encoding="utf-8") as f:
            f.write(content)
        print(f"✅ {folder}/index.html")
    print("\n🎉 All pages regenerated with Plyr.js + HLS.js player!")

if __name__ == "__main__":
    main()
