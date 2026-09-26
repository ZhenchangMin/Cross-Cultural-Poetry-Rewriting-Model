"""Prepare frozen proposals and leakage checks. No model imports or training."""
import json
from pathlib import Path
import sys
from copy import deepcopy

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.data.human_review import read_jsonl, write_jsonl
from src.training.pilot_protocol import sha, check_isolation, select_sanity_subset, load_pilot_dataset


def main():
    out = ROOT / 'outputs/b0_training_pilot_20260926'
    out.mkdir(parents=True, exist_ok=True)
    if (out / 'protocol.json').exists(): raise FileExistsError('Preserve frozen pilot preparation')
    load = lambda path: json.loads(path.read_text(encoding='utf-8'))
    save = lambda name, value: (out / name).write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    gold_path = 'data/processed/style_annotation/gold_calibration_v1.jsonl'
    silver_path = 'data/processed/partial_silver_v1/partial_silver_v1.jsonl'
    gold = read_jsonl(ROOT / gold_path); silver = read_jsonl(ROOT / silver_path)
    assert len(gold) == 24 and len(silver) == 825
    pending_path = ROOT / 'data/processed/style_annotation/adjudication_pending_v1.jsonl'
    flags_path = ROOT / 'data/processed/style_annotation/quality_flags_v1.jsonl'
    variants_path = ROOT / 'data/processed/style_annotation/variant_groups_v2.json'
    pending = read_jsonl(pending_path); flags = read_jsonl(flags_path); variants = load(variants_path)['groups']
    cv = load(ROOT / 'data/processed/semantic_annotator_v3/frozen_cv.json')
    cv_checks = []
    for fold in cv['folds']:
        train = [r for r in gold if r['id'] in fold['calibration_ids']]
        evaluation = [r for r in gold if r['id'] in fold['evaluation_ids']]
        cv_checks.append({'fold': fold['fold'], 'gold_only': check_isolation(train, evaluation, pending, flags, variants),
                          'gold_partial': check_isolation(train + silver, evaluation, pending, flags, variants)})
    fold = cv['folds'][0]
    diag_gold = [r for r in gold if r['id'] in fold['calibration_ids']]
    eval_gold = [r for r in gold if r['id'] in fold['evaluation_ids']]
    write_jsonl(diag_gold, out / 'diagnostic_gold18.jsonl')
    write_jsonl(eval_gold, out / 'reserved_development_eval6.jsonl')
    subset = select_sanity_subset(diag_gold, silver)
    save('sanity_subset.json', subset)
    base = load(ROOT / 'configs/baseline_qwen_lora.json')
    base['training'].update(batch_size=1, gradient_accumulation_steps=8, learning_rate=.0002, seed=20260926,
                            log_every_steps=1, save_every_steps=10, checkpoint_interval_unit='optimizer_steps')
    base['model'].update(precision='bf16', gradient_checkpointing=True, max_length=512)
    proposals = {}
    for key, mode, weights, epochs in [('A', 'gold-only', {'gold': 1.}, 3),
                                     ('B', 'gold+partial-silver', {'gold': .3, 'partial-silver': .7}, 1)]:
        config = deepcopy(base)
        config['experiment_name'] = 'b0_gold_only' if key == 'A' else 'b0_gold_partial_silver'
        config['training'].update(epochs=epochs, output_dir='outputs/' + config['experiment_name'])
        config['data'] = {'mode': mode, 'gold_path': gold_path, 'partial_silver_path': silver_path if key == 'B' else None,
                          'source_weights': weights, 'control_dropout': .1, 'records': 24 if key == 'A' else 849}
        config['evaluation'] = {'scope': 'all-source reconstruction pilot; no held-out claim for these full-data configs',
            'formal_training_authorized': False, 'development_cv_manifest': 'data/processed/semantic_annotator_v3/frozen_cv.json',
            'cv_requires_filtering_gold_to_fold_calibration_ids': True,
            'semantic_generated_style_scorer': 'disabled; v1/v2/v3 are not valid evaluation truth'}
        config['checkpoint_interval_unit'] = 'optimizer_steps'
        dataset = load_pilot_dataset(config, ROOT, training=True)
        save('proposed_b0_' + key + '.json', config)
        save('data_manifest_' + key + '.json', dataset.manifest())
        proposals[key] = 'proposed_b0_' + key + '.json'
    protected = {p.relative_to(ROOT).as_posix(): sha(p) for p in [ROOT / gold_path, ROOT / silver_path, pending_path, flags_path, variants_path, ROOT / 'configs/style_schema.json']}
    protocol = {'purpose': 'engineering smoke and tiny overfit sanity only; not an experiment result',
        'seed': 20260926, 'smoke_optimizer_steps': 10, 'smoke_gradient_accumulation': 8,
        'smoke_gold_path': 'outputs/b0_training_pilot_20260926/diagnostic_gold18.jsonl',
        'smoke_source_weights': {'gold': .3, 'partial-silver': .7}, 'smoke_control_dropout': .1,
        'overfit_records': 8, 'overfit_learning_rate': .0005, 'overfit_max_optimizer_steps': 160,
        'overfit_gradient_accumulation': 4, 'overfit_check_every_optimizer_steps': 20, 'overfit_control_dropout': 0.,
        'overfit_stop_criteria': {'loss_ratio_max': .4, 'teacher_forced_token_accuracy_min': .90, 'generation_character_exact_match_min': .5},
        'reserved_eval_ids': [r['id'] for r in eval_gold], 'reserved_eval_used_for_tuning_or_diagnostics': False,
        'cv_leakage_checks': cv_checks, 'all_source_configs_evaluation_scope': 'in-sample reconstruction only; use separately filtered CV training for held-out evaluation',
        'protected_inputs': protected, 'proposals': proposals,
        'subset_ids': [x['record']['id'] for x in subset], 'long_pilot_training_started': False}
    assert set(protocol['subset_ids']).isdisjoint(protocol['reserved_eval_ids'])
    save('protocol.json', protocol)
    print('Data protocol prepared: all 4 folds isolated; diagnostics reserve 6 Gold; sanity subset 4 Gold + 4 Silver')


if __name__ == '__main__': main()
