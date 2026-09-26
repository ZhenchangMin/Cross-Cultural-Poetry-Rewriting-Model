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
import hashlib
import math
from copy import deepcopy
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Iterator, List, Mapping, Optional, Sequence

from .validate_dataset import DEFAULT_SCHEMA, STYLE_DIMS, load_schema, validate_jsonl


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
    available_controls: tuple[str, ...] = ()
    active_controls: tuple[str, ...] = ()
    source: str = 'gold'
    supervision_type: Mapping[str, str] = field(default_factory=dict)
    sampling_weight: float = 1.0
    provenance: Mapping[str, Any] = field(default_factory=dict)


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


def available_controls(record: Mapping[str, Any]) -> tuple[str, ...]:
    declared = record.get('available_controls')
    allowed = ('form',) + STYLE_DIMS
    inferred = tuple(d for d in allowed if d == 'form' or record['style'].get(d) is not None)
    if declared is None:
        return inferred
    if len(set(declared)) != len(declared) or 'form' not in declared or any(d not in inferred for d in declared):
        raise ValueError('Invalid available_controls')
    return tuple(d for d in allowed if d in declared)


def dropout_controls(record, probability=0., seed=0, epoch=0, training=False):
    if not math.isfinite(probability) or not 0 <= probability <= 1:
        raise ValueError('control dropout probability must be in [0,1]')
    controls = available_controls(record)
    if not training or probability == 0: return controls
    # 按seed/epoch/id/维度生成稳定随机数，不依赖读取顺序或worker全局RNG。
    def keep(d):
        digest = hashlib.sha256(f'{seed}:{epoch}:{record["id"]}:{d}'.encode()).digest()
        return int.from_bytes(digest[:8], 'big') / 2**64 >= probability
    return tuple(d for d in controls if d == 'form' or keep(d))


def build_control_summary(record: Mapping[str, Any], controls=None) -> str:
    """Turn the structured V1 control labels into deterministic readable text.

    For baseline B0 we intentionally expose controls as text. Later B1/M1 can replace
    this textual representation with learned style tokens/vectors without changing
    the underlying dataset schema.
    """
    form = str(record["form"])
    style = record["style"]
    available = available_controls(record)
    controls = available if controls is None else tuple(controls)
    if 'form' not in controls or not set(controls) <= set(available):
        raise ValueError('Controls must be supervised and always include form')
    names = dict(emotion='情感', imagery='意象', diction='辞藻', expression='表达', energy='气势', density='密度')
    lines = [f'诗体：{FORM_NAMES[form]}']
    for d in STYLE_DIMS:
        if d not in controls: continue
        value = _join_labels(style[d], STYLE_ZH[d]) if d in ('emotion', 'imagery') else STYLE_ZH[d][style[d]]
        lines.append(f'{names[d]}：{value}')
    return '\n'.join(lines)


def build_reconstruction_prompt(record: Mapping[str, Any], controls=None) -> str:
    """Build B0 self-reconstruction instruction.

    The target poem is NOT included in the prompt; it is the supervised answer.
    Author/title/metadata are also excluded to prevent identity shortcuts.
    """
    controls = build_control_summary(record, controls)
    return (
        "你是一名中国古典诗歌生成模型。请严格依据给定诗体和风格控制，"
        "生成一首符合要求的古典诗。\n\n"
        "【控制条件】\n"
        f"{controls}\n\n"
        "【输出要求】\n"
        "只输出诗歌正文，不输出作者、标题、解释或额外说明。"
    )


def record_to_example(record: Mapping[str, Any], *, controls=None, source=None, sampling_weight=1.0, provenance=None) -> TrainingExample:
    available = available_controls(record)
    active = available if controls is None else tuple(controls)
    source = source or record.get('dataset_stage', 'gold')
    return TrainingExample(
        id=str(record["id"]),
        form=str(record["form"]),
        style=dict(record["style"]),
        target_text=str(record["text"]),
        prompt_text=build_reconstruction_prompt(record, active),
        available_controls=available, active_controls=active, source=source,
        supervision_type=deepcopy(record.get('supervision', {d: 'human_gold' for d in available})),
        sampling_weight=sampling_weight,
        provenance=deepcopy(provenance if provenance is not None else record.get('annotation', {})),
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
        stage: str = 'gold',
        training: bool = False,
        control_dropout: float = 0.,
        seed: int = 0,
    ) -> None:
        self.path = Path(path)
        self.schema_path = Path(schema_path)
        if stage not in ('gold', 'partial-silver', 'form-only'): raise ValueError('Unsupported training data stage')
        self.stage = stage
        self.training = training
        self.control_dropout = control_dropout
        self.seed = seed
        self.epoch = 0
        if not math.isfinite(control_dropout) or not 0 <= control_dropout <= 1: raise ValueError('Invalid control dropout')

        if validate:
            schema = load_schema(self.schema_path)
            report = validate_jsonl(self.path, schema, stage=stage)
            if not report.ok:
                preview = "; ".join(
                    f"line {x.line} {x.field}: {x.message}" for x in report.issues[:5]
                )
                raise ValueError(
                    f"Dataset is not {'Gold' if stage == 'gold' else stage}-ready: {report.invalid_records}/{report.records} invalid records. "
                    f"{preview}"
                )

        self._records = _load_jsonl(self.path)

    def __len__(self) -> int:
        return len(self._records)

    def __getitem__(self, index: int) -> TrainingExample:
        record = self._records[index]
        controls = dropout_controls(record, self.control_dropout, self.seed, self.epoch, self.training)
        return record_to_example(record, controls=controls, source=self.stage,
                                 provenance={'source_file': str(self.path), 'annotation': deepcopy(record.get('annotation', {}))})

    def set_epoch(self, epoch: int) -> None:
        self.epoch = epoch

    def __iter__(self) -> Iterator[TrainingExample]:
        for i in range(len(self)):
            yield self[i]


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
