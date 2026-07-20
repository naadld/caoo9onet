#!/usr/bin/env python3
"""
Generate all grade HTML pages for o9o.net static clone.
Each lesson page embeds an iframe pointing to o9o.net original.
"""

import os

BASE_DIR = "/media/vpsg24gb/DATA1/o9o"

# Grade configuration: (folder, display_name, lesson_prefix, count, emoji, level, description)
GRADES = [
    ("k4",  "K4 (Age 4)",  "2023-k4",  170, "🌱", "Pre-Kindergarten",
     "Abeka K4 video lessons for 4-year-olds. Covers phonics, numbers, and skills development."),
    ("k5",  "K5 (Age 5)",  "2024-k5",  170, "🌟", "Kindergarten",
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
    ("../k4/index.html",  "K4 (Age 4)"),
    ("../k5/index.html",  "K5 (Age 5)"),
    ("../g1/index.html",  "Grade 1"),
    ("../g2/index.html",  "Grade 2"),
    ("../g3/index.html",  "Grade 3"),
    ("../g4/index.html",  "Grade 4"),
    ("../g5/index.html",  "Grade 5"),
    ("../g6/index.html",  "Grade 6"),
    ("../g7/index.html",  "Grade 7"),
    ("../g8/index.html",  "Grade 8"),
    ("../g9/index.html",  "Grade 9"),
    ("../g10/index.html", "Grade 10"),
    ("../g11/index.html", "Grade 11"),
    ("../g12/index.html", "Grade 12"),
]


def build_nav(active_folder):
    items = []
    for href, label in NAV_ITEMS:
        folder = href.split("/")[-2]
        active_class = ' class="active"' if folder == active_folder else ""
        items.append(f'        <li{active_class}><a href="{href}">{label}</a></li>')
    return "\n".join(items)


def build_lesson_buttons(prefix, count):
    btns = []
    for i in range(1, count + 1):
        code = f"{prefix}-{i:03d}"
        btns.append(f'        <button class="lesson-btn" data-lesson="{code}">{i:03d}</button>')
    return "\n".join(btns)


def generate_grade_page(folder, display_name, prefix, count, emoji, level, description):
    nav_html = build_nav(folder)
    btns_html = build_lesson_buttons(prefix, count)
    slug = folder  # e.g. k4, g1
    original_url = f"https://www.o9o.net/{slug}/"

    html = f"""<!DOCTYPE html>
<html lang="en-US">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Abeka {display_name} Video Lessons - o9o.net</title>
  <meta name="description" content="{description}">
  <meta name="robots" content="follow, index">
  <link rel="canonical" href="{original_url}">
  <meta property="og:type" content="website">
  <meta property="og:title" content="Abeka {display_name} Video Lessons - o9o.net">
  <meta property="og:description" content="{description}">
  <link rel="icon" type="image/png" sizes="32x32" href="https://www.o9o.net/images/ico/favicon-32x32.png">
  <link rel="stylesheet" href="../css/style.css">
</head>
<body>

<!-- HEADER -->
<header class="site-header">
  <div class="header-top">
    <div class="container">
      <a href="../index.html" class="site-logo">
        o9o.net
        <span>Free Abeka Homeschooling Video Lessons</span>
      </a>
      <button class="menu-toggle" id="menu-toggle" aria-label="Toggle menu" aria-expanded="false">☰</button>
    </div>
  </div>
  <nav class="site-nav" aria-label="Main navigation">
    <div class="container">
      <ul class="nav-list" role="list">
{nav_html}
      </ul>
    </div>
  </nav>
</header>

<!-- MAIN -->
<main>

  <!-- Page Header -->
  <div class="page-header">
    <div class="container">
      <div class="breadcrumb">
        <a href="../index.html">Home</a>
        <span class="breadcrumb-sep">›</span>
        <span>{display_name}</span>
      </div>
      <h1>{emoji} Abeka {display_name} Video Lessons</h1>
      <p>{level} · {count} daily lessons · Free homeschool curriculum</p>
    </div>
  </div>

  <div class="container">

    <!-- Video Player (iframe embed) -->
    <div class="video-section" style="margin: 28px 0 0;">
      <div class="video-container">
        <div id="video-placeholder" class="video-placeholder">
          <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor">
            <path d="M8 5v14l11-7z"/>
          </svg>
          <p>Select a lesson below to start watching</p>
        </div>
        <iframe id="video-frame" class="video-frame"
          src="about:blank"
          style="display:none"
          allowfullscreen
          allow="autoplay; fullscreen"
          loading="lazy"
          title="Abeka {display_name} Video Lesson">
        </iframe>
        <div class="video-info">
          <h3 id="video-title">Choose a lesson to watch</h3>
          <div class="meta" id="video-meta">
            <span>📚 Abeka {display_name}</span>
            <span>·</span>
            <span id="lesson-code-display">Select a lesson</span>
          </div>
        </div>
      </div>

      <!-- Prev/Next buttons -->
      <div class="lesson-nav">
        <button class="btn btn-outline" id="btn-prev" disabled>◀ Previous</button>
        <button class="btn btn-primary" id="btn-next" disabled>Next ▶</button>
        <a class="btn btn-outline" id="btn-original" href="{original_url}" target="_blank" rel="noopener" style="margin-left:auto">
          🔗 Open on o9o.net
        </a>
      </div>
    </div>

    <!-- Lessons Grid -->
    <section class="lessons-section">
      <h2 class="lessons-title">📅 Abeka {display_name} lessons by daily schedule:</h2>
      <div class="lesson-grid" id="lesson-grid">
{btns_html}
      </div>
    </section>

    <!-- About -->
    <div class="info-card" style="margin-bottom:40px">
      <span class="icon">{emoji}</span>
      <h3>About Abeka {display_name}</h3>
      <p>{description}</p>
    </div>

  </div>
</main>

<!-- FOOTER -->
<footer class="site-footer">
  <div class="container">
    <div class="footer-inner">
      <span>
        <a href="../index.html">o9o.net</a> — Copyright &copy; 2026. Abeka homeschool video lessons.
      </span>
      <nav class="footer-links">
        <a href="https://www.o9o.net/privacy-policy/" target="_blank" rel="noopener">Privacy Policy</a>
        <a href="{original_url}" target="_blank" rel="noopener">Original Site</a>
      </nav>
    </div>
  </div>
</footer>

<script>
// ---- Lesson Page Logic ----
(function() {{
  const slug = '{slug}';
  const originalBase = '{original_url}';
  const buttons = document.querySelectorAll('.lesson-btn');
  const frame = document.getElementById('video-frame');
  const placeholder = document.getElementById('video-placeholder');
  const titleEl = document.getElementById('video-title');
  const codeEl = document.getElementById('lesson-code-display');
  const prevBtn = document.getElementById('btn-prev');
  const nextBtn = document.getElementById('btn-next');
  const origLink = document.getElementById('btn-original');

  let current = -1;

  // Read ?lesson= from URL
  const params = new URLSearchParams(window.location.search);
  const initLesson = params.get('lesson');

  function activate(index) {{
    if (index < 0 || index >= buttons.length) return;
    current = index;
    const btn = buttons[index];
    const code = btn.dataset.lesson;
    const num = btn.textContent;

    // Highlight button
    buttons.forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
    btn.scrollIntoView({{ behavior: 'smooth', block: 'nearest', inline: 'nearest' }});

    // Update URL
    const url = new URL(window.location.href);
    url.searchParams.set('lesson', code);
    history.pushState({{}}, '', url);

    // Load iframe
    const src = originalBase + '?lesson=' + code;
    frame.src = src;
    frame.style.display = 'block';
    placeholder.style.display = 'none';

    // Update original link
    origLink.href = src;

    // Update info
    titleEl.textContent = 'Lesson ' + num + ' — Abeka {display_name}';
    codeEl.textContent = code;

    // Update nav
    prevBtn.disabled = index === 0;
    nextBtn.disabled = index === buttons.length - 1;
    prevBtn.style.opacity = index === 0 ? '0.45' : '1';
    nextBtn.style.opacity = index === buttons.length - 1 ? '0.45' : '1';
  }}

  // Button click
  buttons.forEach((btn, i) => {{
    btn.addEventListener('click', () => activate(i));
  }});

  prevBtn.addEventListener('click', () => activate(current - 1));
  nextBtn.addEventListener('click', () => activate(current + 1));

  // Keyboard navigation
  document.addEventListener('keydown', e => {{
    if (e.key === 'ArrowLeft') activate(current - 1);
    if (e.key === 'ArrowRight') activate(current + 1);
  }});

  // Mobile menu
  const toggle = document.getElementById('menu-toggle');
  const navList = document.querySelector('.nav-list');
  if (toggle) {{
    toggle.addEventListener('click', () => {{
      const open = navList.classList.toggle('open');
      toggle.setAttribute('aria-expanded', open);
    }});
    document.addEventListener('click', e => {{
      if (!toggle.contains(e.target) && !navList.contains(e.target))
        navList.classList.remove('open');
    }});
  }}

  // Init from URL param
  if (initLesson) {{
    const idx = Array.from(buttons).findIndex(b => b.dataset.lesson === initLesson);
    if (idx >= 0) activate(idx);
  }}
}})();
</script>

</body>
</html>
"""
    return html


def main():
    for folder, display_name, prefix, count, emoji, level, description in GRADES:
        out_dir = os.path.join(BASE_DIR, folder)
        os.makedirs(out_dir, exist_ok=True)
        out_path = os.path.join(out_dir, "index.html")
        content = generate_grade_page(folder, display_name, prefix, count, emoji, level, description)
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(content)
        print(f"✅ Generated: {out_path} ({count} lessons)")

    print("\n🎉 All grade pages generated!")


if __name__ == "__main__":
    main()
