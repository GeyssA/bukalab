/* Galerie de cartographies + visionneuse plein écran (zoom, pan, image/PDF). */

const CATALOG = (window.BUKALAB_CARTO || []).map((c) => ({ tags: [], ...c }));

const grid = document.getElementById("carto-grid");
const emptyMsg = document.getElementById("carto-empty");
const countEl = document.getElementById("carto-count");
const searchInput = document.getElementById("carto-search");
const tagRow = document.getElementById("carto-tags");

const viewer = document.getElementById("viewer");
const shell = viewer.querySelector(".viewer-shell");
const canvas = document.getElementById("viewer-canvas");
const imgEl = document.getElementById("viewer-image");
const pdfEl = document.getElementById("viewer-pdf");
const spinner = document.getElementById("viewer-spinner");
const strip = document.getElementById("viewer-strip");
const prevBtn = document.getElementById("viewer-prev");
const nextBtn = document.getElementById("viewer-next");
const titleEl = document.getElementById("viewer-title");
const subEl = document.getElementById("viewer-subtitle");
const eyebrowEl = document.getElementById("viewer-eyebrow");
const downloadEl = document.getElementById("viewer-download");
const zoomTools = document.getElementById("zoom-tools");
const zoomLevelEl = document.getElementById("zoom-level");
const formatBtns = viewer.querySelectorAll(".format-btn");

const PAD = 28;

let visible = CATALOG.slice();
let activeTag = null;
let query = "";

let openIndex = -1;
let format = "image";
let scale = 1;
let fitScale = 1;
let tx = 0;
let ty = 0;
let lastFocus = null;

/* ---------------------------------------------------------------- Galerie */

function matches(item) {
  if (activeTag && !item.tags.includes(activeTag)) return false;
  if (!query) return true;
  const hay = [item.title, item.subtitle, item.year, ...item.tags].join(" ").toLowerCase();
  return query
    .toLowerCase()
    .split(/\s+/)
    .filter(Boolean)
    .every((w) => hay.includes(w));
}

function renderGrid() {
  visible = CATALOG.filter(matches);
  grid.innerHTML = "";

  visible.forEach((item) => {
    const card = document.createElement("article");
    card.className = "carto-card";
    card.dataset.id = item.id;
    card.innerHTML = `
      <div class="carto-card-figure">
        <img src="${item.thumb || item.image}" alt="" loading="lazy" decoding="async" />
        <div class="carto-card-overlay"><span>Ouvrir en grand</span></div>
      </div>
      <div class="carto-card-body">
        <h2><button type="button" class="carto-card-link">${item.title}</button></h2>
        <p>${item.subtitle || ""}</p>
        <div class="carto-card-tags">${item.tags.map((t) => `<span>${t}</span>`).join("")}</div>
      </div>`;
    card.querySelector(".carto-card-link").addEventListener("click", () => openViewer(item.id));
    grid.appendChild(card);
  });

  emptyMsg.hidden = visible.length > 0;
  countEl.textContent =
    CATALOG.length === visible.length
      ? `${CATALOG.length} carte${CATALOG.length > 1 ? "s" : ""}`
      : `${visible.length} / ${CATALOG.length} cartes`;
}

function renderFilters() {
  const toolbar = document.querySelector(".carto-toolbar");
  if (CATALOG.length < 2) {
    toolbar.hidden = true;
    return;
  }
  const tags = [...new Set(CATALOG.flatMap((c) => c.tags))].sort((a, b) => a.localeCompare(b, "fr"));
  tagRow.innerHTML = "";
  if (!tags.length) {
    tagRow.hidden = true;
    return;
  }
  tags.forEach((tag) => {
    const chip = document.createElement("button");
    chip.type = "button";
    chip.className = "chip";
    chip.textContent = tag;
    chip.addEventListener("click", () => {
      activeTag = activeTag === tag ? null : tag;
      tagRow.querySelectorAll(".chip").forEach((c) => c.classList.toggle("is-active", c.textContent === activeTag));
      renderGrid();
    });
    tagRow.appendChild(chip);
  });
}

