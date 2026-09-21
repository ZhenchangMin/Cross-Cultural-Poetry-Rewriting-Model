# -*- coding: utf-8 -*-
from __future__ import annotations

import pytest

from src.data.apply_calibration_review import apply_reviews, build_report


SCHEMA = {
    "form": {
        "values": {
            "qijue7": {"constraints": {"lines": 4, "chars_per_line": 7}},
            "qilv7": {"constraints": {"lines": 8, "chars_per_line": 7}},
        }
    },
    "style": {
        "emotion": {"type": "multi_label", "min_items": 1, "max_items": 2, "values": {"serene": "x"}},
        "imagery": {"type": "multi_label", "min_items": 1, "max_items": 4, "values": {"landscape": "x"}},
        "diction": {"type": "single_label", "values": {"plain": "x"}},
        "expression": {"type": "single_label", "values": {"direct": "x"}},
        "energy": {"type": "single_label", "values": {"gentle": "x"}},
        "density": {"type": "single_label", "values": {"sparse": "x"}},
    },
    "culture": {"adaptation": {"min": 1, "max": 5}},
}


def _row(rid: str):
    return {
        "id": rid,
        "text": "\n".join(["甲乙丙丁戊己庚"] * 4),
        "form": "qijue7",
        "style": {
            "emotion": [], "imagery": [], "diction": "",
            "expression": "", "energy": "", "density": "",
        },
        "culture": {"adaptation": None},
        "metadata": {},
        "annotation": {
            "prelabel": {
                "imagery": {"value": ["landscape"]},
                "density": {"value": "sparse"},
            }
        },
    }


def _style():
    return {
        "emotion": {"value": ["serene"], "confidence": 0.9, "evidence": ["甲乙"]},
        "imagery": {"value": ["landscape"], "confidence": 0.9, "evidence": ["甲乙"]},
        "diction": {"value": "plain", "confidence": 0.9, "evidence": ["甲乙"]},
        "expression": {"value": "direct", "confidence": 0.9, "evidence": ["甲乙"]},
        "energy": {"value": "gentle", "confidence": 0.9, "evidence": ["甲乙"]},
        "density": {"value": "sparse", "confidence": 0.9, "evidence": ["甲乙"]},
    }


def test_apply_keeps_canonical_style_blank():
    rows = [_row("a")]
    doc = {
        "version": "v1",
        "reviewer": "assistant",
        "records": {"a": {"quality": {"status": "include", "reason": ""}, "style": _style()}},
    }
    out = apply_reviews(rows, doc, SCHEMA)
    assert out[0]["style"]["emotion"] == []
    assert out[0]["annotation"]["assistant_calibration"]["style_proposal"]["emotion"]["value"] == ["serene"]
    report = build_report(out)
    assert report["canonical_style_promoted"] == 0
    assert report["included"] == 1
    assert report["rule_comparison"]["imagery_exact_match_rate"] == 1.0


def test_excluded_record_requires_no_style():
    rows = [_row("a")]
    doc = {
        "records": {
            "a": {
                "quality": {"status": "exclude", "reason": "fragment"},
                "style": None,
            }
        }
    }
    out = apply_reviews(rows, doc, SCHEMA)
    report = build_report(out)
    assert report["excluded"] == 1
    assert report["exclusions"][0]["reason"] == "fragment"


def test_evidence_must_be_verbatim():
    rows = [_row("a")]
    style = _style()
    style["emotion"]["evidence"] = ["不存在"]
    doc = {
        "records": {"a": {"quality": {"status": "include", "reason": ""}, "style": style}}
    }
    with pytest.raises(ValueError, match="not found verbatim"):
        apply_reviews(rows, doc, SCHEMA)
