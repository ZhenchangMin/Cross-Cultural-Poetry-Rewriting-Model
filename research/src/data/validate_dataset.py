# -*- coding: utf-8 -*-
"""Validate poetry JSONL datasets against the project's V1 schema.

The key design is to distinguish dataset *stage* from dataset *format*:

- candidate:      structural candidate; final style labels may still be blank.
- preannotated:   weak/LLM prelabels may exist under annotation.prelabel, but final
                  style labels are still allowed to be blank.
- gold:           final style labels must be complete and schema-valid. This is the
                  default stage required by the training Dataset loader.

We intentionally do NOT copy weak prelabels into ``style`` here. Promotion from
prelabel -> final style must be an explicit human-review step.

Run from research/:
    python -m src.data.validate_dataset \
        data/processed/style_annotation/preannotated_v1.jsonl \
        --stage preannotated

Later, for a reviewed Gold Dataset:
    python -m src.data.validate_dataset path/to/gold.jsonl --stage gold
"""
from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Sequence, Tuple

DEFAULT_SCHEMA = Path("configs/style_schema.json")
SUPPORTED_STAGES = ("candidate", "preannotated", "gold")
STYLE_DIMS = ("emotion", "imagery", "diction", "expression", "energy", "density")


@dataclass(frozen=True)
class ValidationIssue:
    line: int
    record_id: str
    field: str
    message: str


@dataclass(frozen=True)
class ValidationReport:
    path: str
    stage: str
    records: int
    valid_records: int
    invalid_records: int
    duplicate_ids: int
    issues: List[ValidationIssue]

    @property
    def ok(self) -> bool:
        return self.invalid_records == 0 and self.duplicate_ids == 0

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data["ok"] = self.ok
        return data


def load_schema(path: Path = DEFAULT_SCHEMA) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        schema = json.load(f)
    if not isinstance(schema, dict):
        raise ValueError(f"Schema must be a JSON object: {path}")
    return schema


def iter_jsonl(path: Path) -> Iterable[Tuple[int, Dict[str, Any]]]:
    with path.open("r", encoding="utf-8") as f:
        for lineno, raw in enumerate(f, 1):
            raw = raw.strip()
            if not raw:
                continue
            try:
                obj = json.loads(raw)
            except json.JSONDecodeError as exc:
                raise ValueError(f"Invalid JSON at {path}:{lineno}: {exc}") from exc
            if not isinstance(obj, dict):
                raise ValueError(f"Expected JSON object at {path}:{lineno}")
            yield lineno, obj


def _record_id(record: Mapping[str, Any]) -> str:
    value = record.get("id")
    return value.strip() if isinstance(value, str) else ""


def _add(issues: List[ValidationIssue], line: int, rid: str, field: str, message: str) -> None:
    issues.append(ValidationIssue(line=line, record_id=rid or "<missing>", field=field, message=message))


def _is_blank_style(style: Mapping[str, Any]) -> bool:
    return (
        style.get("emotion") in (None, [])
        and style.get("imagery") in (None, [])
        and style.get("diction") in (None, "")
        and style.get("expression") in (None, "")
        and style.get("energy") in (None, "")
        and style.get("density") in (None, "")
    )


def _validate_form_structure(
    record: Mapping[str, Any], schema: Mapping[str, Any], line: int, rid: str, issues: List[ValidationIssue]
) -> None:
    form = record.get("form")
    form_values = schema["form"]["values"]
    if form not in form_values:
        _add(issues, line, rid, "form", f"unsupported form: {form!r}")
        return

    text = record.get("text")
    if not isinstance(text, str) or not text.strip():
        _add(issues, line, rid, "text", "must be a non-empty string")
        return

    constraints = form_values[form]["constraints"]
    poem_lines = [x.strip() for x in text.splitlines() if x.strip()]
    expected_lines = int(constraints["lines"])
    expected_chars = int(constraints["chars_per_line"])

    if len(poem_lines) != expected_lines:
        _add(
            issues,
            line,
            rid,
            "text",
            f"{form} requires {expected_lines} lines, got {len(poem_lines)}",
        )
        return

    bad_lengths = [(i + 1, len(poem_line)) for i, poem_line in enumerate(poem_lines) if len(poem_line) != expected_chars]
    if bad_lengths:
        details = ", ".join(f"L{i}={n}" for i, n in bad_lengths)
        _add(issues, line, rid, "text", f"{form} requires {expected_chars} chars per line; {details}")


def _validate_style(
    style: Any,
    schema: Mapping[str, Any],
    *,
    stage: str,
    line: int,
    rid: str,
    issues: List[ValidationIssue],
) -> None:
    if not isinstance(style, Mapping):
        _add(issues, line, rid, "style", "must be an object")
        return

    missing_dims = [dim for dim in STYLE_DIMS if dim not in style]
    for dim in missing_dims:
        _add(issues, line, rid, f"style.{dim}", "missing field")

    if missing_dims:
        return

    # Candidate/preannotation records deliberately keep final style blank.
    if stage != "gold" and _is_blank_style(style):
        return

    style_schema = schema["style"]
    for dim in STYLE_DIMS:
        spec = style_schema[dim]
        value = style.get(dim)
        allowed = set(spec["values"].keys())

        if spec["type"] == "multi_label":
            if not isinstance(value, list):
                _add(issues, line, rid, f"style.{dim}", "must be a list")
                continue
            min_items = int(spec.get("min_items", 0))
            max_items = int(spec.get("max_items", 10**9))
            if not min_items <= len(value) <= max_items:
                _add(
                    issues,
                    line,
                    rid,
                    f"style.{dim}",
                    f"requires {min_items}..{max_items} labels, got {len(value)}",
                )
            if len(value) != len(set(value)):
                _add(issues, line, rid, f"style.{dim}", "contains duplicate labels")
            invalid = [x for x in value if x not in allowed]
            if invalid:
                _add(issues, line, rid, f"style.{dim}", f"invalid labels: {invalid}")
        else:
            if value not in allowed:
                _add(issues, line, rid, f"style.{dim}", f"invalid label: {value!r}")


