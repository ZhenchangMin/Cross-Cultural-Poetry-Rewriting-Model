"""Separate semantic labels from protocol validity; at most one bounded repair."""
from collections import Counter
from copy import deepcopy
from itertools import combinations
import json
import math

DIMS=('emotion','diction','expression','energy')


def select_examples(rows,n=4):
    """Exhaustive maximum enum coverage, balanced dimension coverage, ID tie-break."""
    rows=sorted(rows,key=lambda r:r['id'])
    if len(rows)<n or len({r['id'] for r in rows})!=len(rows):
        raise ValueError('Need distinct calibration candidates')
    def coverage(group):
        return {d:sorted({v for r in group for v in (r['style'][d] if d=='emotion' else [r['style'][d]])}) for d in DIMS}
    best=None;best_score=None
    for group in combinations(rows,n):
        c=coverage(group)
        score=(sum(map(len,c.values())), min(map(len,c.values())),len({r['form'] for r in group}))
        if best_score is None or score>best_score:best,best_score=group,score
    return list(best),{'objective':'max total dimension-label coverage, then min dimension coverage, then form diversity; lexicographic IDs break ties',
                       'score':list(best_score),'coverage':coverage(best),
                       'reasons':[{'id':r['id'],'labels':{d:r['style'][d] for d in DIMS}} for r in best]}


def check_response(raw,poem,schema):
    text=raw.strip(); wrapper=False
    if text.startswith('```') and text.endswith('```') and '\n' in text:
        text=text.split('\n',1)[1].rsplit('```',1)[0].strip();wrapper=True
    parsed=None;errors=[]
    try:
        parsed=json.loads(text)
        if not isinstance(parsed,dict):raise ValueError('root must be object')
        parse=True
    except (ValueError,TypeError) as exc:
        parse=False;errors.append('JSON: '+str(exc))
    shape=parse and set(parsed)==set(DIMS)
    dimensions={}
    for d in DIMS:
        block=parsed.get(d) if parse else None
        block_shape=isinstance(block,dict) and set(block)=={'value','confidence','evidence'}
        shape=shape and block_shape
        value=block.get('value') if isinstance(block,dict) else None
        allowed=schema['style'][d]['values']
        type_valid=isinstance(value,list) if d=='emotion' else isinstance(value,str)
        normalized=deepcopy(value); repairs=[]
        if d=='emotion' and isinstance(value,str) and value in allowed:
            normalized=[value];repairs.append('emotion_string_to_singleton_list')
        elif d!='emotion' and isinstance(value,list) and len(value)==1 and isinstance(value[0],str) and value[0] in allowed:
            normalized=value[0];repairs.append('single_label_singleton_list_to_string')
        if d=='emotion':
            legal=(isinstance(normalized,list) and 1<=len(normalized)<=2 and
                   all(isinstance(x,str) and x in allowed for x in normalized) and len(set(normalized))==len(normalized))
        else:legal=isinstance(normalized,str) and normalized in allowed
        confidence=block.get('confidence') if isinstance(block,dict) else None
        confidence_valid=isinstance(confidence,(int,float)) and not isinstance(confidence,bool) and math.isfinite(confidence) and 0<=confidence<=1
        evidence=block.get('evidence') if isinstance(block,dict) else None
        evidence_valid=isinstance(evidence,list) and 1<=len(evidence)<=3 and all(isinstance(x,str) and bool(x.strip()) and x in poem for x in evidence)
        item={'raw_prediction':deepcopy(block),'normalized_prediction':normalized if legal else None,
              'label_valid':bool(legal),'type_valid':type_valid,'type_repaired':bool(repairs),
              'confidence_valid':bool(confidence_valid),'evidence_valid':bool(evidence_valid),
              'schema_valid':bool(block_shape),'full_protocol_valid':bool(block_shape and legal and type_valid and confidence_valid and evidence_valid),
              'repair_used':False,'normalization_provenance':repairs}
        dimensions[d]=item
        for key in ['schema_valid','label_valid','type_valid','confidence_valid','evidence_valid']:
            if not item[key]:errors.append(f'{d}.{key}=false')
    if parse and set(parsed)!=set(DIMS):errors.append('schema: root keys must equal four dimensions')
    return {'json_parse_success':parse,'json_wrapper_removed':wrapper,
            'schema_success':bool(shape and all(x['label_valid'] for x in dimensions.values())),
            'type_success':all(x['type_valid'] for x in dimensions.values()),
            'evidence_verbatim_success':all(x['evidence_valid'] for x in dimensions.values()),
            'full_protocol_success':bool(shape and all(x['full_protocol_valid'] for x in dimensions.values())),
            'dimensions':dimensions,'errors':errors}


