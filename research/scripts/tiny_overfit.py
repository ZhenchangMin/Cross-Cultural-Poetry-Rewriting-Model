# -*- coding: utf-8 -*-
"""Run the CPU tiny-Qwen2 + LoRA overfit checkpoint from the command line."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

RESEARCH_ROOT = Path(__file__).resolve().parents[1]
if str(RESEARCH_ROOT) not in sys.path:
    sys.path.insert(0, str(RESEARCH_ROOT))

from src.training.tiny_overfit import TinyOverfitConfig, run_tiny_overfit


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--steps", type=int, default=600)
    parser.add_argument("--lr", type=float, default=1e-2)
    parser.add_argument("--device", default="cpu")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    result = run_tiny_overfit(
        TinyOverfitConfig(
            steps=args.steps,
            learning_rate=args.lr,
            device=args.device,
        )
    )
    print(f"trainable_parameters={result.trainable_parameters}")
    print(f"total_parameters={result.total_parameters}")
    print(f"trainable_ratio={result.trainable_parameters / result.total_parameters:.4%}")
    print(f"initial_loss={result.initial_loss:.6f}")
    print(f"final_loss={result.final_loss:.6f}")
    print(f"loss_ratio={result.loss_ratio:.6f}")
    print(f"initial_token_accuracy={result.initial_token_accuracy:.4f}")
    print(f"final_token_accuracy={result.final_token_accuracy:.4f}")

    if not result.passed:
        raise SystemExit(
            "Tiny overfit did not meet the memorization criterion: "
            "final token accuracy must be >= 0.95 and loss_ratio <= 0.90."
        )


if __name__ == "__main__":
    main()
