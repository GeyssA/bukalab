const plot = document.getElementById("gauss-plot");
const curve = document.getElementById("gauss-curve");
const ghost = document.getElementById("gauss-ghost");
const meanLine = document.getElementById("gauss-mean");
const muInput = document.getElementById("mu");
const sigmaInput = document.getElementById("sigma");
const muVal = document.getElementById("mu-val");
const sigmaVal = document.getElementById("sigma-val");
const readout = document.getElementById("gauss-readout");

if (plot && curve && muInput && sigmaInput) {
  const X0 = 28;
  const X1 = 340;
  const Y0 = 22;
  const Y1 = 168;
  const XMIN = -4.2;
  const XMAX = 4.2;

  const pdf = (x, mu, sigma) => {
    const z = (x - mu) / sigma;
    return Math.exp(-0.5 * z * z) / (sigma * Math.sqrt(2 * Math.PI));
  };

  const sx = (x) => X0 + ((x - XMIN) / (XMAX - XMIN)) * (X1 - X0);
  const sy = (y) => Y1 - y * (Y1 - Y0);

  function pathFor(mu, sigma) {
    let d = "";
    const steps = 90;
    for (let i = 0; i <= steps; i++) {
      const x = XMIN + ((XMAX - XMIN) * i) / steps;
      const y = Math.min(pdf(x, mu, sigma), 1.15);
      d += `${i === 0 ? "M" : "L"}${sx(x).toFixed(1)} ${sy(y).toFixed(1)} `;
    }
    return d.trim();
  }

  function draw() {
    const mu = Number(muInput.value);
    const sigma = Number(sigmaInput.value);
    const line = pathFor(mu, sigma);
    const base = `L${sx(XMAX).toFixed(1)} ${Y1} L${sx(XMIN).toFixed(1)} ${Y1} Z`;
    curve.setAttribute("d", `${line} ${base}`);
    ghost.setAttribute("d", pathFor(0, 1));
    const mx = sx(Math.min(XMAX, Math.max(XMIN, mu)));
    meanLine.setAttribute("x1", mx);
    meanLine.setAttribute("x2", mx);
    meanLine.setAttribute("y1", Y1);
    meanLine.setAttribute("y2", sy(pdf(mu, mu, sigma)));
    const decimal = window.BukaLabI18n?.lang === "en" ? "." : ",";
    const num = (value, digits) => value.toFixed(digits).replace(".", decimal);
    muVal.textContent = num(mu, 1);
    sigmaVal.textContent = num(sigma, 2).replace(/0$/, "");
    readout.textContent = `N(${num(mu, 1)} ; ${num(sigma, 2)}²)`;
  }

  window.addEventListener("bukalab-lang", draw);

  muInput.addEventListener("input", draw);
  sigmaInput.addEventListener("input", draw);
  draw();
}