def required_schema(schema):
    return {d:{'value_type':'array of 1-2 unique labels' if d=='emotion' else 'single string',
               'allowed_labels':list(schema['style'][d]['values']),
               'confidence':'finite number in [0,1]', 'evidence':'array of 1-3 nonempty verbatim substrings of poem'} for d in DIMS}


def repair_prompt(poem,original,errors,schema):
    # Signature deliberately cannot receive a Gold record or few-shot labels.
    return ('最终根对象只能有emotion、diction、expression、energy四个键，不要返回输入材料或schema。\n'
            'Do not reinterpret the poem unless the existing label is illegal. '
            'Only repair the response format/type/evidence. Preserve every existing legal label, including singleton normalization. '
            'Evidence must be copied verbatim from the poem. Return JSON only.\n'+
            json.dumps({'original_poem':poem,'original_model_response':original,
                        'validator_errors':errors,'required_JSON_schema':required_schema(schema)},ensure_ascii=False))


def first_prompt(poem,form,examples,schema):
    shots=[]
    for row in examples:
        result={}
        for d in DIMS:
            proposals=row.get('annotation',{}).get('assistant_calibration',{}).get('style_proposal',{})
            evidence=proposals.get(d,{}).get('evidence',[])
            evidence=[s for s in evidence if isinstance(s,str) and s and s in row['text']][:2]
            if not evidence:evidence=[row['text'].splitlines()[0]]
            result[d]={'value':row['style'][d],'confidence':.8,'evidence':evidence}
        shots.append({'poem':row['text'],'response_format_example':result})
    definitions='\n'.join(d+': '+', '.join(f'{k}={v}' for k,v in schema['style'][d]['values'].items()) for d in DIMS)
    demonstrations='\n\n'.join('示例诗歌：\n'+s['poem']+'\n标注答案：\n'+json.dumps(s['response_format_example'],ensure_ascii=False) for s in shots)
    return ('任务：阅读最后的待标注诗歌，输出它的四维风格JSON。不要复述任务、标签定义或示例。\n'
            '根对象只能有emotion、diction、expression、energy四个键。每维含value、confidence、evidence。'
            'emotion.value必须是1~2个标签的数组，其余value是单个标签字符串。'
            'confidence为0到1数值。evidence为1~3个短语的数组，逐字复制待标注诗的正文，保留繁简，不写标签释义。'
            '示例的0.8只演示数值格式，不是人工置信度。\n合法标签：\n'+definitions+'\n\n'+demonstrations+
            '\n\n现在只标注下面这一首，不要输出示例的答案：\n诗体：'+form+'\n正文：\n'+poem+
            '\n\n标注答案（只有四维JSON，无Markdown）：')