searchInput?.addEventListener("input", () => {
  query = searchInput.value.trim();
  renderGrid();
});

/* ----------------------------------------------------------- Zoom / pan */

function applyTransform() {
  // Taille réelle en CSS, pas un scale() : le navigateur rééchantillonne
  // le PNG dans les pixels de l'écran au lieu de flouter une texture GPU.
  const w = imgEl.naturalWidth * scale;
  const h = imgEl.naturalHeight * scale;
  imgEl.style.width = `${w}px`;
  imgEl.style.height = `${h}px`;
  imgEl.style.transform = `translate(${tx}px, ${ty}px)`;
  zoomLevelEl.textContent = `${Math.round((scale / fitScale) * 100)} %`;
}

function clampTranslate() {
  const vw = canvas.clientWidth;
  const vh = canvas.clientHeight;
  const w = imgEl.naturalWidth * scale;
  const h = imgEl.naturalHeight * scale;
  tx = w <= vw ? (vw - w) / 2 : Math.min(0, Math.max(vw - w, tx));
  ty = h <= vh ? (vh - h) / 2 : Math.min(0, Math.max(vh - h, ty));
}

function computeFit() {
  const vw = canvas.clientWidth - PAD * 2;
  const vh = canvas.clientHeight - PAD * 2;
  if (!imgEl.naturalWidth || vw <= 0 || vh <= 0) return;
  fitScale = Math.min(vw / imgEl.naturalWidth, vh / imgEl.naturalHeight);
}

function fitToScreen() {
  computeFit();
  scale = fitScale;
  clampTranslate();
  applyTransform();
}

function zoomTo(nextScale, cx, cy) {
  const min = fitScale;
  const max = Math.max(fitScale * 8, 1.5);
  const s = Math.min(max, Math.max(min, nextScale));
  if (s === scale) return;
  tx = cx - ((cx - tx) * s) / scale;
  ty = cy - ((cy - ty) * s) / scale;
  scale = s;
  clampTranslate();
  applyTransform();
}

function zoomByFactor(factor) {
  zoomTo(scale * factor, canvas.clientWidth / 2, canvas.clientHeight / 2);
}

canvas.addEventListener(
  "wheel",
  (e) => {
    e.preventDefault();
    const r = canvas.getBoundingClientRect();
    zoomTo(scale * (e.deltaY < 0 ? 1.15 : 1 / 1.15), e.clientX - r.left, e.clientY - r.top);
  },
  { passive: false },
);

canvas.addEventListener("dblclick", (e) => {
  const r = canvas.getBoundingClientRect();
  const target = Math.min(1, fitScale * 5);
  if (scale > fitScale * 1.05) fitToScreen();
  else zoomTo(target, e.clientX - r.left, e.clientY - r.top);
});

const pointers = new Map();
let pinchStart = null;

canvas.addEventListener("pointerdown", (e) => {
  canvas.setPointerCapture(e.pointerId);
  pointers.set(e.pointerId, { x: e.clientX, y: e.clientY });
  if (pointers.size === 2) {
    const [a, b] = [...pointers.values()];
    pinchStart = { dist: Math.hypot(a.x - b.x, a.y - b.y), scale };
  }
  canvas.classList.add("is-panning");
});

canvas.addEventListener("pointermove", (e) => {
  const p = pointers.get(e.pointerId);
  if (!p) return;
  const dx = e.clientX - p.x;
  const dy = e.clientY - p.y;
  pointers.set(e.pointerId, { x: e.clientX, y: e.clientY });

  if (pointers.size === 2 && pinchStart) {
    const [a, b] = [...pointers.values()];
    const r = canvas.getBoundingClientRect();
    const dist = Math.hypot(a.x - b.x, a.y - b.y);
    zoomTo(pinchStart.scale * (dist / pinchStart.dist), (a.x + b.x) / 2 - r.left, (a.y + b.y) / 2 - r.top);
    return;
  }

  tx += dx;
  ty += dy;
  clampTranslate();
  applyTransform();
});

