# -*- coding: utf-8 -*-
"""Validate and attach assistant calibration reviews without promoting them to Gold."""
from __future__ import annotations

import argparse
import copy
import json
from collections import Counter
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping

from .validate_dataset import STYLE_DIMS, load_schema, validate_record

DEFAULT_INPUT = Path("data/processed/style_annotation/calibration_sample_v1.jsonl")
DEFAULT_LABELS = Path("data/processed/style_annotation/assistant_calibration_labels_v1.json")
DEFAULT_OUTPUT = Path("data/processed/style_annotation/assistant_calibrated_v1.jsonl")
DEFAULT_REPORT = Path("data/processed/style_annotation/assistant_calibration_report_v1.json")
DEFAULT_SCHEMA = Path("configs/style_schema.json")


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


def _validate_evidence(text: str, block: Mapping[str, Any], *, record_id: str, dim: str) -> None:
    evidence = block.get("evidence", [])
    if not isinstance(evidence, list) or not 1 <= len(evidence) <= 3:
        raise ValueError(f"{record_id} {dim}.evidence must contain 1..3 strings")
    compact = text.replace("\n", "")
    for phrase in evidence:
        if not isinstance(phrase, str) or not phrase:
            raise ValueError(f"{record_id} {dim}.evidence contains invalid phrase")
        if phrase not in compact:
            raise ValueError(
                f"{record_id} {dim}.evidence not found verbatim in poem: {phrase!r}"
            )


def _validate_confidence(block: Mapping[str, Any], *, record_id: str, dim: str) -> None:
    value = block.get("confidence")
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{record_id} {dim}.confidence must be numeric")
    if not 0.0 <= float(value) <= 1.0:
        raise ValueError(f"{record_id} {dim}.confidence outside [0,1]")


def validate_label_entry(
    row: Mapping[str, Any],
    label_entry: Mapping[str, Any],
    schema: Mapping[str, Any],
) -> None:
    rid = str(row.get("id"))
    quality = label_entry.get("quality")
    if not isinstance(quality, Mapping) or quality.get("status") not in {"include", "exclude"}:
        raise ValueError(f"{rid} quality.status must be include/exclude")

    style = label_entry.get("style")
    if quality.get("status") == "exclude":
        if style is not None:
            raise ValueError(f"{rid} excluded records must have style=null")
        reason = str(quality.get("reason", "")).strip()
        if not reason:
            raise ValueError(f"{rid} excluded records require a reason")
        return

    if not isinstance(style, Mapping):
        raise ValueError(f"{rid} included record requires style object")
    if set(style) != set(STYLE_DIMS):
        raise ValueError(f"{rid} style dimensions must exactly match {STYLE_DIMS}")

    flat_style: Dict[str, Any] = {}
    for dim in STYLE_DIMS:
        block = style[dim]
        if not isinstance(block, Mapping) or "value" not in block:
            raise ValueError(f"{rid} style.{dim} must be an object with value")
        _validate_confidence(block, record_id=rid, dim=dim)
        _validate_evidence(str(row["text"]), block, record_id=rid, dim=dim)
        flat_style[dim] = block["value"]

    # Reuse the canonical Gold validator by validating a temporary copy only.
    temp = copy.deepcopy(dict(row))
    temp["style"] = flat_style
    issues = validate_record(temp, schema, stage="gold", line=1)
    if issues:
        preview = "; ".join(f"{x.field}: {x.message}" for x in issues[:5])
        raise ValueError(f"{rid} proposed style violates schema: {preview}")


def apply_reviews(
    rows: List[Dict[str, Any]],
    labels_doc: Mapping[str, Any],
    schema: Mapping[str, Any],
) -> List[Dict[str, Any]]:
    records = labels_doc.get("records")
    if not isinstance(records, Mapping):
        raise ValueError("labels document missing records object")

    by_id = {str(row["id"]): row for row in rows}
    if set(records) != set(by_id):
        missing = sorted(set(by_id) - set(records))
        extra = sorted(set(records) - set(by_id))
        raise ValueError(f"Calibration ID mismatch: missing={missing}, extra={extra}")

    out: List[Dict[str, Any]] = []
    for row in rows:
        rid = str(row["id"])
        entry = records[rid]
        if not isinstance(entry, Mapping):
            raise ValueError(f"{rid} label entry must be object")
        validate_label_entry(row, entry, schema)

        item = copy.deepcopy(row)
        annotation = item.setdefault("annotation", {})
        annotation["assistant_calibration"] = {
            "version": labels_doc.get("version", "v1"),
            "reviewer": labels_doc.get("reviewer"),
            "status": labels_doc.get(
                "review_status", "assistant_calibrated_pending_human"
            ),
            "quality": copy.deepcopy(entry["quality"]),
            "style_proposal": copy.deepcopy(entry.get("style")),
        }
        metadata = item.setdefault("metadata", {})
        if isinstance(metadata, dict):
            metadata["review_status"] = "assistant_calibrated_pending_human"
        # Canonical style intentionally remains untouched.
        out.append(item)
    return out