def finish_result(first_raw,repair_raw,poem,schema):
    first=check_response(first_raw,poem,schema)
    repaired=check_response(repair_raw,poem,schema) if repair_raw is not None else None
    final=deepcopy(repaired or first);blocked=[]
    if repaired:
        for d in DIMS:
            old,new=first['dimensions'][d],final['dimensions'][d]
            old_value,new_value=old['normalized_prediction'],new['normalized_prediction']
            same=(set(old_value)==set(new_value) if d=='emotion' and old['label_valid'] and new['label_valid'] else old_value==new_value)
            if old['label_valid'] and (not new['label_valid'] or not same):
                # Reject a semantic change; preserve first-pass label and annotation, never use Gold.
                final['dimensions'][d]=deepcopy(old)
                final['dimensions'][d]['full_protocol_valid']=False
                final['dimensions'][d]['repair_semantic_change_rejected']=True
                blocked.append(d)
            final['dimensions'][d]['repair_used']=True
        if blocked:
            final['full_protocol_success']=False
            final['errors'] += ['repair_changed_legal_label:'+d for d in blocked]
        final['type_success']=all(x['type_valid'] for x in final['dimensions'].values())
        final['evidence_verbatim_success']=all(x['evidence_valid'] for x in final['dimensions'].values())
        final['schema_success']=final['schema_success'] and all(x['schema_valid'] and x['label_valid'] for x in final['dimensions'].values())
    return {'first_pass_raw':first_raw,'first_pass_errors':first['errors'],'first_pass_result':first,
            'repair_raw':repair_raw,'repair_errors':repaired['errors'] if repaired else [],
            'repair_used':repaired is not None,'repair_semantic_changes_rejected':blocked,'final_result':final}


def evaluate(rows,records,phase='final_result'):
    lookup={r['id']:r for r in records}
    if len(lookup)!=len(records) or set(lookup)!={r['id'] for r in rows}:raise ValueError('Evaluation ID mismatch')
    n=len(rows);semantic={};failures=[]
    for d in DIMS:
        tp=fp=fn=correct=valid=0;confusions=Counter()
        for row in rows:
            p=lookup[row['id']][phase]['dimensions'][d];v=p['normalized_prediction'];g=row['style'][d]
            valid+=p['label_valid']
            if d=='emotion':
                a,b=set(g),set(v or []);tp+=len(a&b);fp+=len(b-a);fn+=len(a-b);ok=a==b
                for x in a-b:confusions['missed:'+x]+=1
                for x in b-a:confusions['extra:'+x]+=1
            else:ok=v==g
            correct+=ok
            if not ok:
                if d!='emotion':confusions[f'{g}->{v}']+=1
                failures.append({'id':row['id'],'dimension':d,'gold':g,'prediction':v,'label_valid':p['label_valid']})
        m={'label_coverage':valid/n,'valid_labels':valid,'n':n,'exact_match_accuracy_all':correct/n,
           'accuracy_on_legal_predictions':correct/valid if valid else None,'confusion':dict(confusions)}
        if d=='emotion':m.update(precision=tp/(tp+fp) if tp+fp else 0,recall=tp/(tp+fn) if tp+fn else 0,
                                 f1=2*tp/(2*tp+fp+fn) if 2*tp+fp+fn else 0,averaging='micro')
        else:m['accuracy']=correct/n
        semantic[d]=m
    fields=['json_parse_success','schema_success','type_success','evidence_verbatim_success','full_protocol_success']
    protocol={f+'_rate':sum(lookup[r['id']][phase][f] for r in rows)/n for f in fields}
    per_dim={d:{f+'_rate':sum(lookup[r['id']][phase]['dimensions'][d][f] for r in rows)/n
                for f in ['label_valid','type_valid','confidence_valid','evidence_valid','full_protocol_valid']} for d in DIMS}
    return {'n':n,'semantic':semantic,'protocol':protocol,'per_dimension_protocol':per_dim,'semantic_failures':failures,
            'protocol_failures':[{'id':r['id'],'errors':lookup[r['id']][phase]['errors']} for r in rows if not lookup[r['id']][phase]['full_protocol_success']],
            'metric_note':'semantic labels survive evidence/confidence/type failures; illegal labels count as missing, never dropped from denominator'}
