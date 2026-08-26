# -*- coding: utf-8 -*-
from __future__ import annotations

from collections import Counter

import pytest

from src.data.sample_for_annotation import (
    build_report,
    prepare_annotation_records,
    sample_balanced,
    sample_form_author_balanced,
)


def _record(idx: int, author: str, form: str) -> dict:
    lines = 4 if form == "qijue7" else 8
    return {
        "id": f"r-{idx}",
        "text": "\n".join(["春風明月照長安"] * lines),
        "form": form,
        "style": {
            "emotion": [],
            "imagery": [],
            "diction": "",
            "expression": "",
            "energy": "",
            "density": "",
        },
        "culture": {"adaptation": None},
        "metadata": {"author": author, "title": f"t-{idx}", "dynasty": "唐"},
    }


def _dataset() -> list[dict]:
    rows = []
    idx = 0
    # qijue: A/B/C/D each 3 poems
    for author in "ABCD":
        for _ in range(3):
            idx += 1
            rows.append(_record(idx, author, "qijue7"))
    # qilv: A/B/E/F each 3 poems
    for author in "ABEF":
        for _ in range(3):
            idx += 1
            rows.append(_record(idx, author, "qilv7"))
    return rows


def test_sample_form_one_per_author():
    rows = _dataset()
    out = sample_form_author_balanced(rows, form="qijue7", target=4, seed=7, max_per_author=1)
    assert len(out) == 4
    assert len({r["metadata"]["author"] for r in out}) == 4


def test_sample_form_capacity_error():
    rows = _dataset()
    with pytest.raises(ValueError, match="capacity"):
        sample_form_author_balanced(rows, form="qijue7", target=5, seed=7, max_per_author=1)


def test_balanced_is_reproducible_and_exact():
    rows = _dataset()
    targets = {"qijue7": 3, "qilv7": 3}
    a = sample_balanced(rows, targets=targets, seed=123, max_per_author_per_form=1)
    b = sample_balanced(rows, targets=targets, seed=123, max_per_author_per_form=1)

    assert [r["id"] for r in a] == [r["id"] for r in b]
    counts = Counter(r["form"] for r in a)
    assert counts == {"qijue7": 3, "qilv7": 3}
    assert len({r["id"] for r in a}) == 6


def test_prepare_annotation_records_does_not_mutate_source():
    rows = _dataset()
    selected = sample_balanced(
        rows,
        targets={"qijue7": 2, "qilv7": 2},
        seed=9,
        max_per_author_per_form=1,
    )
    original_first_metadata = dict(selected[0]["metadata"])

    prepared = prepare_annotation_records(
        selected,
        seed=9,
        targets={"qijue7": 2, "qilv7": 2},
        max_per_author_per_form=1,
    )

    assert selected[0]["metadata"] == original_first_metadata
    assert prepared[0]["metadata"]["review_status"] == "pending_annotation"
    assert prepared[0]["metadata"]["sampling"]["sample_version"] == "v1"
    assert prepared[0]["style"]["emotion"] == []


def test_report_contains_diversity_stats(tmp_path):
    rows = _dataset()
    selected = sample_balanced(
        rows,
        targets={"qijue7": 3, "qilv7": 3},
        seed=5,
        max_per_author_per_form=1,
    )
    prepared = prepare_annotation_records(
        selected,
        seed=5,
        targets={"qijue7": 3, "qilv7": 3},
        max_per_author_per_form=1,
    )

    report = build_report(
        source_path=tmp_path / "source.jsonl",
        source_sha256="abc",
        all_records=rows,
        selected=prepared,
        seed=5,
        targets={"qijue7": 3, "qilv7": 3},
        max_per_author_per_form=1,
    )

    assert report["selected"]["records"] == 6
    assert report["selected"]["by_form"] == {"qijue7": 3, "qilv7": 3}
    assert report["selected"]["max_records_from_one_author"] <= 2
    assert report["constraints"]["gold_status"] == "candidate_only_until_human_review"
