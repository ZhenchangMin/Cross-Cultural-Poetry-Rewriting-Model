from copy import deepcopy
import json
from pathlib import Path

import pytest
from src.data.silver_annotation import (discover_gold,split_gold,frozen_prompt,assemble_prediction,
    metrics,gate_passes,make_silver,distribution,STYLE_DIMS)
from src.data.human_review import read_jsonl,write_jsonl
from src.data.validate_dataset import load_schema

ROOT=Path(__file__).resolve().parents[1]
DATA=ROOT/'data/processed/style_annotation'
SCHEMA=load_schema(ROOT/'configs/style_schema.json')
LEX=json.loads((ROOT/'configs/imagery_lexicon_v1.json').read_text(encoding='utf-8'))
GOLD=read_jsonl(DATA/'gold_calibration_v1.jsonl')


def valid_raw(row):
    return json.dumps({d:{'value':row['style'][d],'confidence':.9,'evidence':[row['text'].splitlines()[0]]}
                       for d in ['emotion','diction','expression','energy']},ensure_ascii=False)


def test_gold_inventory_deduplicates_and_rejects_conflict(tmp_path):
    a=tmp_path/'a.jsonl';b=tmp_path/'b.jsonl'
    write_jsonl(GOLD,a);write_jsonl(GOLD,b)
    unique,_=discover_gold([a,b],SCHEMA)
    assert len(unique)==24
    changed=deepcopy(GOLD);changed[0]['style']['energy']='vigorous'
    write_jsonl(changed,b)
    with pytest.raises(ValueError,match='Conflicting'):discover_gold([a,b],SCHEMA)


def test_split_disjoint_reproducible_and_grouped():
    c,v=split_gold(GOLD,[])
    c2,v2=split_gold(list(reversed(GOLD)),[])
    assert {r['id'] for r in v}=={r['id'] for r in v2}
    assert len(c)==16 and len(v)==8
    assert {r['id'] for r in c}.isdisjoint(r['id'] for r in v)
    assert sum(r['form']=='qijue7' for r in v)==4
    assert {r['metadata']['author'] for r in c}.isdisjoint(r['metadata']['author'] for r in v)
    same=deepcopy(GOLD)
    same[0]['metadata']['author']=same[1]['metadata']['author']
    c,v=split_gold(same,[])
    held={r['id'] for r in v}
    assert (same[0]['id'] in held)==(same[1]['id'] in held)


def test_prompt_never_reads_target_label_metadata_or_review():
    c,v=split_gold(GOLD,[])
    before=frozen_prompt(v[0],SCHEMA,c[:2])
    altered=deepcopy(v[0]);altered['style']={'private':'TARGET_LABEL_SENTINEL'}
    altered['metadata']={'author':'AUTHOR_SECRET','title':'TITLE_SECRET'}
    altered['annotation']={'human_review':'REVIEW_SECRET'}
    assert frozen_prompt(altered,SCHEMA,c[:2])==before
    assert all(x not in before for x in ['TARGET_LABEL_SENTINEL','AUTHOR_SECRET','TITLE_SECRET','REVIEW_SECRET'])


def test_invalid_output_keeps_rule_predictions_without_inventing_llm():
    p=assemble_prediction(GOLD[0],'not JSON',SCHEMA,LEX,'test-model','hash')
    assert p['error'] and set(p['blocks'])=={'imagery','density'}
    report=metrics([GOLD[0]],[p],SCHEMA)
    assert report['dimensions']['emotion']['f1']==0
    assert report['dimensions']['energy']['accuracy']==0
    assert report['dimensions']['energy']['missing_predictions']==1


def test_evidence_and_confidence_are_required():
    raw=json.loads(valid_raw(GOLD[0]));raw['energy']['evidence']=['不在原文的证据']
    p=assemble_prediction(GOLD[0],json.dumps(raw),SCHEMA,LEX,'test','hash')
    assert p['error']
    raw=json.loads(valid_raw(GOLD[0]));raw['energy']['confidence']=float('nan')
    assert assemble_prediction(GOLD[0],json.dumps(raw),SCHEMA,LEX,'test','hash')['error']


def test_metrics_manual_multilabel_counts_and_confusion():
    row=deepcopy(GOLD[0]);row['style']['emotion']=['serene','joyful']
    p=assemble_prediction(row,valid_raw(row),SCHEMA,LEX,'test','hash')
    p['blocks']['emotion']['value']=['serene','melancholic']
    p['blocks']['diction']['value']='plain'
    m=metrics([row],[p],SCHEMA)['dimensions']
    assert m['emotion']['precision']==m['emotion']['recall']==m['emotion']['f1']==.5
    assert m['emotion']['counts']=={'tp':1,'fp':1,'fn':1}
    assert m['diction']['accuracy']==0
    assert m['diction']['confusion']=={'refined->plain':1}
    with pytest.raises(ValueError):metrics([row],[p,p],SCHEMA)


def test_silver_threshold_provenance_and_never_gold(tmp_path):
    row=GOLD[0]
    p=assemble_prediction(row,valid_raw(row),SCHEMA,LEX,'test-model','prompt-hash')
    silver,reasons=make_silver(row,p,{d:0 for d in STYLE_DIMS},SCHEMA,{'llm':'test-model'})
    assert not reasons and silver['metadata']['label_source']=='automatic_silver'
    assert silver['metadata']['review_status']=='automatic_silver_accepted'
    assert 'human_review' not in silver['annotation'] and 'reviewer' not in silver['metadata']
    assert silver['annotation']['per_dimension']['energy']['label_source']=='llm'
    assert silver['annotation']['per_dimension']['density']['label_source']=='rule'
    path=tmp_path/'silver.jsonl';write_jsonl([silver],path)
    assert discover_gold([path],SCHEMA)[0]==[]
    rejected,reasons=make_silver(row,p,{d:1 for d in STYLE_DIMS},SCHEMA,{})
    assert rejected is None and 'confidence:energy' in reasons


def test_quality_gate_fails_closed_and_empty_distribution():
    evaluation={'dimensions':{'emotion':{'f1':.69},'density':{'accuracy':1}}}
    assert not gate_passes(evaluation,{'emotion':['f1',.7],'density':['accuracy',.95]})
    assert all(sum(counts.values())==0 for counts in distribution([],SCHEMA).values())
