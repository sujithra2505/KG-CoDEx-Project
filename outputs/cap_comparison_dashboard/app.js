/* Cap comparison dashboard. Static: reads window.CAP_DATA from data/cap_results.js,
   which cap_dashboard_build.py writes from the experiment's output files. No numbers live here. */
(function () {
  "use strict";
  const $ = (id) => document.getElementById(id);
  const SVGNS = "http://www.w3.org/2000/svg";
  const D = window.CAP_DATA;

  function banner(cls, text) { const b = $("load-status"); b.className = "banner " + cls; b.textContent = text; }
  if (!D) {
    const failed = (window.UI_FAILED_ASSETS || []).join(", ") || "data/cap_results.js";
    banner("error", `Could not load the results (${failed}). Rebuild with "py cap_dashboard_build.py --replace", ` +
      `or run "py -m http.server 8000" in the project folder and open http://localhost:8000/outputs/cap_comparison_dashboard/index.html`);
    return;
  }

  const fmtInt = (x) => (x == null ? "—" : Number(x).toLocaleString());
  const fmtPct = (x) => (x == null ? "—" : (100 * x).toFixed(2) + "%");
  const key = (cap, v) => `cap${cap}_${v}`;
  const V = D.validation;
  const SEL = D.selection.selected;

  function el(tag, attrs, text) {
    const n = tag.startsWith("svg:") ? document.createElementNS(SVGNS, tag.slice(4)) : document.createElement(tag);
    for (const [k, v] of Object.entries(attrs || {})) n.setAttribute(k, v);
    if (text != null) n.textContent = text;
    return n;
  }

  // ------------------------------------------------------------------ summary
  function card(value, label) {
    const c = el("div", { class: "card" });
    c.append(el("span", { class: "v" }, value), el("span", { class: "k" }, label));
    return c;
  }
  const s = V[SEL].overall;
  $("summary").append(
    card(`cap ${D.selection.selected_cap} · ${D.selection.selected_version}`, "selected on validation (rule " + D.rule.id + ")"),
    card(fmtPct(s.precision), "validation benchmark precision of the selection"),
    card(fmtPct(s.recall), "validation recall of the selection"),
    card(D.test.selected ? fmtPct(D.test.selected.precision) : "not run", "test precision of the selection"),
  );

  // ------------------------------------------------------------------- charts
  const METRICS = [
    ["predictions", "Predictions kept", "all predictions in the configuration", fmtInt],
    ["tp_matched_positives", "Positive matches (TP)", "predictions found in validation positives", fmtInt],
    ["fp_matched_supplied_negatives", "Negative matches (FP)", "predictions found in supplied validation negatives", fmtInt],
    ["unlabelled_predictions", "Unlabelled", "in neither file — not counted as wrong", fmtInt],
    ["precision", "Benchmark precision", "TP / (TP + FP), labelled predictions only", fmtPct],
    ["recall", "Recall", "TP / all validation positives", fmtPct],
    ["f1", "F1", "2TP / (2TP + FP + FN)", fmtPct],
    ["positive_hit_rate", "Positive hit rate", "TP / all predictions (lower bound)", fmtPct],
  ];
  const tip = $("tooltip");
  function showTip(evt, cap, metric, label, fmt) {
    tip.replaceChildren(el("div", { class: "t" }, `${label} · cap ${cap.toLocaleString()}`));
    for (const v of D.versions) {
      const row = el("div", { class: "row" });
      row.append(el("i", { class: `key ${v}` }), el("b", {}, fmt(V[key(cap, v)].overall[metric])), el("span", {}, v + (key(cap, v) === SEL ? " (selected)" : "")));
      tip.append(row);
    }
    tip.hidden = false;
    const r = evt.target.getBoundingClientRect ? evt.target.getBoundingClientRect() : { left: evt.clientX, top: evt.clientY, width: 0 };
    const x = evt.clientX != null && evt.clientX !== 0 ? evt.clientX : r.left + r.width / 2;
    const y = evt.clientY != null && evt.clientY !== 0 ? evt.clientY : r.top + 20;
    tip.style.left = Math.min(window.innerWidth - tip.offsetWidth - 8, x + 12) + "px";
    tip.style.top = Math.max(8, y - tip.offsetHeight - 10) + "px";
  }
  function hideTip() { tip.hidden = true; }

  function niceMax(x) {
    if (!(x > 0)) return 1;
    const p = Math.pow(10, Math.floor(Math.log10(x)));
    for (const m of [1, 1.2, 1.5, 2, 2.5, 3, 4, 5, 6, 8, 10]) if (m * p >= x) return m * p;
    return 10 * p;
  }

  function chart([metric, label, sub, fmt]) {
    const W = 300, H = 170, L = 44, R = 30, T = 10, B = 24;
    const box = el("div", { class: "chart" });
    box.append(el("h3", {}, label), el("p", {}, sub));
    const svg = el("svg:svg", { viewBox: `0 0 ${W} ${H}`, role: "img", "aria-label": `${label} by cap for v1 and v2` });
    const vals = D.caps.flatMap((c) => D.versions.map((v) => V[key(c, v)].overall[metric])).filter((x) => x != null);
    const ymax = niceMax(Math.max(0, ...vals));
    const xs = (i) => L + (i * (W - L - R)) / (D.caps.length - 1);
    const ys = (y) => T + (H - T - B) * (1 - y / ymax);
    for (let k = 0; k <= 4; k++) {
      const y = (ymax * k) / 4;
      svg.append(el("svg:line", { class: "grid", x1: L, x2: W - R, y1: ys(y), y2: ys(y) }));
      svg.append(el("svg:text", { class: "axis-label", x: L - 6, y: ys(y) + 3, "text-anchor": "end" }, fmt === fmtPct ? (100 * y).toFixed(ymax < 0.05 ? 1 : 0) + "%" : fmtInt(Math.round(y))));
    }
    D.caps.forEach((c, i) => svg.append(el("svg:text", { class: "axis-label", x: xs(i), y: H - 6, "text-anchor": "middle" }, c.toLocaleString())));
    const hair = el("svg:line", { class: "hair", y1: T, y2: H - B, visibility: "hidden" });
    svg.append(hair);
    const lastY = D.versions.map((v) => V[key(D.caps[D.caps.length - 1], v)].overall[metric]).map((y) => (y == null ? null : ys(y)));
    const close = lastY[0] != null && lastY[1] != null && Math.abs(lastY[0] - lastY[1]) < 10;
    for (const [vi, v] of D.versions.entries()) {
      const pts = D.caps.map((c, i) => [xs(i), V[key(c, v)].overall[metric]]).filter((p) => p[1] != null).map((p) => [p[0], ys(p[1])]);
      svg.append(el("svg:polyline", { class: `line ${v}`, points: pts.map((p) => p.join(",")).join(" ") }));
      D.caps.forEach((c, i) => {
        const y = V[key(c, v)].overall[metric];
        if (y == null) return;
        svg.append(el("svg:circle", { class: `dot ${v}`, cx: xs(i), cy: ys(y), r: 4 }));
        if (key(c, v) === SEL) svg.append(el("svg:circle", { class: "sel", cx: xs(i), cy: ys(y), r: 8 }));
      });
      const last = pts[pts.length - 1];
      // When both lines end together, stack the labels: v1 above, v2 below.
      const dy = close ? (vi === 0 ? -6 : 10) : 3;
      if (last) svg.append(el("svg:text", { class: "end-label", x: last[0] + 10, y: last[1] + dy }, v));
    }
    D.caps.forEach((c, i) => {
      const half = (W - L - R) / (D.caps.length - 1) / 2;
      const hit = el("svg:rect", { class: "hit", x: xs(i) - half, y: T, width: 2 * half, height: H - T - B, tabindex: 0,
        "aria-label": `${label}, cap ${c}: ` + D.versions.map((v) => `${v} ${fmt(V[key(c, v)].overall[metric])}`).join(", ") });
      const on = (e) => { hair.setAttribute("x1", xs(i)); hair.setAttribute("x2", xs(i)); hair.setAttribute("visibility", "visible"); showTip(e, c, metric, label, fmt); };
      const off = () => { hair.setAttribute("visibility", "hidden"); hideTip(); };
      hit.addEventListener("pointermove", on); hit.addEventListener("pointerleave", off);
      hit.addEventListener("focus", on); hit.addEventListener("blur", off);
      svg.append(hit);
    });
    box.append(svg);
    return box;
  }
  $("charts").append(...METRICS.map(chart));

  // -------------------------------------------------------------------- table
  function table(id, header, rows, selectedKey) {
    const t = $(id);
    const thead = el("thead"), tr = el("tr");
    header.forEach((h) => tr.append(el("th", {}, h)));
    thead.append(tr);
    const tbody = el("tbody");
    for (const [k, cells] of rows) {
      const r = el("tr", k === selectedKey ? { class: "selected" } : {});
      cells.forEach((c) => r.append(el("td", {}, c)));
      tbody.append(r);
    }
    t.replaceChildren(thead, tbody);
  }
  $("rule-text").textContent = `Selection rule ${D.rule.id} (frozen ${D.rule_frozen_at}, before validation): ${D.rule.objective}; ` +
    `subject to: ${D.rule.constraint}. Ties: ${D.rule.tie_break.join(", then ")}.`;
  table("val-table",
    ["Configuration", "Predictions", "Relations still capped", "Positive matches (TP)", "Negative matches (FP)", "Unlabelled",
      "Precision", "Precision 95% lower", "Floor for this version", "Recall", "F1", "Positive hit rate", "Meets rule"],
    D.caps.flatMap((c) => D.versions.map((v) => {
      const k = key(c, v), o = V[k].overall, r = D.selection.table[k];
      return [k, [`cap ${c.toLocaleString()} · ${v}`, fmtInt(o.predictions), fmtInt(V[k].relations_still_capped), fmtInt(o.tp_matched_positives),
        fmtInt(o.fp_matched_supplied_negatives), fmtInt(o.unlabelled_predictions), fmtPct(o.precision), fmtPct(r.precision_wilson_lower),
        fmtPct(r.threshold), fmtPct(o.recall), fmtPct(o.f1), fmtPct(o.positive_hit_rate), r.eligible ? "yes" : "no"]];
    })), SEL);

  const testRows = [];
  for (const v of D.versions) {
    const o = D.test.baseline[v];
    testRows.push([key(D.caps[0], v), [`cap ${D.caps[0]} · ${v} (Phase 6 baseline)`, fmtInt(o.predictions), fmtInt(o.tp_matched_positives),
      fmtInt(o.fp_matched_supplied_negatives), fmtInt(o.unlabelled_predictions), fmtPct(o.precision), fmtPct(o.recall), fmtPct(o.f1), fmtPct(o.positive_hit_rate)]]);
  }
  const so = D.test.selected;
  testRows.push([SEL, [`cap ${D.selection.selected_cap} · ${D.selection.selected_version} (selected)`].concat(so
    ? [fmtInt(so.predictions), fmtInt(so.tp_matched_positives), fmtInt(so.fp_matched_supplied_negatives), fmtInt(so.unlabelled_predictions),
      fmtPct(so.precision), fmtPct(so.recall), fmtPct(so.f1), fmtPct(so.positive_hit_rate)]
    : ["awaiting approval", "", "", "", "", "", "", ""])]);
  table("test-table", ["Configuration", "Predictions", "Positive test matches (TP)", "Supplied-negative matches (FP)", "Unlabelled",
    "Precision", "Recall", "F1", "Positive hit rate"], testRows, null);
  $("test-note").textContent = so
    ? `Final test evaluation of the selected configuration, generated ${D.test.selected_generated_at}. This is the second use of the test split (the first was Phase 6); nothing may be tuned on it.`
    : "The final test evaluation of the selected configuration has not been run. It is gated and runs only after explicit approval " +
      "(py cap_experiment.py test --i-approve-cap-test-evaluation), then rebuild this page.";

  for (const src of D.sources) {
    const li = el("li");
    li.append(el("code", {}, src.path), document.createTextNode(` — sha256 ${src.sha256.slice(0, 16)}…`));
    $("sources").append(li);
  }
  document.body.dataset.uiState = "ready";
  banner("ok", `Loaded results for ${D.caps.length * D.versions.length} configurations (built ${D.built_at}).`);
})();
