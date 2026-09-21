# -*- coding: utf-8 -*-
from __future__ import annotations

from src.data.prepare_calibration import build_report, select_calibration


def _row(form: str, author: str, idx: int):
    return {
        "id": f"{form}-{idx}",
        "text": "甲乙丙丁戊己庚\n甲乙丙丁戊己庚\n甲乙丙丁戊己庚\n甲乙丙丁戊己庚"
        if form == "qijue7"
        else "\n".join(["甲乙丙丁戊己庚"] * 8),
        "form": form,
        "style": {
            "emotion": [],
            "imagery": [],
            "diction": "",
            "expression": "",
            "energy": "",
            "density": "",
        },
        "metadata": {"author": author},
        "annotation": {
            "prelabel": {
                "imagery": {"value": ["landscape"]},
                "density": {"value": "medium"},
            }
        },
    }


def test_calibration_is_balanced_deterministic_and_author_unique():
    rows = []
    for i in range(10):
        rows.append(_row("qijue7", f"J{i}", i))
        rows.append(_row("qilv7", f"L{i}", i))

    a = select_calibration(rows, per_form=4, seed=7)
    b = select_calibration(rows, per_form=4, seed=7)

    assert [x["id"] for x in a] == [x["id"] for x in b]
    assert sum(x["form"] == "qijue7" for x in a) == 4
    assert sum(x["form"] == "qilv7" for x in a) == 4
    authors = [x["metadata"]["author"] for x in a]
    assert len(authors) == len(set(authors))
    assert all(x["style"]["emotion"] == [] for x in a)
    assert all("calibration_selection" in x["metadata"] for x in a)


def test_calibration_report_marks_non_gold():
    rows = [_row("qijue7", "A", 1), _row("qilv7", "B", 2)]
    report = build_report(rows, seed=1, per_form=1)
    assert report["records"] == 2
    assert report["unique_authors"] == 2
    assert report["form_counts"] == {"qijue7": 1, "qilv7": 1}
    assert "not Gold" in report["note"]
