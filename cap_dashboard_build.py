"""Build outputs/cap_comparison_dashboard/ from the cap experiment's output files.

Reads (read-only): outputs/cap_experiment/{selection_rule.json, selection.json, validation/validation_results.json},
outputs/phase6/evaluation_test/evaluation_results.json (cap-100 baseline test evaluation) and, if it exists,
outputs/cap_experiment/test_final/test_results.json. Copies the page from cap_dashboard_src/ and writes every
number into data/cap_results.js. Refuses to overwrite unless --replace is given (then only its own files change).
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

import cap_experiment as ce

ROOT = Path(__file__).resolve().parent
SRC_DIR = ROOT / "cap_dashboard_src"
NAME = "cap_dashboard_build.py"
PAGE_FILES = ("index.html", "app.js", "app.css")
DATA_FILE = "data/cap_results.js"
MANIFEST = "dashboard_manifest.json"
OVERALL_KEYS = ("predictions", "tp_matched_positives", "fp_matched_supplied_negatives", "unlabelled_predictions",
                "precision", "recall", "f1", "specificity", "labelled_coverage", "positive_hit_rate", "recall_ceiling_under_cap")


def _read(path: Path, root: Path, sources: list) -> dict[str, Any]:
    raw = path.read_bytes()
    sources.append({"path": path.relative_to(root).as_posix(), "sha256": hashlib.sha256(raw).hexdigest()})
    return json.loads(raw.decode("utf-8"))


def pick(overall: dict[str, Any]) -> dict[str, Any]:
    o = {k.replace("split_positives", "test_positives"): v for k, v in overall.items()}
    return {k: o.get(k) for k in OVERALL_KEYS + ("precision_wilson95_lower",) if k in o}


def build_data(root: Path) -> dict[str, Any]:
    exp, sources = ce.exp_dir(root), []
    rule = _read(exp / ce.RULE_FILE, root, sources)
    sel = _read(exp / ce.SELECTION_FILE, root, sources)
    val = _read(exp / "validation" / "validation_results.json", root, sources)
    if hashlib.sha256((exp / "validation" / "validation_results.json").read_bytes()).hexdigest() != sel["validation_results_sha256"]:
        raise RuntimeError("validation results do not match selection.json")
    base = _read(root / "outputs" / "phase6" / "evaluation_test" / "evaluation_results.json", root, sources)
    final_path = exp / "test_final" / "test_results.json"
    final = _read(final_path, root, sources) if final_path.is_file() else None
    if final and final["selected"] != sel["selected"]:
        raise RuntimeError("test_final does not belong to the current selection")
    return {
        "built_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "caps": val["caps"], "versions": list(ce.VERSIONS),
        "rule": rule["rule"], "rule_frozen_at": rule["frozen_at"],
        "validation": {k: {"cap": c["cap"], "version": c["version"], "path": c["path"], "overall": pick(c["overall"]),
                           "relations_still_capped": c["relations_still_capped"]} for k, c in val["configs"].items()},
        "validation_split": val["splits"],
        "selection": {k: sel[k] for k in ("selected", "selected_cap", "selected_version", "table")},
        "test": {"baseline": {v: pick(base["versions"][v]["overall"]) for v in ce.VERSIONS},
                 "baseline_generated_at": base["generated_at"],
                 "selected": pick(final["overall"]) if final else None,
                 "selected_generated_at": final["generated_at"] if final else None},
        "sources": sources,
    }


def build(root: Path = ROOT, out_dir: Path | None = None, replace: bool = False) -> Path:
    out_dir = out_dir or root / "outputs" / "cap_comparison_dashboard"
    managed = PAGE_FILES + (DATA_FILE, MANIFEST)
    if out_dir.exists():
        unknown = [p for p in out_dir.rglob("*") if p.is_file() and p.relative_to(out_dir).as_posix() not in managed]
        if not replace:
            raise FileExistsError(f"Refusing to overwrite {out_dir} (use --replace to rebuild)")
        if unknown:
            raise FileExistsError(f"{out_dir} holds files this builder does not manage: {unknown}")
    data = build_data(root)
    texts = {n: (SRC_DIR / n).read_text(encoding="utf-8") for n in PAGE_FILES}
    texts[DATA_FILE] = "window.CAP_DATA = " + json.dumps(data, ensure_ascii=False, sort_keys=True).replace("</", "<\\/") + ";\n"
    manifest = {"tool": NAME, "built_at": data["built_at"], "sources": data["sources"],
                "outputs": {n: hashlib.sha256(t.encode("utf-8")).hexdigest() for n, t in texts.items()},
                "note": "All numbers come from the listed source files; the page contains none."}
    for name, text in texts.items():
        path = out_dir / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8", newline="\n")
    (out_dir / MANIFEST).write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")
    return out_dir / "index.html"


def main(argv: Iterable[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--replace", action="store_true", help="rebuild an existing dashboard folder")
    args = parser.parse_args(list(argv) if argv is not None else None)
    print(build(ROOT, replace=args.replace))
    return 0


if __name__ == "__main__":
    sys.exit(main())
