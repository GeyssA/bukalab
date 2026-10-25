const PANELS = ["accueil", "cartographie", "cours", "apropos"];
const logo = document.getElementById("site-logo");
const LOGO_SIMPLE = "assets/bukalab_logo_simple.svg";
const LOGO_COURS = "assets/bukalab_logo_plain.svg";

const panels = document.querySelectorAll("[data-panel]");
const navBtns = document.querySelectorAll("[data-nav]");

function currentQuery() {
  return location.search;
}

function showPanel(id, { scroll = true } = {}) {
  if (!PANELS.includes(id)) id = "accueil";
  panels.forEach((p) => p.classList.toggle("is-active", p.dataset.panel === id));
  navBtns.forEach((b) => b.classList.toggle("is-active", b.dataset.nav === id));
  document.body.classList.toggle("theme-cours", id === "cours");
  if (logo) logo.src = id === "cours" ? LOGO_COURS : LOGO_SIMPLE;
  const hash = id === "accueil" ? "" : `#${id}`;
  history.replaceState(history.state, "", `${location.pathname}${currentQuery()}${hash}`);
  if (scroll) window.scrollTo({ top: 0, behavior: "auto" });
}

navBtns.forEach((btn) => {
  btn.addEventListener("click", () => showPanel(btn.dataset.nav));
});

document.querySelectorAll("[data-goto]").forEach((el) => {
  el.addEventListener("click", (e) => {
    e.preventDefault();
    showPanel(el.dataset.goto);
  });
});

window.addEventListener("hashchange", () => {
  showPanel(location.hash.replace("#", "") || "accueil", { scroll: false });
});

const initialParams = new URLSearchParams(location.search);
const initialPanel =
  location.hash.replace("#", "") || (initialParams.get("carte") ? "cartographie" : "accueil");
showPanel(initialPanel, { scroll: false });

window.BukaLab = { showPanel, PANELS };
