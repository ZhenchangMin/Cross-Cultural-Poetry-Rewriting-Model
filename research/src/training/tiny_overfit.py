# -*- coding: utf-8 -*-
"""A CPU-friendly end-to-end overfit test for the Qwen2 + LoRA training path.

This module does **not** download or train the real 1.5B checkpoint. It instantiates a
very small random Qwen2 architecture locally and repeatedly trains the same four
synthetic causal-LM samples. The purpose is engineering validation:

    TokenizedExample -> tensor batch -> Qwen2 forward -> masked loss
    -> LoRA gradients -> backward -> optimizer.step

If this tiny problem cannot be memorized, scaling to a real pretrained checkpoint would
only make debugging harder and more expensive.
"""
from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Dict, List, Sequence

import torch
from peft import LoraConfig, TaskType, get_peft_model
from transformers import Qwen2Config, Qwen2ForCausalLM

from src.data.tokenization import IGNORE_INDEX, TokenizedExample
from src.training.collator import CausalLMCollator


@dataclass(frozen=True)
class TinyOverfitConfig:
    vocab_size: int = 64
    hidden_size: int = 48
    intermediate_size: int = 96
    num_hidden_layers: int = 2
    num_attention_heads: int = 4
    num_key_value_heads: int = 2
    max_position_embeddings: int = 64
    lora_r: int = 8
    lora_alpha: int = 16
    learning_rate: float = 1e-2
    steps: int = 600
    seed: int = 20260901
    device: str = "cpu"


@dataclass(frozen=True)
class TinyOverfitResult:
    initial_loss: float
    final_loss: float
    initial_token_accuracy: float
    final_token_accuracy: float
    trainable_parameters: int
    total_parameters: int
    losses: List[float]

    @property
    def loss_ratio(self) -> float:
        return self.final_loss / self.initial_loss

    @property
    def passed(self) -> bool:
        """Engineering success criterion for pure LoRA on a frozen random base.

        A random frozen LM head can keep cross-entropy numerically high even after the
        adapter makes every gold token top-1. For this smoke test, successful memorization
        therefore means near-perfect teacher-forced token accuracy plus a clear loss
        decrease, not an arbitrary near-zero loss target.
        """
        return self.final_token_accuracy >= 0.95 and self.loss_ratio <= 0.90


def set_seed(seed: int) -> None:
    random.seed(seed)
    torch.manual_seed(seed)


def build_synthetic_examples() -> List[TokenizedExample]:
    """Return four tiny prompt->completion pairs using the real project data contract.

    Tokens 1..19 behave like prompt/control tokens and are masked with -100. Tokens
    20..39 are supervised completions. The exact IDs are artificial on purpose: the
    test validates optimization mechanics rather than Chinese tokenizer quality, which
    is already covered separately by ``smoke_tokenizer.py``.
    """
    pairs = [
        ([1, 10, 11, 12, 13], [20, 21, 22, 23, 2]),
        ([1, 10, 14, 15, 16], [24, 25, 26, 27, 2]),
        ([1, 17, 11, 15, 18], [28, 29, 30, 31, 2]),
        ([1, 17, 14, 12, 19], [32, 33, 34, 35, 2]),
    ]
    examples: List[TokenizedExample] = []
    for index, (prompt, completion) in enumerate(pairs):
        input_ids = prompt + completion
        labels = [IGNORE_INDEX] * len(prompt) + completion
        examples.append(
            TokenizedExample(
                id=f"tiny-{index}",
                input_ids=input_ids,
                attention_mask=[1] * len(input_ids),
                labels=labels,
                prompt_tokens=len(prompt),
                supervised_tokens=len(completion),
                truncated=False,
            )
        )
    return examples


