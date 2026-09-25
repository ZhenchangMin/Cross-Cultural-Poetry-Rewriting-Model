"""Automatic Silver annotation: explicit provenance, frozen split, fail-closed gates."""
from collections import Counter
from copy import deepcopy
import hashlib
import json
import random
import re

from .preannotate_style import (LLM_DIMS, RULE_METHOD, build_llm_prompt,
                                rule_preannotate_record, validate_llm_result, _extract_json_object)
from .validate_dataset import STYLE_DIMS, validate_record

VERSION = 'automatic_silver_v1'


def digest(obj):
    return hashlib.sha256(json.dumps(obj,ensure_ascii=False,sort_keys=True).encode()).hexdigest()


def discover_gold(paths, schema):
    unique, sources = {}, {}
    for path in sorted(paths):
        for line in path.read_text(encoding='utf-8').splitlines():
            if not line.strip():
                continue
            row=json.loads(line)
            review=row.get('annotation',{}).get('human_review',{})
            if row.get('metadata',{}).get('review_status')!='gold_adjudicated' or review.get('decision') not in ['accept','edit']:
                continue
            if not review.get('reviewer') or not review.get('confirmation_provenance'):
                raise ValueError(f"Gold without explicit review provenance: {row.get('id')}")
            if validate_record(row,schema,stage='gold',line=1):
                raise ValueError(f"Invalid Gold: {row.get('id')}")
            rid=row['id']
            if rid in unique and any(unique[rid][k]!=row[k] for k in ['text','form','style']):
                raise ValueError(f'Conflicting Gold copies: {rid}')
            unique[rid]=row
            sources.setdefault(rid,[]).append(str(path))
    return [unique[k] for k in sorted(unique)],sources


def split_gold(rows, variant_groups, seed=20260925, per_form=4):
    """Conservative grouping by author, exact text and known variant family."""
    ids={r['id'] for r in rows}
    parent={rid:rid for rid in ids}
    def find(x):
        while parent[x]!=x:
            parent[x]=parent[parent[x]]
            x=parent[x]
        return x
    def union(a,b):
        parent[find(a)]=find(b)
    keys={}
    for row in rows:
        for key in [('author',row['metadata'].get('author')),
                    ('text',re.sub(r'\W','',row['text']))]:
            if not key[1]: continue
            if key in keys: union(row['id'],keys[key])
            keys[key]=row['id']
    for group in variant_groups:
        members=sorted(ids.intersection(group['members']))
        for rid in members[1:]: union(members[0],rid)
    groups={}
    for row in sorted(rows,key=lambda r:r['id']): groups.setdefault(find(row['id']),[]).append(row)
    blocks=sorted(groups.values(),key=lambda g:g[0]['id'])
    random.Random(seed).shuffle(blocks)
    counts=Counter(); held=set()
    for block in blocks:
        additions=Counter(r['form'] for r in block)
        if all(counts[f]+n<=per_form for f,n in additions.items()):
            held.update(r['id'] for r in block); counts.update(additions)
    if any(counts[f]!=per_form for f in ['qijue7','qilv7']):
        raise ValueError('Cannot achieve grouped validation quotas; do not split groups')
    calibration=[r for r in rows if r['id'] not in held]
    validation=[r for r in rows if r['id'] in held]
    if not calibration: raise ValueError('Empty calibration split')
    return calibration,validation


def frozen_prompt(record,schema,examples):
    # Construct fresh records: do not pass title, author, review notes or target labels.
    prompt=build_llm_prompt({'text':record['text'],'form':record['form']},schema)
    shots=[{'text':r['text'],'form':r['form'],
            'human_labels':{d:r['style'][d] for d in LLM_DIMS}} for r in examples]
    return ('下列是人工确认的校准例，仅用于理解标签。它们没有概率置信度。\n'+
            json.dumps(shots,ensure_ascii=False)+'\n每个预测维度至少给出一条原文证据。\n'+prompt)


def assemble_prediction(row, raw, schema, lexicon, model_version, prompt_hash):
    rules=rule_preannotate_record({'id':row['id'],'text':row['text'],'form':row['form']},lexicon_cfg=lexicon)['annotation']['prelabel']
    blocks={d:rules[d] for d in ['imagery','density']}
    error=None
    try:
        semantic=validate_llm_result(_extract_json_object(raw),schema,row['text'])
        if any(not b['evidence'] for b in semantic.values()):
            raise ValueError('Missing verbatim evidence')
        for b in semantic.values(): b['method']=model_version
        blocks.update(semantic)
    except (ValueError,TypeError,KeyError) as exc:
        error=f'{type(exc).__name__}: {exc}'
    for dim,b in blocks.items():
        b['label_source']='rule' if dim in ['imagery','density'] else 'llm'
        b['version']=RULE_METHOD if b['label_source']=='rule' else model_version
    return {'id':row['id'],'blocks':blocks,'error':error,'raw_response':raw,
            'annotation_version':VERSION,'prompt_sha256':prompt_hash}


