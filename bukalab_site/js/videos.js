/* Vidéos : lecture silencieuse dans la page + visionneuse grand format avec son et chapitres.

   Pour ajouter une vidéo : déposer le .mp4 (H.264, idéalement « faststart ») dans assets/video/,
   puis ajouter une entrée ci-dessous. Les vignettes de chapitres et le poster sont optionnels. */

window.BUKALAB_VIDEOS = [
  {
    id: "memoire-du-feu-corse",
    src: "assets/video/memoire_du_feu_corse.mp4",
    poster: "assets/video/memoire_du_feu_corse_poster.jpg",
    duration: 161,
    width: 1920,
    height: 1080,
    title: "Mémoire du feu",
    subtitle: "Corse, 1970 – 2025 · les contours de feu, année après année",
    subtitleEn: "Corsica, 1970 – 2025 · fire perimeters, year after year",
    description:
      "Cinquante-cinq ans d’incendies en Corse, contour par contour. Chaque feu cartographié s’allume l’année où il a brûlé, puis garde la couleur de sa décennie. Le film compare ensuite l’avant et l’après 2000, les régions de l’île, et ce que disent le climat et la végétation.",
    descriptionEn:
      "Fifty-five years of wildfires in Corsica, perimeter by perimeter. Each mapped fire lights up in the year it burned, then keeps the colour of its decade. The film then compares before and after 2000, the island’s regions, and what climate and vegetation have to say.",
    sources: "contours de feu DDTM 2A, DDT 2B (Prométhée, BDIFF)",
    sourcesEn: "fire perimeters from DDTM 2A, DDT 2B (Prométhée, BDIFF)",
    chapters: [
      { t: 0, label: "Chronique", labelEn: "Chronicle", thumb: "assets/video/memoire_du_feu_corse_ch1.jpg" },
      { t: 38, label: "Avant / depuis 2000", labelEn: "Before / since 2000", thumb: "assets/video/memoire_du_feu_corse_ch2.jpg" },
      { t: 74, label: "Entre régions", labelEn: "Between regions", thumb: "assets/video/memoire_du_feu_corse_ch3.jpg" },
      { t: 107, label: "Pourquoi", labelEn: "Why", thumb: "assets/video/memoire_du_feu_corse_ch4.jpg" },
      { t: 134, label: "À retenir", labelEn: "Key takeaways", thumb: "assets/video/memoire_du_feu_corse_ch5.jpg" },
    ],
  },
];

