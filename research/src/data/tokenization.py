# -*- coding: utf-8 -*-
"""Supervised tokenization for the B0 controllable-poetry baseline.

For an instruction-tuned causal language model, one training sample is represented as:

    user prompt -> assistant target poem

The model receives the whole token sequence, but the prompt portion is masked with
``IGNORE_INDEX = -100`` in ``labels``. Hugging Face causal-LM heads ignore those label
positions when computing cross-entropy loss, so the model is supervised only on the
assistant/poem completion.

This module intentionally stays independent from torch. It returns Python lists so the
alignment logic is easy to unit-test. A later training collator can convert batches to
PyTorch tensors.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Mapping, MutableSequence, Protocol, Sequence

from .dataset import TrainingExample


IGNORE_INDEX = -100
DEFAULT_MODEL_ID = "Qwen/Qwen2.5-1.5B-Instruct"


class ChatTokenizer(Protocol):
    """Minimal tokenizer surface required by this module."""

    pad_token_id: int | None
    eos_token_id: int | None

    def apply_chat_template(
        self,
        conversation: Sequence[Mapping[str, str]],
        *,
        tokenize: bool,
        add_generation_prompt: bool,
    ) -> Any: ...


@dataclass(frozen=True)
class TokenizedExample:
    id: str
    input_ids: List[int]
    attention_mask: List[int]
    labels: List[int]
    prompt_tokens: int
    supervised_tokens: int
    truncated: bool

    def __post_init__(self) -> None:
        n = len(self.input_ids)
        if len(self.attention_mask) != n or len(self.labels) != n:
            raise ValueError("input_ids, attention_mask and labels must have equal length")
        if self.prompt_tokens + self.supervised_tokens != n:
            raise ValueError("prompt_tokens + supervised_tokens must equal sequence length")


def _as_int_list(value: Any) -> List[int]:
    """Normalize tokenizer output to a flat list of ints."""
    if isinstance(value, list):
        if value and isinstance(value[0], list):
            if len(value) != 1:
                raise ValueError("Expected a single tokenized sequence")
            value = value[0]
        return [int(x) for x in value]

    # Support tensor-like output without importing torch/numpy here.
    if hasattr(value, "tolist"):
        return _as_int_list(value.tolist())

    raise TypeError(f"Unsupported token sequence type: {type(value).__name__}")


def build_chat_token_ids(
    tokenizer: ChatTokenizer,
    example: TrainingExample,
) -> tuple[List[int], List[int]]:
    """Return ``(prompt_ids, full_ids)`` using the tokenizer's native chat template.

    ``prompt_ids`` ends at the assistant-generation boundary. ``full_ids`` contains the
    same prefix followed by the gold target poem and the template's assistant terminator.
    Exact prefix equality is checked because label masking would be unsafe otherwise.
    """
    user_only = [{"role": "user", "content": example.prompt_text}]
    full_conversation = [
        {"role": "user", "content": example.prompt_text},
        {"role": "assistant", "content": example.target_text},
    ]

    prompt_ids = _as_int_list(
        tokenizer.apply_chat_template(
            user_only,
            tokenize=True,
            add_generation_prompt=True,
        )
    )
    full_ids = _as_int_list(
        tokenizer.apply_chat_template(
            full_conversation,
            tokenize=True,
            add_generation_prompt=False,
        )
    )

    if not prompt_ids:
        raise ValueError("Tokenizer produced an empty prompt sequence")
    if len(full_ids) <= len(prompt_ids):
        raise ValueError("Full conversation must contain supervised assistant tokens")
    if full_ids[: len(prompt_ids)] != prompt_ids:
        raise ValueError(
            "Chat-template prefix mismatch: cannot safely determine which tokens belong to the prompt"
        )
    return prompt_ids, full_ids


def _truncate_preserving_supervision(
    prompt_ids: List[int],
    completion_ids: List[int],
    max_length: int,
) -> tuple[List[int], List[int], bool]:
    """Fit one sample into ``max_length`` while prioritizing target-poem supervision.

    Policy:
    1. keep all completion tokens whenever possible;
    2. if space is tight, drop tokens from the *left* of the prompt first, preserving the
       control summary and final output instruction near the prompt end;
    3. only if the completion itself is too long, truncate its tail.

    In the current qijue/qilv task, target poems are very short, so step 3 should be rare
    and is mainly a defensive safeguard.
    """
    if max_length <= 0:
        raise ValueError("max_length must be positive")

    total = len(prompt_ids) + len(completion_ids)
    if total <= max_length:
        return list(prompt_ids), list(completion_ids), False

    if len(completion_ids) >= max_length:
        # No room for prompt. This is an abnormal case, but keeping the first max_length
        # completion tokens still yields a valid causal-LM sample.
        return [], list(completion_ids[:max_length]), True

    prompt_budget = max_length - len(completion_ids)
    kept_prompt = prompt_ids[-prompt_budget:] if prompt_budget else []
    return list(kept_prompt), list(completion_ids), True


def encode_training_example(
    tokenizer: ChatTokenizer,
    example: TrainingExample,
    *,
    max_length: int = 512,
) -> TokenizedExample:
    """Convert a Gold ``TrainingExample`` into causal-LM inputs and masked labels."""
    prompt_ids, full_ids = build_chat_token_ids(tokenizer, example)
    completion_ids = full_ids[len(prompt_ids) :]

    prompt_ids, completion_ids, truncated = _truncate_preserving_supervision(
        prompt_ids,
        completion_ids,
        max_length,
    )

    input_ids = prompt_ids + completion_ids
    labels = [IGNORE_INDEX] * len(prompt_ids) + list(completion_ids)
    attention_mask = [1] * len(input_ids)

    if not completion_ids:
        raise ValueError("No supervised completion tokens remain after tokenization")
    if all(x == IGNORE_INDEX for x in labels):
        raise ValueError("Sample contains no supervised labels")

    return TokenizedExample(
        id=example.id,
        input_ids=input_ids,
        attention_mask=attention_mask,
        labels=labels,
        prompt_tokens=len(prompt_ids),
        supervised_tokens=len(completion_ids),
        truncated=truncated,
    )


def resolve_pad_token_id(tokenizer: ChatTokenizer) -> int:
    """Use an explicit pad id, or fall back to EOS as commonly done for decoder LMs."""
    if tokenizer.pad_token_id is not None:
        return int(tokenizer.pad_token_id)
    if tokenizer.eos_token_id is not None:
        return int(tokenizer.eos_token_id)
    raise ValueError("Tokenizer must define pad_token_id or eos_token_id")


def collate_tokenized_examples(
    examples: Sequence[TokenizedExample],
    *,
    pad_token_id: int,
    pad_to_multiple_of: int | None = None,
) -> Dict[str, List[List[int]]]:
    """Dynamically right-pad tokenized samples for one batch.

    Padding labels are always ``-100`` so padding does not contribute to loss.
    The function returns Python lists; the training layer will later convert them to
    tensors. Dynamic padding avoids padding every dataset item to a global fixed length.
    """
    if not examples:
        raise ValueError("Cannot collate an empty batch")
    if pad_to_multiple_of is not None and pad_to_multiple_of <= 0:
        raise ValueError("pad_to_multiple_of must be positive")

    target_len = max(len(x.input_ids) for x in examples)
    if pad_to_multiple_of:
        remainder = target_len % pad_to_multiple_of
        if remainder:
            target_len += pad_to_multiple_of - remainder

    batch_input_ids: List[List[int]] = []
    batch_attention: List[List[int]] = []
    batch_labels: List[List[int]] = []

    for ex in examples:
        pad_len = target_len - len(ex.input_ids)
        batch_input_ids.append(ex.input_ids + [pad_token_id] * pad_len)
        batch_attention.append(ex.attention_mask + [0] * pad_len)
        batch_labels.append(ex.labels + [IGNORE_INDEX] * pad_len)

    return {
        "input_ids": batch_input_ids,
        "attention_mask": batch_attention,
        "labels": batch_labels,
    }
