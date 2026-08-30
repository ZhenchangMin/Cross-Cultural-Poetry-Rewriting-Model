# -*- coding: utf-8 -*-
from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping, Sequence

import pytest

from src.data.dataset import TrainingExample
from src.data.tokenization import (
    IGNORE_INDEX,
    TokenizedExample,
    build_chat_token_ids,
    collate_tokenized_examples,
    encode_training_example,
    resolve_pad_token_id,
)


class FakeChatTokenizer:
    """Deterministic character tokenizer with a Qwen-like chat prefix relation."""

    pad_token_id = None
    eos_token_id = 99

    def _encode_text(self, text: str) -> list[int]:
        # Stable, non-zero IDs; exact values do not matter for masking tests.
        return [10 + (ord(ch) % 70) for ch in text]

    def apply_chat_template(
        self,
        conversation: Sequence[Mapping[str, str]],
        *,
        tokenize: bool,
        add_generation_prompt: bool,
    ) -> list[int]:
        assert tokenize is True
        ids = [1]  # begin-chat marker
        for item in conversation:
            if item["role"] == "user":
                ids += [2] + self._encode_text(item["content"]) + [3]
            elif item["role"] == "assistant":
                ids += [4] + self._encode_text(item["content"]) + [5]
            else:
                raise AssertionError(item["role"])
        if add_generation_prompt:
            ids += [4]
        return ids


class BrokenPrefixTokenizer(FakeChatTokenizer):
    def apply_chat_template(self, conversation, *, tokenize, add_generation_prompt):
        ids = super().apply_chat_template(
            conversation,
            tokenize=tokenize,
            add_generation_prompt=add_generation_prompt,
        )
        if not add_generation_prompt:
            ids[0] = 88
        return ids


def make_example(prompt: str = "控制条件", target: str = "春风入夜") -> TrainingExample:
    return TrainingExample(
        id="sample-1",
        form="qijue7",
        style={},
        prompt_text=prompt,
        target_text=target,
    )


def test_chat_template_prompt_is_exact_prefix():
    tok = FakeChatTokenizer()
    prompt_ids, full_ids = build_chat_token_ids(tok, make_example())
    assert full_ids[: len(prompt_ids)] == prompt_ids
    assert len(full_ids) > len(prompt_ids)


def test_prefix_mismatch_is_rejected():
    with pytest.raises(ValueError, match="prefix mismatch"):
        build_chat_token_ids(BrokenPrefixTokenizer(), make_example())


def test_prompt_labels_are_masked_and_completion_is_supervised():
    encoded = encode_training_example(FakeChatTokenizer(), make_example())

    assert len(encoded.input_ids) == len(encoded.attention_mask) == len(encoded.labels)
    assert encoded.labels[: encoded.prompt_tokens] == [IGNORE_INDEX] * encoded.prompt_tokens
    assert encoded.labels[encoded.prompt_tokens :] == encoded.input_ids[encoded.prompt_tokens :]
    assert all(x == 1 for x in encoded.attention_mask)
    assert encoded.supervised_tokens > 0
    assert encoded.truncated is False


def test_truncation_drops_prompt_before_short_completion():
    tok = FakeChatTokenizer()
    ex = make_example(prompt="甲" * 100, target="乙丙")
    prompt_ids, full_ids = build_chat_token_ids(tok, ex)
    completion_len = len(full_ids) - len(prompt_ids)

    encoded = encode_training_example(tok, ex, max_length=completion_len + 5)

    assert encoded.truncated is True
    assert encoded.supervised_tokens == completion_len
    assert encoded.prompt_tokens == 5
    assert len(encoded.input_ids) == completion_len + 5


def test_dynamic_collator_masks_padding_labels():
    a = TokenizedExample(
        id="a",
        input_ids=[1, 2, 3],
        attention_mask=[1, 1, 1],
        labels=[IGNORE_INDEX, 2, 3],
        prompt_tokens=1,
        supervised_tokens=2,
        truncated=False,
    )
    b = TokenizedExample(
        id="b",
        input_ids=[4, 5],
        attention_mask=[1, 1],
        labels=[IGNORE_INDEX, 5],
        prompt_tokens=1,
        supervised_tokens=1,
        truncated=False,
    )

    batch = collate_tokenized_examples([a, b], pad_token_id=99, pad_to_multiple_of=4)

    assert batch["input_ids"] == [[1, 2, 3, 99], [4, 5, 99, 99]]
    assert batch["attention_mask"] == [[1, 1, 1, 0], [1, 1, 0, 0]]
    assert batch["labels"] == [
        [IGNORE_INDEX, 2, 3, IGNORE_INDEX],
        [IGNORE_INDEX, 5, IGNORE_INDEX, IGNORE_INDEX],
    ]


def test_pad_token_falls_back_to_eos():
    assert resolve_pad_token_id(FakeChatTokenizer()) == 99
