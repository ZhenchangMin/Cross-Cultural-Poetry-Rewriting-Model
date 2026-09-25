import json
from copy import deepcopy
from pathlib import Path
import pytest
from src.data.semantic_annotator_v2 import (DIMS,check_response,finish_result,repair_prompt,
                                           first_prompt,select_examples,evaluate)
from src.data.human_review import read_jsonl
from src.data.validate_dataset import load_schema
ROOT=Path(__file__).resolve().parents[1]
SCHEMA=load_schema(ROOT/'configs/style_schema.json')
ROWS=read_jsonl(ROOT/'data/processed/silver_annotation_v1/annotation_calibration.jsonl')
POEM='春風入夜明月照\n江水悠悠過小橋'


def response():
    return {d:{'value':v,'confidence':.8,'evidence':['春風']} for d,v in
            dict(emotion=['serene'],diction='refined',expression='implicit',energy='gentle').items()}
def check(obj):return check_response(json.dumps(obj,ensure_ascii=False),POEM,SCHEMA)


def test_emotion_string_normalizes_without_semantic_change():
    raw=response();raw['emotion']['value']='melancholic'
    x=check(raw)['dimensions']['emotion']
    assert x['normalized_prediction']==['melancholic'] and x['label_valid']
    assert not x['type_valid'] and x['type_repaired']
    assert x['normalization_provenance']==['emotion_string_to_singleton_list']
    assert not x['full_protocol_valid']


def test_single_label_list_normalizes():
    raw=response();raw['diction']['value']=['refined']
    x=check(raw)['dimensions']['diction']
    assert x['normalized_prediction']=='refined' and x['type_repaired'] and not x['type_valid']


@pytest.mark.parametrize('value',['new_emotion',['serene','serene'],['serene','joyful','lonely'],[],42])
def test_illegal_label_rejected(value):
    raw=response();raw['emotion']['value']=value
    assert not check(raw)['dimensions']['emotion']['label_valid']


def test_bad_evidence_does_not_erase_label_or_cross_line():
    raw=response();raw['diction']['evidence']=['诗中没有这个短语']
    x=check(raw)['dimensions']['diction']
    assert x['label_valid'] and x['normalized_prediction']=='refined' and not x['evidence_valid']
    raw['diction']['evidence']=['照江']
    assert not check(raw)['dimensions']['diction']['evidence_valid']


def test_repair_history_and_label_preservation():
    raw=response();raw['emotion']['value']='serene'
    fixed=response()
    first=json.dumps(raw);repair=json.dumps(fixed)
    record=finish_result(first,repair,POEM,SCHEMA)
    assert record['first_pass_raw']==first and record['repair_raw']==repair
    assert record['first_pass_errors'] and not record['repair_errors']
    assert record['final_result']['full_protocol_success']
    assert record['final_result']['dimensions']['emotion']['repair_used']
    fixed['emotion']['value']=['joyful']
    blocked=finish_result(first,json.dumps(fixed),POEM,SCHEMA)
    assert blocked['repair_semantic_changes_rejected']==['emotion']
    assert blocked['final_result']['dimensions']['emotion']['normalized_prediction']==['serene']
    assert not blocked['final_result']['full_protocol_success']
    assert not blocked['final_result']['type_success']


def test_repair_prompt_contains_only_authorized_inputs():
    original=json.dumps(response())
    p=repair_prompt(POEM,original,['emotion.type_valid=false'],SCHEMA)
    assert original in json.loads(p[p.index('{'):])['original_model_response']
    assert 'Do not reinterpret the poem unless the existing label is illegal.' in p
    assert 'gold' not in p.lower() and 'AUTHOR_SENTINEL' not in p
    with pytest.raises(TypeError):repair_prompt(POEM,original,[],SCHEMA,gold=ROWS[0])


def test_selection_order_independent_and_covers_maximum():
    selected,info=select_examples(ROWS)
    selected2,info2=select_examples(list(reversed(ROWS)))
    assert [r['id'] for r in selected]==[r['id'] for r in selected2]
    assert info==info2 and len(selected)==4
    assert all(set(info['coverage'][d])==set(SCHEMA['style'][d]['values']) for d in ['diction','expression','energy'])
    for target in selected:
        others,_=select_examples([r for r in ROWS if r['id']!=target['id']])
        assert target['id'] not in {r['id'] for r in others}


def test_semantic_metrics_independent_from_protocol():
    row={'id':'x','style':{d:b['value'] for d,b in response().items()}}
    raw=response();raw['emotion']['value']='serene'
    raw['energy']['confidence']=1.5;raw['diction']['evidence']=['不存在']
    record=dict(id='x',**finish_result(json.dumps(raw),None,POEM,SCHEMA))
    m=evaluate([row],[record])
    assert m['semantic']['emotion']['f1']==1
    assert all(m['semantic'][d]['accuracy']==1 for d in ['diction','expression','energy'])
    assert m['protocol']['full_protocol_success_rate']==0


def test_json_failure_no_guessed_labels():
    checked=check_response('bad JSON',POEM,SCHEMA)
    assert not checked['json_parse_success']
    assert all(not b['label_valid'] for b in checked['dimensions'].values())


def test_evaluation_does_not_drop_invalid_predictions():
    row={'id':'x','style':{d:b['value'] for d,b in response().items()}}
    record=dict(id='x',**finish_result('bad JSON',None,POEM,SCHEMA))
    m=evaluate([row],[record])
    assert m['semantic']['energy']['accuracy']==0
    assert m['semantic']['energy']['accuracy_on_legal_predictions'] is None


def test_malformed_fence_is_protocol_failure_not_crash():
    result=check_response("```bad```",POEM,SCHEMA)
    assert not result["json_parse_success"]
