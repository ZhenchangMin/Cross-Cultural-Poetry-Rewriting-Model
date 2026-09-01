# -*- coding: utf-8 -*-
from __future__ import annotations

import torch

from src.data.tokenization import IGNORE_INDEX, TokenizedExample
from src.training.collator import CausalLMCollator
from src.training.tiny_overfit import (
    TinyOverfitConfig,
    TinyOverfitResult,
    build_synthetic_examples,
    build_tiny_qwen_lora,
    parameter_counts,
)


def test_torch_collator_preserves_mask_and_padding():
    examples = [
        TokenizedExample(
            id="a",
            input_ids=[1, 2, 3],
            attention_mask=[1, 1, 1],
            labels=[IGNORE_INDEX, 2, 3],
            prompt_tokens=1,
            supervised_tokens=2,
            truncated=False,
        ),
        TokenizedExample(
            id="b",
            input_ids=[4, 5],
            attention_mask=[1, 1],
            labels=[IGNORE_INDEX, 5],
            prompt_tokens=1,
            supervised_tokens=1,
            truncated=False,
        ),
    ]

    batch = CausalLMCollator(pad_token_id=0, pad_to_multiple_of=4)(examples)

    assert batch["input_ids"].dtype == torch.long
    assert batch["attention_mask"].dtype == torch.long
    assert batch["labels"].dtype == torch.long
    assert tuple(batch["input_ids"].shape) == (2, 4)
    assert batch["input_ids"].tolist() == [[1, 2, 3, 0], [4, 5, 0, 0]]
    assert batch["attention_mask"].tolist() == [[1, 1, 1, 0], [1, 1, 0, 0]]
    assert batch["labels"].tolist() == [
        [IGNORE_INDEX, 2, 3, IGNORE_INDEX],
        [IGNORE_INDEX, 5, IGNORE_INDEX, IGNORE_INDEX],
    ]


def test_tiny_qwen_lora_backward_updates_adapter_parameter():
    torch.manual_seed(7)
    config = TinyOverfitConfig(
        hidden_size=32,
        intermediate_size=64,
        num_hidden_layers=1,
        num_attention_heads=4,
        num_key_value_heads=2,
        lora_r=4,
        lora_alpha=8,
        steps=1,
    )
    model = build_tiny_qwen_lora(config)
    trainable, total = parameter_counts(model)

    assert 0 < trainable < total
    assert any("lora_" in name for name, p in model.named_parameters() if p.requires_grad)
    assert all(
        ("lora_" in name) == p.requires_grad
        for name, p in model.named_parameters()
    )

    batch = CausalLMCollator(pad_token_id=0)(build_synthetic_examples())
    trainable_params = [p for p in model.parameters() if p.requires_grad]
    before = [p.detach().clone() for p in trainable_params]

    optimizer = torch.optim.AdamW(trainable_params, lr=1e-2)
    optimizer.zero_grad(set_to_none=True)
    loss = model(**batch).loss
    assert torch.isfinite(loss)
    loss.backward()
    assert any(p.grad is not None and torch.count_nonzero(p.grad).item() > 0 for p in trainable_params)
    optimizer.step()

    assert any(not torch.equal(old, new.detach()) for old, new in zip(before, trainable_params))


def test_tiny_overfit_acceptance_requires_memorization_and_loss_drop():
    passed = TinyOverfitResult(
        initial_loss=4.0,
        final_loss=3.2,
        initial_token_accuracy=0.0,
        final_token_accuracy=1.0,
        trainable_parameters=10,
        total_parameters=100,
        losses=[4.0, 3.2],
    )
    weak_accuracy = TinyOverfitResult(
        initial_loss=4.0,
        final_loss=3.0,
        initial_token_accuracy=0.0,
        final_token_accuracy=0.8,
        trainable_parameters=10,
        total_parameters=100,
        losses=[4.0, 3.0],
    )
    no_loss_drop = TinyOverfitResult(
        initial_loss=4.0,
        final_loss=3.8,
        initial_token_accuracy=0.0,
        final_token_accuracy=1.0,
        trainable_parameters=10,
        total_parameters=100,
        losses=[4.0, 3.8],
    )

    assert passed.passed is True
    assert weak_accuracy.passed is False
    assert no_loss_drop.passed is False
