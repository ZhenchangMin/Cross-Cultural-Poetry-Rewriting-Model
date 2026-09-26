"""Frozen development holdout and compute-matched B0 protocol (no model imports)."""
from collections import Counter
from itertools import combinations
from fractions import Fraction
import json
import random
from pathlib import Path
from src.training.pilot_protocol import sha, check_isolation, load_pilot_dataset


def read_json(path): return json.loads(Path(path).read_text(encoding='utf-8'))
def read_rows(path): return [json.loads(x) for x in Path(path).read_text(encoding='utf-8').splitlines() if x.strip()]
def write_json(path, value):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def label_counts(rows):
    counts = Counter()
    for row in rows:
        counts['form:' + row['form']] += 1
        for dim, value in row['style'].items():
            for label in value if isinstance(value, list) else [value]: counts[dim + ':' + label] += 1
    return counts


def select_split(rows, seed=20260926):
    """Exhaustive 3+3 evaluation candidates; inverse-frequency label imbalance.

    Every observed class must remain in train. Seed resolves equal-score ties only.
    No model predictions or previous losses are used.
    """
    if len(rows) != 24 or len({r['id'] for r in rows}) != 24: raise ValueError('Expected 24 unique Gold')
    ordered = sorted(rows, key=lambda r: r['id']); random.Random(seed).shuffle(ordered)
    groups = [[r for r in ordered if r['form'] == form] for form in ('qijue7', 'qilv7')]
    total = label_counts(rows); best = None; chosen = None
    for a in combinations(groups[0], 3):
        for b in combinations(groups[1], 3):
            candidate = a + b; counts = label_counts(candidate)
            if any(counts[k] == n for k, n in total.items()): continue
            score = sum(Fraction((4 * counts[k] - n) ** 2, n) for k, n in total.items())
            if best is None or score < best: best, chosen = score, candidate
    if chosen is None: raise ValueError('No balanced split preserves training classes')
    ids = {r['id'] for r in chosen}
    return sorted([r for r in rows if r['id'] not in ids], key=lambda r: r['id']), sorted(chosen, key=lambda r: r['id'])


def assert_matched(a, b):
    for key in ('model', 'lora', 'training', 'generation', 'evaluation', 'split_path'):
        if a[key] != b[key]: raise ValueError('A/B mismatch: ' + key)
    t = a['training']
    if 'epochs' in t or t['max_optimizer_steps'] != 100 or t['batch_size'] != 1 or t['gradient_accumulation_steps'] != 8:
        raise ValueError('Frozen step budget changed')
    if a['data']['control_dropout'] != b['data']['control_dropout']: raise ValueError('Dropout mismatch')
    if a['data']['gold_path'] != b['data']['gold_path']: raise ValueError('Train split mismatch')
    if a['data']['mode'] != 'gold-only' or b['data']['mode'] != 'gold+partial-silver': raise ValueError('Source modes changed')
    if a['data']['source_weights'] != {'gold': 1.0} or b['data']['source_weights'] != {'gold': .3, 'partial-silver': .7}:
        raise ValueError('Frozen source masses changed')


def audit_config(config_path, root):
    """Fail closed BEFORE tokenizer/model loading; validate both comparison arms."""
    root = Path(root); config_path = Path(config_path)
    freeze = read_json(root / 'configs/b0_pilot_freeze.json')
    for name, digest in freeze['sha256'].items():
        if sha(root / name) != digest: raise ValueError('Frozen input/code changed: ' + name)
    allowed = [root / p for p in freeze['configs']]
    if config_path.resolve() not in [p.resolve() for p in allowed]: raise ValueError('Not a frozen pilot config')
    a, b = [read_json(p) for p in allowed]; assert_matched(a, b)
    split = read_json(root / a['split_path']); train = read_rows(root / split['train_path']); evaluation = read_rows(root / split['eval_path'])
    original = read_rows(root / split['gold_source'])
    if train + evaluation == [] or len(train) != 18 or len(evaluation) != 6: raise ValueError('Invalid split size')
    if {r['id']: r for r in train + evaluation} != {r['id']: r for r in original}: raise ValueError('Gold partition/content changed')
    if [r['id'] for r in train] != split['train_ids'] or [r['id'] for r in evaluation] != split['eval_ids']: raise ValueError('Split IDs changed')
    pending = read_rows(root / split['pending_path']); flags = read_rows(root / split['flags_path'])
    variants = read_json(root / split['variants_path'])['groups']
    # Close overlapping variant groups transitively before testing boundaries.
    groups = []
    for group in variants:
        members = set(group['members'])
        touching = [g for g in groups if g & members]
        for g in touching: members |= g; groups.remove(g)
        groups.append(members)
    variants = [{'members': sorted(g)} for g in groups]
    silver = read_rows(root / b['data']['partial_silver_path'])
    audit = check_isolation(train + silver, evaluation, pending, flags, variants)
    # Stage validation and provenance requirements run for BOTH arms.
    for config in (a, b): load_pilot_dataset(config, root, training=False)
    from src.data.dataset import PoetryTrainingDataset
    PoetryTrainingDataset(root / split['eval_path'], schema_path=root / 'configs/style_schema.json', training=False)
    return read_json(config_path), split, audit


def sampling_plan(weights, steps, batch_size, accumulation, seed):
    """Independent CPU RNG, replacement sampling, no epoch tails or resets."""
    if not weights or min(weights) <= 0 or min(steps, batch_size, accumulation) <= 0: raise ValueError('Invalid sampling budget')
    rng = random.Random(seed); per_step = batch_size * accumulation
    return [rng.choices(range(len(weights)), weights=weights, k=per_step) for _ in range(steps)]
