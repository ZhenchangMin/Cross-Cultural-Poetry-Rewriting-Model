# -*- coding: utf-8 -*-
"""Transparent PyTorch training loop for B0 Qwen2.5 + LoRA.

The framework is intentionally inactive until a human-reviewed Gold JSONL exists.
`build_training_dataloader` constructs `PoetryTrainingDataset(validate=True)` first,
so weak/preannotated data cannot silently reach the model.
"""
from __future__ import annotations

import json
import random
from pathlib import Path
from typing import Dict

import torch

from src.data.dataset import PoetryTrainingDataset
from src.training.config import BaselineConfig
from src.training.data_pipeline import build_training_dataloader
from src.training.model_factory import (
    load_model_for_training,
    load_tokenizer,
    trainable_parameter_counts,
)


def set_training_seed(seed: int) -> None:
    random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)


def move_batch(batch: Dict[str, torch.Tensor], device: torch.device) -> Dict[str, torch.Tensor]:
    return {key: value.to(device) for key, value in batch.items()}


def save_adapter_checkpoint(
    model,
    tokenizer,
    config: BaselineConfig,
    *,
    output_root: Path,
    global_step: int,
    epoch: int,
    mean_loss: float,
) -> Path:
    checkpoint = output_root / f"checkpoint-{global_step:06d}"
    checkpoint.mkdir(parents=True, exist_ok=True)
    model.save_pretrained(checkpoint)
    tokenizer.save_pretrained(checkpoint)
    state = {
        "experiment_name": config.experiment_name,
        "global_step": global_step,
        "epoch": epoch,
        "mean_loss": mean_loss,
        "base_model": config.model.model_id,
    }
    with (checkpoint / "training_state.json").open("w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)
    return checkpoint


def train_baseline(
    config: BaselineConfig,
    gold_path: Path | str,
    *,
    model_name_or_path: str | None = None,
    device: str = "auto",
) -> Dict[str, float | int | str]:
    set_training_seed(config.training.seed)

    # Important order: validate Gold data BEFORE any tokenizer/model network access.
    gold_dataset = PoetryTrainingDataset(gold_path, validate=True)
    tokenizer_source = model_name_or_path or config.model.model_id
    tokenizer = load_tokenizer(tokenizer_source)
    loader = build_training_dataloader(
        gold_dataset,
        tokenizer,
        max_length=config.model.max_length,
        batch_size=config.training.batch_size,
        seed=config.training.seed,
        shuffle=True,
    )

    model, runtime = load_model_for_training(
        config,
        model_name_or_path=model_name_or_path,
        device=device,
    )
    trainable, total = trainable_parameter_counts(model)
    if trainable <= 0 or trainable >= total:
        raise RuntimeError(f"Invalid LoRA isolation: trainable={trainable}, total={total}")

    optimizer = torch.optim.AdamW(
        (p for p in model.parameters() if p.requires_grad),
        lr=config.training.learning_rate,
        weight_decay=config.training.weight_decay,
    )

    accumulation = config.training.gradient_accumulation_steps
    output_root = Path(config.training.output_dir)
    output_root.mkdir(parents=True, exist_ok=True)

    global_step = 0
    optimizer_steps = 0
    micro_batches_since_step = 0
    running_loss = 0.0
    model.train()
    optimizer.zero_grad(set_to_none=True)

    for epoch in range(1, config.training.epochs + 1):
        for batch_index, batch in enumerate(loader, 1):
            batch = move_batch(batch, runtime.device)
            outputs = model(**batch)
            raw_loss = outputs.loss
            if not torch.isfinite(raw_loss):
                raise RuntimeError(f"Non-finite loss at step {global_step + 1}: {raw_loss.item()}")

            (raw_loss / accumulation).backward()
            global_step += 1
            micro_batches_since_step += 1
            running_loss += float(raw_loss.detach().item())

            should_step = micro_batches_since_step >= accumulation or batch_index == len(loader)
            if should_step:
                torch.nn.utils.clip_grad_norm_(
                    [p for p in model.parameters() if p.requires_grad],
                    config.training.max_grad_norm,
                )
                optimizer.step()
                optimizer.zero_grad(set_to_none=True)
                optimizer_steps += 1
                micro_batches_since_step = 0

            if global_step % config.training.log_every_steps == 0:
                mean_loss = running_loss / global_step
                print(
                    f"epoch={epoch} step={global_step} optimizer_steps={optimizer_steps} "
                    f"mean_loss={mean_loss:.6f}"
                )

            if global_step % config.training.save_every_steps == 0:
                save_adapter_checkpoint(
                    model,
                    tokenizer,
                    config,
                    output_root=output_root,
                    global_step=global_step,
                    epoch=epoch,
                    mean_loss=running_loss / global_step,
                )

    final_loss = running_loss / max(global_step, 1)
    final_checkpoint = save_adapter_checkpoint(
        model,
        tokenizer,
        config,
        output_root=output_root,
        global_step=global_step,
        epoch=config.training.epochs,
        mean_loss=final_loss,
    )
    return {
        "global_steps": global_step,
        "optimizer_steps": optimizer_steps,
        "mean_loss": final_loss,
        "trainable_parameters": trainable,
        "total_parameters": total,
        "final_checkpoint": str(final_checkpoint),
    }