function endPointer(e) {
  pointers.delete(e.pointerId);
  if (pointers.size < 2) pinchStart = null;
  if (pointers.size === 0) canvas.classList.remove("is-panning");
}

canvas.addEventListener("pointerup", endPointer);
canvas.addEventListener("pointercancel", endPointer);
canvas.addEventListener("pointerleave", endPointer);

document.getElementById("zoom-in").addEventListener("click", () => zoomByFactor(1.25));
document.getElementById("zoom-out").addEventListener("click", () => zoomByFactor(1 / 1.25));
document.getElementById("zoom-fit").addEventListener("click", fitToScreen);

/* ------------------------------------------------------------ Visionneuse */

function setFormat(next, { push = true } = {}) {
  const item = CATALOG[openIndex];
  if (!item) return;
  format = item.pdf ? next : "image";

  formatBtns.forEach((b) => {
    const on = b.dataset.format === format;
    b.classList.toggle("is-active", on);
    b.setAttribute("aria-selected", on ? "true" : "false");
    b.disabled = b.dataset.format === "pdf" && !item.pdf;
  });

  const isImage = format === "image";
  canvas.hidden = !isImage;
  pdfEl.hidden = isImage;
  zoomTools.hidden = !isImage;

  if (!isImage && pdfEl.getAttribute("src") !== item.pdf) pdfEl.setAttribute("src", item.pdf);

  downloadEl.href = isImage ? item.image : item.pdf;
  downloadEl.setAttribute("download", (isImage ? item.image : item.pdf).split("/").pop());
  downloadEl.textContent = isImage ? "Télécharger le PNG" : "Télécharger le PDF";

  if (isImage) requestAnimationFrame(fitToScreen);
  if (push) syncUrl();
}

function renderStrip() {
  strip.hidden = CATALOG.length < 2;
  if (strip.hidden) return;
  strip.innerHTML = "";
  CATALOG.forEach((item, i) => {
    const b = document.createElement("button");
    b.type = "button";
    b.className = "strip-thumb" + (i === openIndex ? " is-active" : "");
    b.title = item.title;
    b.setAttribute("aria-label", item.title);
    b.innerHTML = `<img src="${item.thumb || item.image}" alt="" loading="lazy" />`;
    b.addEventListener("click", () => showIndex(i));
    strip.appendChild(b);
  });
  strip.children[openIndex]?.scrollIntoView({ block: "nearest", inline: "center" });
}

function preloadNeighbours() {
  [-1, 1].forEach((d) => {
    const n = CATALOG[(openIndex + d + CATALOG.length) % CATALOG.length];
    if (n && n !== CATALOG[openIndex]) new Image().src = n.image;
  });
}

function showIndex(i, { push = true } = {}) {
  if (i < 0 || i >= CATALOG.length) return;
  openIndex = i;
  const item = CATALOG[i];

  eyebrowEl.textContent = [item.year, ...item.tags].filter(Boolean).join(" · ");
  titleEl.textContent = item.title;
  subEl.textContent = item.subtitle || "";
  imgEl.alt = item.title;

  imgEl.classList.remove("is-ready");
  spinner.hidden = false;
  imgEl.src = item.image;

  const ready = () => {
    imgEl.removeAttribute("width");
    imgEl.removeAttribute("height");
    spinner.hidden = true;
    imgEl.classList.add("is-ready");
    fitToScreen();
    preloadNeighbours();
  };
  if (imgEl.complete && imgEl.naturalWidth) ready();
  else imgEl.onload = ready;

  const multiple = CATALOG.length > 1;
  prevBtn.hidden = !multiple;
  nextBtn.hidden = !multiple;

  setFormat(item.pdf ? format : "image", { push: false });
  renderStrip();
  if (push) syncUrl();
}

function step(delta) {
  showIndex((openIndex + delta + CATALOG.length) % CATALOG.length);
}

