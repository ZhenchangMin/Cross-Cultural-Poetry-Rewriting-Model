# -*- coding: utf-8 -*-
from __future__ import annotations

from src.data.flag_quality_risks import build_flags, flag_record


def _row(title: str):
    return {
        "id": "x",
        "form": "qilv7",
        "text": "甲乙丙丁戊己庚",
        "metadata": {"title": title, "author": "某甲"},
    }


def test_exact_fragment_title_is_high_priority_flag():
    flags = flag_record(_row("句"))
    assert any(x["code"] == "source_fragment_title" for x in flags)
    assert any(x["severity"] == "high" for x in flags)


def test_normal_title_is_not_flagged():
    assert flag_record(_row("春夜宿寺")) == []


def test_flags_are_review_priorities_not_exclusions():
    flagged = build_flags([_row("句")])
    assert flagged[0]["status"] == "priority_quality_review"
    assert "exclude" not in flagged[0]
