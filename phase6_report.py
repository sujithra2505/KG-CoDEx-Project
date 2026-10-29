"""Phase 6 report: tables and charts from outputs/phase6/evaluation_test/.

Reads only the finished Phase 6 results (never the split files) and writes to
outputs/phase6/evaluation_test/report/. Refuses to overwrite. Changes nothing.
"""

from __future__ import annotations

import csv
import io
import json
import math
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

from display_labels import DisplayLabels  # noqa: E402

ROOT = Path(__file__).resolve().parent
EVAL_DIR = ROOT / "outputs" / "phase6" / "evaluation_test"
OUT_DIR = EVAL_DIR / "report"
V1, V2, GREY, NEG = "#2a78d6", "#eb6834", "#c9c8c2", "#52514e"
INK, MUTED, GRID = "#0b0b0b", "#52514e", "#e6e5e0"


def wilson(k: int, n: int, z: float = 1.96) -> tuple[float, float] | None:
    if n == 0:
        return None
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return round(c - h, 4), round(c + h, 4)


def fmt(x) -> str:
    return "—" if x is None else f"{x:.4f}"


def pct(x) -> str:
    return "—" if x is None else f"{100 * x:.2f}%"


def _csv(rows) -> str:
    buf = io.StringIO()
    csv.writer(buf, lineterminator="\n").writerows(rows)
    return buf.getvalue()


def _style(ax) -> None:
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    for s in ("left", "bottom"):
        ax.spines[s].set_color(GRID)
    ax.tick_params(colors=MUTED, labelsize=9)
    ax.set_axisbelow(True)


