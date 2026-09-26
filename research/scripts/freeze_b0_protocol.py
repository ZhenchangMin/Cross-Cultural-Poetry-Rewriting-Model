"""Materialize the protocol once; does not import torch or load a model."""
from collections import Counter
from copy import deepcopy
from pathlib import Path
import json
import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.training.frozen_pilot import read_json, read_rows, write_json, select_split, label_counts, assert_matched, audit_config
from src.training.pilot_protocol import sha


def main():
    destination = ROOT / 'configs/b0_pilot_freeze.json'
    if destination.exists(): raise FileExistsError('Protocol already frozen; do not regenerate silently')
    prefix = 'data/processed/style_annotation/'
    gold = prefix + 'gold_calibration_v1.jsonl'; rows = read_rows(ROOT / gold)
    train, evaluation = select_split(rows)
    train_path = 'data/processed/b0_pilot_20260926/gold_train18.jsonl'
    eval_path = 'data/processed/b0_pilot_20260926/gold_eval6.jsonl'
    for name, values in ((train_path, train), (eval_path, evaluation)):
        path = ROOT / name; path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(''.join(json.dumps(x, ensure_ascii=False) + '\n' for x in values), encoding='utf-8')
    split = {'version': 'b0_pilot_split_v1', 'seed': 20260926, 'scope': 'development holdout; all Gold previously used for annotation development and some for engineering diagnostics; not historically unseen test',
        'selection': 'exhaustive 3 qijue7 + 3 qilv7; minimize sum((4*eval_label_count-total_label_count)^2/total_label_count); preserve every observed class in training; seeded order resolves ties',
        'gold_source': gold, 'train_path': train_path, 'eval_path': eval_path,
        'train_ids': [r['id'] for r in train], 'eval_ids': [r['id'] for r in evaluation],
        'train_distribution': dict(label_counts(train)), 'eval_distribution': dict(label_counts(evaluation)),
        'pending_path': prefix + 'adjudication_pending_v1.jsonl', 'flags_path': prefix + 'quality_flags_v1.jsonl',
        'variants_path': prefix + 'variant_groups_v2.json', 'fresh_base_and_fresh_lora_required': True}
    write_json(ROOT / 'configs/b0_pilot_split.json', split)
    a = read_json(ROOT / 'configs/b0_gold_only.json')
    a = {k: a[k] for k in ('model', 'lora', 'training', 'generation', 'data')}
    a['experiment_name'] = 'b0_pilot_gold_only'; a['output_dir'] = 'outputs/b0_pilot_gold_only'
    a['split_path'] = 'configs/b0_pilot_split.json'
    a['model'].update({'local_path': 'models/_cache/Qwen2.5-1.5B-Instruct',
        'weights_sha256': 'dd924a11b4c220f385b51ffa522daea7c9f3d850e31b162bb5661df483c6d3ee', 'attention_implementation': 'eager'})
    a['training'].pop('epochs'); a['training'].pop('output_dir')
    a['training'].update({'max_optimizer_steps': 100, 'eval_every_steps': 10, 'scheduler': 'constant', 'effective_batch_size': 8})
    a['generation'] = {'max_new_tokens': 128, 'do_sample': False, 'num_beams': 1}
    a['data'].update({'gold_path': train_path, 'records': 18})
    a['evaluation'] = {'gold_path': eval_path, 'records': 6, 'control_dropout': 0., 'sampling': 'all records once',
        'cadence': 'step 0 and every 10 optimizer updates including final', 'checkpoint_selection': 'fixed final step 100; no best-checkpoint selection',
        'teacher_forced': ['completion_token_weighted_loss', 'completion_token_accuracy'],
        'generation': ['line_and_character_form_compliance', 'imagery_rule_micro_precision_recall_F1', 'density_rule_accuracy'],
        'semantic_style_scoring': 'disabled', 'rule_version': 'lexicon_heuristic_v1_1',
        'invalid_form_policy': 'imagery empty / density null; keep all six in metric accounting',
        'interpretation': 'development holdout; rule metrics are controllability proxies, not independent quality truth'}
    b = deepcopy(a); b['experiment_name'] = 'b0_pilot_gold_partial_silver'; b['output_dir'] = 'outputs/b0_pilot_gold_partial_silver'
    b['data'].update({'mode': 'gold+partial-silver', 'partial_silver_path': 'data/processed/partial_silver_v1/partial_silver_v1.jsonl',
                      'source_weights': {'gold': .3, 'partial-silver': .7}, 'records': 843})
    assert_matched(a, b)
    configs = ['configs/b0_pilot_gold_only.json', 'configs/b0_pilot_gold_partial_silver.json']
    for name, config in zip(configs, (a, b)): write_json(ROOT / name, config)
    files = configs + ['configs/b0_pilot_split.json', gold, train_path, eval_path, b['data']['partial_silver_path'],
        split['pending_path'], split['flags_path'], split['variants_path'], 'configs/style_schema.json', 'configs/imagery_lexicon_v1.json',
        'scripts/run_frozen_b0_pilot.py', 'scripts/freeze_b0_protocol.py', 'src/training/frozen_pilot.py', 'src/training/pilot_evaluation.py',
        'src/training/pilot_protocol.py', 'src/data/dataset.py', 'src/data/mixed_dataset.py', 'src/data/tokenization.py',
        'src/data/validate_dataset.py', 'src/data/preannotate_style.py', 'src/data/partial_silver.py']
    write_json(destination, {'protocol_version': 'b0_pilot_v1', 'configs': configs, 'sha256': {p: sha(ROOT / p) for p in files},
        'execution_status': 'prepared_only_not_started', 'budget_reason': '100 updates x 8 examples; smoke measured 3.20 s/update, approximately 5.3 min training-only plus evaluation/save/load overhead per arm',
        'matching_scope': 'same optimizer updates/effective batch/hyperparameters; not exact token FLOPs or wall-clock due to sequence lengths',
        'dropout_clock': 'optimizer_step-1, per-record per-dimension hash, form retained; evaluation always disabled'})
    _, _, audit = audit_config(ROOT / configs[0], ROOT)
    write_json(ROOT / 'outputs/b0_pilot_protocol_20260926/audit.json', audit)
    print(json.dumps({'train_forms': dict(Counter(r['form'] for r in train)), 'eval_forms': dict(Counter(r['form'] for r in evaluation)), 'eval_ids': split['eval_ids'], 'audit': audit}, ensure_ascii=False))


if __name__ == '__main__': main()
