from copy import deepcopy
import json
from pathlib import Path
import pytest

from src.data.dataset import (PoetryTrainingDataset, build_control_summary, build_reconstruction_prompt,
                              dropout_controls, record_to_example)
from src.data.human_review import read_jsonl, write_jsonl
from src.data.mixed_dataset import MixedPoetryDataset, make_form_only
from src.data.partial_silver import make_partial, build_partial, source_fragment
from src.data.partial_supervision import UNKNOWN_DIMS, RULE_VERSION
from src.data.validate_dataset import load_schema, validate_record

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = load_schema(ROOT / 'configs/style_schema.json')
LEX = json.loads((ROOT / 'configs/imagery_lexicon_v1.json').read_text(encoding='utf-8'))
GOLD = read_jsonl(ROOT / 'data/processed/style_annotation/gold_calibration_v1.jsonl')
PROVENANCE = {'source_file': 'test-source.jsonl', 'source_sha256': 'a' * 64, 'rule_version': RULE_VERSION,
              'rule_code_sha256': 'b' * 64, 'lexicon_sha256': 'c' * 64, 'gate_report_sha256': 'd' * 64,
              'text_policy': 'source_preserved_v1'}


def partial():
    for row in GOLD:
        copy = deepcopy(row); copy['id'] = 'silver-fixture'
        record, _ = make_partial(copy, LEX, PROVENANCE, SCHEMA)
        if record: return record
    raise AssertionError('Need one rule-qualified fixture')


@pytest.mark.parametrize('dim,value', [('emotion', ['serene']), ('diction', 'refined'), ('expression', 'balanced'), ('energy', 'gentle')])
def test_partial_semantic_pseudo_labels_rejected(dim, value):
    row = partial(); row['style'][dim] = value
    assert any(x.field == 'style.' + dim for x in validate_record(row, SCHEMA, stage='partial-silver'))


def test_partial_nulls_provenance_and_gold_separation():
    row = partial()
    assert not validate_record(row, SCHEMA, stage='partial-silver')
    assert all(row['style'][d] is None for d in UNKNOWN_DIMS)
    assert validate_record(row, SCHEMA, stage='gold')
    row['metadata']['review_status'] = 'gold_adjudicated'
    assert validate_record(row, SCHEMA, stage='partial-silver')
    row = partial(); row['annotation']['human_review'] = {'reviewer': 'fake'}
    assert validate_record(row, SCHEMA, stage='partial-silver')
    row = partial(); del row['annotation']['provenance']['lexicon_sha256']
    assert validate_record(row, SCHEMA, stage='partial-silver')
    row = deepcopy(GOLD[0]); row['style']['energy'] = None
    assert validate_record(row, SCHEMA, stage='gold')


def test_missing_unknown_and_invalid_rule_labels_rejected():
    row = partial(); del row['style']['energy']
    assert validate_record(row, SCHEMA, stage='partial-silver')
    for value in ([], ['fake'], ['landscape', 'landscape'], [['landscape']]):
        row = partial(); row['style']['imagery'] = value
        assert validate_record(row, SCHEMA, stage='partial-silver')


def test_partial_prompt_omits_unsupervised_and_metadata():
    row = partial(); prompt = build_reconstruction_prompt(row)
    assert all(x in prompt for x in ('诗体：', '意象：', '密度：'))
    assert not any(x in prompt for x in ('情感：', '辞藻：', '表达：', '气势：', '未知', 'null', 'silver', 'source_file'))
    assert row['text'] not in prompt
    with pytest.raises(ValueError): build_control_summary(row, ('form', 'energy'))


def test_gold_prompt_byte_content_unchanged():
    row = deepcopy(GOLD[0]); row['style'] = {'emotion': ['serene'], 'imagery': ['landscape'], 'diction': 'plain',
                                          'expression': 'direct', 'energy': 'gentle', 'density': 'sparse'}
    row['form'] = 'qijue7'
    assert build_reconstruction_prompt(row) == ('你是一名中国古典诗歌生成模型。请严格依据给定诗体和风格控制，'
        '生成一首符合要求的古典诗。\n\n【控制条件】\n诗体：七言绝句\n情感：清宁平和\n意象：山水自然\n辞藻：质朴\n表达：直抒\n气势：舒缓\n密度：疏朗'
        '\n\n【输出要求】\n只输出诗歌正文，不输出作者、标题、解释或额外说明。')


def test_dropout_deterministic_order_independent_and_disabled_for_eval():
    expected = {r['id']: dropout_controls(r, .5, 17, 2, True) for r in GOLD}
    assert expected == {r['id']: dropout_controls(r, .5, 17, 2, True) for r in reversed(GOLD)}
    assert any(expected[r['id']] != dropout_controls(r, .5, 17, 3, True) for r in GOLD)
    assert all(dropout_controls(r, 1., 17, 2, True) == ('form',) for r in GOLD)
    assert all(len(dropout_controls(r, 1., 17, 2, False)) == 7 for r in GOLD)
    assert all(len(dropout_controls(r, 0., 17, 2, True)) == 7 for r in GOLD)


def paths(tmp_path):
    gold = tmp_path / 'gold.jsonl'; silver = tmp_path / 'silver.jsonl'
    write_jsonl(GOLD[:2], gold); write_jsonl([partial()], silver)
    return gold, silver


