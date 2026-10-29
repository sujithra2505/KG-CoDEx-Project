/* Browser smoke test for outputs/prediction_ui: drives headless Chrome/Edge over the DevTools protocol.
   Usage: node tests/ui/browser_smoke.js <page-url> [browser-exe]
   Exits 0 when every check passes; prints one line per check. Needs Node >= 22 (global WebSocket). */
"use strict";
const { spawn } = require("child_process");
const fs = require("fs");
const os = require("os");
const path = require("path");

const URL_ = process.argv[2];
const CANDIDATES = [process.argv[3], process.env.CHROME_PATH,
  "C:/Program Files/Google/Chrome/Application/chrome.exe", "C:/Program Files (x86)/Google/Chrome/Application/chrome.exe",
  "C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe", "/usr/bin/google-chrome", "/usr/bin/chromium"];
const EXE = CANDIDATES.find((p) => p && fs.existsSync(p));
if (!URL_ || !EXE) { console.error("usage: node browser_smoke.js <url> [browser-exe] (no browser found)"); process.exit(2); }

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
const PORT = 9300 + Math.floor(Math.random() * 500);
const profile = fs.mkdtempSync(path.join(os.tmpdir(), "ui-smoke-"));
const proc = spawn(EXE, ["--headless=new", "--disable-gpu", "--no-first-run", `--remote-debugging-port=${PORT}`,
  `--user-data-dir=${profile}`, "--window-size=1400,1000", "about:blank"], { stdio: "ignore" });

let ws, seq = 0;
const pending = new Map(), errors = [];
function send(method, params = {}) {
  const id = ++seq;
  ws.send(JSON.stringify({ id, method, params }));
  return new Promise((res, rej) => pending.set(id, { res, rej }));
}
async function ev(expr) {
  const r = await send("Runtime.evaluate", { expression: expr, returnByValue: true, awaitPromise: true });
  if (r.exceptionDetails) throw new Error(r.exceptionDetails.exception ? r.exceptionDetails.exception.description : r.exceptionDetails.text);
  return r.result.value;
}
async function until(expr, ms = 15000) {
  const end = Date.now() + ms;
  while (Date.now() < end) {
    try { if (await ev(expr)) return true; } catch (_) { /* page not ready yet */ }
    await sleep(150);
  }
  return false;
}
const typeInto = (id, text) => ev(`(() => { const el = document.getElementById(${JSON.stringify(id)}); el.value = ${JSON.stringify(text)};
  el.dispatchEvent(new Event("input", { bubbles: true })); el.dispatchEvent(new Event("change", { bubbles: true })); })()`);
const text = (sel) => ev(`(document.querySelector(${JSON.stringify(sel)}) || {}).textContent || ""`);
const count = (sel) => ev(`document.querySelectorAll(${JSON.stringify(sel)}).length`);
const edges = () => ev(`window.__UI_DEBUG ? window.__UI_DEBUG.graphEdges() : -1`);

const results = [];
function check(name, ok, detail) { results.push(ok); console.log(`${ok ? "PASS" : "FAIL"}  ${name}${detail ? "  — " + detail : ""}`); }

