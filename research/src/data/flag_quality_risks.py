# -*- coding: utf-8 -*-
"""Flag candidate records that deserve quality review before style/Gold promotion.

Flags are conservative review priorities, not automatic exclusions.
"""
from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping

DEFAULT_INPUT = Path("data/processed/style_annotation/annotation_sample_v1.jsonl")
DEFAULT_OUTPUT = Path("data/processed/style_annotation/quality_flags_v1.jsonl")
DEFAULT_REPORT = Path("data/processed/style_annotation/quality_flags_report_v1.json")


def read_jsonl(path: Path) -> List[Dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def flag_record(record: Mapping[str, Any]) -> List[Dict[str, str]]:
    flags: List[Dict[str, str]] = []
    metadata = record.get("metadata", {})
    title = str(metadata.get("title", "")).strip() if isinstance(metadata, Mapping) else ""

    if title == "句":
        flags.append(
            {
                "code": "source_fragment_title",
                "severity": "high",
                "reason": "Title is exactly '句'; source collections often use this for surviving verse fragments, so structural line counts may accidentally concatenate unrelated fragments.",
            }
        )
    if not title:
        flags.append(
            {
                "code": "missing_title",
                "severity": "medium",
                "reason": "Missing title makes source-fragment/provenance review harder.",
            }
        )
    return flags


def build_flags(rows: Iterable[Mapping[str, Any]]) -> List[Dict[str, Any]]:
    output: List[Dict[str, Any]] = []
    for row in rows:
        flags = flag_record(row)
        if flags:
            output.append(
                {
                    "id": row.get("id"),
                    "form": row.get("form"),
                    "text": row.get("text"),
                    "title": row.get("metadata", {}).get("title"),
                    "author": row.get("metadata", {}).get("author"),
                    "flags": flags,
                    "status": "priority_quality_review",
                }
            )
    return output


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    ap.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    ap.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    args = ap.parse_args()

    rows = read_jsonl(args.input)
    flagged = build_flags(rows)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8") as f:
        for item in flagged:
            f.write(json.dumps(item, ensure_ascii=False) + "\n")

    code_counts: Counter[str] = Counter()
    severity_counts: Counter[str] = Counter()
    for item in flagged:
        for flag in item["flags"]:
            code_counts[flag["code"]] += 1
            severity_counts[flag["severity"]] += 1

    report = {
        "version": "v1",
        "records_scanned": len(rows),
        "records_flagged": len(flagged),
        "flag_counts": dict(sorted(code_counts.items())),
        "severity_counts": dict(sorted(severity_counts.items())),
        "policy": "flags prioritize review; they do not automatically exclude records from Gold",
    }
    args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
