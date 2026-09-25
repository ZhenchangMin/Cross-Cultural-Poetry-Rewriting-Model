from copy import deepcopy
import json
from pathlib import Path
import pytest
from src.data.human_review import read_jsonl
from src.data.validate_dataset import load_schema
from src.data.semantic_annotator_v3 import (DIMS, make_folds, select_anchors, semantic_prompt,
    normalize, evidence_prompt, validate_evidence, evaluate, gate)

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = load_schema(ROOT / 'configs/style_schema.json')
ROWS = read_jsonl(ROOT / 'data/processed/style_annotation/gold_calibration_v1.jsonl')
POEM = '春風入夜明月照\n江水悠悠過小橋'


def predict(d, value):
    return normalize(json.dumps({'value': value, 'confidence': .8}), d, SCHEMA)


def fixture_record():
    values = dict(emotion=['serene'], diction='refined', expression='implicit', energy='gentle')
    semantic = {d: predict(d, v) for d, v in values.items()}
    evidence = validate_evidence(json.dumps({d: ['春風'] for d in DIMS}), POEM, semantic)
    return {'id': 'x', 'style': values}, {'id': 'x', 'semantic': semantic, 'evidence': evidence}


@pytest.fixture(scope='module')
def folds():
    return make_folds(ROWS)


def test_cv_exact_partition_reproducible_and_balanced(folds):
    assert folds == make_folds(list(reversed(ROWS)))
    seen = []
    lookup = {r['id']: r for r in ROWS}
    for fold in folds:
        train, evaluation = set(fold['calibration_ids']), set(fold['evaluation_ids'])
        assert len(train) == 18 and len(evaluation) == 6 and train.isdisjoint(evaluation)
        assert train | evaluation == set(lookup)
        assert 2 <= sum(lookup[x]['form'] == 'qijue7' for x in evaluation) <= 4
        seen.extend(evaluation)
    assert len(seen) == len(set(seen)) == 24


def test_anchors_are_dimension_specific_deterministic_and_never_eval(folds):
    for fold in folds:
        train = [r for r in ROWS if r['id'] in fold['calibration_ids']]
        for d in DIMS:
            anchors = select_anchors(train, d)
            assert anchors == select_anchors(list(reversed(train)), d)
            assert {a['id'] for a in anchors}.isdisjoint(fold['evaluation_ids'])
            if d != 'emotion':
                assert {a['label'] for a in anchors} == set(SCHEMA['style'][d]['values'])


def test_normalization_is_semantic_preserving():
    emotion = predict('emotion', 'serene')
    diction = predict('diction', ['refined'])
    assert emotion['normalized_prediction'] == ['serene']
    assert diction['normalized_prediction'] == 'refined'
    for p in (emotion, diction):
        assert not p['type_valid'] and p['type_repaired'] and p['repair_provenance']
        assert p['semantic_schema_success'] and not p['full_semantic_protocol_valid']
        assert not p['llm_repair_used']


@pytest.mark.parametrize('d,value', [('emotion', 'new_label'), ('emotion', ['serene', 'serene']),
    ('emotion', ['serene', 'joyful', 'lonely']), ('energy', 'heroic'), ('expression', ['direct', 'balanced'])])
def test_illegal_enum_never_guessed(d, value):
    p = predict(d, value)
    assert not p['label_valid'] and p['normalized_prediction'] is None


def test_evidence_failure_cannot_mutate_prediction():
    row, record = fixture_record()
    before = deepcopy(record['semantic'])
    checked = validate_evidence(json.dumps({d: ['照江'] for d in DIMS}), POEM, record['semantic'])
    assert not any(x['evidence_valid'] for x in checked['dimensions'].values())
    assert record['semantic'] == before
    record['evidence'] = checked
    report = evaluate([row], [record], SCHEMA)
    assert report['dimensions']['emotion']['f1'] == 1
    assert all(report['dimensions'][d]['accuracy'] == 1 for d in DIMS)
    assert report['record_level_protocol']['evidence_success_rate'] == 0


def test_no_gold_or_examples_in_evidence_and_only_target_dimension_in_shots():
    row, record = fixture_record()
    prompt = evidence_prompt(POEM, record['semantic'])
    payload = json.loads(prompt[prompt.index('{'):])
    assert set(payload) == {'poem', 'fixed_predictions'}
    assert payload['fixed_predictions'] == row['style']
    with pytest.raises(TypeError): evidence_prompt(POEM, record['semantic'], gold=row)
    examples = deepcopy(ROWS[:3])
    before = semantic_prompt(POEM, 'energy', examples, SCHEMA)
    for r in examples:
        r['style']['emotion'] = ['GOLD_SENTINEL']; r['metadata'] = {'title': 'TITLE_SENTINEL'}
    assert before == semantic_prompt(POEM, 'energy', examples, SCHEMA)
    assert 'GOLD_SENTINEL' not in before and 'TITLE_SENTINEL' not in before


def test_invalid_evidence_schema_and_missing_predictions_count():
    row, record = fixture_record()
    record['semantic']['energy'] = predict('energy', 'heroic')
    record['evidence'] = validate_evidence('{}', POEM, record['semantic'])
    report = evaluate([row], [record], SCHEMA)
    assert report['dimensions']['energy']['accuracy'] == 0
    assert report['dimensions']['energy']['confusion']['gentle-><invalid>'] == 1
    assert report['record_level_protocol']['semantic_schema_success_rate'] == 0
    with pytest.raises(ValueError): evaluate([row], [record, record], SCHEMA)


def test_confidence_does_not_erase_legal_labels():
    p = normalize('{"value":"gentle","confidence":true}', 'energy', SCHEMA)
    assert p['label_valid'] and not p['confidence_valid'] and not p['semantic_schema_success']


def test_gate_preserves_thresholds_and_separates_ready_dimensions():
    row, record = fixture_record()
    report = evaluate([row], [record], SCHEMA)
    rules = {'imagery': {'f1': .75}, 'density': {'accuracy': 1}}
    assert gate(report, rules)['silver_gate'] == 'pass'
    report['dimensions']['energy']['accuracy'] = .59
    result = gate(report, rules)
    assert result['silver_gate'] == 'fail' and not result['dimension_ready']['energy']
    assert result['dimension_ready']['diction'] and result['dimension_ready']['imagery']
    assert not result['silver_batch_started']


def test_json_failure_no_retry_or_invented_labels():
    result = normalize('not json', 'emotion', SCHEMA)
    assert not result['json_parse_success'] and not result['label_valid']
    assert not result['llm_repair_used']
