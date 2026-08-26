# -*- coding: utf-8 -*-
from __future__ import annotations

import json
from pathlib import Path

from src.data.collect_corpus import (
    Candidate,
    candidate_to_record,
    detect_form,
    is_exact_han_line,
    iter_candidates,
    split_verse_lines,
)


def test_split_upstream_couplets_into_lines():
    paragraphs = [
        "秦川雄帝宅，函谷壯皇居。",
        "綺殿千尋起，離宮百雉餘。",
    ]
    assert split_verse_lines(paragraphs) == [
        "秦川雄帝宅",
        "函谷壯皇居",
        "綺殿千尋起",
        "離宮百雉餘",
    ]


def test_detect_qijue7_by_structure():
    lines = [
        "朝辭白帝彩雲間",
        "千里江陵一日還",
        "兩岸猿聲啼不住",
        "輕舟已過萬重山",
    ]
    assert detect_form(lines) == "qijue7"


def test_detect_qilv7_by_structure():
    lines = [
        "昔人已乘黃鶴去",
        "此地空餘黃鶴樓",
        "黃鶴一去不復返",
        "白雲千載空悠悠",
        "晴川歷歷漢陽樹",
        "芳草萋萋鸚鵡洲",
        "日暮鄉關何處是",
        "煙波江上使人愁",
    ]
    assert detect_form(lines) == "qilv7"


def test_reject_non_han_annotation_or_wrong_length():
    assert not is_exact_han_line("千里江陵一日還（一作回）", 7)
    assert not is_exact_han_line("千里江陵一日", 7)
    assert detect_form(["千里江陵一日還"] * 3 + ["abc江陵一日還"]) is None


def test_candidate_record_keeps_style_unlabeled():
    c = Candidate(
        source_id="upstream-id",
        title="早發白帝城",
        author="李白",
        source_file="poet.tang.1000.json",
        form="qijue7",
        lines=(
            "朝辭白帝彩雲間",
            "千里江陵一日還",
            "兩岸猿聲啼不住",
            "輕舟已過萬重山",
        ),
    )
    record = candidate_to_record(c)
    assert record["id"] == "tang-upstream-id"
    assert record["form"] == "qijue7"
    assert record["style"]["emotion"] == []
    assert record["culture"]["adaptation"] is None
    assert record["metadata"]["form_detection"] == "automatic_structure_only"
    assert record["metadata"]["script"] == "traditional"


def test_iter_candidates_reads_json_and_deduplicates(tmp_path: Path):
    source = tmp_path / "poet.tang.0.json"
    item = {
        "id": "1",
        "title": "示例",
        "author": "某甲",
        "paragraphs": [
            "朝辭白帝彩雲間，千里江陵一日還。",
            "兩岸猿聲啼不住，輕舟已過萬重山。",
        ],
    }
    source.write_text(json.dumps([item, item], ensure_ascii=False), encoding="utf-8")

    result = list(iter_candidates([source]))
    assert len(result) == 1
    assert result[0].form == "qijue7"