def _validate_culture(
    culture: Any, schema: Mapping[str, Any], line: int, rid: str, issues: List[ValidationIssue]
) -> None:
    if not isinstance(culture, Mapping):
        _add(issues, line, rid, "culture", "must be an object")
        return
    if "adaptation" not in culture:
        _add(issues, line, rid, "culture.adaptation", "missing field")
        return
    value = culture["adaptation"]
    spec = schema["culture"]["adaptation"]
    if value is None:
        return
    if isinstance(value, bool) or not isinstance(value, int) or not int(spec["min"]) <= value <= int(spec["max"]):
        _add(
            issues,
            line,
            rid,
            "culture.adaptation",
            f"must be null or integer {spec['min']}..{spec['max']}",
        )


def _validate_preannotation(
    record: Mapping[str, Any], schema: Mapping[str, Any], line: int, rid: str, issues: List[ValidationIssue]
) -> None:
    annotation = record.get("annotation")
    if not isinstance(annotation, Mapping):
        _add(issues, line, rid, "annotation", "preannotated stage requires annotation object")
        return
    prelabel = annotation.get("prelabel")
    if not isinstance(prelabel, Mapping):
        _add(issues, line, rid, "annotation.prelabel", "preannotated stage requires prelabel object")
        return

    for dim in STYLE_DIMS:
        entry = prelabel.get(dim)
        if not isinstance(entry, Mapping):
            _add(issues, line, rid, f"annotation.prelabel.{dim}", "missing or not an object")
            continue
        if "status" not in entry:
            _add(issues, line, rid, f"annotation.prelabel.{dim}.status", "missing field")
        if "method" not in entry:
            _add(issues, line, rid, f"annotation.prelabel.{dim}.method", "missing field")

        # Only validate a concrete prediction if one exists; pending_llm may have null value.
        value = entry.get("value")
        if value is None:
            continue
        spec = schema["style"][dim]
        allowed = set(spec["values"].keys())
        if spec["type"] == "multi_label":
            if not isinstance(value, list) or any(x not in allowed for x in value):
                _add(issues, line, rid, f"annotation.prelabel.{dim}.value", f"invalid prelabel: {value!r}")
        elif value not in allowed:
            _add(issues, line, rid, f"annotation.prelabel.{dim}.value", f"invalid prelabel: {value!r}")


def validate_record(
    record: Mapping[str, Any],
    schema: Mapping[str, Any],
    *,
    stage: str,
    line: int = 1,
) -> List[ValidationIssue]:
    if stage not in SUPPORTED_STAGES:
        raise ValueError(f"Unsupported stage={stage!r}; choose from {SUPPORTED_STAGES}")

    issues: List[ValidationIssue] = []
    rid = _record_id(record)
    if not rid:
        _add(issues, line, rid, "id", "must be a non-empty string")

    _validate_form_structure(record, schema, line, rid, issues)
    _validate_style(record.get("style"), schema, stage=stage, line=line, rid=rid, issues=issues)
    _validate_culture(record.get("culture"), schema, line, rid, issues)

    metadata = record.get("metadata")
    if metadata is not None and not isinstance(metadata, Mapping):
        _add(issues, line, rid, "metadata", "must be an object when present")

    if stage == "preannotated":
        _validate_preannotation(record, schema, line, rid, issues)

    return issues


def validate_jsonl(path: Path, schema: Mapping[str, Any], *, stage: str = "gold") -> ValidationReport:
    all_issues: List[ValidationIssue] = []
    seen: Dict[str, int] = {}
    duplicate_ids = 0
    records = 0
    invalid_lines: set[int] = set()

    for lineno, record in iter_jsonl(path):
        records += 1
        rid = _record_id(record)
        if rid:
            if rid in seen:
                duplicate_ids += 1
                issue = ValidationIssue(
                    line=lineno,
                    record_id=rid,
                    field="id",
                    message=f"duplicate id; first seen at line {seen[rid]}",
                )
                all_issues.append(issue)
                invalid_lines.add(lineno)
            else:
                seen[rid] = lineno

        issues = validate_record(record, schema, stage=stage, line=lineno)
        if issues:
            invalid_lines.add(lineno)
            all_issues.extend(issues)

    return ValidationReport(
        path=str(path),
        stage=stage,
        records=records,
        valid_records=records - len(invalid_lines),
        invalid_records=len(invalid_lines),
        duplicate_ids=duplicate_ids,
        issues=all_issues,
    )


def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser(description="Validate poetry JSONL against V1 data schema")
    ap.add_argument("path", type=Path)
    ap.add_argument("--schema", type=Path, default=DEFAULT_SCHEMA)
    ap.add_argument("--stage", choices=SUPPORTED_STAGES, default="gold")
    ap.add_argument("--max-issues", type=int, default=20)
    return ap.parse_args()


def main() -> int:
    args = parse_args()
    schema = load_schema(args.schema)
    report = validate_jsonl(args.path, schema, stage=args.stage)

    compact = report.to_dict()
    compact["issues"] = [asdict(x) for x in report.issues[: args.max_issues]]
    compact["issues_truncated"] = max(0, len(report.issues) - args.max_issues)
    print(json.dumps(compact, ensure_ascii=False, indent=2))
    return 0 if report.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
