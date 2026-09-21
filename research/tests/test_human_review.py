# -*- coding: utf-8 -*-
from __future__ import annotations

import pytest

from src.data.human_review import init_review_state, promote_reviewed_gold


SCHEMA = {
    "form": {
        "values": {
            "qijue7": {"constraints": {"lines": 4, "chars_per_line": 7}},
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


def _proposal():
    return {
        "emotion": {"value": ["serene"]},
        "imagery": {"value": ["landscape"]},
        "diction": {"value": "plain"},
        "expression": {"value": "direct"},
        "energy": {"value": "gentle"},
        "density": {"value": "sparse"},
    }


def _row(rid="x", excluded=False):
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
            "assistant_calibration": {
                "quality": {
                    "status": "exclude" if excluded else "include",
                    "reason": "fragment" if excluded else "",
                },
                "style_proposal": None if excluded else _proposal(),
            }
        },
    }


def test_init_review_state_never_auto_accepts():
    state = init_review_state([_row()], reviewer="human-a")
    entry = state["records"]["x"]
    assert entry["decision"] == "pending"
    assert entry["suggested_decision"] == "accept"
    assert entry["final_style"]["emotion"] == ["serene"]


def test_named_accept_promotes_to_gold():
    rows = [_row()]
    state = init_review_state(rows, reviewer="human-a")
    state["records"]["x"]["decision"] = "accept"
    gold, report = promote_reviewed_gold(rows, state, SCHEMA)
    assert report["gold_records"] == 1
    assert report["accepted"] == 1
    assert report["pending"] == 0
    assert gold[0]["style"]["emotion"] == ["serene"]
    assert gold[0]["metadata"]["review_status"] == "gold_adjudicated"
    assert gold[0]["annotation"]["human_review"]["reviewer"] == "human-a"


def test_completed_decision_requires_named_human():
    rows = [_row()]
    state = init_review_state(rows)
    state["records"]["x"]["decision"] = "accept"
    with pytest.raises(ValueError, match="non-empty reviewer"):
        promote_reviewed_gold(rows, state, SCHEMA)


def test_pending_is_not_promoted():
    rows = [_row()]
    state = init_review_state(rows, reviewer="human-a")
    gold, report = promote_reviewed_gold(rows, state, SCHEMA)
    assert gold == []
    assert report["pending"] == 1
    assert report["gold_complete"] is False


def test_exclusion_requires_human_decision_too():
    rows = [_row(excluded=True)]
    state = init_review_state(rows, reviewer="human-a")
    assert state["records"]["x"]["suggested_decision"] == "exclude"
    assert state["records"]["x"]["decision"] == "pending"
    state["records"]["x"]["decision"] = "exclude"
    gold, report = promote_reviewed_gold(rows, state, SCHEMA)
    assert gold == []
    assert report["excluded"] == 1
    assert report["pending"] == 0
