# -*- coding: utf-8 -*-
"""Human-review state and Gold promotion for style calibration.

Assistant proposals are reviewer aids only. A record becomes Gold only when a named
human reviewer explicitly accepts/edits it and the resulting style passes the canonical
Gold validator.
"""
from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping

from .validate_dataset import STYLE_DIMS, load_schema, validate_record


VALID_DECISIONS = {"pending", "accept", "edit", "exclude"}


def read_jsonl(path: Path) -> List[Dict[str, Any]]:
    return [json.loads(x) for x in path.read_text(encoding="utf-8").splitlines() if x.strip()]


def write_jsonl(rows: Iterable[Mapping[str, Any]], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


def proposal_values(proposal: Mapping[str, Any]) -> Dict[str, Any]:
    out: Dict[str, Any] = {}
    for dim in STYLE_DIMS:
        block = proposal.get(dim)
        if not isinstance(block, Mapping) or "value" not in block:
            raise ValueError(f"assistant proposal missing {dim}.value")
        out[dim] = copy.deepcopy(block["value"])
    return out


def init_review_state(
    rows: List[Mapping[str, Any]],
    *,
    reviewer: str = "",
) -> Dict[str, Any]:
    records: Dict[str, Any] = {}
    for row in rows:
        rid = str(row["id"])
        calibration = row.get("annotation", {}).get("assistant_calibration", {})
        if not isinstance(calibration, Mapping):
            raise ValueError(f"{rid} missing annotation.assistant_calibration")
        quality = calibration.get("quality", {})
        proposal = calibration.get("style_proposal")

        if isinstance(quality, Mapping) and quality.get("status") == "exclude":
            suggested = "exclude"
            final_style = None
        else:
            suggested = "accept"
            if not isinstance(proposal, Mapping):
                raise ValueError(f"{rid} included calibration record has no style proposal")
            final_style = proposal_values(proposal)

        records[rid] = {
            "decision": "pending",
            "suggested_decision": suggested,
            "reviewer": reviewer,
            "final_style": final_style,
            "notes": "",
        }

    return {
        "version": "v1",
        "status": "human_review_in_progress",
        "records": records,
    }


def validate_review_entry(
    row: Mapping[str, Any],
    entry: Mapping[str, Any],
    schema: Mapping[str, Any],
) -> None:
    rid = str(row["id"])
    decision = entry.get("decision")
    if decision not in VALID_DECISIONS:
        raise ValueError(f"{rid} invalid review decision: {decision!r}")
    if decision == "pending":
        return

    reviewer = str(entry.get("reviewer", "")).strip()
    if not reviewer:
        raise ValueError(f"{rid} completed review requires non-empty reviewer")

    if decision == "exclude":
        if entry.get("final_style") is not None:
            raise ValueError(f"{rid} excluded review must have final_style=null")
        return

    style = entry.get("final_style")
    if not isinstance(style, Mapping):
        raise ValueError(f"{rid} {decision} review requires final_style object")
    if set(style) != set(STYLE_DIMS):
        raise ValueError(f"{rid} final_style dimensions must exactly match {STYLE_DIMS}")

    temp = copy.deepcopy(dict(row))
    temp["style"] = copy.deepcopy(dict(style))
    issues = validate_record(temp, schema, stage="gold", line=1)
    if issues:
        preview = "; ".join(f"{x.field}: {x.message}" for x in issues[:5])
        raise ValueError(f"{rid} final_style violates Gold schema: {preview}")


def promote_reviewed_gold(
    rows: List[Dict[str, Any]],
    review_state: Mapping[str, Any],
    schema: Mapping[str, Any],
) -> tuple[List[Dict[str, Any]], Dict[str, Any]]:
    records = review_state.get("records")
    if not isinstance(records, Mapping):
        raise ValueError("review state missing records object")

    by_id = {str(row["id"]): row for row in rows}
    if set(records) != set(by_id):
        raise ValueError("review-state IDs do not exactly match input IDs")

    gold: List[Dict[str, Any]] = []
    pending = accepted = edited = excluded = 0

    for rid, row in by_id.items():
        entry = records[rid]
        if not isinstance(entry, Mapping):
            raise ValueError(f"{rid} review entry must be an object")
        validate_review_entry(row, entry, schema)
        decision = entry["decision"]

        if decision == "pending":
            pending += 1
            continue
        if decision == "exclude":
            excluded += 1
            continue

        item = copy.deepcopy(row)
        item["style"] = copy.deepcopy(dict(entry["final_style"]))
        reviewer = str(entry["reviewer"]).strip()
        metadata = item.setdefault("metadata", {})
        if isinstance(metadata, dict):
            metadata["review_status"] = "gold_adjudicated"
            metadata["reviewer"] = reviewer
        annotation = item.setdefault("annotation", {})
        annotation["human_review"] = {
            "decision": decision,
            "reviewer": reviewer,
            "notes": str(entry.get("notes", "")),
            "status": "gold_adjudicated",
        }

        issues = validate_record(item, schema, stage="gold", line=1)
        if issues:
            preview = "; ".join(f"{x.field}: {x.message}" for x in issues[:5])
            raise ValueError(f"{rid} failed Gold validation after promotion: {preview}")
        gold.append(item)
        if decision == "accept":
            accepted += 1
        else:
            edited += 1

    report = {
        "version": "v1",
        "input_records": len(rows),
        "gold_records": len(gold),
        "accepted": accepted,
        "edited": edited,
        "excluded": excluded,
        "pending": pending,
        "gold_complete": pending == 0,
    }
    return gold, report


def load_review_state(path: Path) -> Dict[str, Any]:
    obj = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(obj, dict):
        raise ValueError("review state must be a JSON object")
    return obj


def save_review_state(state: Mapping[str, Any], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(state, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
