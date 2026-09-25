from copy import deepcopy
import json
from pathlib import Path
import subprocess
import sys

import pytest

from src.data.calibration_gold import (audit_gold, export_unresolved, reconcile_reviews,
                                       sample_review_batch, index_unique)
from src.data.human_review import read_jsonl, promote_reviewed_gold
from src.data.dataset import PoetryTrainingDataset, record_to_example
from src.data.validate_dataset import load_schema, validate_jsonl

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT/'data/processed/style_annotation'
def obj(name):
    return json.loads((DATA/name).read_text(encoding='utf-8'))
def rows(name):
    return read_jsonl(DATA/name)

@pytest.fixture
def inputs():
    return (rows('assistant_calibrated_v1_1.jsonl'), rows('review_candidates24_v2.jsonl'),
            obj('human_review_state_v1.json'), obj('human_review_state24_v2.json'),
            load_schema(ROOT/'configs/style_schema.json'))

def test_partial_promotion_preserves_decisions_and_provenance(inputs):
    before = deepcopy(inputs)
    source, state = reconcile_reviews(*inputs)
    gold, report = promote_reviewed_gold(source, state, inputs[-1])
    assert inputs == before
    assert report == {'version':'v1','input_records':30,'gold_records':24,'accepted':21,
                      'edited':3,'excluded':0,'pending':6,'gold_complete':False}
    for row in gold:
        assert row['annotation']['human_review']['confirmation_provenance'] == state['records'][row['id']]
        assert row['style'] == inputs[3]['records'][row['id']]['final_style']
    assert all(state['records'][r['id']]['decision'] != 'pending' for r in gold)

def test_review_conflicts_and_text_changes_are_rejected(inputs):
    changed = deepcopy(inputs)
    rid = changed[1][0]['id']
    changed[2]['records'][rid]['decision']='accept'
    with pytest.raises(ValueError, match='conflicting'):
        reconcile_reviews(*changed)
    changed = deepcopy(inputs)
    changed[1][0]['text'] += '改'
    with pytest.raises(ValueError, match='text/form'):
        reconcile_reviews(*changed)
    with pytest.raises(ValueError, match='duplicate'):
        index_unique([inputs[0][0], inputs[0][0]])

def test_invalid_final_style_is_not_silently_accepted(inputs):
    bad = deepcopy(inputs)
    next(iter(bad[3]['records'].values()))['final_style']['energy']='unknown'
    with pytest.raises(ValueError, match='Gold schema'):
        reconcile_reviews(*bad)

def test_unresolved_export_does_not_invent_decisions(inputs):
    source, state = reconcile_reviews(*inputs)
    pending = export_unresolved(source,state,rows('source_reference_all30_v2.jsonl'),rows('calibration_rule_v1_1.jsonl'))
    assert len(pending)==6
    assert {r['id'] for r in pending} == {r['id'] for r in source} - set(inputs[3]['records'])
    assert all(r['human_review']['decision']=='pending' and r['human_review']['final_style'] is None for r in pending)
    assert all(r['disputed_dimensions']==[] and not r['gold_eligible'] for r in pending)
    assert sum(r['assistant_review_route'].startswith('exclude') for r in pending)==3

def test_real_gold_validator_loader_and_metadata_invariance():
    path=DATA/'gold_calibration_v1.jsonl'
    report=validate_jsonl(path,load_schema(ROOT/'configs/style_schema.json'),stage='gold')
    assert report.ok and report.valid_records==24
    ds=PoetryTrainingDataset(path,schema_path=ROOT/'configs/style_schema.json')
    assert len(ds)==24
    for row, example in zip(read_jsonl(path),ds):
        row['metadata']={'author':'AUTHOR_SENTINEL','title':'TITLE_SENTINEL'}
        assert record_to_example(row).prompt_text == example.prompt_text
        assert 'AUTHOR_SENTINEL' not in example.prompt_text

def test_cli_requires_explicit_partial_flag(tmp_path):
    cmd=[sys.executable,str(ROOT/'scripts/human_review.py'),'promote',
         '--input',str(DATA/'calibration_promotion_input_v1.jsonl'),
         '--state',str(DATA/'human_review_state30_reconciled_v1.json'),
         '--schema',str(ROOT/'configs/style_schema.json'),
         '--output',str(tmp_path/'gold.jsonl'),'--report',str(tmp_path/'report.json')]
    assert subprocess.run(cmd,capture_output=True).returncode != 0
    assert not (tmp_path/'gold.jsonl').exists()
    completed=subprocess.run(cmd+['--allow-partial'],capture_output=True)
    assert completed.returncode==0, completed.stderr
    assert len(read_jsonl(tmp_path/'gold.jsonl'))==24

def test_audit_counts_are_correct(inputs):
    audit=audit_gold(rows('gold_calibration_v1.jsonl'), obj('human_review_state30_reconciled_v1.json'),inputs[-1],inputs[1])
    assert audit['total']==24 and audit['unique_authors']==24
    assert audit['forms']=={'qijue7':13,'qilv7':11}
    assert audit['style_distribution']['emotion']=={'serene':7,'joyful':6,'melancholic':13,'lonely':0,'heroic':3,'indignant':0}
    assert audit['human_changes_vs_source_assisted_proposal']==dict(emotion=2,imagery=0,diction=1,expression=0,energy=0,density=0)
    assert audit['rule_disagreements_with_gold']=={'imagery':17,'density':0}
    for dim in ['diction','expression','energy','density']:
        assert sum(audit['style_distribution'][dim].values())==24

def test_sampling_reproducible_diverse_and_pending():
    pool=rows('preannotated_v1_1.jsonl')
    ids={r['id'] for r in rows('calibration_sample_v1.jsonl')}
    flags=rows('quality_flags_v1.jsonl')
    lex=json.loads((ROOT/'configs/imagery_lexicon_v1.json').read_text(encoding='utf-8'))
    batch,report=sample_review_batch(pool,ids,flags,lex)
    repeated,repeated_report=sample_review_batch(list(reversed(pool)),ids,flags,lex)
    assert (batch,report)==(repeated,repeated_report)
    assert report['forms']=={'qijue7':50,'qilv7':50}
    assert report['unique_authors']==100 and report['max_records_per_author']==1
    assert report['high_risk_selected']==report['high_risk_eligible']==13
    assert not ids.intersection(r['id'] for r in batch)
    assert all(not any(r['style'].values()) for r in batch)
    assert all(r['annotation']['quality_review']['decision']=='pending' for r in batch)
    assert batch==rows('review_batch_v2_100.jsonl')
    changed,_=sample_review_batch(pool,ids,flags,lex,seed=20260925)
    assert [r['id'] for r in batch] != [r['id'] for r in changed]
    with pytest.raises(ValueError,match='insufficient'):
        sample_review_batch(pool[:3],ids,flags,lex)
