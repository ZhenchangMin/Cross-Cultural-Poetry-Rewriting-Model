# -*- coding: utf-8 -*-
"""Model/tokenizer construction for the B0 Qwen2.5 LoRA baseline."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Tuple

import torch
from peft import LoraConfig, TaskType, get_peft_model
from transformers import AutoModelForCausalLM, AutoTokenizer

from src.training.config import BaselineConfig


@dataclass(frozen=True)
class ModelRuntime:
    device: torch.device
    dtype: torch.dtype


def resolve_runtime(config: BaselineConfig, device: str = "auto") -> ModelRuntime:
    if device == "auto":
        resolved_device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    else:
        resolved_device = torch.device(device)

    precision = config.model.precision
    if resolved_device.type == "cpu" and precision != "fp32":
        raise RuntimeError(
            f"Configured precision={precision} requires GPU for the real baseline; "
            "use fp32 only for CPU diagnostics."
        )
    if precision == "bf16":
        if not torch.cuda.is_available() or not torch.cuda.is_bf16_supported():
            raise RuntimeError("bf16 requested but CUDA bf16 support is unavailable")
        dtype = torch.bfloat16
    elif precision == "fp16":
        if resolved_device.type != "cuda":
            raise RuntimeError("fp16 training requires CUDA")
        dtype = torch.float16
    else:
        dtype = torch.float32
    return ModelRuntime(device=resolved_device, dtype=dtype)


def load_tokenizer(model_name_or_path: str):
    tokenizer = AutoTokenizer.from_pretrained(model_name_or_path)
    if tokenizer.pad_token_id is None:
        if tokenizer.eos_token is None:
            raise ValueError("Tokenizer has neither pad token nor EOS token")
        tokenizer.pad_token = tokenizer.eos_token
    tokenizer.padding_side = "right"
    return tokenizer


def apply_lora(model, config: BaselineConfig):
    lora = LoraConfig(
        task_type=TaskType.CAUSAL_LM,
        inference_mode=False,
        r=config.lora.r,
        lora_alpha=config.lora.alpha,
        lora_dropout=config.lora.dropout,
        bias="none",
        target_modules=list(config.lora.target_modules),
    )
    return get_peft_model(model, lora)


def load_model_for_training(
    config: BaselineConfig,
    *,
    model_name_or_path: str | None = None,
    device: str = "auto",
):
    runtime = resolve_runtime(config, device=device)
    source = model_name_or_path or config.model.model_id
    model = AutoModelForCausalLM.from_pretrained(source, torch_dtype=runtime.dtype)
    model.config.use_cache = False
    if config.model.gradient_checkpointing:
        model.gradient_checkpointing_enable()
    model = apply_lora(model, config)
    model.to(runtime.device)
    return model, runtime


def trainable_parameter_counts(model) -> Tuple[int, int]:
    total = sum(p.numel() for p in model.parameters())
    trainable = sum(p.numel() for p in model.parameters() if p.requires_grad)
    return trainable, total