def metrics(gold,predictions,schema):
    by_id={p['id']:p for p in predictions}
    if len(by_id)!=len(predictions) or set(by_id)!={r['id'] for r in gold}:
        raise ValueError('Prediction IDs must exactly match evaluation Gold')
    result={}
    errors=[]
    for dim in STYLE_DIMS:
        multi=dim in ['emotion','imagery']
        tp=fp=fn=correct=missing=0
        conf=[]; conf_correct=[]; confusion=Counter(); perlabel={k:Counter() for k in schema['style'][dim]['values']}
        for row in gold:
            block=by_id[row['id']]['blocks'].get(dim)
            actual=row['style'][dim]
            predicted=block['value'] if block else ([] if multi else None)
            equal=set(predicted)==set(actual) if multi else predicted==actual
            correct+=equal; missing+=block is None
            if block and isinstance(block.get('confidence'),(float,int)):
                conf.append(block['confidence']); conf_correct.append((block['confidence'],bool(equal)))
            if multi:
                a,b=set(actual),set(predicted)
                tp+=len(a&b);fp+=len(b-a);fn+=len(a-b)
                for label in perlabel:
                    perlabel[label]['tp']+=int(label in a&b)
                    perlabel[label]['fp']+=int(label in b-a)
                    perlabel[label]['fn']+=int(label in a-b)
                for x in a-b:confusion[f'missed:{x}']+=1
                for x in b-a:confusion[f'extra:{x}']+=1
            elif not equal: confusion[f'{actual}->{predicted}']+=1
            if not equal:errors.append({'id':row['id'],'dimension':dim,'gold':actual,'predicted':predicted,
                                        'confidence':block.get('confidence') if block else None})
        def prf(t,p,n):
            return {'precision':t/(t+p) if t+p else 0.,'recall':t/(t+n) if t+n else 0.,
                    'f1':2*t/(2*t+p+n) if 2*t+p+n else 0.}
        score={'n':len(gold),'missing_predictions':missing,'exact_match_accuracy':correct/len(gold),
               'mean_confidence':sum(conf)/len(conf) if conf else None,
               'confusion':dict(confusion.most_common()),
               'confidence_bins':[{'lower':lo,'upper':hi,'count':sum(lo<=c<hi for c,_ in conf_correct),
                   'exact_matches':sum(lo<=c<hi and ok for c,ok in conf_correct)} for lo,hi in [(0,.6),(.6,.8),(.8,1.000001)]]}
        if multi:
            score.update(prf(tp,fp,fn));score['averaging']='micro';score['counts']={'tp':tp,'fp':fp,'fn':fn}
            score['per_label']={label:prf(c['tp'],c['fp'],c['fn']) for label,c in perlabel.items()}
        else:score['accuracy']=correct/len(gold)
        result[dim]=score
    return {'dimensions':result,'errors':errors,'annotation_failures':sum(bool(p['error']) for p in predictions),
            'confidence_note':'LLM self-report and rule heuristics are not calibrated probabilities'}


def gate_passes(evaluation,gate):
    return all(evaluation['dimensions'][d][metric]>=threshold for d,(metric,threshold) in gate.items())


def make_silver(row,prediction,thresholds,schema,provenance):
    reasons=[]
    if prediction['error']: reasons.append('invalid_llm_output')
    for dim in STYLE_DIMS:
        block=prediction['blocks'].get(dim)
        if not block or block.get('confidence') is None or block['confidence']<thresholds[dim]:
            reasons.append(f'confidence:{dim}')
    if reasons:return None,reasons
    result={k:deepcopy(row[k]) for k in ['id','text','form','culture','metadata']}
    result['style']={d:deepcopy(prediction['blocks'][d]['value']) for d in STYLE_DIMS}
    # Existing validator checks label/form structure; it does not confer human provenance.
    if validate_record(result,schema,stage='gold',line=1):return None,['invalid_schema']
    result['metadata'].update(review_status='automatic_silver_accepted',label_source='automatic_silver',
                              annotation_version=VERSION,text_policy='source_preserved_v1')
    for key in ['reviewer','annotation_scope']:
        result['metadata'].pop(key,None)
    result['annotation']={'version':VERSION,'label_source':'automatic_silver',
                          'per_dimension':deepcopy(prediction['blocks']),
                          'provenance':deepcopy(provenance),'prompt_sha256':prediction['prompt_sha256']}
    return result,[]


def distribution(rows,schema):
    counts={d:{label:0 for label in schema['style'][d]['values']} for d in STYLE_DIMS}
    for row in rows:
        for d in counts:
            value=row['style'][d]
            for label in value if isinstance(value,list) else [value]:counts[d][label]+=1
    return counts
