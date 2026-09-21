# -*- coding: utf-8 -*-
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

RESEARCH_ROOT = Path(__file__).resolve().parents[1]
if str(RESEARCH_ROOT) not in sys.path:
    sys.path.insert(0, str(RESEARCH_ROOT))

from src.data.human_review import (
    init_review_state,
    load_review_state,
    promote_reviewed_gold,
    read_jsonl,
    save_review_state,
    write_jsonl,
)
from src.data.validate_dataset import load_schema


DEFAULT_INPUT = Path("data/processed/style_annotation/assistant_calibrated_v1_1.jsonl")
DEFAULT_STATE = Path("data/processed/style_annotation/human_review_state_v1.json")
DEFAULT_GOLD = Path("data/processed/style_annotation/gold_calibration_v1.jsonl")
DEFAULT_REPORT = Path("data/processed/style_annotation/gold_calibration_report_v1.json")
DEFAULT_SCHEMA = Path("configs/style_schema.json")


def _summary(state: dict) -> dict:
    counts = {"pending": 0, "accept": 0, "edit": 0, "exclude": 0}
    for entry in state.get("records", {}).values():
        decision = entry.get("decision", "pending")
        if decision in counts:
            counts[decision] += 1
    counts["total"] = sum(counts.values())
    counts["completed"] = counts["total"] - counts["pending"]
    return counts


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Initialize, inspect, or promote the calibration human-review state."
    )
    sub = ap.add_subparsers(dest="command", required=True)

    init = sub.add_parser("init")
    init.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    init.add_argument("--state", type=Path, default=DEFAULT_STATE)
    init.add_argument("--reviewer", default="")
    init.add_argument("--force", action="store_true")

    status = sub.add_parser("status")
    status.add_argument("--state", type=Path, default=DEFAULT_STATE)

    promote = sub.add_parser("promote")
    promote.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    promote.add_argument("--state", type=Path, default=DEFAULT_STATE)
    promote.add_argument("--schema", type=Path, default=DEFAULT_SCHEMA)
    promote.add_argument("--output", type=Path, default=DEFAULT_GOLD)
    promote.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    promote.add_argument(
        "--allow-partial",
        action="store_true",
        help="Write reviewed records even when pending decisions remain. Default refuses partial promotion.",
    )

    args = ap.parse_args()

    if args.command == "init":
        if args.state.exists() and not args.force:
            raise SystemExit(
                f"Review state already exists: {args.state}. Use --force only if you intentionally want to reset it."
            )
        rows = read_jsonl(args.input)
        state = init_review_state(rows, reviewer=args.reviewer)
        save_review_state(state, args.state)
        print(json.dumps({"state": str(args.state), **_summary(state)}, ensure_ascii=False, indent=2))
        return 0

    if args.command == "status":
        state = load_review_state(args.state)
        print(json.dumps({"state": str(args.state), **_summary(state)}, ensure_ascii=False, indent=2))
        return 0

    rows = read_jsonl(args.input)
    state = load_review_state(args.state)
    schema = load_schema(args.schema)
    gold, report = promote_reviewed_gold(rows, state, schema)
    if report["pending"] and not args.allow_partial:
        print(json.dumps(report, ensure_ascii=False, indent=2))
        raise SystemExit(
            "Human review is incomplete; Gold output was not written. "
            "Complete every decision or explicitly use --allow-partial."
        )

    write_jsonl(gold, args.output)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({"output": str(args.output), "report": str(args.report), **report}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
