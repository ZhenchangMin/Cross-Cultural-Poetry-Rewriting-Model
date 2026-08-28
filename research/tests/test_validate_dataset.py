import json
from pathlib import Path

from src.data.validate_dataset import load_schema, validate_jsonl, validate_record


SCHEMA = load_schema(Path("configs/style_schema.json"))


def gold_record():
    return {
        "id": "x1",
        "text": "春风拂柳入新塘\n月照孤舟夜未央\n远客凭栏思故里\n寒星点点落清霜",
        "form": "qijue7",
        "style": {
            "emotion": ["melancholic", "lonely"],
            "imagery": ["celestial", "travel", "season_weather"],
            "diction": "refined",
            "expression": "balanced",
            "energy": "gentle",
            "density": "medium",
        },
        "culture": {"adaptation": None},
        "metadata": {"author": "测试"},
    }


def test_valid_gold_record():
    assert validate_record(gold_record(), SCHEMA, stage="gold") == []


def test_blank_style_allowed_for_candidate_but_not_gold():
    record = gold_record()
    record["style"] = {
        "emotion": [],
        "imagery": [],
        "diction": "",
        "expression": "",
        "energy": "",
        "density": "",
    }
    assert validate_record(record, SCHEMA, stage="candidate") == []
    issues = validate_record(record, SCHEMA, stage="gold")
    fields = {x.field for x in issues}
    assert "style.emotion" in fields
    assert "style.imagery" in fields
    assert "style.diction" in fields


def test_structure_is_checked():
    record = gold_record()
    record["text"] = "春风拂柳入新塘\n月照孤舟夜未央"
    issues = validate_record(record, SCHEMA, stage="gold")
    assert any(x.field == "text" and "requires 4 lines" in x.message for x in issues)


def test_invalid_style_label_rejected():
    record = gold_record()
    record["style"]["diction"] = "super_fancy"
    issues = validate_record(record, SCHEMA, stage="gold")
    assert any(x.field == "style.diction" for x in issues)


def test_duplicate_ids_are_reported(tmp_path):
    p = tmp_path / "dup.jsonl"
    row = json.dumps(gold_record(), ensure_ascii=False)
    p.write_text(row + "\n" + row + "\n", encoding="utf-8")
    report = validate_jsonl(p, SCHEMA, stage="gold")
    assert not report.ok
    assert report.duplicate_ids == 1
    assert report.invalid_records == 1


def test_real_preannotated_dataset_passes_preannotation_gate():
    path = Path("data/processed/style_annotation/preannotated_v1.jsonl")
    report = validate_jsonl(path, SCHEMA, stage="preannotated")
    assert report.ok
    assert report.records == 1000


def test_real_preannotated_dataset_is_not_gold_ready():
    path = Path("data/processed/style_annotation/preannotated_v1.jsonl")
    report = validate_jsonl(path, SCHEMA, stage="gold")
    assert not report.ok
    assert report.invalid_records == 1000
