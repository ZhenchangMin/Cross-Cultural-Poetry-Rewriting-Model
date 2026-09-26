"""Data-only interface for all three modes; never loads a tokenizer or model."""
import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.data.mixed_dataset import MODES, MixedPoetryDataset


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--gold', type=Path, required=True)
    p.add_argument('--partial-silver', type=Path)
    p.add_argument('--form-only', type=Path)
    p.add_argument('--mode', choices=MODES, default='gold-only')
    p.add_argument('--control-dropout', type=float, default=0.)
    p.add_argument('--seed', type=int, default=20260926)
    p.add_argument('--training-view', action='store_true')
    p.add_argument('--source-weights', default='{}', help='JSON positive source sampling masses')
    args = p.parse_args()
    dataset = MixedPoetryDataset(args.gold, mode=args.mode, partial_silver_path=args.partial_silver,
        form_only_path=args.form_only, source_weights=json.loads(args.source_weights),
        control_dropout=args.control_dropout, training=args.training_view, seed=args.seed,
        schema_path=ROOT / 'configs/style_schema.json')
    manifest = dataset.manifest()
    manifest.pop('examples')
    manifest['first_prompt'] = dataset[0].prompt_text
    print(json.dumps(manifest, ensure_ascii=False, indent=2))


if __name__ == '__main__': main()
