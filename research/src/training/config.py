# -*- coding: utf-8 -*-
"""Configuration objects for the B0 Qwen LoRA baseline."""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import List


DEFAULT_BASELINE_CONFIG = Path("configs/baseline_qwen_lora.json")
SUPPORTED_PRECISIONS = {"fp32", "fp16", "bf16"}


@dataclass(frozen=True)
class ModelConfig:
    model_id: str
    precision: str
    gradient_checkpointing: bool
    max_length: int


@dataclass(frozen=True)
class LoraSettings:
    r: int
    alpha: int
    dropout: float
    target_modules: List[str]


@dataclass(frozen=True)
class TrainingSettings:
    batch_size: int
    gradient_accumulation_steps: int
    epochs: int
    learning_rate: float
    weight_decay: float
    max_grad_norm: float
    seed: int
    log_every_steps: int
    save_every_steps: int
    output_dir: str


@dataclass(frozen=True)
class GenerationSettings:
    max_new_tokens: int
    do_sample: bool
    temperature: float
    top_p: float


@dataclass(frozen=True)
class BaselineConfig:
    experiment_name: str
    model: ModelConfig
    lora: LoraSettings
    training: TrainingSettings
    generation: GenerationSettings

    def validate(self) -> None:
        if not self.experiment_name.strip():
            raise ValueError("experiment_name must be non-empty")
        if not self.model.model_id.strip():
            raise ValueError("model.model_id must be non-empty")
        if self.model.precision not in SUPPORTED_PRECISIONS:
            raise ValueError(
                f"model.precision must be one of {sorted(SUPPORTED_PRECISIONS)}, got {self.model.precision!r}"
            )
        if self.model.max_length <= 0:
            raise ValueError("model.max_length must be positive")
        if self.lora.r <= 0 or self.lora.alpha <= 0:
            raise ValueError("LoRA r/alpha must be positive")
        if not 0.0 <= self.lora.dropout < 1.0:
            raise ValueError("LoRA dropout must be in [0, 1)")
        if not self.lora.target_modules:
            raise ValueError("LoRA target_modules must not be empty")
        if self.training.batch_size <= 0:
            raise ValueError("training.batch_size must be positive")
        if self.training.gradient_accumulation_steps <= 0:
            raise ValueError("training.gradient_accumulation_steps must be positive")
        if self.training.epochs <= 0:
            raise ValueError("training.epochs must be positive")
        if self.training.learning_rate <= 0:
            raise ValueError("training.learning_rate must be positive")
        if self.training.max_grad_norm <= 0:
            raise ValueError("training.max_grad_norm must be positive")
        if self.training.log_every_steps <= 0 or self.training.save_every_steps <= 0:
            raise ValueError("log/save intervals must be positive")
        if self.generation.max_new_tokens <= 0:
            raise ValueError("generation.max_new_tokens must be positive")
        if self.generation.temperature <= 0:
            raise ValueError("generation.temperature must be positive")
        if not 0.0 < self.generation.top_p <= 1.0:
            raise ValueError("generation.top_p must be in (0, 1]")


def load_baseline_config(path: Path | str = DEFAULT_BASELINE_CONFIG) -> BaselineConfig:
    path = Path(path)
    with path.open("r", encoding="utf-8") as f:
        raw = json.load(f)

    config = BaselineConfig(
        experiment_name=str(raw["experiment_name"]),
        model=ModelConfig(**raw["model"]),
        lora=LoraSettings(**raw["lora"]),
        training=TrainingSettings(**raw["training"]),
        generation=GenerationSettings(**raw["generation"]),
    )
    config.validate()
    return config