function syncUrl() {
  const item = CATALOG[openIndex];
  if (!item) return;
  const url = `${location.pathname}?carte=${encodeURIComponent(item.id)}&vue=${format}#cartographie`;
  history.replaceState({ viewer: item.id, format }, "", url);
}

function openViewer(id, requestedFormat) {
  const i = CATALOG.findIndex((c) => c.id === id);
  if (i < 0) return;
  lastFocus = document.activeElement;
  format = requestedFormat === "pdf" ? "pdf" : "image";
  viewer.hidden = false;
  document.body.classList.add("is-locked");
  history.pushState({ viewer: id, format }, "", `${location.pathname}?carte=${encodeURIComponent(id)}&vue=${format}#cartographie`);
  showIndex(i, { push: false });
  viewer.querySelector(".tool-btn-close").focus({ preventScroll: true });
}

function closeViewer({ pop = true } = {}) {
  if (viewer.hidden) return;
  viewer.hidden = true;
  document.body.classList.remove("is-locked");
  imgEl.removeAttribute("src");
  pdfEl.removeAttribute("src");
  openIndex = -1;
  if (pop && history.state?.viewer) history.back();
  else history.replaceState(null, "", `${location.pathname}#cartographie`);
  lastFocus?.focus?.({ preventScroll: true });
}

viewer.querySelectorAll("[data-viewer-close]").forEach((el) => {
  el.addEventListener("click", () => closeViewer());
});

formatBtns.forEach((b) => b.addEventListener("click", () => setFormat(b.dataset.format)));
prevBtn.addEventListener("click", () => step(-1));
nextBtn.addEventListener("click", () => step(1));

document.addEventListener("keydown", (e) => {
  if (viewer.hidden) return;
  switch (e.key) {
    case "Escape":
      closeViewer();
      break;
    case "ArrowLeft":
      step(-1);
      break;
    case "ArrowRight":
      step(1);
      break;
    case "+":
    case "=":
      zoomByFactor(1.25);
      break;
    case "-":
      zoomByFactor(1 / 1.25);
      break;
    case "0":
      fitToScreen();
      break;
    case "Tab": {
      const focusables = shell.querySelectorAll("button:not([disabled]):not([hidden]), a[href]");
      if (!focusables.length) return;
      const first = focusables[0];
      const last = focusables[focusables.length - 1];
      if (e.shiftKey && document.activeElement === first) {
        e.preventDefault();
        last.focus();
      } else if (!e.shiftKey && document.activeElement === last) {
        e.preventDefault();
        first.focus();
      }
      break;
    }
    default:
      return;
  }
  if (e.key !== "Tab") e.preventDefault();
});

window.addEventListener("resize", () => {
  if (!viewer.hidden && format === "image") fitToScreen();
});

window.addEventListener("popstate", (e) => {
  const state = e.state;
  if (state?.viewer) {
    const i = CATALOG.findIndex((c) => c.id === state.viewer);
    if (i >= 0) {
      if (viewer.hidden) {
        viewer.hidden = false;
        document.body.classList.add("is-locked");
      }
      format = state.format === "pdf" ? "pdf" : "image";
      showIndex(i, { push: false });
      return;
    }
  }
  closeViewer({ pop: false });
});

document.querySelectorAll("[data-open-first]").forEach((el) => {
  el.addEventListener("click", () => {
    if (!CATALOG.length) return;
    window.BukaLab?.showPanel("cartographie", { scroll: false });
    openViewer(CATALOG[0].id, el.dataset.openFirst);
  });
});

/* ------------------------------------------------------------- Démarrage */

renderFilters();
renderGrid();

const params = new URLSearchParams(location.search);
const deepLink = params.get("carte");
if (deepLink && CATALOG.some((c) => c.id === deepLink)) {
  window.BukaLab?.showPanel("cartographie", { scroll: false });
  // L'entrée d'historique initiale doit rester « visionneuse fermée » pour que Échap / retour sortent vraiment.
  history.replaceState(null, "", `${location.pathname}#cartographie`);
  openViewer(deepLink, params.get("vue"));
}
