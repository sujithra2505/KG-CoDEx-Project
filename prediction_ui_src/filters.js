/* Pure data helpers for the prediction UI (no DOM). Works in the browser and in Node tests. */
(function (root, factory) {
  if (typeof module === "object" && module.exports) module.exports = factory();
  else root.UIFilters = factory();
})(typeof self !== "undefined" ? self : this, function () {
  "use strict";

  // Row layout in data/index.js (see phase5_ui_build.py: ROW_FIELDS).
  const F = { pid: 0, s: 1, r: 2, o: 3, v1rank: 4, v2rank: 5, score: 6, maxpca: 7, nrules: 8, evidence: 9 };

  function toRow(a) {
    return {
      pid: a[F.pid], s: a[F.s], r: a[F.r], o: a[F.o],
      v1: a[F.v1rank] == null ? null : { rank: a[F.v1rank] },
      v2: a[F.v2rank] == null ? null : { rank: a[F.v2rank] },
      score: a[F.score], maxpca: a[F.maxpca], nrules: a[F.nrules], evidence: a[F.evidence],
    };
  }

  function scoreTier(score) {
    return score >= 0.7 ? "high" : score >= 0.4 ? "mid" : "low";
  }

  function norm(text) {
    return String(text == null ? "" : text).toLowerCase();
  }

  /** Entity search by exact ID, ID prefix or label substring. Deterministic order. */
  function searchEntities(entities, query, limit) {
    const q = norm(query).trim();
    if (!q) return [];
    const scored = [];
    for (const [id, label] of entities) {
      const lid = id.toLowerCase(), ll = norm(label);
      let rank = -1;
      if (lid === q) rank = 0;
      else if (ll === q) rank = 1;
      else if (lid.startsWith(q)) rank = 2;
      else if (ll.startsWith(q)) rank = 3;
      else if (ll.includes(q)) rank = 4;
      if (rank >= 0) scored.push([rank, Number(id.slice(1)), id, label]);
    }
    scored.sort((a, b) => a[0] - b[0] || a[1] - b[1]);
    return scored.slice(0, limit || 20).map((x) => ({ id: x[2], label: x[3] }));
  }

  /**
   * Expand rows into per-version items and apply filters.
   * filter = {version: "v1"|"v2"|"both"|"all", relation, minScore, maxScore, topN, entity, query, compare}
   * version "all" lists v1 and v2 items separately; "both" keeps only predictions present in both.
   * compare: "both" | "v1_only" | "v2_only" | "rank_changed" | "" (no comparison filter).
   */
  function filterItems(rows, filter, labels) {
    const f = filter || {};
    const versions = f.version === "v1" ? ["v1"] : f.version === "v2" ? ["v2"] : ["v1", "v2"];
    const q = norm(f.query).trim();
    const out = [];
    for (const row of rows) {
      if (f.relation && row.r !== f.relation) continue;
      if (f.minScore != null && row.score < f.minScore) continue;
      if (f.maxScore != null && row.score > f.maxScore) continue;
      if (f.entity && row.s !== f.entity && row.o !== f.entity) continue;
      if (f.version === "both" && !(row.v1 && row.v2)) continue;
      if (f.compare) {
        const c = compareClass(row);
        if (f.compare === "rank_changed" ? !(c === "both" && row.v1.rank !== row.v2.rank) : c !== f.compare) continue;
      }
      if (q) {
        const hay = [row.s, row.r, row.o, labels ? labels.entity(row.s) : "", labels ? labels.relation(row.r) : "",
          labels ? labels.entity(row.o) : "", row.pid].map(norm).join(" ");
        if (!hay.includes(q)) continue;
      }
      for (const v of versions) {
        const info = row[v];
        if (!info) continue;
        if (f.topN && info.rank > f.topN) continue;
        out.push({ row, version: v, rank: info.rank });
      }
    }
    return out;
  }

  function compareClass(row) {
    return row.v1 && row.v2 ? "both" : row.v1 ? "v1_only" : "v2_only";
  }

  const SORT_KEYS = {
    subject: (it, L) => (L ? norm(L.entity(it.row.s)) : it.row.s),
    relation: (it) => Number(it.row.r.slice(1)),
    object: (it, L) => (L ? norm(L.entity(it.row.o)) : it.row.o),
    version: (it) => it.version,
    score: (it) => it.row.score,
    rank: (it) => it.rank,
    nrules: (it) => it.row.nrules,
    evidence: (it) => it.row.evidence,
  };

  /** Stable, deterministic sort; ties fall back to relation, rank, version, prediction id. */
  function sortItems(items, key, dir, labels) {
    const k = SORT_KEYS[key] || SORT_KEYS.rank;
    const sign = dir === "desc" ? -1 : 1;
    return items.slice().sort((a, b) => {
      const x = k(a, labels), y = k(b, labels);
      if (x < y) return -sign;
      if (x > y) return sign;
      return Number(a.row.r.slice(1)) - Number(b.row.r.slice(1)) || a.rank - b.rank ||
        (a.version < b.version ? -1 : a.version > b.version ? 1 : 0) || (a.row.pid < b.row.pid ? -1 : a.row.pid > b.row.pid ? 1 : 0);
    });
  }

  function paginate(items, page, size) {
    const pages = Math.max(1, Math.ceil(items.length / size));
    const p = Math.min(Math.max(1, page), pages);
    return { page: p, pages, items: items.slice((p - 1) * size, p * size) };
  }

  function comparisonSummary(rows) {
    const s = { both: 0, v1_only: 0, v2_only: 0, rank_changed: 0, v1_total: 0, v2_total: 0 };
    for (const r of rows) {
      const c = compareClass(r);
      s[c] += 1;
      if (r.v1) s.v1_total += 1;
      if (r.v2) s.v2_total += 1;
      if (c === "both" && r.v1.rank !== r.v2.rank) s.rank_changed += 1;
    }
    return s;
  }

  /** Evaluation dashboard status: results object or undefined -> "not_run". */
  function evaluationStatus(results) {
    if (!results || typeof results !== "object" || !results.versions) return "not_run";
    return results.status === "complete" ? "complete" : "invalid";
  }

  return { F, toRow, scoreTier, searchEntities, filterItems, compareClass, sortItems, paginate, comparisonSummary, evaluationStatus };
});