def build(res: dict, labelled_rows: list[dict]) -> tuple[dict[str, str], dict[str, plt.Figure]]:
    o = {v: res["versions"][v]["overall"] for v in ("v1", "v2")}
    pr = {v: res["versions"][v]["per_relation"] for v in ("v1", "v2")}
    rels = list(pr["v1"])
    pos_total = o["v1"]["test_positives"]

    # Prediction-set overlap and label agreement between versions.
    keys = {v: {(r["subject"], r["relation"], r["object"]): r["test_label"] for r in labelled_rows if r["version"] == v}
            for v in ("v1", "v2")}
    shared = keys["v1"].keys() & keys["v2"].keys()
    only = {v: keys[v].keys() - shared for v in ("v1", "v2")}
    only_lbl = {v: {l: sum(1 for t in only[v] if keys[v][t] == l) for l in ("test_positive", "test_negative", "unlabelled")}
                for v in ("v1", "v2")}

    # Cap / coverage decomposition (identical for v1 and v2: same per-relation counts).
    no_pred = [r for r in rels if pr["v1"][r]["predictions"] == 0]
    pos_no_pred = sum(pr["v1"][r]["test_positives"] for r in no_pred)
    capped = [r for r in rels if pr["v1"][r]["predictions"] == 100]
    pos_beyond_cap = sum(max(0, pr["v1"][r]["test_positives"] - 100) for r in capped)
    ceiling = round(o["v1"]["recall_ceiling_under_cap"] * pos_total)

    # Concentration of TP.
    top = {v: sorted(rels, key=lambda r: -pr[v][r]["tp_matched_positives"])[:4] for v in ("v1", "v2")}

    summary = {
        "source": "outputs/phase6/evaluation_test/evaluation_results.json",
        "overall": {v: {**{k: o[v][k] for k in ("predictions", "test_positives", "test_negatives", "tp_matched_positives",
                                                  "fp_matched_supplied_negatives", "unlabelled_predictions",
                                                  "fn_unpredicted_positives", "tn_unpredicted_negatives", "precision",
                                                  "recall", "f1", "specificity", "labelled_coverage", "positive_hit_rate",
                                                  "recall_ceiling_under_cap", "unlabelled_annotations")},
                        "precision_wilson95": wilson(o[v]["tp_matched_positives"],
                                                     o[v]["tp_matched_positives"] + o[v]["fp_matched_supplied_negatives"]),
                        "positive_hit_rate_wilson95": wilson(o[v]["tp_matched_positives"], o[v]["predictions"])}
                    for v in ("v1", "v2")},
        "overlap": {"shared_predictions": len(shared), "v1_only": len(only["v1"]), "v2_only": len(only["v2"]),
                    "v1_only_labels": only_lbl["v1"], "v2_only_labels": only_lbl["v2"]},
        "coverage": {"relations_in_benchmark_or_predictions": len(rels), "relations_with_predictions": len(rels) - len(no_pred),
                     "relations_without_predictions": no_pred, "test_positives_in_relations_without_predictions": pos_no_pred,
                     "relations_at_cap_100": len(capped), "test_positives_beyond_per_relation_cap": pos_beyond_cap,
                     "max_reachable_tp_under_cap": ceiling},
        "top_relations_by_tp": {v: {r: pr[v][r]["tp_matched_positives"] for r in top[v]} for v in ("v1", "v2")},
    }

    # Tables.
    overall_rows = [["metric", "formula", "v1_numerator", "v1_denominator", "v1_value", "v2_numerator", "v2_denominator",
                     "v2_value", "better"]]

    def row(name, formula, nums, dens, key, higher=True):
        a, b = o["v1"][key], o["v2"][key]
        better = "tie" if a == b else ("v2" if (b > a) == higher else "v1")
        overall_rows.append([name, formula, nums[0], dens[0], a, nums[1], dens[1], b, better])

    tp = [o[v]["tp_matched_positives"] for v in ("v1", "v2")]
    fp = [o[v]["fp_matched_supplied_negatives"] for v in ("v1", "v2")]
    fn = [o[v]["fn_unpredicted_positives"] for v in ("v1", "v2")]
    n = [o[v]["predictions"] for v in ("v1", "v2")]
    row("benchmark precision", "TP/(TP+FP)", tp, [tp[i] + fp[i] for i in range(2)], "precision")
    row("benchmark recall", "TP/|test positives|", tp, [pos_total] * 2, "recall")
    row("benchmark F1", "2TP/(2TP+FP+FN)", [2 * t for t in tp], [2 * tp[i] + fp[i] + fn[i] for i in range(2)], "f1")
    row("specificity", "TN/|supplied negatives|", [o[v]["tn_unpredicted_negatives"] for v in ("v1", "v2")],
        [o["v1"]["test_negatives"]] * 2, "specificity")
    row("labelled coverage", "(TP+FP)/|predictions|", [tp[i] + fp[i] for i in range(2)], n, "labelled_coverage")
    row("positive hit rate (lower bound)", "TP/|predictions|", tp, n, "positive_hit_rate")
    row("recall ceiling under cap", "Σ min(pred_r, pos_r)/|test positives|", [ceiling] * 2, [pos_total] * 2,
        "recall_ceiling_under_cap")

    rel_rows = [["relation", "relation_label", "test_positives", "supplied_negatives", "predictions", "coverage_status",
                 "v1_tp", "v1_fp", "v1_unlabelled", "v1_precision", "v1_recall", "v1_f1",
                 "v2_tp", "v2_fp", "v2_unlabelled", "v2_precision", "v2_recall", "v2_f1", "tp_change_v2_minus_v1"]]
    labels = DisplayLabels()
    rel_label = {r: labels.relation_label(r) for r in rels}
    for r in rels:
        a, b = pr["v1"][r], pr["v2"][r]
        status = ("no predictions" if a["predictions"] == 0 else
                  "no test positives" if a["test_positives"] == 0 else
                  "capped (100)" if a["predictions"] == 100 else "below cap")
        rel_rows.append([r, rel_label.get(r, ""), a["test_positives"], a["test_negatives"], a["predictions"], status,
                         a["tp_matched_positives"], a["fp_matched_supplied_negatives"], a["unlabelled_predictions"],
                         a["precision"], a["recall"], a["f1"],
                         b["tp_matched_positives"], b["fp_matched_supplied_negatives"], b["unlabelled_predictions"],
                         b["precision"], b["recall"], b["f1"], b["tp_matched_positives"] - a["tp_matched_positives"]])

    md = render_md(o, summary, overall_rows, rel_rows, pos_total)
    texts = {"summary.json": json.dumps(summary, indent=2, ensure_ascii=False) + "\n",
             "comparison_overall.csv": _csv(overall_rows), "comparison_per_relation.csv": _csv(rel_rows),
             "phase6_results_report.md": md}
    figs = {"fig1_label_composition.png": fig_composition(o),
            "fig2_overall_metrics.png": fig_metrics(o),
            "fig3_per_relation_tp.png": fig_per_relation(pr, rels, rel_label)}
    return texts, figs


