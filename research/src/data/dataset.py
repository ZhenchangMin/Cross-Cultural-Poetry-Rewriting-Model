# -*- coding: utf-8 -*-
"""Training-side dataset utilities for the first controllable-poetry baseline.

This module deliberately stops *before* tokenizer/model-specific logic. Its job is:

1. load reviewed Gold JSONL;
2. validate every record against ``style_schema.json``;
3. convert one record into a stable training example with:
   - target poem text;
   - explicit form/style controls;
   - a deterministic text prompt that a later Qwen tokenizer can consume.

The first baseline is self-reconstruction: controls + task instruction -> original poem.
This is intentionally simpler than the final XLM-R + style-vector architecture, because
we want to verify the basic Dataset -> tokenizer -> LoRA -> loss pipeline first.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterator, List, Mapping, Optional, Sequence

from .validate_dataset import DEFAULT_SCHEMA, load_schema, validate_jsonl


FORM_NAMES = {
    "qijue7": "七言绝句",
    "qilv7": "七言律诗",
}

STYLE_ZH = {
    "emotion": {
        "serene": "清宁平和",
        "joyful": "欢愉明朗",
        "melancholic": "感伤惆怅",
        "lonely": "孤寂凄清",
        "heroic": "豪迈昂扬",
        "indignant": "悲愤沉郁",
    },
    "imagery": {
        "landscape": "山水自然",
        "celestial": "天象",
        "season_weather": "时令气候",
        "flora": "植物",
        "fauna": "动物",
        "travel": "行旅",
        "frontier": "边塞军旅",
        "human_culture": "人文文化",
    },
    "diction": {"plain": "质朴", "refined": "典雅", "ornate": "绮丽"},
    "expression": {"direct": "直抒", "balanced": "情景交融", "implicit": "含蓄"},
    "energy": {"gentle": "舒缓", "balanced": "平稳", "vigorous": "强烈顿挫"},
    "density": {"sparse": "疏朗", "medium": "适中", "dense": "密集"},
}


@dataclass(frozen=True)
class TrainingExample:
    id: str
    form: str
    style: Mapping[str, Any]
    target_text: str
    prompt_text: str


def _load_jsonl(path: Path) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as f:
        for lineno, raw in enumerate(f, 1):
            raw = raw.strip()
            if not raw:
                continue
            obj = json.loads(raw)
            if not isinstance(obj, dict):
                raise ValueError(f"Expected object at {path}:{lineno}")
            rows.append(obj)
    return rows


def _join_labels(values: Sequence[str], mapping: Mapping[str, str]) -> str:
    return "、".join(mapping[x] for x in values)


def build_control_summary(record: Mapping[str, Any]) -> str:
    """Turn the structured V1 control labels into deterministic readable text.

    For baseline B0 we intentionally expose controls as text. Later B1/M1 can replace
    this textual representation with learned style tokens/vectors without changing
    the underlying dataset schema.
    """
    form = str(record["form"])
    style = record["style"]
    return "\n".join(
        [
            f"诗体：{FORM_NAMES[form]}",
            f"情感：{_join_labels(style['emotion'], STYLE_ZH['emotion'])}",
            f"意象：{_join_labels(style['imagery'], STYLE_ZH['imagery'])}",
            f"辞藻：{STYLE_ZH['diction'][style['diction']]}",
            f"表达：{STYLE_ZH['expression'][style['expression']]}",
            f"气势：{STYLE_ZH['energy'][style['energy']]}",
            f"密度：{STYLE_ZH['density'][style['density']]}",
        ]
    )


def build_reconstruction_prompt(record: Mapping[str, Any]) -> str:
    """Build B0 self-reconstruction instruction.

    The target poem is NOT included in the prompt; it is the supervised answer.
    Author/title/metadata are also excluded to prevent identity shortcuts.
    """
    controls = build_control_summary(record)
    return (
        "你是一名中国古典诗歌生成模型。请严格依据给定诗体和风格控制，"
        "生成一首符合要求的古典诗。\n\n"
        "【控制条件】\n"
        f"{controls}\n\n"
        "【输出要求】\n"
        "只输出诗歌正文，不输出作者、标题、解释或额外说明。"
    )


def record_to_example(record: Mapping[str, Any]) -> TrainingExample:
    return TrainingExample(
        id=str(record["id"]),
        form=str(record["form"]),
        style=dict(record["style"]),
        target_text=str(record["text"]),
        prompt_text=build_reconstruction_prompt(record),
    )


class PoetryTrainingDataset(Sequence[TrainingExample]):
    """A small, framework-agnostic Gold Dataset loader.

    We intentionally do not inherit from ``torch.utils.data.Dataset`` yet. Python's
    Sequence protocol already provides the same len/getitem semantics and keeps the
    data layer testable before adding Torch/Transformers dependencies.
    """

    def __init__(
        self,
        path: Path | str,
        *,
        schema_path: Path | str = DEFAULT_SCHEMA,
        validate: bool = True,
    ) -> None:
        self.path = Path(path)
        self.schema_path = Path(schema_path)

        if validate:
            schema = load_schema(self.schema_path)
            report = validate_jsonl(self.path, schema, stage="gold")
            if not report.ok:
                preview = "; ".join(
                    f"line {x.line} {x.field}: {x.message}" for x in report.issues[:5]
                )
                raise ValueError(
                    f"Dataset is not Gold-ready: {report.invalid_records}/{report.records} invalid records. "
                    f"{preview}"
                )

        self._records = _load_jsonl(self.path)

    def __len__(self) -> int:
        return len(self._records)

    def __getitem__(self, index: int) -> TrainingExample:
        return record_to_example(self._records[index])

    def __iter__(self) -> Iterator[TrainingExample]:
        for record in self._records:
            yield record_to_example(record)


def inspect_dataset(path: Path | str, limit: int = 3) -> List[Dict[str, str]]:
    """Convenience helper used during development to inspect model-facing examples."""
    dataset = PoetryTrainingDataset(path)
    output: List[Dict[str, str]] = []
    for i, example in enumerate(dataset):
        if i >= limit:
            break
        output.append(
            {
                "id": example.id,
                "form": example.form,
                "prompt": example.prompt_text,
                "target": example.target_text,
            }
        )
    return output
