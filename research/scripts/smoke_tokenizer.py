# -*- coding: utf-8 -*-
"""Smoke-test the real Qwen tokenizer against B0 supervised masking."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

RESEARCH_ROOT = Path(__file__).resolve().parents[1]
if str(RESEARCH_ROOT) not in sys.path:
    sys.path.insert(0, str(RESEARCH_ROOT))

from transformers import AutoTokenizer

from src.data.dataset import TrainingExample
from src.data.tokenization import DEFAULT_MODEL_ID, encode_training_example, resolve_pad_token_id


DEFAULT_LOCAL = Path("models/_cache/Qwen2.5-1.5B-Instruct-tokenizer")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--tokenizer", default=str(DEFAULT_LOCAL))
    parser.add_argument("--online", action="store_true", help="Use DEFAULT_MODEL_ID from the Hub")
    args = parser.parse_args()

    source = DEFAULT_MODEL_ID if args.online else args.tokenizer
    tokenizer = AutoTokenizer.from_pretrained(source, local_files_only=not args.online)

    example = TrainingExample(
        id="smoke-qijue",
        form="qijue7",
        style={},
        prompt_text="诗体：七言绝句\n情感：感伤惆怅\n意象：天象、行旅\n请只输出诗歌正文。",
        target_text="孤舟夜泊月如霜\n客路迢迢梦故乡\n一雁穿云天欲晓\n寒江无语送秋光",
    )
    encoded = encode_training_example(tokenizer, example, max_length=256)

    prompt_mask_ok = all(x == -100 for x in encoded.labels[: encoded.prompt_tokens])
    completion_labels_ok = (
        encoded.labels[encoded.prompt_tokens :] == encoded.input_ids[encoded.prompt_tokens :]
    )

    print(f"source={source}")
    print(f"tokenizer={type(tokenizer).__name__}")
    print(
        f"pad_token_id={tokenizer.pad_token_id} eos_token_id={tokenizer.eos_token_id} "
        f"resolved_pad={resolve_pad_token_id(tokenizer)}"
    )
    print(
        f"sequence_length={len(encoded.input_ids)} prompt_tokens={encoded.prompt_tokens} "
        f"supervised_tokens={encoded.supervised_tokens} truncated={encoded.truncated}"
    )
    print(f"prompt_mask_ok={prompt_mask_ok}")
    print(f"completion_labels_ok={completion_labels_ok}")
    print(
        "completion_decode="
        + repr(
            tokenizer.decode(
                encoded.input_ids[encoded.prompt_tokens :],
                skip_special_tokens=False,
            )
        )
    )

    if not prompt_mask_ok or not completion_labels_ok:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
