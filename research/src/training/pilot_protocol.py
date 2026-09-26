"""Data isolation and bounded engineering diagnostics, independent of model code."""
from collections import Counter
import hashlib
import json
import re
from pathlib import Path


def sha(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def normalized_text(text): return re.sub(r'[^\u3400-\u9fff]', '', text)


def check_isolation(train, evaluation, pending, flags, variants):
    train_ids = {r['id'] for r in train}; eval_ids = {r['id'] for r in evaluation}
    if len(train_ids) != len(train) or len(eval_ids) != len(evaluation): raise ValueError('Duplicate IDs')
    if train_ids & eval_ids: raise ValueError('Evaluation ID leakage')
    if {normalized_text(r['text']) for r in train} & {normalized_text(r['text']) for r in evaluation}:
        raise ValueError('Evaluation text leakage')
    prohibited = {r['id'] for r in pending} | {r['id'] for r in flags if any(f['severity'] == 'high' for f in r.get('flags', []))}
    if train_ids & prohibited: raise ValueError('Unresolved/high-risk records in training')
    for group in variants:
        ids = set(group['members'])
        if ids & train_ids and ids & eval_ids: raise ValueError('Evaluation variant leakage')
        if ids & train_ids and ids & prohibited: raise ValueError('Prohibited variant in training')
    return {'train_records': len(train), 'evaluation_records': len(evaluation), 'id_overlap': 0,
            'text_overlap': 0, 'variant_overlap': 0, 'prohibited_overlap': 0}


def select_sanity_subset(gold, silver, per_source=4):
    """Eight fixed short poems, distinct prompts within each supervision source."""
    from src.data.dataset import record_to_example
    chosen = []; prompts = set()
    for source, rows in [('gold', gold), ('partial-silver', silver)]:
        count = 0
        for row in sorted(rows, key=lambda r: (r['form'] != 'qijue7', r['id'])):
            prompt = record_to_example(row).prompt_text
            if prompt in prompts: continue
            chosen.append({'source': source, 'record': row}); prompts.add(prompt); count += 1
            if count == per_source: break
        if count != per_source: raise ValueError('Insufficient distinct-prompt examples')
    return chosen


def generation_metrics(output, target, form):
    lines = [normalized_text(x) for x in output.strip().splitlines() if x.strip()]
    a, b = normalized_text(output), normalized_text(target)
    previous = [0] * (len(b) + 1)
    for char in a:
        current = [0]
        for j, other in enumerate(b, 1): current.append(previous[j - 1] + 1 if char == other else max(previous[j], current[-1]))
        previous = current
    return {'nonempty': bool(a), 'form_compliance': len(lines) == (4 if form == 'qijue7' else 8) and all(len(x) == 7 for x in lines),
            'character_exact_match': a == b, 'character_lcs_recall': previous[-1] / max(1, len(b)),
            'repeated_line_fraction': (len(lines) - len(set(lines))) / max(1, len(lines))}


def sanity_pass(initial, final, generations):
    return (final['loss'] <= .4 * initial['loss'] and final['token_accuracy'] >= .90 and
            sum(x['metrics']['character_exact_match'] for x in generations) / len(generations) >= .5)


def load_pilot_dataset(config, root, training):
    from src.data.mixed_dataset import MixedPoetryDataset
    data = config['data']
    return MixedPoetryDataset(root / data['gold_path'], mode=data['mode'],
        partial_silver_path=root / data['partial_silver_path'] if data.get('partial_silver_path') else None,
        source_weights=data['source_weights'], control_dropout=data['control_dropout'],
        seed=config['training']['seed'], training=training, schema_path=root / 'configs/style_schema.json')
