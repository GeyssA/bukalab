const CV = {
  fr: ["assets/cv/cv_fr_1.png", "assets/cv/cv_fr_2.png"],
  en: ["assets/cv/cv_en_1.png", "assets/cv/cv_en_2.png"],
};

const page1 = document.getElementById("cv-page-1");
const page2 = document.getElementById("cv-page-2");
const zoom = document.getElementById("cv-zoom");
const zoomImg = document.getElementById("cv-zoom-img");
const cvButtons = document.querySelectorAll("[data-cv-lang]");

let cvLang = window.BukaLabI18n?.lang === "en" ? "en" : "fr";

function showCv(lang) {
  cvLang = lang === "en" ? "en" : "fr";
  if (page1) page1.src = CV[cvLang][0];
  if (page2) page2.src = CV[cvLang][1];
  const alt1 = window.BukaLabI18n?.t("cv.alt1") || "CV";
  const alt2 = window.BukaLabI18n?.t("cv.alt2") || "CV";
  if (page1) page1.alt = alt1;
  if (page2) page2.alt = alt2;
  cvButtons.forEach((btn) => {
    const on = btn.dataset.cvLang === cvLang;
    btn.classList.toggle("is-active", on);
    btn.setAttribute("aria-selected", on ? "true" : "false");
  });
}

function openZoom(src, alt) {
  if (!zoom || !zoomImg) return;
  zoomImg.src = src;
  zoomImg.alt = alt || "";
  zoom.hidden = false;
  document.body.classList.add("is-locked");
  zoom.querySelector(".cv-zoom-close")?.focus();
}

function closeZoom() {
  if (!zoom || zoom.hidden) return;
  zoom.hidden = true;
  zoomImg.removeAttribute("src");
  document.body.classList.remove("is-locked");
}

cvButtons.forEach((btn) => {
  btn.addEventListener("click", () => showCv(btn.dataset.cvLang));
});

document.querySelectorAll("[data-cv-zoom]").forEach((btn) => {
  btn.addEventListener("click", () => {
    const img = btn.querySelector("img");
    if (img) openZoom(img.src, img.alt);
  });
});

zoom?.querySelectorAll("[data-cv-zoom-close]").forEach((el) => {
  el.addEventListener("click", closeZoom);
});

zoomImg?.addEventListener("click", (event) => event.stopPropagation());

document.addEventListener("keydown", (e) => {
  if (e.key === "Escape") closeZoom();
});

window.addEventListener("bukalab-lang", (e) => {
  closeZoom();
  showCv(e.detail);
});

showCv(cvLang);
