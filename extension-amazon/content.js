(() => {
  const HOST_ID = "thred-sidebar-host";
  const SIDEBAR_WIDTH = 420;
  const existing = document.getElementById(HOST_ID);
  const body = document.body;
  const originalBodyWidth = body.style.width;
  const originalBodyMarginRight = body.style.marginRight;
  const originalBodyTransition = body.style.transition;

  if (existing) {
    const open = existing.hidden;
    existing.hidden = !open;
    if (open && window.innerWidth > 520) {
      body.style.transition = "width 220ms ease, margin-right 220ms ease";
      body.style.width = `calc(100% - ${SIDEBAR_WIDTH}px)`;
    } else {
      body.style.width = existing.dataset.originalWidth || "";
      body.style.marginRight = existing.dataset.originalMarginRight || "";
      body.style.transition = existing.dataset.originalTransition || "";
    }
    return;
  }

  // Keep the page's own inline layout intact so closing the panel restores it exactly.
  function setOpen(panelHost, open) {
    panelHost.hidden = !open;
    if (!body) return;
    if (open && window.innerWidth > 520) {
      body.style.transition = "width 220ms ease, margin-right 220ms ease";
      body.style.width = `calc(100% - ${SIDEBAR_WIDTH}px)`;
    } else {
      body.style.width = originalBodyWidth;
      body.style.marginRight = originalBodyMarginRight;
      body.style.transition = originalBodyTransition;
    }
  }

  const host = document.createElement("aside");
  host.id = HOST_ID;
  host.dataset.originalWidth = originalBodyWidth;
  host.dataset.originalMarginRight = originalBodyMarginRight;
  host.dataset.originalTransition = originalBodyTransition;
  host.setAttribute("aria-label", "Thred sustainability sidebar");
  document.documentElement.appendChild(host);
  const root = host.attachShadow({ mode: "open" });

  root.innerHTML = `
    <style>
      :host { all: initial; position: fixed; inset: 0 0 0 auto; z-index: 2147483647; width: min(420px, 100vw); font-family: Arial, Helvetica, sans-serif; color: #18302a; }
      :host([hidden]) { display: none !important; }
      * { box-sizing: border-box; }
      .panel { height: 100vh; overflow-y: auto; background: #fbfdfb; border-left: 1px solid #dce8e2; box-shadow: -16px 0 40px rgba(17, 58, 46, .14); }
      header { height: 72px; padding: 0 20px; display: flex; align-items: center; justify-content: space-between; background: white; border-bottom: 1px solid #e6ece8; position: sticky; top: 0; z-index: 2; }
      .header-title { font-size: 18px; font-weight: 700; }
      button { border: 0; background: transparent; cursor: pointer; color: #5b6b65; font-size: 24px; width: 40px; height: 40px; border-radius: 6px; }
      button:hover { background: #eef5f1; }
      main { padding: 22px 18px 34px; }
      .eyebrow { margin: 0 0 6px; color: #63756d; font-size: 13px; font-weight: 700; text-transform: uppercase; letter-spacing: .08em; }
      .score-row { display: flex; justify-content: space-between; align-items: end; gap: 20px; }
      h1 { margin: 0; font-size: 22px; }
      .score { color: #d49b05; font-size: 42px; line-height: 1; font-weight: 800; }
      .score small { color: #63756d; font-size: 14px; }
      .meter { height: 8px; margin: 18px 0 8px; border-radius: 99px; background: linear-gradient(90deg, #cf4c52, #e4af1a 50%, #2a955d); position: relative; }
      .meter::after { content: ''; position: absolute; width: 18px; height: 18px; border: 3px solid white; border-radius: 50%; background: #e4af1a; left: 48%; top: 50%; transform: translate(-50%, -50%); box-shadow: 0 1px 5px #8c781f66; }
      .labels { display: flex; justify-content: space-between; color: #75847e; font-size: 12px; }
      .notice { margin: 20px 0; padding: 14px; display: flex; gap: 10px; border-radius: 6px; background: #eaf6ef; color: #265d46; font-size: 14px; line-height: 1.45; }
      .card { background: white; border: 1px solid #dfe8e3; border-radius: 8px; box-shadow: 0 4px 14px rgba(17, 58, 46, .05); }
      .item { padding: 16px; display: grid; grid-template-columns: 52px 1fr auto; gap: 12px; align-items: start; }
      .item + .item { border-top: 1px solid #e7ede9; }
      .thumb { width: 52px; height: 64px; border-radius: 6px; background: #eef2ef; display: grid; place-items: center; font-size: 25px; }
      h2, h3, p { margin: 0; }
      h3 { font-size: 15px; line-height: 1.35; }
      .store { margin-top: 3px; color: #71817b; font-size: 12px; }
      .item-score { color: #25845a; font-weight: 800; font-size: 20px; }
      .item-score.low { color: #c46824; }
      .bar-row { margin-top: 10px; display: grid; grid-template-columns: 54px 1fr 32px; gap: 7px; align-items: center; font-size: 11px; color: #66766f; }
      .bar { height: 5px; background: #e9eeeb; border-radius: 9px; overflow: hidden; }
      .fill { display: block; height: 100%; width: 72%; background: #499e62; border-radius: inherit; }
      .fill.low { width: 31%; background: #d47d2b; }
      .tag { grid-column: 2 / -1; margin-top: 8px; color: #3c805d; font-size: 12px; }
      .tag.warn { color: #b45e25; }
      .section-title { display: flex; justify-content: space-between; margin: 24px 0 10px; align-items: center; }
      .section-title h2 { font-size: 17px; }
      .section-title span { color: #176b50; font-size: 13px; font-weight: 700; }
      .alternative { padding: 14px; display: grid; grid-template-columns: 70px 1fr; gap: 14px; }
      .alternative .thumb { width: 70px; height: 88px; }
      .pill { display: inline-block; margin-top: 8px; padding: 4px 7px; background: #e7f5ec; color: #26704e; font-size: 11px; border-radius: 4px; }
      .cta { margin-top: 12px; width: auto; height: 36px; padding: 0 14px; background: #176b50; color: white; font-size: 13px; font-weight: 700; }
      footer { margin-top: 24px; padding-top: 16px; border-top: 1px solid #e0e8e3; color: #77857f; font-size: 11px; text-align: center; }
      @media (max-width: 520px) { :host { width: 100vw; } }
    </style>
    <section class="panel">
      <header><div class="header-title">Cart impact</div><button id="close" aria-label="Close sidebar">×</button></header>
      <main>
        <p class="eyebrow">Cart impact summary · 2 items</p>
        <div class="score-row"><h1>Your cart score</h1><div class="score">50<small>/100</small></div></div>
        <div class="meter"></div><div class="labels"><span>Higher impact</span><span>Lower impact</span></div>
        <div class="notice"><span>🌿</span><span>Placeholder insight: choosing higher-scoring items may reduce your cart’s environmental impact.</span></div>
        <div class="card">
          <article class="item"><div class="thumb">ph</div><div><h3>Placeholder clothing item</h3><p class="store">Amazon · Sample brand</p><div class="bar-row"><span>Materials</span><span class="bar"><i class="fill"></i></span><b>24</b></div><p class="tag">Lower-impact material placeholder</p></div><div class="item-score">72</div></article>
          <article class="item"><div class="thumb">ph</div><div><h3>Placeholder clothing item</h3><p class="store">Amazon · Sample brand</p><div class="bar-row"><span>Materials</span><span class="bar"><i class="fill low"></i></span><b>10</b></div><p class="tag warn">Alternative available placeholder</p></div><div class="item-score low">28</div></article>
        </div>
        <div class="section-title"><h2>Better alternative</h2><span>See all</span></div>
        <article class="card alternative"><div class="thumb">alt</div><div><h3>Suggested item placeholder</h3><p class="store">Example marketplace</p><span class="pill">Better choice</span><br/><button class="cta">View placeholder</button></div></article>
        <footer>Placeholder sustainability information for demonstration only.</footer>
      </main>
    </section>`;

  root.getElementById("close")?.addEventListener("click", () => setOpen(host, false));

  chrome.runtime.onMessage.addListener((message) => {
    if (message?.type === "THRED_TOGGLE") setOpen(host, host.hidden);
  });

  window.addEventListener("resize", () => {
    if (!host.hidden) setOpen(host, true);
  });
})();
