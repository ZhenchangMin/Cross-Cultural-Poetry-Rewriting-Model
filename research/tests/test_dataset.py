import json
from pathlib import Path

import pytest

from src.data.dataset import PoetryTrainingDataset, build_control_summary, build_reconstruction_prompt, record_to_example


def gold_record():
    return {
        "id": "gold-1",
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
        "metadata": {"author": "测试作者", "title": "测试诗"},
    }


def test_control_summary_is_stable_and_human_readable():
    summary = build_control_summary(gold_record())
    assert "诗体：七言绝句" in summary
    assert "情感：感伤惆怅、孤寂凄清" in summary
    assert "意象：天象、行旅、时令气候" in summary
    assert "辞藻：典雅" in summary


def test_prompt_excludes_metadata_and_target_poem():
    record = gold_record()
    prompt = build_reconstruction_prompt(record)
    assert "测试作者" not in prompt
    assert "测试诗" not in prompt
    assert record["text"] not in prompt
    assert "【控制条件】" in prompt


def test_record_to_example_keeps_target_separate():
    record = gold_record()
    ex = record_to_example(record)
    assert ex.id == "gold-1"
    assert ex.target_text == record["text"]
    assert ex.target_text not in ex.prompt_text


def test_gold_dataset_loads(tmp_path):
    p = tmp_path / "gold.jsonl"
    p.write_text(json.dumps(gold_record(), ensure_ascii=False) + "\n", encoding="utf-8")
    ds = PoetryTrainingDataset(p)
    assert len(ds) == 1
    assert ds[0].form == "qijue7"
    assert ds[0].target_text.startswith("春风")


def test_current_preannotated_file_is_rejected_as_training_gold():
    path = Path("data/processed/style_annotation/preannotated_v1.jsonl")
    with pytest.raises(ValueError, match="not Gold-ready"):
        PoetryTrainingDataset(path)
