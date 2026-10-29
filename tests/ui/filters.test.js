// Node tests for prediction_ui_src/filters.js (run: node tests/ui/filters.test.js)
"use strict";
const assert = require("assert");
const path = require("path");
const UF = require(path.join(__dirname, "..", "..", "prediction_ui_src", "filters.js"));

// [pid, s, r, o, v1rank, v2rank, score, maxpca, nrules, evidence]
const raw = [
  ["a1", "Q1", "P26", "Q2", 1, 1, 0.9, 0.95, 2, 3],
  ["a2", "Q3", "P26", "Q4", 2, null, 0.9, 0.95, 1, 1],
  ["a3", "Q5", "P26", "Q6", null, 2, 0.9, 0.95, 1, 2],
  ["b1", "Q1", "P27", "Q30", 1, 2, 0.3, 0.4, 1, 5],
  ["b2", "Q7", "P27", "Q30", 2, 1, 0.3, 0.4, 1, 9],
];
const rows = raw.map(UF.toRow);
const labels = { entity: (id) => ({ Q1: "Alice", Q2: "Bob", Q30: "United States" }[id] || id), relation: (r) => ({ P26: "spouse", P27: "citizenship" }[r] || r) };

// row decoding keeps IDs and direction
assert.deepStrictEqual([rows[0].s, rows[0].r, rows[0].o], ["Q1", "P26", "Q2"]);
assert.strictEqual(rows[1].v2, null);

// version filters
assert.strictEqual(UF.filterItems(rows, { version: "all" }).length, 8);
assert.deepStrictEqual(UF.filterItems(rows, { version: "v1" }).map((i) => i.row.pid), ["a1", "a2", "b1", "b2"]);
assert.deepStrictEqual(UF.filterItems(rows, { version: "both" }).map((i) => i.row.pid + i.version), ["a1v1", "a1v2", "b1v1", "b1v2", "b2v1", "b2v2"]);
// relation, score range, topN, entity, text
assert.deepStrictEqual(UF.filterItems(rows, { version: "v2", relation: "P27" }).map((i) => i.row.pid), ["b1", "b2"]);
assert.strictEqual(UF.filterItems(rows, { version: "all", minScore: 0.5 }).length, 4);
assert.strictEqual(UF.filterItems(rows, { version: "all", maxScore: 0.5 }).length, 4);
assert.deepStrictEqual(UF.filterItems(rows, { version: "v2", topN: 1 }).map((i) => i.row.pid), ["a1", "b2"]);
assert.deepStrictEqual(UF.filterItems(rows, { version: "v1", entity: "Q30" }).map((i) => i.row.pid), ["b1", "b2"]);
assert.deepStrictEqual(UF.filterItems(rows, { version: "v1", query: "alice" }, labels).map((i) => i.row.pid), ["a1", "b1"]);
assert.deepStrictEqual(UF.filterItems(rows, { version: "v1", query: "united" }, labels).map((i) => i.row.pid), ["b1", "b2"]);
// comparison classes
assert.deepStrictEqual(UF.filterItems(rows, { version: "all", compare: "v1_only" }).map((i) => i.row.pid), ["a2"]);
assert.deepStrictEqual(UF.filterItems(rows, { version: "all", compare: "v2_only" }).map((i) => i.row.pid), ["a3"]);
assert.deepStrictEqual([...new Set(UF.filterItems(rows, { version: "all", compare: "rank_changed" }).map((i) => i.row.pid))], ["b1", "b2"]);
assert.deepStrictEqual(UF.comparisonSummary(rows), { both: 3, v1_only: 1, v2_only: 1, rank_changed: 2, v1_total: 4, v2_total: 4 });
// sorting is deterministic and stable
const items = UF.filterItems(rows, { version: "all" });
const byScore = UF.sortItems(items, "score", "desc").map((i) => i.row.pid + i.version);
assert.deepStrictEqual(byScore, UF.sortItems(items.slice().reverse(), "score", "desc").map((i) => i.row.pid + i.version));
assert.strictEqual(UF.sortItems(items, "evidence", "desc")[0].row.pid, "b2");
// pagination
const pg = UF.paginate([1, 2, 3, 4, 5], 2, 2);
assert.deepStrictEqual([pg.page, pg.pages, pg.items], [2, 3, [3, 4]]);
assert.strictEqual(UF.paginate([1, 2], 9, 2).page, 1);
// entity search: exact ID first, then label matches
const ents = [["Q30", "United States"], ["Q3", "Q-thirty"], ["Q300", "Unity"], ["Q1", "Alice"]];
assert.deepStrictEqual(UF.searchEntities(ents, "q3", 5).map((e) => e.id), ["Q3", "Q30", "Q300"]);
assert.deepStrictEqual(UF.searchEntities(ents, "unit", 5).map((e) => e.id), ["Q30", "Q300"]);
assert.deepStrictEqual(UF.searchEntities(ents, "states", 5).map((e) => e.id), ["Q30"]);
assert.deepStrictEqual(UF.searchEntities(ents, "", 5), []);
// score tiers and the evaluation gate status
assert.deepStrictEqual([0.7, 0.69, 0.4, 0.39].map(UF.scoreTier), ["high", "mid", "mid", "low"]);
assert.strictEqual(UF.evaluationStatus(undefined), "not_run");
assert.strictEqual(UF.evaluationStatus({}), "not_run");
assert.strictEqual(UF.evaluationStatus({ status: "complete", versions: {} }), "complete");
console.log("filters.test.js: all assertions passed");
