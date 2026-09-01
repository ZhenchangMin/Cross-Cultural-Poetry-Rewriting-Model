# -*- coding: utf-8 -*-
from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path

import pytest
import torch
from transformers import Qwen2Config, Qwen2ForCausalLM

from src.data.dataset import TrainingExample
from src.training.config import load_baseline_config
from src.training.data_pipeline import TokenizedPoetryDataset
from src.training.model_factory import apply_lora, resolve_runtime, trainable_parameter_counts
from src.training.train_baseline import train_baseline


class FakeChatTokenizer:
    pad_token_id = 0
    eos_token_id = 2

    def apply_chat_template(self, conversation, *, tokenize, add_generation_prompt):
        ids = [1]
        for item in conversation:
            marker = 3 if item["role"] == "user" else 4
            ids += [marker] + [10 + (ord(ch) % 30) for ch in item["content"]] + [5]
        if add_generation_prompt:
            ids += [4]
        return ids


def test_default_baseline_config_is_valid():
    config = load_baseline_config()
    assert config.model.model_id == "Qwen/Qwen2.5-1.5B-Instruct"
    assert config.lora.r == 16
    assert config.training.gradient_accumulation_steps == 8
    assert config.model.max_length == 512


def test_tokenized_dataset_keeps_training_contract():
    example = TrainingExample("x", "qijue7", {}, "春风入夜", "控制条件")
    encoded = TokenizedPoetryDataset([example], FakeChatTokenizer(), max_length=64)[0]
    assert encoded.prompt_tokens > 0
    assert encoded.supervised_tokens > 0
    assert encoded.labels[: encoded.prompt_tokens] == [-100] * encoded.prompt_tokens


def test_default_lora_only_trains_adapters():
    config = load_baseline_config()
    tiny = Qwen2ForCausalLM(Qwen2Config(
        vocab_size=64,
        hidden_size=32,
        intermediate_size=64,
        num_hidden_layers=1,
        num_attention_heads=4,
        num_key_value_heads=2,
    ))
    model = apply_lora(tiny, config)
    trainable, total = trainable_parameter_counts(model)
    assert 0 < trainable < total
    assert all(("lora_" in name) == p.requires_grad for name, p in model.named_parameters())


def test_cpu_runtime_requires_fp32():
    config = load_baseline_config()
    with pytest.raises(RuntimeError, match="requires GPU"):
        resolve_runtime(config, device="cpu")
    fp32 = replace(config, model=replace(config.model, precision="fp32"))
    runtime = resolve_runtime(fp32, device="cpu")
    assert runtime.device.type == "cpu"
    assert runtime.dtype == torch.float32


def test_non_gold_is_rejected_before_tokenizer(tmp_path: Path, monkeypatch):
    path = tmp_path / "not_gold.jsonl"
    record = {
        "id": "x",
        "text": "春风吹柳绿江汀\n明月随舟照客星\n远寺钟声穿夜色\n一帆归梦入烟汀",
        "form": "qijue7",
        "style": {"emotion": [], "imagery": [], "diction": "", "expression": "", "energy": "", "density": ""},
        "culture": {"adaptation": None},
    }
    path.write_text(json.dumps(record, ensure_ascii=False) + "\n", encoding="utf-8")

    monkeypatch.setattr(
        "src.training.train_baseline.load_tokenizer",
        lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("tokenizer loaded too early")),
    )
    with pytest.raises(ValueError, match="not Gold-ready"):
        train_baseline(load_baseline_config(), path, device="cpu")
