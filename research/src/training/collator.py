# -*- coding: utf-8 -*-
"""PyTorch batch collation for causal-LM poetry training."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Sequence

import torch

from src.data.tokenization import TokenizedExample, collate_tokenized_examples


@dataclass(frozen=True)
class CausalLMCollator:
    """Convert tokenized poetry examples into right-padded ``torch.long`` tensors.

    The lower data layer deliberately returns plain Python lists so masking and padding
    remain easy to unit-test. This collator is the boundary where model-facing tensors
    are created.
    """

    pad_token_id: int
    pad_to_multiple_of: int | None = None

    def __call__(self, examples: Sequence[TokenizedExample]) -> Dict[str, torch.Tensor]:
        batch = collate_tokenized_examples(
            examples,
            pad_token_id=self.pad_token_id,
            pad_to_multiple_of=self.pad_to_multiple_of,
        )
        return {
            key: torch.tensor(value, dtype=torch.long)
            for key, value in batch.items()
        }
