# -*- coding: utf-8 -*-
"""CLI entry point for the future B0 Gold-dataset training run."""
from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict
from pathlib import Path

RESEARCH_ROOT = Path(__file__).resolve().parents[1]
if str(RESEARCH_ROOT) not in sys.path:
    sys.path.insert(0, str(RESEARCH_ROOT))

from src.data.dataset import PoetryTrainingDataset
from src.training.config import DEFAULT_BASELINE_CONFIG, load_baseline_config
from src.training.train_baseline import train_baseline


def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", type=Path, default=DEFAULT_BASELINE_CONFIG)
    ap.add_argument("--data", type=Path)
    ap.add_argument("--model-path", help="Optional local pretrained model path; defaults to config model_id")
    ap.add_argument("--device", default="auto")
    ap.add_argument("--dry-run", action="store_true")
    return ap.parse_args()


def main() -> int:
    args = parse_args()
    config = load_baseline_config(args.config)

    if args.dry_run:
        report = {
            "status": "ready_for_gold_data" if args.data is None else "config_and_gold_gate_ok",
            "config": asdict(config),
            "data": str(args.data) if args.data else None,
        }
        if args.data is not None:
            dataset = PoetryTrainingDataset(args.data, validate=True)
            report["gold_records"] = len(dataset)
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 0

    if args.data is None:
        raise SystemExit("--data is required for real training. Do not train before Gold JSONL exists.")

    result = train_baseline(
        config,
        args.data,
        model_name_or_path=args.model_path,
        device=args.device,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
