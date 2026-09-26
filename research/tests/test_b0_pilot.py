from copy import deepcopy
import json
from pathlib import Path
import pytest
from src.training.pilot_protocol import check_isolation, select_sanity_subset, generation_metrics, sanity_pass, load_pilot_dataset
from src.training.config import load_baseline_config
from src.data.human_review import read_jsonl

ROOT = Path(__file__).resolve().parents[1]
GOLD = read_jsonl(ROOT / 'data/processed/style_annotation/gold_calibration_v1.jsonl')
SILVER = read_jsonl(ROOT / 'data/processed/partial_silver_v1/partial_silver_v1.jsonl')


def test_leakage_checks_fail_closed():
    train = [GOLD[0]]; evaluation = [GOLD[1]]
    assert check_isolation(train, evaluation, [], [], [])['id_overlap'] == 0
    with pytest.raises(ValueError, match='ID leakage'): check_isolation(train, train, [], [], [])
    clone = deepcopy(GOLD[0]); clone['id'] = 'same-poem'
    with pytest.raises(ValueError, match='text leakage'): check_isolation(train, [clone], [], [], [])
    with pytest.raises(ValueError, match='Unresolved'): check_isolation(train, [], train, [], [])
    flags = [{'id': GOLD[0]['id'], 'flags': [{'severity': 'high'}]}]
    with pytest.raises(ValueError, match='high-risk'): check_isolation(train, [], [], flags, [])
    groups = [{'members': [GOLD[0]['id'], GOLD[1]['id']]}]
    with pytest.raises(ValueError, match='variant'): check_isolation(train, evaluation, [], [], groups)


def test_sanity_subset_is_fixed_balanced_and_unique_prompt():
    subset = select_sanity_subset(GOLD, SILVER)
    assert subset == select_sanity_subset(list(reversed(GOLD)), list(reversed(SILVER)))
    assert len(subset) == 8 and sum(x['source'] == 'gold' for x in subset) == 4
    assert len({x['record']['id'] for x in subset}) == 8


def test_generation_metric_is_not_style_truth():
    target = GOLD[0]['text']
    m = generation_metrics(target, target, GOLD[0]['form'])
    assert m['character_exact_match'] and m['form_compliance'] and m['character_lcs_recall'] == 1
    assert not generation_metrics('', target, GOLD[0]['form'])['nonempty']
    assert not generation_metrics('a bad poem', target, GOLD[0]['form'])['form_compliance']
    assert 'emotion' not in m and 'energy' not in m


def test_overfit_gate_requires_teacher_forcing_and_generation():
    initial = {'loss': 4}; final = {'loss': .5, 'token_accuracy': .95}
    generated = [{'metrics': {'character_exact_match': True}}] * 4 + [{'metrics': {'character_exact_match': False}}] * 4
    assert sanity_pass(initial, final, generated)
    assert not sanity_pass(initial, {'loss': 3., 'token_accuracy': .99}, generated)
    assert not sanity_pass(initial, final, [{'metrics': {'character_exact_match': False}}] * 8)


def test_pilot_sampling_config_is_respected_and_eval_dropout_disabled():
    raw = {'training': {'seed': 13}, 'data': {'mode': 'gold+partial-silver',
        'gold_path': 'data/processed/style_annotation/gold_calibration_v1.jsonl',
        'partial_silver_path': 'data/processed/partial_silver_v1/partial_silver_v1.jsonl',
        'source_weights': {'gold': .3, 'partial-silver': .7}, 'control_dropout': 1.}}
    train = load_pilot_dataset(raw, ROOT, training=True)
    assert sum(train.sampling_weights[:24]) == pytest.approx(.3)
    assert sum(train.sampling_weights[24:]) == pytest.approx(.7)
    assert train[0].active_controls == ('form',)
    assert len(load_pilot_dataset(raw, ROOT, training=False)[0].active_controls) == 7


def test_checkpoint_interval_unit_validated(tmp_path):
    raw = json.loads((ROOT / 'configs/baseline_qwen_lora.json').read_text())
    raw['training']['checkpoint_interval_unit'] = 'optimizer_steps'
    p = tmp_path / 'config.json'; p.write_text(json.dumps(raw))
    assert load_baseline_config(p).training.checkpoint_interval_unit == 'optimizer_steps'
    raw['training']['checkpoint_interval_unit'] = 'ambiguous'
    p.write_text(json.dumps(raw))
    with pytest.raises(ValueError, match='checkpoint'): load_baseline_config(p)
