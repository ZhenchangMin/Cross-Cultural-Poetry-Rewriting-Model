# -*- coding: utf-8 -*-
from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from src.data.preannotate_style import (
    _extract_json_object,
    build_llm_prompt,
    density_prelabel,
    find_imagery_matches,
    imagery_prelabel,
    rule_preannotate_record,
    validate_llm_result,
)

ROOT = Path(__file__).resolve().parents[1]
LEXICON = json.loads((ROOT / "configs" / "imagery_lexicon_v1.json").read_text(encoding="utf-8"))
SCHEMA = json.loads((ROOT / "configs" / "style_schema.json").read_text(encoding="utf-8"))


def _record(text: str) -> dict:
    return {
        "id": "tang-test-001",
        "text": text,
        "form": "qijue7",
        "style": {
            "emotion": [],
            "imagery": [],
            "diction": "",
            "expression": "",
            "energy": "",
            "density": "",
        },
        "culture": {"adaptation": None},
        "metadata": {"title": "測試", "author": "某甲", "dynasty": "唐", "source": "test"},
    }


def test_longest_match_suppresses_river_inside_galaxy():
    lexicon = {"celestial": ["銀河"], "landscape": ["河"]}
    matches = find_imagery_matches("銀河落九天", lexicon)
    assert matches["celestial"] == ["銀河"]
    assert matches["landscape"] == []


def test_imagery_prelabel_has_interpretable_evidence():
    poem = "秋月照江舟\n孤雁過寒洲\n客路連山遠\n霜風入古樓"
    result = imagery_prelabel(poem, LEXICON)
    assert 1 <= len(result["value"]) <= 4
    assert "landscape" in result["value"]
    assert "season_weather" in result["value"]
    assert result["status"] == "prelabeled"
    assert result["confidence"] > 0.4
    assert result["evidence"]


def test_density_uses_all_lexicon_evidence():
    imagery = {
        "value": ["landscape"],
        "evidence": {"landscape": ["山", "江", "湖", "溪", "峰", "谷", "泉"]},
    }
    result = density_prelabel("山江湖溪峰谷泉\n一二三四五六七\n一二三四五六七\n一二三四五六七", imagery, LEXICON)
    assert result["value"] == "dense"
    assert result["evidence"]["unique_imagery_terms"] == 7
    assert result["evidence"]["unique_imagery_terms_per_line"] == pytest.approx(1.75)


def test_rule_preannotation_never_modifies_training_style():
    original = _record("秋月照江舟\n孤雁過寒洲\n客路連山遠\n霜風入古樓")
    before_style = copy.deepcopy(original["style"])
    out = rule_preannotate_record(original, lexicon_cfg=LEXICON)
    assert out["style"] == before_style
    assert original.get("annotation") is None
    assert out["annotation"]["prelabel"]["imagery"]["status"] == "prelabeled"
    assert out["annotation"]["prelabel"]["emotion"]["status"] == "pending_llm"
    assert out["metadata"]["review_status"] == "preannotated_pending_review"


def test_llm_prompt_is_author_blind():
    record = _record("秋月照江舟\n孤雁過寒洲\n客路連山遠\n霜風入古樓")
    prompt = build_llm_prompt(record, SCHEMA)
    assert "某甲" not in prompt
    assert "測試" not in prompt
    assert record["text"] in prompt
    assert "melancholic" in prompt
    assert "vigorous" in prompt


def test_extract_json_accepts_markdown_fence():
    raw = "```json\n{\"a\": 1}\n```"
    assert _extract_json_object(raw) == {"a": 1}


def test_validate_llm_result_accepts_valid_labels_and_verbatim_evidence():
    poem = "秋月照江舟\n孤雁過寒洲\n客路連山遠\n霜風入古樓"
    result = {
        "emotion": {"value": ["melancholic", "lonely"], "confidence": 0.88, "evidence": ["孤雁", "客路"]},
        "diction": {"value": "refined", "confidence": 0.77, "evidence": ["秋月"]},
        "expression": {"value": "balanced", "confidence": 0.81, "evidence": ["霜風"]},
        "energy": {"value": "gentle", "confidence": 0.70, "evidence": ["照江舟"]},
    }
    out = validate_llm_result(result, SCHEMA, poem)
    assert out["emotion"]["value"] == ["melancholic", "lonely"]
    assert out["diction"]["method"] == "deepseek_semantic_v1"
    assert out["energy"]["status"] == "prelabeled"


def test_validate_llm_result_rejects_hallucinated_evidence():
    poem = "秋月照江舟\n孤雁過寒洲\n客路連山遠\n霜風入古樓"
    result = {
        "emotion": {"value": ["melancholic"], "confidence": 0.9, "evidence": ["萬里悲秋"]},
        "diction": {"value": "refined", "confidence": 0.8, "evidence": []},
        "expression": {"value": "balanced", "confidence": 0.8, "evidence": []},
        "energy": {"value": "gentle", "confidence": 0.8, "evidence": []},
    }
    with pytest.raises(ValueError, match="evidence not found"):
        validate_llm_result(result, SCHEMA, poem)
