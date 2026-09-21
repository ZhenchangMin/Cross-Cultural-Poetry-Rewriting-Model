# -*- coding: utf-8 -*-
"""Prepare a deterministic balanced style-annotation calibration batch.

The calibration batch is intentionally separate from the final Gold file. It copies
preannotated records while keeping `style` untouched, and records exactly how the
subset was selected.
"""
from __future__ import annotations

import argparse
import copy
import json
import random
from collections import Counter
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Sequence

DEFAULT_INPUT = Path("data/processed/style_annotation/preannotated_v1.jsonl")
DEFAULT_OUTPUT = Path("data/processed/style_annotation/calibration_sample_v1.jsonl")
DEFAULT_REPORT = Path("data/processed/style_annotation/calibration_report_v1.json")
DEFAULT_SEED = 20260920
FORMS = ("qijue7", "qilv7")


def read_jsonl(path: Path) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as f:
        for lineno, line in enumerate(f, 1):
            if not line.strip():
                continue
            obj = json.loads(line)
            if not isinstance(obj, dict):
                raise ValueError(f"Expected object at {path}:{lineno}")
            rows.append(obj)
    return rows


def write_jsonl(rows: Iterable[Mapping[str, Any]], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


def select_calibration(
    rows: Sequence[Mapping[str, Any]],
    *,
    per_form: int = 15,
    seed: int = DEFAULT_SEED,
) -> List[Dict[str, Any]]:
    if per_form <= 0:
        raise ValueError("per_form must be positive")

    rng = random.Random(seed)
    by_form: Dict[str, List[Mapping[str, Any]]] = {
        form: [row for row in rows if row.get("form") == form] for form in FORMS
    }
    for form in FORMS:
        rng.shuffle(by_form[form])

    selected: List[Dict[str, Any]] = []
    used_authors: set[str] = set()

    # Alternate forms so global author uniqueness is enforced symmetrically.
    positions = {form: 0 for form in FORMS}
    counts = {form: 0 for form in FORMS}
    while any(counts[form] < per_form for form in FORMS):
        progressed = False
        for form in FORMS:
            if counts[form] >= per_form:
                continue
            pool = by_form[form]
            while positions[form] < len(pool):
                row = pool[positions[form]]
                positions[form] += 1
                author = str(row.get("metadata", {}).get("author", "")).strip()
                if author and author in used_authors:
                    continue
                item = copy.deepcopy(dict(row))
                metadata = item.setdefault("metadata", {})
                if isinstance(metadata, dict):
                    metadata["calibration_selection"] = {
                        "version": "v1",
                        "seed": seed,
                        "per_form": per_form,
                        "unique_author_across_batch": True,
                    }
                selected.append(item)
                counts[form] += 1
                if author:
                    used_authors.add(author)
                progressed = True
                break
        if not progressed:
            raise ValueError(
                f"Could not select {per_form} unique-author records for every form; counts={counts}"
            )

    # Stable deterministic order: interleaved selection order.
    return selected


def build_report(rows: Sequence[Mapping[str, Any]], *, seed: int, per_form: int) -> Dict[str, Any]:
    form_counts = Counter(str(row.get("form")) for row in rows)
    density_counts: Counter[str] = Counter()
    imagery_counts: Counter[str] = Counter()
    authors: List[str] = []

    for row in rows:
        metadata = row.get("metadata", {})
        if isinstance(metadata, Mapping):
            authors.append(str(metadata.get("author", "")))
        annotation = row.get("annotation", {})
        prelabel = annotation.get("prelabel", {}) if isinstance(annotation, Mapping) else {}
        density = prelabel.get("density", {}).get("value") if isinstance(prelabel, Mapping) else None
        if density:
            density_counts[str(density)] += 1
        imagery = prelabel.get("imagery", {}).get("value", []) if isinstance(prelabel, Mapping) else []
        if isinstance(imagery, list):
            imagery_counts.update(str(x) for x in imagery)

    return {
        "version": "v1",
        "seed": seed,
        "per_form": per_form,
        "records": len(rows),
        "form_counts": dict(sorted(form_counts.items())),
        "unique_authors": len(set(authors)),
        "density_prelabel_counts": dict(sorted(density_counts.items())),
        "imagery_prelabel_counts": dict(sorted(imagery_counts.items())),
        "note": "Calibration only; style remains unpromoted and this file is not Gold.",
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    ap.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    ap.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    ap.add_argument("--per-form", type=int, default=15)
    ap.add_argument("--seed", type=int, default=DEFAULT_SEED)
    args = ap.parse_args()

    rows = read_jsonl(args.input)
    selected = select_calibration(rows, per_form=args.per_form, seed=args.seed)
    write_jsonl(selected, args.output)
    report = build_report(selected, seed=args.seed, per_form=args.per_form)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
