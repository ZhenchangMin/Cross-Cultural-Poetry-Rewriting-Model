"""Calibration -> explicit freeze -> development validation. No Silver generation path."""
import argparse
import hashlib
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from src.data.human_review import read_jsonl
from src.data.semantic_annotator_v2 import (DIMS,select_examples,first_prompt,check_response,repair_prompt,finish_result,evaluate)
from src.data.validate_dataset import load_schema


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def save(path,obj):path.write_text(json.dumps(obj,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def load(path):return json.loads(path.read_text(encoding='utf-8'))


def summarize(rows,records):
    first=evaluate(rows,records,'first_pass_result');final=evaluate(rows,records)
    normalizations={d:sum(r['first_pass_result']['dimensions'][d]['type_repaired'] for r in records) for d in DIMS}
    return {'scope':'development diagnosis; not a final test estimate','first_pass':first,'final':final,
            'deterministic_normalization_counts':normalizations,
            'records_with_normalization':sum(any(r['first_pass_result']['dimensions'][d]['type_repaired'] for d in DIMS) for r in records),
            'repair_attempts':sum(r['repair_used'] for r in records),
            'repair_successes':sum(r['repair_used'] and r['final_result']['full_protocol_success'] for r in records),
            'repair_semantic_change_rejections':sum(bool(r['repair_semantic_changes_rejected']) for r in records)}


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('phase',choices=['calibrate','freeze','validate'])
    ap.add_argument('--root',type=Path,default=ROOT)
    ap.add_argument('--output-name',default='semantic_annotator_v2_r3')
    args=ap.parse_args();root=args.root.resolve()
    if not args.output_name.replace('_','').isalnum():raise ValueError('Output name must be simple alphanumeric/underscore')
    old=root/'data/processed/silver_annotation_v1';out=root/'data/processed'/args.output_name
    schema=load_schema(root/'configs/style_schema.json')
    calibration=read_jsonl(old/'annotation_calibration.jsonl')
    assert len(calibration)==16
    examples,selection=select_examples(calibration)
    code=[root/'src/data/semantic_annotator_v2.py',root/'scripts/semantic_v2.py',root/'configs/style_schema.json']
    version_hashes={p.relative_to(root).as_posix():sha(p) for p in code}
    if args.phase=='calibrate':
        if (out/'semantic_annotator_v2_calibration_report.json').exists():raise FileExistsError('Calibration already completed')
        out.mkdir(parents=True,exist_ok=True)
        config={'version':'semantic_annotator_v2','code_hashes':version_hashes,
                'calibration_sha256':sha(old/'annotation_calibration.jsonl'),
                'selection':selection,'few_shot_ids':[r['id'] for r in examples],
                'calibration_policy':'exclude target from its own few-shot examples; deterministic re-selection when necessary',
                'model':'Qwen/Qwen2.5-1.5B-Instruct','model_revision':load(root/'models/_cache/Qwen2.5-1.5B-Instruct/download_provenance.json')['revision'],
                'generation':{'do_sample':False,'max_new_tokens':800},'max_repair_attempts':1,
                'semantic_gate':{'emotion_f1':.7,'diction_accuracy':.6,'expression_accuracy':.6,'energy_accuracy':.6},
                'protocol_gate':{'final_full_protocol_success_rate':.9},
                'imagery_density_gate':'unchanged v1: imagery micro F1 >= .70; density accuracy >= .95',
                'validation_limit':'existing 8 are development validation with historical guideline exposure',
                'silver_batch_forbidden':True,'training_forbidden':True}
        if (out/'config.json').exists():assert load(out/'config.json')==config
        else:save(out/'config.json',config)
        rows=calibration;prefix='calibration'
    else:
        config=load(out/'config.json')
        assert config['code_hashes']==version_hashes
        assert sha(old/'annotation_calibration.jsonl')==config['calibration_sha256']
        if args.phase=='freeze':
            assert (out/'semantic_annotator_v2_calibration_report.json').exists()
            if (out/'frozen_v2.json').exists():raise FileExistsError('Already frozen')
            save(out/'frozen_v2.json',{'config_sha256':sha(out/'config.json'),
                'calibration_report_sha256':sha(out/'semantic_annotator_v2_calibration_report.json'),
                'calibration_predictions_sha256':sha(out/'calibration_predictions.jsonl'),
                'validation_source_sha256':sha(old/'annotation_validation.jsonl'),
                'v1_predictions_sha256':sha(old/'validation_predictions.jsonl'),
                'note':'Frozen after calibration inspection, before reading validation labels for evaluation'})
            print('V2_FROZEN',flush=True);return
        frozen=load(out/'frozen_v2.json')
        for filename,key in [('config.json','config_sha256'),('semantic_annotator_v2_calibration_report.json','calibration_report_sha256'),('calibration_predictions.jsonl','calibration_predictions_sha256')]:assert sha(out/filename)==frozen[key]
        assert sha(old/'annotation_validation.jsonl')==frozen['validation_source_sha256']
        assert sha(old/'validation_predictions.jsonl')==frozen['v1_predictions_sha256']
        if (out/'semantic_annotator_v2_validation_report.json').exists():raise FileExistsError('Validation already completed')
        rows=read_jsonl(old/'annotation_validation.jsonl');prefix='validation'
        assert len(rows)==8 and {r['id'] for r in rows}.isdisjoint(r['id'] for r in calibration)
    print('RUN',prefix,'n=',len(rows),'few_shot_ids=',config['few_shot_ids'],flush=True)
    import os
    os.environ['HF_HUB_OFFLINE']='1';os.environ['TOKENIZERS_PARALLELISM']='false'
    import torch
    from transformers import AutoModelForCausalLM,AutoTokenizer
    assert torch.cuda.is_available()
    model_path=root/'models/_cache/Qwen2.5-1.5B-Instruct'
    tokenizer=AutoTokenizer.from_pretrained(model_path,local_files_only=True)
    model=AutoModelForCausalLM.from_pretrained(model_path,local_files_only=True,torch_dtype=torch.bfloat16).to('cuda');model.eval()
    def generate(prompt):
        ids=tokenizer.apply_chat_template([{'role':'user','content':prompt}],add_generation_prompt=True,return_tensors='pt').to('cuda')
        with torch.inference_mode():
            output=model.generate(input_ids=ids,attention_mask=torch.ones_like(ids),do_sample=False,max_new_tokens=800,pad_token_id=tokenizer.eos_token_id)
        return tokenizer.decode(output[0,ids.shape[1]:],skip_special_tokens=True)
    cache=out/f'{prefix}_predictions.jsonl'
    records=read_jsonl(cache) if cache.exists() else []
    by_id={r['id']:r for r in records}
    assert len(by_id)==len(records) and set(by_id)<={r['id'] for r in rows}
    with cache.open('a',encoding='utf-8') as stream:
        for i,row in enumerate(rows,1):
            shots=examples
            if row['id'] in {r['id'] for r in shots}:shots,_=select_examples([r for r in calibration if r['id']!=row['id']])
            assert row['id'] not in {r['id'] for r in shots}
            prompt=first_prompt(row['text'],row['form'],shots,schema)
            ph=hashlib.sha256(prompt.encode()).hexdigest()
            if row['id'] in by_id:
                assert by_id[row['id']]['prompt_sha256']==ph and by_id[row['id']]['config_sha256']==sha(out/'config.json')
                continue
            raw=generate(prompt);checked=check_response(raw,row['text'],schema)
            repair=None;rp=None
            if not checked['full_protocol_success']:
                rp=repair_prompt(row['text'],raw,checked['errors'],schema);repair=generate(rp)
            record=finish_result(raw,repair,row['text'],schema)
            record.update(id=row['id'],few_shot_ids=[r['id'] for r in shots],prompt_sha256=ph,
                          first_pass_prompt=prompt,repair_prompt=rp,config_sha256=sha(out/'config.json'))
            stream.write(json.dumps(record,ensure_ascii=False)+'\n');stream.flush();records.append(record)
            print(f'{prefix} {i}/{len(rows)} first={checked["full_protocol_success"]} final={record["final_result"]["full_protocol_success"]} repaired={repair is not None}',flush=True)
    summary=summarize(rows,records)
    summary['selection']=selection
    if prefix=='calibration':
        summary['target_example_leakage']=False
        save(out/'semantic_annotator_v2_calibration_report.json',summary)
    else:
        v1=[dict(id=r['id'],**finish_result(r['raw_response'],None,next(x['text'] for x in rows if x['id']==r['id']),schema)) for r in read_jsonl(old/'validation_predictions.jsonl')]
        summary['v1_reanalyzed_same_normalizer']=summarize(rows,v1)
        summary['historical_exposure']=config['validation_limit']
        sem=summary['final']['semantic'];reasons=[]
        for d in DIMS:
            metric='f1' if d=='emotion' else 'accuracy';threshold=config['semantic_gate'][d+'_'+metric]
            if sem[d][metric]<threshold:reasons.append(f'{d}.{metric}={sem[d][metric]:.4f} < {threshold}')
        protocol=summary['final']['protocol']['full_protocol_success_rate']
        if protocol<.9:reasons.append(f'final protocol success={protocol:.4f} < 0.9')
        v1rules=load(old/'heldout_evaluation.json')['dimensions']
        if v1rules['imagery']['f1']<.7 or v1rules['density']['accuracy']<.95:reasons.append('rule metrics below unchanged thresholds')
        summary['silver_gate']='fail' if reasons else 'pass';summary['silver_gate_reasons']=reasons
        summary['silver_batch_started']=False
        save(out/'semantic_annotator_v2_validation_report.json',summary)
    print(json.dumps({'phase':prefix,'first_protocol':summary['first_pass']['protocol'],
        'final_protocol':summary['final']['protocol'],'semantic':summary['final']['semantic'],
        'normalizations':summary['deterministic_normalization_counts'],'silver_gate':summary.get('silver_gate')},ensure_ascii=False),flush=True)


if __name__=='__main__':main()