def build_tiny_qwen_lora(config: TinyOverfitConfig):
    """Instantiate a random tiny Qwen2 and inject LoRA into its transformer linears."""
    qwen_config = Qwen2Config(
        vocab_size=config.vocab_size,
        hidden_size=config.hidden_size,
        intermediate_size=config.intermediate_size,
        num_hidden_layers=config.num_hidden_layers,
        num_attention_heads=config.num_attention_heads,
        num_key_value_heads=config.num_key_value_heads,
        max_position_embeddings=config.max_position_embeddings,
        bos_token_id=1,
        eos_token_id=2,
        pad_token_id=0,
        tie_word_embeddings=False,
    )
    base_model = Qwen2ForCausalLM(qwen_config)
    lora_config = LoraConfig(
        task_type=TaskType.CAUSAL_LM,
        inference_mode=False,
        r=config.lora_r,
        lora_alpha=config.lora_alpha,
        lora_dropout=0.0,
        bias="none",
        target_modules=[
            "q_proj",
            "k_proj",
            "v_proj",
            "o_proj",
            "gate_proj",
            "up_proj",
            "down_proj",
        ],
    )
    return get_peft_model(base_model, lora_config)


def parameter_counts(model: torch.nn.Module) -> tuple[int, int]:
    total = sum(parameter.numel() for parameter in model.parameters())
    trainable = sum(
        parameter.numel() for parameter in model.parameters() if parameter.requires_grad
    )
    return trainable, total


def supervised_token_accuracy(model: torch.nn.Module, batch: Dict[str, torch.Tensor]) -> float:
    """Teacher-forced next-token accuracy over labels that are not masked by -100."""
    model.eval()
    with torch.no_grad():
        logits = model(
            input_ids=batch["input_ids"],
            attention_mask=batch["attention_mask"],
        ).logits

    predictions = logits[:, :-1].argmax(dim=-1)
    labels = batch["labels"][:, 1:]
    active = labels.ne(IGNORE_INDEX)
    if not bool(active.any()):
        raise ValueError("Tiny batch contains no supervised next-token labels")
    correct = predictions.eq(labels) & active
    return float(correct.sum().item() / active.sum().item())


def evaluate_loss(model: torch.nn.Module, batch: Dict[str, torch.Tensor]) -> float:
    model.eval()
    with torch.no_grad():
        return float(model(**batch).loss.item())


def run_tiny_overfit(config: TinyOverfitConfig | None = None) -> TinyOverfitResult:
    """Run the complete LoRA optimization smoke test on CPU by default."""
    config = config or TinyOverfitConfig()
    set_seed(config.seed)

    device = torch.device(config.device)
    model = build_tiny_qwen_lora(config).to(device)
    collator = CausalLMCollator(pad_token_id=0)
    batch = {
        key: value.to(device)
        for key, value in collator(build_synthetic_examples()).items()
    }

    trainable, total = parameter_counts(model)
    if trainable <= 0 or trainable >= total:
        raise RuntimeError(
            f"LoRA parameter isolation failed: trainable={trainable}, total={total}"
        )

    initial_loss = evaluate_loss(model, batch)
    initial_accuracy = supervised_token_accuracy(model, batch)

    optimizer = torch.optim.AdamW(
        (parameter for parameter in model.parameters() if parameter.requires_grad),
        lr=config.learning_rate,
        weight_decay=0.0,
    )

    losses: List[float] = []
    model.train()
    for _ in range(config.steps):
        optimizer.zero_grad(set_to_none=True)
        outputs = model(**batch)
        loss = outputs.loss
        if not torch.isfinite(loss):
            raise RuntimeError(f"Non-finite training loss: {loss.item()}")
        loss.backward()
        torch.nn.utils.clip_grad_norm_(
            [parameter for parameter in model.parameters() if parameter.requires_grad],
            max_norm=1.0,
        )
        optimizer.step()
        losses.append(float(loss.detach().item()))

    final_loss = evaluate_loss(model, batch)
    final_accuracy = supervised_token_accuracy(model, batch)

    return TinyOverfitResult(
        initial_loss=initial_loss,
        final_loss=final_loss,
        initial_token_accuracy=initial_accuracy,
        final_token_accuracy=final_accuracy,
        trainable_parameters=trainable,
        total_parameters=total,
        losses=losses,
    )
