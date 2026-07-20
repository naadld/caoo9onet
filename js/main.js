// ============================================================
// o9o.net Static Clone — Main JavaScript
// ============================================================

(function () {
  'use strict';

  /* === Mobile Nav Toggle === */
  const toggle = document.getElementById('menu-toggle');
  const navList = document.querySelector('.nav-list');

  if (toggle && navList) {
    toggle.addEventListener('click', () => {
      const open = navList.classList.toggle('open');
      toggle.setAttribute('aria-expanded', open);
    });

    // Close on outside click
    document.addEventListener('click', (e) => {
      if (!toggle.contains(e.target) && !navList.contains(e.target)) {
        navList.classList.remove('open');
        toggle.setAttribute('aria-expanded', 'false');
      }
    });
  }

  /* === Active Nav Highlight === */
  const currentPath = window.location.pathname;
  document.querySelectorAll('.nav-list a').forEach((a) => {
    const href = a.getAttribute('href');
    if (href && currentPath.startsWith(href) && href !== '/') {
      a.closest('li').classList.add('active');
    } else if (href === '/' && (currentPath === '/' || currentPath === '/index.html')) {
      a.closest('li').classList.add('active');
    }
  });

  /* === Lesson Page Logic === */
  const lessonBtns = document.querySelectorAll('.lesson-btn');
  const videoFrame = document.getElementById('video-frame');
  const videoPlaceholder = document.getElementById('video-placeholder');
  const videoTitle = document.getElementById('video-title');
  const videoMeta = document.getElementById('video-meta');
  const prevBtn = document.getElementById('btn-prev');
  const nextBtn = document.getElementById('btn-next');

  if (!lessonBtns.length) return;

  // Get lesson code from URL param
  const urlParams = new URLSearchParams(window.location.search);
  let currentLesson = urlParams.get('lesson') || lessonBtns[0]?.dataset.lesson;

  function activateLesson(lessonCode) {
    // Update URL without reload
    const newUrl = new URL(window.location.href);
    newUrl.searchParams.set('lesson', lessonCode);
    history.pushState({}, '', newUrl);
    currentLesson = lessonCode;

    // Update active button
    lessonBtns.forEach((b) => {
      b.classList.toggle('active', b.dataset.lesson === lessonCode);
    });

    // Scroll active button into view
    const activeBtn = document.querySelector(`.lesson-btn[data-lesson="${lessonCode}"]`);
    if (activeBtn) activeBtn.scrollIntoView({ behavior: 'smooth', block: 'nearest', inline: 'nearest' });

    // Load video from o9o.net iframe (redirect to original)
    loadVideo(lessonCode);

    // Update nav buttons
    updateNavBtns();

    // Update title/meta
    if (videoTitle) videoTitle.textContent = 'Lesson ' + lessonCode.split('-').pop();
    if (videoMeta) videoMeta.textContent = lessonCode;
  }

  function loadVideo(lessonCode) {
    if (!videoFrame || !videoPlaceholder) return;
    // Redirect to original o9o.net for the video (since we can't host video)
    const originalUrl = `https://www.o9o.net${window.location.pathname}?lesson=${lessonCode}`;
    // Embed as iframe
    videoFrame.src = originalUrl;
    videoFrame.style.display = 'block';
    videoPlaceholder.style.display = 'none';
  }

  function getLessonIndex() {
    const arr = Array.from(lessonBtns);
    return arr.findIndex((b) => b.dataset.lesson === currentLesson);
  }

  function updateNavBtns() {
    const idx = getLessonIndex();
    if (prevBtn) prevBtn.disabled = idx <= 0;
    if (nextBtn) nextBtn.disabled = idx >= lessonBtns.length - 1;
  }

  lessonBtns.forEach((btn) => {
    btn.addEventListener('click', (e) => {
      e.preventDefault();
      activateLesson(btn.dataset.lesson);
    });
  });

  if (prevBtn) {
    prevBtn.addEventListener('click', () => {
      const idx = getLessonIndex();
      if (idx > 0) activateLesson(lessonBtns[idx - 1].dataset.lesson);
    });
  }

  if (nextBtn) {
    nextBtn.addEventListener('click', () => {
      const idx = getLessonIndex();
      if (idx < lessonBtns.length - 1) activateLesson(lessonBtns[idx + 1].dataset.lesson);
    });
  }

  // Init
  if (currentLesson) activateLesson(currentLesson);

  /* === Keyboard Navigation === */
  document.addEventListener('keydown', (e) => {
    if (e.key === 'ArrowLeft' && prevBtn && !prevBtn.disabled) prevBtn.click();
    if (e.key === 'ArrowRight' && nextBtn && !nextBtn.disabled) nextBtn.click();
  });

})();
