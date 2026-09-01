# -*- coding: utf-8 -*-
"""Gold-dataset -> tokenized DataLoader bridge for B0 training."""
from __future__ import annotations

from typing import Sequence

from torch.utils.data import DataLoader, Dataset

from src.data.dataset import PoetryTrainingDataset, TrainingExample
from src.data.tokenization import TokenizedExample, encode_training_example, resolve_pad_token_id
from src.training.collator import CausalLMCollator


class TokenizedPoetryDataset(Dataset):
    def __init__(self, examples: Sequence[TrainingExample], tokenizer, max_length: int) -> None:
        self.examples = examples
        self.tokenizer = tokenizer
        self.max_length = max_length

    def __len__(self) -> int:
        return len(self.examples)

    def __getitem__(self, index: int) -> TokenizedExample:
        return encode_training_example(
            self.tokenizer,
            self.examples[index],
            max_length=self.max_length,
        )


def build_training_dataloader(
    gold_source,
    tokenizer,
    *,
    max_length: int,
    batch_size: int,
    seed: int,
    shuffle: bool = True,
):
    # Accept an already-validated dataset so the caller can guarantee the Gold gate
    # runs before tokenizer/model loading. A path is still supported for convenience.
    gold_dataset = (
        gold_source
        if isinstance(gold_source, PoetryTrainingDataset)
        else PoetryTrainingDataset(gold_source, validate=True)
    )
    tokenized = TokenizedPoetryDataset(gold_dataset, tokenizer, max_length=max_length)

    import torch

    generator = torch.Generator()
    generator.manual_seed(seed)
    collator = CausalLMCollator(
        pad_token_id=resolve_pad_token_id(tokenizer),
        pad_to_multiple_of=8,
    )
    loader = DataLoader(
        tokenized,
        batch_size=batch_size,
        shuffle=shuffle,
        collate_fn=collator,
        generator=generator if shuffle else None,
    )
    return loader