async function main() {
  let target;
  for (let i = 0; i < 60 && !target; i++) {
    try { target = (await (await fetch(`http://127.0.0.1:${PORT}/json/list`)).json()).find((t) => t.type === "page"); } catch (_) { await sleep(250); }
  }
  ws = new WebSocket(target.webSocketDebuggerUrl);
  await new Promise((r) => (ws.onopen = r));
  ws.onmessage = (m) => {
    const d = JSON.parse(m.data);
    if (d.id && pending.has(d.id)) { const p = pending.get(d.id); pending.delete(d.id); d.error ? p.rej(new Error(d.error.message)) : p.res(d.result); }
    if (d.method === "Runtime.exceptionThrown") errors.push(d.params.exceptionDetails.exception ? d.params.exceptionDetails.exception.description : d.params.exceptionDetails.text);
    if (d.method === "Log.entryAdded" && d.params.entry.level === "error") errors.push(`${d.params.entry.text} ${d.params.entry.url || ""}`);
  };
  await send("Runtime.enable"); await send("Log.enable"); await send("Page.enable");
  await send("Page.navigate", { url: URL_ });

  check("data loaded (no error banner)", await until(`document.body.dataset.uiState === "ready"`, 30000),
    await ev(`document.body.dataset.uiState + " | " + ((document.getElementById("load-status") || {}).textContent || "")`));
  check("default graph has predicted edges", await until(`(window.__UI_DEBUG && window.__UI_DEBUG.graphEdges()) > 0`), `edges=${await edges()}`);
  check("graph canvas is rendered", (await count("#graph canvas")) > 0);
  check("table populated", (await count("#pred-table tbody tr")) === 50, await text("#table-status"));

  for (const q of ["London", "Q84", "london"]) {
    await typeInto("f-entity", q);
    const ok = await until(`[...document.querySelectorAll("#entity-suggest li")].some((li) => li.dataset.id === "Q84")`, 5000);
    check(`entity search "${q}" suggests London (Q84)`, ok, (await text("#entity-suggest")).slice(0, 80));
  }
  await ev(`[...document.querySelectorAll("#entity-suggest li")].find((li) => li.dataset.id === "Q84").click()`);
  const entOk = await until(`/Entity .*Q84/.test(document.getElementById("graph-status").textContent)`, 15000);
  check("selecting Q84 draws its entity graph", entOk && (await edges()) > 0, `${(await text("#graph-status")).slice(0, 140)} edges=${await edges()}`);
  check("entity filter populates table", (await count("#pred-table tbody tr")) > 0, await text("#table-status"));
  await ev(`document.getElementById("clear-entity").click()`);
  await typeInto("f-entity", "Q84");
  await ev(`document.getElementById("f-entity").dispatchEvent(new KeyboardEvent("keydown", { key: "Enter", bubbles: true }))`);
  check("typing Q84 + Enter selects London", await until(`/Q84/.test(document.getElementById("entity-chip").textContent)`, 5000));
  await ev(`document.getElementById("clear-entity").click()`);
  await typeInto("f-entity", "qqqq-nobody");
  check("unknown entity shows 'No entity matches'", await until(`/No entity matches/.test(document.getElementById("entity-suggest").textContent)`, 5000));
  await typeInto("f-entity", "");

  for (const q of ["London", "Q84"]) {
    await typeInto("f-query", q);
    await sleep(600);
    const n = await count("#pred-table tbody tr");
    const firstRow = await text("#pred-table tbody tr");
    check(`text filter "${q}" returns rows containing London`, n > 0 && /London/.test(firstRow), `${await text("#table-status")} first: ${firstRow.slice(0, 70)}`);
    check(`text filter "${q}" redraws graph`, (await edges()) > 0, `edges=${await edges()}`);
  }
  await typeInto("f-query", "zzzz-no-such-thing");
  await sleep(600);
  check("no-match text shows empty message", /No predictions match/.test(await text("#table-status")) && /No predictions match/.test(await text("#graph-status")));
  await typeInto("f-query", "");

  await typeInto("f-min", "0.7");
  await sleep(300);
  const hi = await ev(`Number((document.getElementById("table-status").textContent.match(/^(\\d+)/) || [])[1])`);
  check("score filter >= 0.7 narrows rows", hi > 0 && hi < 6478, `${hi} rows`);
  await typeInto("f-min", "0");

  for (const tab of ["table", "compare", "evaluation", "graph"]) {
    await ev(`document.querySelector('#tabs button[data-tab="${tab}"]').click()`);
    const visible = await until(`getComputedStyle(document.getElementById("tab-${tab}")).display !== "none"`, 3000);
    let extra = "";
    if (tab === "compare") extra = `${await count("#compare-relations tbody tr")} relation rows`;
    if (tab === "evaluation") { await until(`document.getElementById("eval-root").textContent.length > 200`, 8000); extra = (await text("#eval-root")).slice(0, 60); }
    if (tab === "table") extra = `${await count("#pred-table tbody tr")} rows`;
    if (tab === "graph") extra = `edges=${await edges()}`;
    check(`tab "${tab}" shows content`, visible && !/^0 /.test(extra) && extra !== "edges=0", extra);
  }
  await ev(`document.querySelector("#pred-table tbody tr").click()`);
  check("clicking a table row shows provenance", await until(`/Supporting rules/.test(document.getElementById("detail").textContent)`, 8000));

  check("no JavaScript errors", errors.length === 0, errors.slice(0, 3).join(" | "));
}

main().catch((e) => { console.log("FAIL  smoke run crashed — " + e.message); results.push(false); })
  .finally(async () => {
    try { ws && ws.close(); } catch (_) {}
    proc.kill();
    await sleep(500);
    try { fs.rmSync(profile, { recursive: true, force: true }); } catch (_) {}
    const failed = results.filter((x) => !x).length;
    console.log(`${results.length - failed}/${results.length} checks passed`);
    process.exit(failed || !results.length ? 1 : 0);
  });
