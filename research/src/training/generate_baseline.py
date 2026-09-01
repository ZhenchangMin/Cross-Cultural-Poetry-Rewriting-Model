# -*- coding: utf-8 -*-
"""Load a trained LoRA adapter and generate one controlled poem."""
from __future__ import annotations

from pathlib import Path
from typing import Mapping

import torch
from peft import PeftModel
from transformers import AutoModelForCausalLM

from src.data.dataset import build_reconstruction_prompt
from src.training.config import BaselineConfig
from src.training.model_factory import load_tokenizer, resolve_runtime


def generate_from_control(
    config: BaselineConfig,
    control_record: Mapping[str, object],
    adapter_path: Path | str,
    *,
    model_name_or_path: str | None = None,
    device: str = "auto",
) -> str:
    runtime = resolve_runtime(config, device=device)
    base_source = model_name_or_path or config.model.model_id
    tokenizer = load_tokenizer(base_source)

    base_model = AutoModelForCausalLM.from_pretrained(
        base_source,
        torch_dtype=runtime.dtype,
    )
    model = PeftModel.from_pretrained(base_model, adapter_path)
    model.to(runtime.device)
    model.eval()
    model.config.use_cache = True

    prompt = build_reconstruction_prompt(control_record)
    input_ids = tokenizer.apply_chat_template(
        [{"role": "user", "content": prompt}],
        tokenize=True,
        add_generation_prompt=True,
        return_tensors="pt",
    ).to(runtime.device)
    attention_mask = torch.ones_like(input_ids)

    generation_kwargs = {
        "max_new_tokens": config.generation.max_new_tokens,
        "do_sample": config.generation.do_sample,
        "pad_token_id": tokenizer.pad_token_id,
        "eos_token_id": tokenizer.eos_token_id,
    }
    if config.generation.do_sample:
        generation_kwargs.update(
            temperature=config.generation.temperature,
            top_p=config.generation.top_p,
        )

    with torch.no_grad():
        output_ids = model.generate(
            input_ids=input_ids,
            attention_mask=attention_mask,
            **generation_kwargs,
        )
    completion = output_ids[0, input_ids.shape[1] :]
    return tokenizer.decode(completion, skip_special_tokens=True).strip()