(() => {
  const FILMS = window.BUKALAB_VIDEOS || [];
  const byId = (id) => FILMS.find((f) => f.id === id);
  const tr = (key, vars = {}) => {
    let s = window.BukaLabI18n ? window.BukaLabI18n.t(key) : key;
    Object.entries(vars).forEach(([k, v]) => (s = s.replace(`{${k}}`, v)));
    return s;
  };
  const inEnglish = () => window.BukaLabI18n?.lang === "en";
  const field = (item, name) => (inEnglish() && item[`${name}En`]) || item[name] || "";
  const reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)");

  const fmt = (s) => {
    s = Math.max(0, Math.floor(s || 0));
    return `${Math.floor(s / 60)}:${String(s % 60).padStart(2, "0")}`;
  };
  const durationOf = (item, video) => (video && isFinite(video.duration) && video.duration) || item.duration || 0;

  const ICONS = {
    expand: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M14 4h6v6M10 20H4v-6M20 4l-7 7M4 20l7-7"/></svg>',
    play: '<svg viewBox="0 0 24 24" aria-hidden="true"><path class="fill" d="M8 5.5v13l10.5-6.5z"/></svg>',
    pause: '<svg viewBox="0 0 24 24" aria-hidden="true"><path class="fill" d="M7 5h3.6v14H7zM13.4 5H17v14h-3.6z"/></svg>',
    muted: '<svg viewBox="0 0 24 24" aria-hidden="true"><path class="fill" d="M4 9.5h3.5L12 5.5v13l-4.5-4H4z"/><path d="M16 9.5l5 5M21 9.5l-5 5"/></svg>',
    sound: '<svg viewBox="0 0 24 24" aria-hidden="true"><path class="fill" d="M4 9.5h3.5L12 5.5v13l-4.5-4H4z"/><path d="M15.5 9a4.2 4.2 0 010 6M18.2 6.5a8 8 0 010 11"/></svg>',
  };

  /* ------------------------------------------------------------ Lecteur dans la page */

  const inlinePlayers = [];

  function chapterTicks(item) {
    const d = item.duration || 1;
    return (item.chapters || [])
      .filter((c) => c.t > 0)
      .map((c) => `<i style="left:${((c.t / d) * 100).toFixed(3)}%"></i>`)
      .join("");
  }

  function chapterList(item, extraClass = "") {
    return `<ol class="film-chapters ${extraClass}">${(item.chapters || [])
      .map(
        (c, i) => `
        <li>
          <button type="button" class="film-chapter" data-chapter="${i}" data-t="${c.t}">
            ${c.thumb ? `<span class="film-chapter-thumb"><img src="${c.thumb}" alt="" loading="lazy" decoding="async" /></span>` : ""}
            <span class="film-chapter-text">
              <span class="film-chapter-num">${i + 1}</span>
              <span class="film-chapter-label" data-role="chapter-label" data-i="${i}">${field(c, "label")}</span>
              <span class="film-chapter-time">${fmt(c.t)}</span>
            </span>
          </button>
        </li>`
      )
      .join("")}</ol>`;
  }

  function buildFilm(item, { feature = false } = {}) {
    const fig = document.createElement("figure");
    fig.className = `film${feature ? " film--feature" : ""}`;
    fig.dataset.film = item.id;
    fig.innerHTML = `
      <div class="film-frame" style="aspect-ratio:${item.width || 16} / ${item.height || 9}">
        <video class="film-video" muted loop playsinline preload="none" ${item.poster ? `poster="${item.poster}"` : ""}>
          <source src="${item.src}" type="video/mp4" />
        </video>
        <button type="button" class="film-open" data-role="open">
          <span class="film-badge">${ICONS.expand}<span data-role="open-label"></span></span>
        </button>
        <div class="film-controls">
          <button type="button" class="film-ctl" data-role="play"></button>
          <button type="button" class="film-ctl" data-role="sound"></button>
          <span class="film-time" data-role="time">0:00 / ${fmt(item.duration)}</span>
        </div>
        <div class="film-progress" aria-hidden="true">
          <span class="film-progress-fill" data-role="fill"></span>
          ${chapterTicks(item)}
        </div>
      </div>
      <figcaption class="film-caption">
        <div class="film-caption-head">
          <p class="film-eyebrow" data-role="eyebrow"></p>
          <h3 class="film-title" data-role="title"></h3>
          <p class="film-sub" data-role="sub"></p>
        </div>
        ${
          feature
            ? `<div class="film-details">
                <div class="film-about">
                  <p class="film-desc" data-role="desc"></p>
                  <p class="film-sources"><span data-role="sources-label"></span> · <span data-role="sources"></span></p>
                </div>
                <div class="film-chapters-wrap">
                  <p class="film-chapters-title" data-role="chapters-title"></p>
                  ${chapterList(item)}
                </div>
              </div>`
            : ""
        }
      </figcaption>`;

    const video = fig.querySelector("video");
    const player = { item, fig, video, userPaused: reduceMotion.matches, visible: false };
    inlinePlayers.push(player);

    fig.querySelector('[data-role="open"]').addEventListener("click", () => openViewer(item.id, video.currentTime || 0, player));
    fig.querySelectorAll(".film-chapter").forEach((btn) =>
      btn.addEventListener("click", () => openViewer(item.id, Number(btn.dataset.t), player))
    );
    fig.querySelector('[data-role="play"]').addEventListener("click", () => {
      player.userPaused = !video.paused;
      if (player.userPaused) video.pause();
      else safePlay(video);
      syncControls(player);
    });
    fig.querySelector('[data-role="sound"]').addEventListener("click", () => {
      video.muted = !video.muted;
      if (!video.muted && video.paused) {
        player.userPaused = false;
        safePlay(video);
      }
      syncControls(player);
    });
    ["play", "pause", "volumechange"].forEach((ev) => video.addEventListener(ev, () => syncControls(player)));
    video.addEventListener("play", () => tick(player));
    video.addEventListener("timeupdate", () => drawProgress(player));
    video.addEventListener("loadedmetadata", () => drawProgress(player));

    applyFilmTexts(player);
    observer.observe(fig.querySelector(".film-frame"));
    return fig;
  }

  function applyFilmTexts(player) {
    const { item, fig } = player;
    const set = (role, text) => fig.querySelectorAll(`[data-role="${role}"]`).forEach((el) => (el.textContent = text));
    set("eyebrow", tr("films.eyebrow", { d: fmt(item.duration) }));
    set("title", field(item, "title"));
    set("sub", field(item, "subtitle"));
    set("desc", field(item, "description"));
    set("sources", field(item, "sources"));
    set("sources-label", tr("films.sources"));
    set("chapters-title", tr("films.chapters"));
    set("open-label", tr("films.open"));
    fig.querySelector('[data-role="open"]').setAttribute("aria-label", tr("films.open.aria", { t: field(item, "title") }));
    fig.querySelectorAll('[data-role="chapter-label"]').forEach((el) => {
      el.textContent = field(item.chapters[Number(el.dataset.i)], "label");
    });
    syncControls(player);
  }

  function syncControls(player) {
    const { video, fig } = player;
    const play = fig.querySelector('[data-role="play"]');
    const sound = fig.querySelector('[data-role="sound"]');
    const paused = video.paused;
    play.innerHTML = paused ? ICONS.play : ICONS.pause;
    play.setAttribute("aria-label", tr(paused ? "films.play" : "films.pause"));
    play.title = play.getAttribute("aria-label");
    sound.innerHTML = video.muted ? ICONS.muted : ICONS.sound;
    sound.setAttribute("aria-label", tr(video.muted ? "films.sound.on" : "films.sound.off"));
    sound.title = sound.getAttribute("aria-label");
    fig.classList.toggle("is-playing", !paused);
  }

  function drawProgress(player) {
    const { item, video, fig } = player;
    const d = durationOf(item, video);
    const p = d ? Math.min(1, video.currentTime / d) : 0;
    fig.querySelector('[data-role="fill"]').style.clipPath = `inset(0 ${((1 - p) * 100).toFixed(3)}% 0 0)`;
    fig.querySelector('[data-role="time"]').textContent = `${fmt(video.currentTime)} / ${fmt(d)}`;
  }

  function tick(player) {
    drawProgress(player);
    if (!player.video.paused) requestAnimationFrame(() => tick(player));
  }

  function safePlay(video) {
    const p = video.play();
    if (p && p.catch) p.catch(() => {});
  }

  function updatePlayback(player) {
    const shouldPlay = player.visible && !player.userPaused && viewer.hidden && !document.hidden;
    if (shouldPlay && player.video.paused) safePlay(player.video);
    else if (!shouldPlay && !player.video.paused) player.video.pause();
  }

  const observer = new IntersectionObserver(
    (entries) => {
      entries.forEach((entry) => {
        const player = inlinePlayers.find((p) => p.fig.contains(entry.target));
        if (!player) return;
        player.visible = entry.isIntersecting && entry.intersectionRatio >= 0.35;
        updatePlayback(player);
      });
    },
    { threshold: [0, 0.35, 0.6] }
  );

  document.addEventListener("visibilitychange", () => inlinePlayers.forEach(updatePlayback));

  /* ------------------------------------------------------------ Visionneuse grand format */

  const viewer = document.getElementById("film-viewer");
  const vVideo = document.getElementById("film-viewer-video");
  const vTitle = document.getElementById("film-viewer-title");
  const vSub = document.getElementById("film-viewer-sub");
  const vEyebrow = document.getElementById("film-viewer-eyebrow");
  const vChapters = document.getElementById("film-viewer-chapters");
  const vDownload = document.getElementById("film-download");
  const vFullscreen = document.getElementById("film-fullscreen");

  let current = null;
  let source = null;
  let lastFocus = null;

  function fillViewerTexts() {
    if (!current) return;
    vEyebrow.textContent = tr("films.eyebrow", { d: fmt(current.duration) });
    vTitle.textContent = field(current, "title");
    vSub.textContent = field(current, "subtitle");
    vChapters.querySelectorAll('[data-role="chapter-label"]').forEach((el) => {
      el.textContent = field(current.chapters[Number(el.dataset.i)], "label");
    });
  }

  function openViewer(id, startAt = 0, fromPlayer = null) {
    const item = byId(id);
    if (!item) return;
    current = item;
    source = fromPlayer;
    lastFocus = document.activeElement;

    vChapters.outerHTML = chapterList(item, "film-chapters--strip").replace("<ol ", '<ol id="film-viewer-chapters" ');
    bindViewerChapters();
    fillViewerTexts();
    vDownload.href = item.src;

    if (vVideo.dataset.src !== item.src) {
      vVideo.src = item.src;
      vVideo.dataset.src = item.src;
      if (item.poster) vVideo.poster = item.poster;
    }
    const start = () => {
      try {
        vVideo.currentTime = startAt;
      } catch (_) {}
      vVideo.muted = false;
      safePlay(vVideo);
    };
    if (vVideo.readyState >= 1) start();
    else vVideo.addEventListener("loadedmetadata", start, { once: true });

    viewer.hidden = false;
    document.body.classList.add("is-locked");
    inlinePlayers.forEach(updatePlayback);
    viewer.querySelector(".tool-btn-close").focus({ preventScroll: true });
    highlightChapter();
  }

  function closeViewer() {
    if (viewer.hidden) return;
    if (document.fullscreenElement) document.exitFullscreen().catch(() => {});
    vVideo.pause();
    viewer.hidden = true;
    document.body.classList.remove("is-locked");
    if (source && isFinite(vVideo.currentTime)) {
      try {
        source.video.currentTime = vVideo.currentTime;
      } catch (_) {}
      drawProgress(source);
    }
    inlinePlayers.forEach(updatePlayback);
    if (lastFocus && lastFocus.focus) lastFocus.focus({ preventScroll: true });
  }

  function bindViewerChapters() {
    const list = document.getElementById("film-viewer-chapters");
    list.querySelectorAll(".film-chapter").forEach((btn) =>
      btn.addEventListener("click", () => {
        vVideo.currentTime = Number(btn.dataset.t);
        safePlay(vVideo);
      })
    );
  }

  function highlightChapter() {
    if (!current) return;
    const t = vVideo.currentTime || 0;
    let active = 0;
    (current.chapters || []).forEach((c, i) => {
      if (t >= c.t - 0.25) active = i;
    });
    document.querySelectorAll("#film-viewer-chapters .film-chapter").forEach((btn, i) => {
      btn.classList.toggle("is-active", i === active);
      btn.setAttribute("aria-current", i === active ? "true" : "false");
    });
  }

  function toggleFullscreen() {
    if (document.fullscreenElement) return document.exitFullscreen().catch(() => {});
    if (vVideo.requestFullscreen) vVideo.requestFullscreen().catch(() => {});
    else if (vVideo.webkitEnterFullscreen) vVideo.webkitEnterFullscreen();
  }

  vVideo.addEventListener("timeupdate", highlightChapter);
  vVideo.addEventListener("seeked", highlightChapter);
  vFullscreen.addEventListener("click", toggleFullscreen);
  vVideo.addEventListener("dblclick", (e) => {
    e.preventDefault();
    toggleFullscreen();
  });

  viewer.querySelectorAll("[data-film-close]").forEach((el) =>
    el.addEventListener("click", (e) => {
      if (e.target === el || el.tagName === "BUTTON") closeViewer();
    })
  );

  document.addEventListener("keydown", (e) => {
    if (viewer.hidden) return;
    if (e.target.closest && e.target.closest("button, a") && (e.key === " " || e.key === "Enter")) return;
    switch (e.key) {
      case "Escape":
        closeViewer();
        break;
      case " ":
      case "k":
        if (vVideo.paused) safePlay(vVideo);
        else vVideo.pause();
        break;
      case "ArrowLeft":
        vVideo.currentTime = Math.max(0, vVideo.currentTime - 5);
        break;
      case "ArrowRight":
        vVideo.currentTime = Math.min(durationOf(current, vVideo), vVideo.currentTime + 5);
        break;
      case "f":
      case "F":
        toggleFullscreen();
        break;
      case "m":
        vVideo.muted = !vVideo.muted;
        break;
      default:
        return;
    }
    e.preventDefault();
  });

  /* ------------------------------------------------------------ Montage */

  document.querySelectorAll("[data-film-slot]").forEach((slot) => {
    const item = byId(slot.dataset.filmSlot);
    if (item) slot.appendChild(buildFilm(item));
  });

  const list = document.getElementById("film-list");
  if (list) FILMS.forEach((item) => list.appendChild(buildFilm(item, { feature: true })));

  window.addEventListener("bukalab-lang", () => {
    inlinePlayers.forEach(applyFilmTexts);
    fillViewerTexts();
  });

  window.BukaLabFilms = { open: openViewer, close: closeViewer };
})();