def fig_composition(o):
    fig, ax = plt.subplots(figsize=(8, 2.8), dpi=150)
    _style(ax)
    for i, v in enumerate(("v2", "v1")):
        tp, fp, un = (o[v]["tp_matched_positives"], o[v]["fp_matched_supplied_negatives"], o[v]["unlabelled_predictions"])
        left = 0
        for val, col, name in ((tp, V1 if v == "v1" else V2, "test positive"), (fp, NEG, "supplied negative"),
                               (un, GREY, "unlabelled")):
            ax.barh(i, val, left=left, color=col, edgecolor="white", linewidth=2, height=0.55)
            left += val
        ax.text(tp / 2, i, str(tp), ha="center", va="center", color="white", fontsize=9, fontweight="bold")
        ax.text(tp + fp + un / 2, i, f"{fp} supplied negatives  ·  {un:,} unlabelled (not counted as false)",
                ha="center", va="center", color=INK, fontsize=9)
    ax.set_yticks([0, 1], ["v2 (evidence tie-break)", "v1"], color=INK)
    ax.set_xlim(0, 3239)
    ax.set_xlabel("predictions (3,239 per ranking)", color=MUTED, fontsize=9)
    ax.set_title("Most predictions fall outside the test benchmark", loc="left", color=INK, fontsize=11)
    fig.tight_layout()
    return fig


def fig_metrics(o):
    names = [("precision", "Benchmark precision\nTP/(TP+FP)"), ("positive_hit_rate", "Positive hit rate\nTP/all preds (lower bound)"),
             ("recall", "Recall\nTP/all test positives"), ("recall_ceiling_under_cap", "Recall ceiling\nunder 100 cap")]
    fig, ax = plt.subplots(figsize=(8, 3.6), dpi=150)
    _style(ax)
    ax.yaxis.grid(True, color=GRID, linewidth=0.8)
    w = 0.36
    for j, (v, col) in enumerate((("v1", V1), ("v2", V2))):
        xs = [i + (j - 0.5) * w for i in range(len(names))]
        vals = [o[v][k] for k, _ in names]
        ax.bar(xs, vals, width=w - 0.03, color=col, label=v)
        for x, val in zip(xs, vals):
            ax.text(x, val + 0.015, f"{100 * val:.1f}%", ha="center", va="bottom", fontsize=8, color=INK)
    ax.set_xticks(range(len(names)), [lab for _, lab in names], fontsize=8, color=INK)
    ax.set_ylim(0, 1.08)
    ax.yaxis.set_major_formatter(matplotlib.ticker.PercentFormatter(1.0))
    ax.legend(frameon=False, fontsize=9, loc="upper right")
    ax.set_title("High precision on labelled predictions, very low recall", loc="left", color=INK, fontsize=11)
    fig.tight_layout()
    return fig


def fig_per_relation(pr, rels, rel_label):
    shown = [r for r in rels if pr["v1"][r]["test_positives"] > 0]
    shown.sort(key=lambda r: (pr["v2"][r]["tp_matched_positives"], pr["v1"][r]["tp_matched_positives"]))
    fig, ax = plt.subplots(figsize=(8, 9.5), dpi=150)
    _style(ax)
    ax.xaxis.grid(True, color=GRID, linewidth=0.8)
    h = 0.4
    for j, (v, col) in enumerate((("v1", V1), ("v2", V2))):
        ys = [i + (0.5 - j) * h for i in range(len(shown))]
        ax.barh(ys, [pr[v][r]["tp_matched_positives"] for r in shown], height=h - 0.04, color=col, label=v)
    for i, r in enumerate(shown):
        a, b = pr["v1"][r]["tp_matched_positives"], pr["v2"][r]["tp_matched_positives"]
        np_ = pr["v1"][r]["predictions"]
        note = "no predictions" if np_ == 0 else f"{max(a, b)}" if a == b else f"{a} → {b}"
        ax.text(max(a, b) + 0.8, i, note, va="center", fontsize=7, color=MUTED if np_ == 0 else INK)
    ax.set_yticks(range(len(shown)),
                  [f"{rel_label.get(r, r)} [{r}] · {pr['v1'][r]['test_positives']} pos" for r in shown], fontsize=7, color=INK)
    ax.set_xlabel("predictions matching held-out test positives (TP)", color=MUTED, fontsize=9)
    ax.legend(frameon=False, fontsize=9, loc="lower right")
    ax.set_title("TP per relation (v1 vs v2) — relations with test positives", loc="left", color=INK, fontsize=11)
    fig.tight_layout()
    return fig