def build_report(rows: List[Mapping[str, Any]]) -> Dict[str, Any]:
    include = 0
    exclude = 0
    exclusions: List[Dict[str, str]] = []
    imagery_exact = 0
    imagery_jaccard: List[float] = []
    density_agree = 0
    density_overrides: List[Dict[str, str]] = []
    low_confidence: List[Dict[str, Any]] = []

    distributions = {
        "emotion": Counter(),
        "imagery": Counter(),
        "diction": Counter(),
        "expression": Counter(),
        "energy": Counter(),
        "density": Counter(),
    }

    for row in rows:
        rid = str(row["id"])
        annotation = row["annotation"]
        review = annotation["assistant_calibration"]
        quality = review["quality"]
        if quality["status"] == "exclude":
            exclude += 1
            exclusions.append({"id": rid, "reason": str(quality["reason"])})
            continue
        include += 1
        proposal = review["style_proposal"]

        for dim in STYLE_DIMS:
            block = proposal[dim]
            value = block["value"]
            if isinstance(value, list):
                distributions[dim].update(value)
            else:
                distributions[dim][str(value)] += 1
            if float(block["confidence"]) < 0.75:
                low_confidence.append(
                    {
                        "id": rid,
                        "dimension": dim,
                        "confidence": float(block["confidence"]),
                        "value": value,
                    }
                )

        pre = annotation.get("prelabel", {})
        rule_imagery = set(pre.get("imagery", {}).get("value", []))
        reviewed_imagery = set(proposal["imagery"]["value"])
        if rule_imagery == reviewed_imagery:
            imagery_exact += 1
        union = rule_imagery | reviewed_imagery
        imagery_jaccard.append(
            1.0 if not union else len(rule_imagery & reviewed_imagery) / len(union)
        )

        rule_density = pre.get("density", {}).get("value")
        reviewed_density = proposal["density"]["value"]
        if rule_density == reviewed_density:
            density_agree += 1
        else:
            density_overrides.append(
                {
                    "id": rid,
                    "rule": str(rule_density),
                    "reviewed": str(reviewed_density),
                    "note": str(proposal["density"].get("note", "")),
                }
            )

    return {
        "version": "v1",
        "records": len(rows),
        "included": include,
        "excluded": exclude,
        "exclusions": exclusions,
        "canonical_style_promoted": 0,
        "status": "assistant_calibrated_pending_human",
        "rule_comparison": {
            "imagery_exact_match": imagery_exact,
            "imagery_exact_match_rate": round(imagery_exact / include, 4) if include else 0.0,
            "imagery_mean_jaccard": round(sum(imagery_jaccard) / len(imagery_jaccard), 4)
            if imagery_jaccard
            else 0.0,
            "density_agreement": density_agree,
            "density_agreement_rate": round(density_agree / include, 4) if include else 0.0,
            "density_overrides": density_overrides,
        },
        "low_confidence_decisions": sorted(
            low_confidence, key=lambda x: (x["confidence"], x["id"], x["dimension"])
        ),
        "style_distributions": {
            dim: dict(sorted(counter.items())) for dim, counter in distributions.items()
        },
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    ap.add_argument("--labels", type=Path, default=DEFAULT_LABELS)
    ap.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    ap.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    ap.add_argument("--schema", type=Path, default=DEFAULT_SCHEMA)
    args = ap.parse_args()

    rows = read_jsonl(args.input)
    labels_doc = json.loads(args.labels.read_text(encoding="utf-8"))
    schema = load_schema(args.schema)
    reviewed = apply_reviews(rows, labels_doc, schema)
    write_jsonl(reviewed, args.output)
    report = build_report(reviewed)
    args.report.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