def test_mixed_provenance_weights_and_target_preserved(tmp_path):
    gold, silver = paths(tmp_path)
    ds = MixedPoetryDataset(gold, mode='gold+partial-silver', partial_silver_path=silver, training=True,
                           control_dropout=1., source_weights={'gold': 2., 'partial-silver': 1.})
    assert len(ds) == 3 and ds.sampling_weights == [1., 1., 1.]
    g, s = ds[0], ds[2]
    assert g.source == 'gold' and s.source == 'partial-silver'
    assert g.supervision_type['energy'] == 'human_gold' and 'energy' not in s.supervision_type
    assert 'human_review' in g.provenance['annotation'] and 'human_review' not in s.provenance['annotation']
    assert g.active_controls == s.active_controls == ('form',)
    assert g.target_text == GOLD[0]['text'] and s.target_text == partial()['text']
    assert len(g.available_controls) == 7 and s.available_controls == ('form', 'imagery', 'density')
    manifest = ds.manifest()
    assert manifest['sources'][0]['source_sampling_mass'] == 2.
    assert manifest['examples'][2]['supervision_type']['imagery'] == 'silver_rule_v1_1'


def test_all_modes_and_form_only_interface(tmp_path):
    gold, silver = paths(tmp_path)
    assert len(MixedPoetryDataset(gold)) == 2
    empty_form = MixedPoetryDataset(gold, mode='gold+partial-silver+form-only', partial_silver_path=silver)
    assert empty_form.manifest()['form_only_interface_unpopulated']
    row = deepcopy(GOLD[-1]); row['id'] = 'form-only-fixture'
    form = make_form_only(row, SCHEMA, 'corpus.jsonl', 'a' * 64)
    path = tmp_path / 'form.jsonl'; write_jsonl([form], path)
    ds = MixedPoetryDataset(gold, mode='gold+partial-silver+form-only', partial_silver_path=silver, form_only_path=path,
                           training=False, control_dropout=1.)
    assert len(ds) == 4 and ds[-1].available_controls == ('form',)
    assert len(ds[0].active_controls) == 7 and len(ds[2].active_controls) == 3
    assert '意象：' not in ds[-1].prompt_text


def test_source_duplicates_and_unconfirmed_gold_rejected(tmp_path):
    gold, silver = paths(tmp_path)
    row = partial(); row['id'] = GOLD[0]['id']; row['annotation']['provenance']['source_record_id'] = row['id']
    write_jsonl([row], silver)
    with pytest.raises(ValueError, match='duplicate'): MixedPoetryDataset(gold, mode='gold+partial-silver', partial_silver_path=silver)
    row = deepcopy(GOLD[0]); row['annotation'].pop('human_review')
    write_jsonl([row], gold)
    with pytest.raises(ValueError, match='confirmation'): MixedPoetryDataset(gold)


def test_quality_exclusion_and_no_llm_path():
    source = deepcopy(GOLD[0]); source['id'] = 'source-fragment'; source['metadata']['title'] = '句'
    high = deepcopy(GOLD[0]); high['id'] = 'high-risk'
    variant = deepcopy(GOLD[0]); variant['id'] = 'known-variant'
    accepted, rejected = build_partial([GOLD[0], GOLD[1], source, high, variant], [GOLD[0]], [GOLD[1]],
        {'high-risk': {'flags': [{'code': 'test-risk', 'severity': 'high'}]}},
        [{'members': [GOLD[0]['id'], 'known-variant']}], LEX, SCHEMA, PROVENANCE)
    assert not accepted
    reasons = {r['id']: r['reasons'] for r in rejected}
    assert 'existing_gold' in reasons[GOLD[0]['id']]
    assert 'unresolved_calibration' in reasons[GOLD[1]['id']]
    assert 'source_fragment' in reasons['source-fragment'] and 'high_risk_quality' in reasons['high-risk']
    assert 'protected_variant' in reasons['known-variant']


def test_weighted_dataloader_and_evaluation_sampling(tmp_path):
    from src.training.data_pipeline import build_training_dataloader
    from torch.utils.data import WeightedRandomSampler
    from test_baseline_framework import FakeChatTokenizer
    gold, silver = paths(tmp_path)
    train = MixedPoetryDataset(gold, mode='gold+partial-silver', partial_silver_path=silver, training=True, control_dropout=.3)
    loader = build_training_dataloader(train, FakeChatTokenizer(), max_length=512, batch_size=2, seed=19)
    assert isinstance(loader.sampler, WeightedRandomSampler)
    assert next(iter(loader))['labels'].shape[0] == 2
    repeat = build_training_dataloader(train, FakeChatTokenizer(), max_length=512, batch_size=2, seed=19)
    first = build_training_dataloader(train, FakeChatTokenizer(), max_length=512, batch_size=2, seed=19)
    assert list(first.sampler) == list(repeat.sampler)
    evaluation = MixedPoetryDataset(gold, mode='gold+partial-silver', partial_silver_path=silver, training=False, control_dropout=1.)
    loader = build_training_dataloader(evaluation, FakeChatTokenizer(), max_length=512, batch_size=2, seed=19, shuffle=False)
    assert not isinstance(loader.sampler, WeightedRandomSampler)
    assert len(evaluation[0].active_controls) == 7
