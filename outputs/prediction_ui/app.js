/* CoDEx-M prediction explorer. Static: reads data/*.js written by phase5_ui_build.py.
   Opening this page never runs an evaluation; the Phase 6 tab only displays results
   written by `py phase6_evaluate.py --i-approve-phase6-test-evaluation`, if they exist. */
(function () {
  "use strict";
  const UF = window.UIFilters;
  const EVAL_DIR = "../phase6/evaluation_test/";
  const PAGE = 50, GRAPH_PRED_LIMIT = 250, GRAPH_TRAIN_LIMIT = 150;
  const S = {
    index: null, rows: [], byPid: new Map(), ent: new Map(), rel: {}, prov: {}, provWait: {}, train: {}, trainWait: {},
    entity: null, focus: null, network: null, tableSort: { key: "rank", dir: "asc" }, tablePage: 1, comparePage: 1,
    evalState: "unknown", evalPage: 1, evalLabels: null,
  };
  const L = { entity: (id) => S.ent.get(id) || id, relation: (r) => S.rel[r] || r };
  const $ = (id) => document.getElementById(id);
  const esc = (t) => String(t == null ? "" : t).replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  const tierColor = { high: "#2e7d32", mid: "#ef6c00", low: "#c62828" };
  const ent = (id) => `${esc(L.entity(id))} <span class="muted">(${esc(id)})</span>`;
  const relTxt = (r) => `${esc(L.relation(r))} <span class="muted">(${esc(r)})</span>`;
  const scoreTxt = (s) => `<span class="score-${UF.scoreTier(s)}">${s.toFixed(3)}</span>`;
  const SERVER_HINT = `If your browser blocks local files, start a local server in the project folder with
    <code>py -m http.server 8000</code> and open
    <a href="http://localhost:8000/outputs/prediction_ui/index.html">http://localhost:8000/outputs/prediction_ui/index.html</a>.`;
  const NO_MATCH = "No predictions match the current filters. Clear the Text box, widen the Score range or choose “all relations”.";

  // ------------------------------------------------------- load state & errors
  function banner(cls, html) {
    const el = $("load-status");
    el.className = "banner " + cls;
    el.innerHTML = html;
  }
  function fail(html) {
    document.body.dataset.uiState = "error";
    banner("error", html);
    if (!S.index) $("graph").innerHTML = `<div class="empty">No data loaded — see the red message above.</div>`;
  }
  function loadFailureHtml() {
    const failed = window.UI_FAILED_ASSETS || [];
    let html = "<b>Could not load the prediction data.</b> ";
    if (/\/prediction_ui_src\//.test(location.pathname)) {
      html += "This is the <code>prediction_ui_src</code> template, which has no <code>data/</code> or <code>lib/</code> folder. " +
        "Open <code>outputs/prediction_ui/index.html</code> instead. ";
    } else if (failed.length) {
      html += `These files did not load: ${failed.map((f) => `<code>${esc(f)}</code>`).join(", ")} (expected next to this page). `;
    } else if (!UF) {
      html += "<code>filters.js</code> did not run. ";
    } else {
      html += "<code>data/index.js</code> did not deliver any data. ";
    }
    return html + SERVER_HINT;
  }
  window.addEventListener("error", (e) => {
    if (e.message && !/ResizeObserver/.test(e.message)) fail(`<b>JavaScript error:</b> ${esc(e.message)} <span class="muted">(${esc((e.filename || "").split("/").pop())}:${e.lineno})</span>. ` +
      "Reload the page; if it persists, report this message.");
  });
  window.addEventListener("load", () => { if (!S.index && document.body.dataset.uiState !== "error") fail(loadFailureHtml()); });
  document.body.dataset.uiState = "loading";
  window.__UI_DEBUG = { graphEdges: () => (S.graphData ? S.graphData.edges.length : 0) };

  function loadScript(src, onerror, onload) {
    const el = document.createElement("script");
    el.src = src;
    if (onerror) el.onerror = onerror;
    if (onload) el.onload = onload;
    document.body.appendChild(el);
  }

  window.UI_INDEX_LOADED = function (data) {
    try {
      if (!UF) throw new Error("filters.js did not load");
      if (!data || !Array.isArray(data.rows) || !Array.isArray(data.entities)) throw new Error("data/index.js has an unexpected format");
      S.index = data;
      S.rel = data.relations;
      for (const [id, label] of data.entities) S.ent.set(id, label);
      S.rows = data.rows.map(UF.toRow);
      for (const r of S.rows) S.byPid.set(r.pid, r);
      init();
      document.body.dataset.uiState = "ready";
      banner("ok", `Loaded ${S.rows.length.toLocaleString()} predicted triples (v1 ${data.comparison.summary.v1_total.toLocaleString()} · ` +
        `v2 ${data.comparison.summary.v2_total.toLocaleString()}) and ${data.entities.length.toLocaleString()} entities.` +
        (typeof vis === "undefined" ? " <b>The graph library did not load; the graph tab is unavailable.</b>" : ""));
    } catch (err) {
      fail(`<b>Could not start the explorer:</b> ${esc(err.message)}. ` + loadFailureHtml());
    }
  };
  window.UI_PROV_LOADED = function (rel, prov) {
    S.prov[rel] = prov;
    (S.provWait[rel] || []).forEach((cb) => cb(prov));
    delete S.provWait[rel];
  };
  window.UI_TRAIN_LOADED = function (bucket, adj) {
    S.train[bucket] = adj;
    (S.trainWait[bucket] || []).forEach((cb) => cb(adj));
    delete S.trainWait[bucket];
  };
  function withProv(rel, cb) {
    if (S.prov[rel]) return cb(S.prov[rel]);
    const first = !S.provWait[rel];
    (S.provWait[rel] = S.provWait[rel] || []).push(cb);
    if (first) loadScript(`data/prov/${rel}.js`, () => {
      const msg = `<span class="error-text">Could not load <code>data/prov/${esc(rel)}.js</code> (provenance).</span> ${SERVER_HINT}`;
      setStatus("graph-status", msg);
      $("detail").innerHTML = `<p>${msg}</p>`;
      delete S.provWait[rel];
    });
  }
  function withTrain(entity, cb) {
    const b = Number(entity.slice(1)) % S.index.meta.buckets;
    const done = (adj) => cb(adj[entity] || []);
    if (S.train[b]) return done(S.train[b]);
    const first = !S.trainWait[b];
    (S.trainWait[b] = S.trainWait[b] || []).push(done);
    const file = `data/train/b${String(b).padStart(2, "0")}.js`;
    if (first) loadScript(file, () => {
      setStatus("graph-status", `<span class="error-text">Could not load training edges (<code>${file}</code>).</span> ${SERVER_HINT}`);
      delete S.trainWait[b];
    });
  }
  function setStatus(id, html) { $(id).innerHTML = html; }

  function filter() {
    const top = $("f-top").value;
    return {
      version: $("f-version").value, relation: $("f-relation").value,
      minScore: parseFloat($("f-min").value || "0"), maxScore: parseFloat($("f-max").value || "1"),
      topN: top ? Number(top) : null, query: $("f-query").value, entity: S.entity,
    };
  }
  function uniqueByPid(items) {
    const seen = new Map();
    for (const it of items) {
      const prev = seen.get(it.row.pid);
      if (!prev || it.rank < prev.rank) seen.set(it.row.pid, it);
    }
    return [...seen.values()].sort((a, b) => a.rank - b.rank || Number(a.row.r.slice(1)) - Number(b.row.r.slice(1)) || (a.row.pid < b.row.pid ? -1 : 1));
  }

  // ------------------------------------------------------------------ init & tabs
  function init() {
    const relSel = $("f-relation");
    const predRels = [...new Set(S.rows.map((r) => r.r))].sort((a, b) => Number(a.slice(1)) - Number(b.slice(1)));
    relSel.innerHTML += predRels.map((r) => `<option value="${esc(r)}">${esc(L.relation(r))} (${esc(r)})</option>`).join("");
    document.querySelectorAll("#tabs button").forEach((b) => (b.onclick = () => showTab(b.dataset.tab)));
    ["f-version", "f-relation", "f-min", "f-max", "f-top"].forEach((id) => ($(id).onchange = refresh));
    let t; $("f-query").oninput = () => { clearTimeout(t); t = setTimeout(refresh, 250); };
    let t3; ["f-min", "f-max"].forEach((id) => ($(id).oninput = () => { clearTimeout(t3); t3 = setTimeout(refresh, 300); }));
    const box = $("f-entity"), sug = $("entity-suggest");
    const pick = (id) => { setEntity(id); sug.innerHTML = ""; box.value = ""; };
    const suggest = () => {
      const q = box.value.trim();
      if (!q) { sug.innerHTML = ""; return []; }
      const hits = UF.searchEntities(S.index.entities, q, 20);
      sug.innerHTML = hits.length
        ? hits.map((h) => `<li data-id="${esc(h.id)}" role="option">${esc(h.label)} <span class="muted">(${esc(h.id)})</span></li>`).join("") +
          `<li class="hint">Click a name or press Enter for the first one.</li>`
        : `<li class="empty">No entity matches “${esc(q)}”.</li>`;
      sug.querySelectorAll("li[data-id]").forEach((li) => (li.onclick = () => pick(li.dataset.id)));
      return hits;
    };
    let t2; box.oninput = () => { clearTimeout(t2); t2 = setTimeout(suggest, 200); };
    box.onkeydown = (e) => {
      if (e.key === "Enter") { e.preventDefault(); clearTimeout(t2); const hits = suggest(); if (hits.length) pick(hits[0].id); }
      else if (e.key === "Escape") sug.innerHTML = "";
    };
    document.querySelectorAll("#pred-table th[data-sort]").forEach((th) => (th.onclick = () => {
      const k = th.dataset.sort;
      S.tableSort = { key: k, dir: S.tableSort.key === k && S.tableSort.dir === "asc" ? "desc" : "asc" };
      S.tablePage = 1; renderTable();
    }));
    $("c-class").onchange = () => { S.comparePage = 1; renderCompare(); };
    refresh();
  }
  function showTab(name) {
    document.querySelectorAll("#tabs button").forEach((b) => b.classList.toggle("active", b.dataset.tab === name));
    document.querySelectorAll(".tab").forEach((t) => t.classList.toggle("active", t.id === "tab-" + name));
    if (name === "evaluation") loadEvaluation();
    if (name === "graph" && S.network) S.network.redraw();
  }
  function setEntity(id) {
    S.entity = id; S.focus = null;
    $("entity-chip").innerHTML = id ? `${ent(id)} <button id="clear-entity">clear</button>` : "";
    if (id) $("clear-entity").onclick = () => setEntity(null);
    S.tablePage = 1; S.comparePage = 1;
    refresh();
  }
  function refresh() { renderGraph(); renderTable(); renderCompare(); if (S.evalState === "complete") renderEvalTable(); }

  // ---------------------------------------------------------------------- graph
  function predEdge(it) {
    const r = it.row, tier = UF.scoreTier(r.score);
    const ver = [r.v1 ? `v1 #${r.v1.rank}` : "", r.v2 ? `v2 #${r.v2.rank}` : ""].filter(Boolean).join(", ");
    return { id: "p:" + r.pid, from: r.s, to: r.o, dashes: true, width: 1 + 4 * r.score, color: { color: tierColor[tier] },
      label: L.relation(r.r), title: `PREDICTED (not a training fact)\n${L.entity(r.s)} (${r.s}) → ${L.relation(r.r)} (${r.r}) → ${L.entity(r.o)} (${r.o})\nscore ${r.score} | ${ver}` };
  }
  function trainEdge(t, i) {
    return { id: "t:" + i + ":" + t.join("|"), from: t[0], to: t[2], dashes: false, width: 1, color: { color: "#94a3b8" },
      label: L.relation(t[1]), title: `TRAINING FACT\n${L.entity(t[0])} (${t[0]}) → ${L.relation(t[1])} (${t[1]}) → ${L.entity(t[2])} (${t[2]})` };
  }
  function graphMessage(html) {
    if (S.network) { S.network.destroy(); S.network = null; }
    S.graphData = null;
    $("graph").innerHTML = `<div class="empty">${html}</div>`;
  }
  function draw(nodesIds, edges) {
    if (typeof vis === "undefined") {
      return graphMessage(`The graph library <code>lib/vis-network.js</code> did not load, so the graph cannot be drawn. The other tabs still work. ${SERVER_HINT}`);
    }
    const nodes = [...nodesIds].map((id) => ({ id, label: L.entity(id), title: `${L.entity(id)} (${id})`,
      color: id === S.entity ? { background: "#1d4ed8", border: "#1e3a8a" } : undefined, font: id === S.entity ? { color: "#1d4ed8" } : undefined }));
    const data = { nodes: new vis.DataSet(nodes), edges: new vis.DataSet(edges) };
    const options = { nodes: { shape: "dot", size: 11, font: { size: 12 } }, edges: { arrows: { to: { enabled: true, scaleFactor: 0.55 } }, font: { size: 9, align: "middle" }, smooth: false },
      physics: { solver: "barnesHut", stabilization: { iterations: 120 } }, interaction: { hover: true, navigationButtons: true },
      layout: { improvedLayout: false } };
    if (S.network) S.network.destroy();
    $("graph").innerHTML = "";
    S.graphData = data;
    S.network = new vis.Network($("graph"), data, options);
    S.network.on("click", (ev) => {
      if (ev.edges.length && String(ev.edges[0]).startsWith("p:")) showDetail(String(ev.edges[0]).slice(2));
      else if (ev.nodes.length && !ev.edges.length) setEntity(ev.nodes[0]);
    });
  }
  function renderGraph() {
    if (S.focus) return drawFocus(S.focus);
    const f = filter();
    const preds = uniqueByPid(UF.filterItems(S.rows, f, L));
    if (S.entity) {
      setStatus("graph-status", `Loading training edges for ${ent(S.entity)}…`);
      const want = S.entity;
      withTrain(S.entity, (train) => {
        if (S.entity !== want || S.focus) return;
        const tr = train.filter((t) => !f.relation || t[1] === f.relation);
        if (!tr.length && !preds.length) {
          graphMessage(`No training or predicted edges for ${ent(S.entity)} match the current filters.`);
          setStatus("graph-status", `Entity ${ent(S.entity)}: ${NO_MATCH}`);
          return;
        }
        const shownT = tr.slice(0, GRAPH_TRAIN_LIMIT), shownP = preds.slice(0, GRAPH_PRED_LIMIT);
        const nodes = new Set([S.entity]);
        shownT.forEach((t) => { nodes.add(t[0]); nodes.add(t[2]); });
        shownP.forEach((it) => { nodes.add(it.row.s); nodes.add(it.row.o); });
        draw(nodes, shownT.map(trainEdge).concat(shownP.map(predEdge)));
        const out = tr.filter((t) => t[0] === S.entity).length;
        setStatus("graph-status", `Entity ${ent(S.entity)}: <b>${tr.length}</b> training edges (${out} outgoing, ${tr.length - out} incoming${f.relation ? ", relation filter applied" : ""}), showing ${shownT.length}; ` +
          `<b>${preds.length}</b> predicted edges match the filters (${preds.filter((p) => p.row.s === S.entity).length} outgoing), showing ${shownP.length}.`);
      });
      return;
    }
    if (!preds.length) {
      graphMessage(esc(NO_MATCH));
      setStatus("graph-status", esc(NO_MATCH));
      return;
    }
    const shown = preds.slice(0, GRAPH_PRED_LIMIT);
    const nodes = new Set();
    shown.forEach((it) => { nodes.add(it.row.s); nodes.add(it.row.o); });
    draw(nodes, shown.map(predEdge));
    setStatus("graph-status", `<b>${preds.length}</b> predicted triples match the filters; showing the ${shown.length} best-ranked. ` +
      `Pick an entity (search box or click a node) to see its training edges too. Training edges are loaded per entity on demand.`);
  }
  function drawFocus(pid) {
    const row = S.byPid.get(pid);
    withProv(row.r, (prov) => {
      const p = prov[pid];
      const tri = new Map();
      p.supporting_rules.forEach((sr) => sr.body_groundings.slice(0, 20).forEach((g) => g.forEach((t) => tri.set(t.join("|"), t))));
      const ts = [...tri.values()];
      const nodes = new Set([row.s, row.o]);
      ts.forEach((t) => { nodes.add(t[0]); nodes.add(t[2]); });
      draw(nodes, ts.map(trainEdge).concat([predEdge({ row, rank: 0 })]));
      setStatus("graph-status", `Evidence view for one prediction: the dashed edge is predicted; solid edges are the training facts in its rule groundings (up to 20 per rule). <button id="back-graph">back to filtered view</button>`);
      $("back-graph").onclick = () => { S.focus = null; renderGraph(); };
    });
  }

  // --------------------------------------------------------------------- detail
  function showDetail(pid, opts) {
    const row = S.byPid.get(pid);
    if (!row) return;
    $("detail").innerHTML = `<p class="muted">Loading provenance…</p>`;
    withProv(row.r, (prov) => {
      const p = prov[pid];
      const evalLabel = S.evalLabels ? S.evalLabels.get(pid) : null;
      let html = `<span class="badge pred">PREDICTED — not a training fact</span>` +
        (evalLabel ? Object.entries(evalLabel).map(([v, l]) => `<span class="badge ${esc(l[0])}">${v}: ${esc(l[0])}${l[1] ? " (" + esc(l[1]) + ")" : ""}</span>`).join("") : "") +
        `<h4>Triple</h4><div>${ent(row.s)}<br>&rarr; <b>${relTxt(row.r)}</b> &rarr;<br>${ent(row.o)}</div>` +
        `<h4>Ranking</h4><div>Score (${esc(p.ranking_score.name)}): ${scoreTxt(row.score)} from rule <code>${esc(p.ranking_score.from_rule_id)}</code><br>` +
        `v1 rank: ${row.v1 ? "#" + row.v1.rank : "not retained"} &nbsp; v2 rank: ${row.v2 ? "#" + row.v2.rank : "not retained"} (within ${esc(row.r)})<br>` +
        `Inference round: ${esc(p.round)} &nbsp; Supporting rules: ${row.nrules} &nbsp; Distinct evidence matches: ${row.evidence}<br>` +
        `Prediction ID: <code>${esc(pid)}</code></div>` +
        `<p class="muted">The score is a rule statistic from training data, not a probability and not proof.</p>` +
        `<h4>Supporting rules and training evidence</h4>`;
      p.supporting_rules.forEach((sr, i) => {
        const gs = sr.body_groundings;
        html += `<div class="rule"><code>${esc(sr.rule_id)}</code> <span class="badge">${esc(sr.type)}</span><br><code>${esc(sr.rule)}</code><br>` +
          `<span class="muted">${esc(sr.display)}</span><br>std conf ${sr.std_confidence} · PCA ${sr.pca_confidence} · Wilson ${sr.wilson_lower} · support ${sr.support} (${esc(sr.counting)})<br>` +
          `${sr.grounding_count} grounding(s):<ul>` + gs.slice(0, 10).map((g) => `<li>${g.map((t) => `${ent(t[0])} —${esc(t[1])}→ ${ent(t[2])}`).join("<br>")}</li>`).join("") + `</ul>` +
          (gs.length > 10 ? `<button data-more="${i}">show all ${gs.length}</button>` : "") + `</div>`;
      });
      html += `<p><button id="focus-btn">Show this evidence in the graph</button></p>`;
      $("detail").innerHTML = html;
      $("detail").querySelectorAll("button[data-more]").forEach((b) => (b.onclick = () => {
        const sr = p.supporting_rules[Number(b.dataset.more)];
        b.outerHTML = `<ul>${sr.body_groundings.slice(10).map((g) => `<li>${g.map((t) => `${ent(t[0])} —${esc(t[1])}→ ${ent(t[2])}`).join("<br>")}</li>`).join("")}</ul>`;
      }));
      $("focus-btn").onclick = () => { S.focus = pid; showTab("graph"); renderGraph(); };
      if (opts && opts.openGraph) showTab("graph");
    });
  }

  // ---------------------------------------------------------------------- table
  function renderTable() {
    const items = UF.sortItems(UF.filterItems(S.rows, filter(), L), S.tableSort.key, S.tableSort.dir, L);
    const pg = UF.paginate(items, S.tablePage, PAGE);
    S.tablePage = pg.page;
    document.querySelectorAll("#pred-table th[data-sort]").forEach((th) => {
      th.classList.toggle("sorted-asc", th.dataset.sort === S.tableSort.key && S.tableSort.dir === "asc");
      th.classList.toggle("sorted-desc", th.dataset.sort === S.tableSort.key && S.tableSort.dir === "desc");
    });
    $("pred-table").querySelector("tbody").innerHTML = pg.items.length ? pg.items.map((it) => {
      const r = it.row;
      return `<tr data-pid="${esc(r.pid)}"><td>${ent(r.s)}</td><td>${relTxt(r.r)}</td><td>${ent(r.o)}</td><td>${it.version}</td>` +
        `<td>${scoreTxt(r.score)}</td><td>${it.rank}</td><td>${r.nrules}</td><td>${r.evidence}</td><td><a href="#" data-pid="${esc(r.pid)}">view</a></td></tr>`;
    }).join("") : emptyRow(9, NO_MATCH);
    $("pred-table").querySelectorAll("tbody tr[data-pid]").forEach((tr) => (tr.onclick = (e) => { e.preventDefault(); showDetail(tr.dataset.pid, { openGraph: true }); }));
    setStatus("table-status", items.length ? `${items.length} rows (one row per prediction and version). Click a row for provenance.` : esc(NO_MATCH));
    pager("table-pager", pg, (p) => { S.tablePage = p; renderTable(); });
  }
  function emptyRow(cols, text) { return `<tr class="empty"><td colspan="${cols}">${esc(text)}</td></tr>`; }
  function pager(id, pg, go) {
    $(id).innerHTML = `<button ${pg.page <= 1 ? "disabled" : ""} data-p="${pg.page - 1}">prev</button> page ${pg.page} of ${pg.pages} <button ${pg.page >= pg.pages ? "disabled" : ""} data-p="${pg.page + 1}">next</button>`;
    $(id).querySelectorAll("button").forEach((b) => (b.onclick = () => go(Number(b.dataset.p))));
  }

  // ------------------------------------------------------------------ comparison
  function hist(bins) {
    const max = Math.max(1, ...bins);
    return `<span class="hist" title="score bins 0–1 in steps of 0.1: ${bins.join(", ")}">${bins.map((b) => `<i style="height:${Math.round(28 * b / max)}px"></i>`).join("")}</span>`;
  }
  function renderCompare() {
    const c = S.index.comparison, s = c.summary;
    $("compare-summary").innerHTML = [["Predictions in v1", s.v1_total], ["Predictions in v2", s.v2_total], ["Kept in both", s.both],
      ["Only in v1 (dropped)", s.v1_only], ["Only in v2 (added)", s.v2_only], ["Rank changed (in both)", s.rank_changed]]
      .map(([k, v]) => `<div class="card"><b>${v}</b>${k}</div>`).join("") +
      `<div class="card muted">Counts confirmed against<br><code>${esc(s.confirmed_by)}</code></div>`;
    const f = filter();
    const items = uniqueByPid(UF.filterItems(S.rows, { ...f, version: "all", topN: null, compare: $("c-class").value }, L));
    const pg = UF.paginate(items, S.comparePage, PAGE);
    S.comparePage = pg.page;
    $("compare-table").querySelector("tbody").innerHTML = pg.items.length ? pg.items.map((it) => {
      const r = it.row;
      return `<tr data-pid="${esc(r.pid)}"><td>${ent(r.s)}</td><td>${relTxt(r.r)}</td><td>${ent(r.o)}</td><td>${scoreTxt(r.score)}</td>` +
        `<td>${r.v1 ? r.v1.rank : "—"}</td><td>${r.v2 ? r.v2.rank : "—"}</td><td>${r.evidence}</td><td>${r.nrules}</td></tr>`;
    }).join("") : emptyRow(8, "No predictions in this group match the current filters.");
    $("compare-table").querySelectorAll("tbody tr[data-pid]").forEach((tr) => (tr.onclick = () => showDetail(tr.dataset.pid, { openGraph: true })));
    pager("compare-pager", pg, (p) => { S.comparePage = p; renderCompare(); });
    $("compare-relations").querySelector("tbody").innerHTML = Object.entries(c.per_relation).map(([rel, v]) =>
      `<tr><td>${relTxt(rel)}</td><td>${v.v1}</td><td>${v.v2}</td><td>${v.both}</td><td>${v.v1_only}</td><td>${v.v2_only}</td><td>${v.rank_changed}</td><td>${hist(v.hist_v1)}</td><td>${hist(v.hist_v2)}</td></tr>`).join("");
  }

  // ------------------------------------------------------------------ evaluation
  function loadEvaluation() {
    if (S.evalState !== "unknown") return;
    S.evalState = "loading";
    renderEvalStatusOnly("Checking for existing evaluation results (read-only)…");
    loadScript(EVAL_DIR + "evaluation_results.js",
      () => { S.evalState = "not_run"; renderEvaluation(); },
      () => { S.evalState = UF.evaluationStatus(window.PHASE6_RESULTS); renderEvaluation(); });
  }
  function renderEvalStatusOnly(msg) { $("eval-root").innerHTML = `<p class="muted">${esc(msg)}</p>`; }
  const DEFS = [
    ["Benchmark universe U", "test positives (data/test.txt) ∪ supplied test negatives (data/test_negatives.txt). Only triples in U have labels."],
    ["TP", "predictions that are test positives"], ["FP", "predictions that are supplied test negatives (not merely unobserved)"],
    ["Unlabelled", "predictions in neither file. Not counted as false; reported separately"],
    ["Precision", "TP / (TP + FP) — over labelled predictions only"],
    ["Recall", "TP / number of test positives (all relations)"], ["F1", "harmonic mean of the precision and recall above"],
    ["Specificity", "supplied negatives not predicted / number of supplied negatives"],
    ["Labelled coverage", "(TP + FP) / all predictions — how many predictions the benchmark can judge at all"],
    ["Positive hit rate", "TP / all predictions — a lower bound: unlabelled predictions may still be true"],
    ["Recall ceiling under cap", "Σ over relations of min(predictions, test positives) / test positives"],
  ];
  function renderEvaluation() {
    const root = $("eval-root");
    if (S.evalState !== "complete") {
      root.innerHTML = `<div class="notice"><b>Phase 6 evaluation has not been run.</b> Opening this page never runs it.
        The dashboard only displays results written by a separate, explicitly approved command.</div>
        <h3>Planned protocol (summary — full text in <code>outputs/phase6/phase6_protocol.md</code>)</h3>
        <ul><li>Predictions: the existing v1 and v2 files, unchanged (3,239 each), both made from the training graph only.</li>
        <li>Held-out split: test positives and the supplied test negatives. Validation is not used to tune anything.</li>
        <li>Each prediction is labelled <span class="badge test_positive">test_positive</span>, <span class="badge test_negative">test_negative</span> or
        <span class="badge unlabelled">unlabelled</span>. Unlabelled predictions are <b>not</b> treated as false.</li>
        <li>Metrics are computed over the benchmark universe with explicit denominators (see definitions below).</li></ul>
        <dl class="defs">${DEFS.map(([k, v]) => `<dt>${esc(k)}</dt><dd>${esc(v)}</dd>`).join("")}</dl>
        <p>To run after approval (from the project folder): <code>py phase6_evaluate.py --i-approve-phase6-test-evaluation</code>, then reload this page.</p>`;
      return;
    }
    const R = window.PHASE6_RESULTS;
    S.evalLabels = new Map();
    for (const v of ["v1", "v2"]) for (const [pid, label, note] of R.versions[v].labels) {
      const m = S.evalLabels.get(pid) || {}; m[v] = [label, note]; S.evalLabels.set(pid, m);
    }
    const o1 = R.versions.v1.overall, o2 = R.versions.v2.overall;
    const fmt = (x) => (x == null ? "n/a" : typeof x === "number" && !Number.isInteger(x) ? x.toFixed(4) : x);
    const keys = ["predictions", "test_positives", "test_negatives", "tp_matched_positives", "fp_matched_supplied_negatives", "unlabelled_predictions",
      "precision", "recall", "f1", "specificity", "labelled_coverage", "positive_hit_rate", "recall_ceiling_under_cap"];
    const rels = Object.keys(R.versions.v1.per_relation).sort((a, b) => Number(a.slice(1)) - Number(b.slice(1)));
    const bar = (x, cls) => x == null ? "n/a" : `<span class="bar ${cls}" style="width:${Math.round(120 * x)}px"></span> ${x.toFixed(3)}`;
    root.innerHTML = `<div class="notice"><b>Evaluation results (split: ${esc(R.split)}), generated ${esc(R.generated_at)}.</b>
      Unlabelled predictions are not confirmed false. The supplied negatives were not independently verified, and the knowledge graph is incomplete.</div>
      <p>Exports: <a href="${EVAL_DIR}evaluation_results.json">evaluation_results.json</a> · <a href="${EVAL_DIR}predictions_labelled.csv">predictions_labelled.csv</a> ·
      <a href="${EVAL_DIR}per_relation_metrics.csv">per_relation_metrics.csv</a> · <a href="${EVAL_DIR}evaluation_manifest.json">evaluation_manifest.json</a></p>
      <h3>Inputs</h3><ul>${Object.entries(R.inputs.splits).map(([k, v]) => `<li>${esc(k)}: ${esc(v.path)} — ${v.triples} triples, SHA-256 <code>${esc(v.sha256.slice(0, 12))}…</code></li>`).join("")}</ul>
      <h3>Overall (identical conditions for v1 and v2)</h3>
      <table class="data"><thead><tr><th>Measure</th><th>v1</th><th>v2</th></tr></thead><tbody>${keys.map((k) => `<tr><td>${esc(k)}</td><td>${fmt(o1[k])}</td><td>${fmt(o2[k])}</td></tr>`).join("")}
      <tr><td>unlabelled also in validation positives / negatives</td><td>${o1.unlabelled_annotations.in_valid_positives} / ${o1.unlabelled_annotations.in_valid_negatives}</td><td>${o2.unlabelled_annotations.in_valid_positives} / ${o2.unlabelled_annotations.in_valid_negatives}</td></tr></tbody></table>
      <dl class="defs">${DEFS.map(([k, v]) => `<dt>${esc(k)}</dt><dd>${esc(v)}</dd>`).join("")}</dl>
      <h3>Per relation (precision and recall; grey = v1, blue = v2)</h3>
      <table class="data bars"><thead><tr><th>Relation</th><th>Predictions v1 / v2</th><th>Test positives</th><th>TP v1 / v2</th><th>FP v1 / v2</th><th>Precision</th><th>Recall</th></tr></thead><tbody>
      ${rels.map((r) => { const a = R.versions.v1.per_relation[r], b = R.versions.v2.per_relation[r];
        return `<tr><td>${relTxt(r)}</td><td>${a.predictions} / ${b.predictions}</td><td>${a.test_positives}</td><td>${a.tp_matched_positives} / ${b.tp_matched_positives}</td><td>${a.fp_matched_supplied_negatives} / ${b.fp_matched_supplied_negatives}</td>` +
          `<td>${bar(a.precision, "v1")}<br>${bar(b.precision, "v2")}</td><td>${bar(a.recall, "v1")}<br>${bar(b.recall, "v2")}</td></tr>`; }).join("")}</tbody></table>
      <h3>Labelled predictions</h3>
      <div>Version <select id="e-version"><option>v1</option><option>v2</option></select>
        Label <select id="e-label"><option value="test_positive">matched test positives</option><option value="test_negative">matched supplied negatives</option><option value="unlabelled">unlabelled</option></select>
        (shared filters above also apply)</div>
      <table class="data" id="eval-table"><thead><tr><th>Subject</th><th>Relation</th><th>Object</th><th>Score</th><th>Rank</th><th>Label</th><th>Note</th></tr></thead><tbody></tbody></table>
      <div class="pager" id="eval-pager"></div>`;
    $("e-version").onchange = $("e-label").onchange = () => { S.evalPage = 1; renderEvalTable(); };
    renderEvalTable();
  }
  function renderEvalTable() {
    const R = window.PHASE6_RESULTS;
    if (!R || !$("eval-table")) return;
    const v = $("e-version").value, lab = $("e-label").value;
    const allowed = new Set(UF.filterItems(S.rows, { ...filter(), version: v }, L).map((it) => it.row.pid));
    const rows = R.versions[v].labels.filter(([pid, l]) => l === lab && allowed.has(pid)).map(([pid, l, n]) => [S.byPid.get(pid), l, n]);
    const pg = UF.paginate(rows, S.evalPage, PAGE);
    S.evalPage = pg.page;
    $("eval-table").querySelector("tbody").innerHTML = pg.items.length ? pg.items.map(([r, l, n]) =>
      `<tr data-pid="${esc(r.pid)}"><td>${ent(r.s)}</td><td>${relTxt(r.r)}</td><td>${ent(r.o)}</td><td>${scoreTxt(r.score)}</td><td>${r[v].rank}</td><td><span class="badge ${esc(l)}">${esc(l)}</span></td><td>${esc(n)}</td></tr>`).join("")
      : emptyRow(7, "No predictions with this label match the current filters.");
    $("eval-table").querySelectorAll("tbody tr[data-pid]").forEach((tr) => (tr.onclick = () => showDetail(tr.dataset.pid, { openGraph: true })));
    pager("eval-pager", pg, (p) => { S.evalPage = p; renderEvalTable(); });
  }
})();
