# -*- coding: utf-8 -*-
"""CLI for controlled generation from a trained B0 LoRA adapter."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

RESEARCH_ROOT = Path(__file__).resolve().parents[1]
if str(RESEARCH_ROOT) not in sys.path:
    sys.path.insert(0, str(RESEARCH_ROOT))

from src.training.config import DEFAULT_BASELINE_CONFIG, load_baseline_config
from src.training.generate_baseline import generate_from_control


def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", type=Path, default=DEFAULT_BASELINE_CONFIG)
    ap.add_argument("--adapter", type=Path, required=True)
    ap.add_argument("--control", type=Path, required=True, help="JSON with form/style controls")
    ap.add_argument("--model-path", help="Optional local base-model path")
    ap.add_argument("--device", default="auto")
    return ap.parse_args()


def main() -> int:
    args = parse_args()
    config = load_baseline_config(args.config)
    with args.control.open("r", encoding="utf-8") as f:
        control = json.load(f)
    poem = generate_from_control(
        config,
        control,
        args.adapter,
        model_name_or_path=args.model_path,
        device=args.device,
    )
    print(poem)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