def render_md(o, s, overall_rows, rel_rows, pos_total) -> str:
    a, b = o["v1"], o["v2"]
    L = ["# Phase 6 results — held-out test split", "",
         "Source: `outputs/phase6/evaluation_test/evaluation_results.json` (evaluator v6.0.1). "
         "Predictions are the frozen Phase 5 files; nothing was re-ranked, re-thresholded or re-generated.", "",
         "**Read this first.** Benchmark precision is measured only on predictions that appear in the supplied test "
         "positives or supplied test negatives. It is *not* accuracy over all predicted triples, and not accuracy over "
         "all unknown KG triples. Unlabelled predictions are neither true nor false here.", "",
         "## 1. Overall metrics", "",
         "| Metric | Formula | v1 | v2 | Better |", "|---|---|---|---|---|"]
    for r in overall_rows[1:]:
        L.append(f"| {r[0]} | {r[1].replace('|', chr(92) + '|')} | {r[2]:,}/{r[3]:,} = {pct(r[4])} | {r[5]:,}/{r[6]:,} = {pct(r[7])} | {r[8]} |")
    ci1, ci2 = s["overall"]["v1"]["precision_wilson95"], s["overall"]["v2"]["precision_wilson95"]
    L += ["", f"Wilson 95% interval for benchmark precision: v1 {pct(ci1[0])}–{pct(ci1[1])}, "
              f"v2 {pct(ci2[0])}–{pct(ci2[1])}. The intervals overlap almost fully.", "",
          "## 2. Prediction labels", "",
          "| Label | v1 | v2 |", "|---|---|---|",
          f"| Matches held-out test positive | {a['tp_matched_positives']} | {b['tp_matched_positives']} |",
          f"| Matches supplied test negative | {a['fp_matched_supplied_negatives']} | {b['fp_matched_supplied_negatives']} |",
          f"| Unlabelled (not in test files) | {a['unlabelled_predictions']:,} | {b['unlabelled_predictions']:,} |",
          f"| — of which in validation positives (info only) | {a['unlabelled_annotations']['in_valid_positives']} | {b['unlabelled_annotations']['in_valid_positives']} |",
          f"| — of which in validation negatives (info only) | {a['unlabelled_annotations']['in_valid_negatives']} | {b['unlabelled_annotations']['in_valid_negatives']} |",
          f"| — in no split file | {a['unlabelled_annotations']['in_neither']:,} | {b['unlabelled_annotations']['in_neither']:,} |",
          f"| Total | {a['predictions']:,} | {b['predictions']:,} |", "",
          f"v1 and v2 share {s['overlap']['shared_predictions']:,} predictions; each has "
          f"{s['overlap']['v1_only']} the other lacks. v1-only: {s['overlap']['v1_only_labels']}. "
          f"v2-only: {s['overlap']['v2_only_labels']}.", "",
          "## 3. Coverage and the 100-per-relation cap", "",
          f"- {s['coverage']['relations_in_benchmark_or_predictions']} relations appear in predictions or the test files; "
          f"{s['coverage']['relations_with_predictions']} have predictions.",
          f"- No predictions for {len(s['coverage']['relations_without_predictions'])} relations "
          f"({', '.join(s['coverage']['relations_without_predictions'])}); they hold "
          f"{s['coverage']['test_positives_in_relations_without_predictions']} test positives, all counted as FN in recall.",
          f"- {s['coverage']['relations_at_cap_100']} relations hit the 100 cap. "
          f"{s['coverage']['test_positives_beyond_per_relation_cap']:,} test positives lie beyond the cap in their relation.",
          f"- Best possible TP under the cap = {s['coverage']['max_reachable_tp_under_cap']:,} of {pos_total:,} "
          f"→ recall ceiling {pct(a['recall_ceiling_under_cap'])} for both versions.",
          f"- Top TP relations — v1: {s['top_relations_by_tp']['v1']}; v2: {s['top_relations_by_tp']['v2']}.", "",
          "## 4. Per-relation results", "",
          "| Relation | Pos | Neg | Preds | Status | v1 TP/FP/Unl | v1 P | v1 R | v2 TP/FP/Unl | v2 P | v2 R | ΔTP |",
          "|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for r in rel_rows[1:]:
        L.append(f"| {r[1]} [{r[0]}] | {r[2]} | {r[3]} | {r[4]} | {r[5]} | {r[6]}/{r[7]}/{r[8]} | {fmt(r[9])} | {fmt(r[10])} "
                 f"| {r[12]}/{r[13]}/{r[14]} | {fmt(r[15])} | {fmt(r[16])} | {r[18]:+d} |")
    L += ["", "P = — means no prediction matched either test file (precision undefined, not zero).", "",
          "## 5. Interpretation and limitations", "",
          "- **v1 vs v2.** v2 is equal or higher on every metric, but the gap is 21 TP (257 → 278) with the same 13 FP. "
          "Precision differs by 0.35 points inside overlapping 95% intervals: not a meaningful precision difference. "
          "The gain is concentrated in P463 (+14), P1412 (+3), P361 (+3), P101/P106 (+1 each); P102 loses 1.",
          "- **Precision is benchmark-specific.** It is computed on 270 (v1) / 291 (v2) of 3,239 predictions (8–9%). "
          "The other ~91% are unlabelled: they may be true facts missing from the benchmark or wrong. "
          "The positive hit rate (7.9% / 8.6%) is only a lower bound on the share of correct predictions.",
          "- **Concentration.** Four symmetric/structural relations (P26, P530, P3373, P495) give 141 of the TP in both "
          "versions, so overall precision mostly reflects those relations.",
          "- **Low-precision relations.** P37 (1 TP / 3 neg.), P136 (1/2), P30 (5/4), P161 (2/1) and P361 in v1 (0/1) "
          "collide with supplied negatives; all are tiny counts.",
          "- **Recall is structurally capped.** The 100-per-relation cap and 11 relations with no rules bound recall at "
          "23.94%; observed recall 2.5–2.7% is about 11% of that ceiling. P106 alone has 3,635 positives vs 100 predictions.",
          "- **Supplied negatives** were only checked structurally; FP counts collisions with this particular negative set.",
          "- **Validation annotation** (246 / 253 unlabelled predictions in valid.txt) is information only and was not used "
          "to change anything; validation is not clean held-out data (used in Phase 4).",
          "- **Single run, no tuning.** Test results were not used to choose thresholds, rules, rankings or a model.", "",
          "## 6. Charts", "", "- `fig1_label_composition.png`", "- `fig2_overall_metrics.png`", "- `fig3_per_relation_tp.png`", ""]
    return "\n".join(L)


def main() -> int:
    res = json.loads((EVAL_DIR / "evaluation_results.json").read_text(encoding="utf-8"))
    with (EVAL_DIR / "predictions_labelled.csv").open(encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f))
    texts, figs = build(res, rows)
    names = list(texts) + list(figs)
    existing = [n for n in names if (OUT_DIR / n).exists()]
    if existing:
        raise FileExistsError("Refusing to overwrite: " + ", ".join(existing))
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for n, t in texts.items():
        with (OUT_DIR / n).open("x", encoding="utf-8", newline="\n") as h:
            h.write(t)
    for n, fig in figs.items():
        fig.savefig(OUT_DIR / n, facecolor="white")
        plt.close(fig)
    for n in names:
        print(OUT_DIR / n)
    return 0


if __name__ == "__main__":
    sys.exit(main())
