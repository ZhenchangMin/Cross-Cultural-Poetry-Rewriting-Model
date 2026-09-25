"""Frozen 24-Gold development CV only. No training, Silver batch, or LLM repair."""
import argparse
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.data.human_review import read_jsonl
from src.data.validate_dataset import load_schema
from src.data.silver_annotation import discover_gold, metrics as rule_metrics, distribution
from src.data.preannotate_style import rule_preannotate_record
from src.data.semantic_annotator_v3 import (DIMS, SEED, SEMANTIC_GATE, PROTOCOL_GATE,
    make_folds, select_anchors, semantic_prompt, normalize, evidence_prompt, validate_evidence, evaluate, gate)


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save(path, obj):
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def load(path):
    return json.loads(path.read_text(encoding='utf-8'))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('phase', choices=['prepare', 'run'])
    args = parser.parse_args()
    out = ROOT / 'data/processed/semantic_annotator_v3'
    schema = load_schema(ROOT / 'configs/style_schema.json')
    sources = sorted((ROOT / 'data/processed/style_annotation').glob('gold_calibration*_v1.jsonl'))
    rows, provenance = discover_gold(sources, schema)
    if len(rows) != 24:
        raise ValueError('Gold inventory changed: expected 24; re-design experiment explicitly')
    lookup = {r['id']: r for r in rows}
    files = sources + [ROOT / p for p in ['configs/style_schema.json', 'configs/imagery_lexicon_v1.json',
        'src/data/semantic_annotator_v3.py', 'scripts/semantic_v3.py', 'src/data/preannotate_style.py',
        'src/data/silver_annotation.py']]
    hashes = {p.relative_to(ROOT).as_posix(): sha(p) for p in files}
    if args.phase == 'prepare':
        if (out / 'frozen_cv.json').exists():
            raise FileExistsError('Frozen CV already exists; never overwrite')
        folds = make_folds(rows)
        for fold in folds:
            train = [lookup[rid] for rid in fold['calibration_ids']]
            fold['anchors'] = {d: select_anchors(train, d) for d in DIMS}
            fold['evaluation_distribution'] = distribution([lookup[rid] for rid in fold['evaluation_ids']], schema)
            fold['evaluation_forms'] = {f: sum(lookup[rid]['form'] == f for rid in fold['evaluation_ids']) for f in ('qijue7', 'qilv7')}
        config = {'version': 'semantic_annotator_v3', 'scope': 'development 4-fold cross-validation; all Gold historically exposed; not independent test',
            'seed': SEED, 'gold_total': len(rows), 'gold_sources': provenance, 'file_hashes': hashes, 'folds': folds,
            'fold_selection': '4000 fixed-seed form-quota assignments; inverse-frequency weighted label balance; no model scores used',
            'anchor_selection': 'single-label: one character-Jaccard class medoid per available label; emotion: four examples maximizing coverage then singleton clarity then medoid centrality; ID tie breaks',
            'anchor_limitation': 'lexical medoid is a deterministic representativeness proxy, not independent human clarity adjudication',
            'model': 'Qwen/Qwen2.5-1.5B-Instruct',
            'model_revision': load(ROOT / 'models/_cache/Qwen2.5-1.5B-Instruct/download_provenance.json')['revision'],
            'generation': {'do_sample': False, 'semantic_max_new_tokens': 96, 'evidence_max_new_tokens': 320},
            'llm_repair_enabled': False, 'semantic_gate': SEMANTIC_GATE, 'protocol_gate': PROTOCOL_GATE,
            'rule_gate': {'imagery_f1': .70, 'density_accuracy': .95},
            'future_confidence_filters': {'semantic': .80, 'imagery': .70, 'density': .50},
            'silver_batch_forbidden': True, 'training_forbidden': True}
        out.mkdir(parents=True, exist_ok=True)
        save(out / 'frozen_cv.json', config)
        print('Frozen V3 development CV: 24 unique Gold, 4 x (18 calibration + 6 evaluation)', flush=True)
        return
    config = load(out / 'frozen_cv.json')
    if config['file_hashes'] != hashes:
        raise ValueError('Frozen inputs/code changed')
    if (out / 'semantic_annotator_v3_cv_report.json').exists():
        raise FileExistsError('CV already completed; no repeat tuning against evaluation results')
    import os
    os.environ['HF_HUB_OFFLINE'] = '1'; os.environ['TOKENIZERS_PARALLELISM'] = 'false'
    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer
    assert torch.cuda.is_available()
    model_path = ROOT / 'models/_cache/Qwen2.5-1.5B-Instruct'
    tokenizer = AutoTokenizer.from_pretrained(model_path, local_files_only=True)
    model = AutoModelForCausalLM.from_pretrained(model_path, local_files_only=True, torch_dtype=torch.bfloat16).to('cuda')
    model.eval()
    def generate(prompt, max_tokens):
        ids = tokenizer.apply_chat_template([{'role': 'user', 'content': prompt}], add_generation_prompt=True, return_tensors='pt').to('cuda')
        with torch.inference_mode():
            generated = model.generate(input_ids=ids, attention_mask=torch.ones_like(ids), do_sample=False,
                                       max_new_tokens=max_tokens, pad_token_id=tokenizer.eos_token_id)
        return tokenizer.decode(generated[0, ids.shape[1]:], skip_special_tokens=True)
    # 每个请求单独缓存，恢复时不重复调用；缓存绑定冻结配置和完整prompt。
    cache_path = out / 'requests.jsonl'
    cached = read_jsonl(cache_path) if cache_path.exists() else []
    request_lookup = {r['key']: r for r in cached}
    assert len(cached) == len(request_lookup)
    config_hash = sha(out / 'frozen_cv.json')
    def request(key, prompt, max_tokens):
        ph = hashlib.sha256(prompt.encode()).hexdigest()
        if key in request_lookup:
            item = request_lookup[key]
            assert item['prompt_sha256'] == ph and item['config_sha256'] == config_hash
            return item['raw']
        raw = generate(prompt, max_tokens)
        item = {'key': key, 'prompt': prompt, 'prompt_sha256': ph, 'raw': raw,
                'config_sha256': config_hash, 'max_new_tokens': max_tokens}
        with cache_path.open('a', encoding='utf-8') as stream:
            stream.write(json.dumps(item, ensure_ascii=False) + '\n')
        request_lookup[key] = item
        return raw
    records = []; fold_reports = []; lexicon = load(ROOT / 'configs/imagery_lexicon_v1.json')
    rule_predictions = []
    for fold in config['folds']:
        part = []
        for i, rid in enumerate(fold['evaluation_ids'], 1):
            row = lookup[rid]; predictions = {}; raw_semantics = {}; shots = {}
            for d in DIMS:
                shots[d] = [a['id'] for a in fold['anchors'][d]]
                assert set(shots[d]) <= set(fold['calibration_ids']) and rid not in shots[d]
                prompt = semantic_prompt(row['text'], d, [lookup[x] for x in shots[d]], schema)
                raw = request(f'{rid}:semantic:{d}', prompt, 96)
                predictions[d] = normalize(raw, d, schema); raw_semantics[d] = raw
            if any(p['label_valid'] for p in predictions.values()):
                raw_evidence = request(f'{rid}:evidence', evidence_prompt(row['text'], predictions), 320)
            else:
                raw_evidence = '{}'
            evidence = validate_evidence(raw_evidence, row['text'], predictions)
            record = {'id': rid, 'fold': fold['fold'], 'few_shot_ids': shots, 'semantic': predictions,
                'semantic_raw': raw_semantics, 'evidence_raw': raw_evidence, 'evidence': evidence,
                'annotation_version': 'semantic_annotator_v3', 'label_source': 'automatic_development_prediction',
                'model_revision': config['model_revision'], 'llm_repair_used': False}
            part.append(record); records.append(record)
            prelabels = rule_preannotate_record({'id': rid, 'text': row['text'], 'form': row['form']}, lexicon_cfg=lexicon)['annotation']['prelabel']
            rule_predictions.append({'id': rid, 'blocks': {d: prelabels[d] for d in ('imagery', 'density')}, 'error': None})
            print(f'fold {fold["fold"] + 1}/4 record {i}/6 semantic_valid={sum(p["label_valid"] for p in predictions.values())}/4 evidence={evidence["all_dimensions_success"]}', flush=True)
        part_rows = [lookup[rid] for rid in fold['evaluation_ids']]
        result = evaluate(part_rows, part, schema)
        result['fold'] = fold['fold']; fold_reports.append(result)
        save(out / f'fold_{fold["fold"] + 1}_report.json', result)
    aggregate = evaluate(rows, records, schema)
    rule_result = rule_metrics(rows, rule_predictions, schema)['dimensions']
    rules = {d: rule_result[d] for d in ('imagery', 'density')}
    report = {'scope': config['scope'], 'aggregate': aggregate, 'folds': fold_reports, 'rules': rules,
              'gate': gate(aggregate, rules), 'llm_repair_calls': 0,
              'request_count': len(request_lookup), 'evidence_note': 'verbatim protocol success does not establish semantic relevance of evidence',
              'rules_exposure_note': 'fixed lexicon/rules v1.1 evaluated on all 24; historically calibrated on Gold, not independent CV-trained rules'}
    with (out / 'out_of_fold_predictions.jsonl').open('w', encoding='utf-8') as stream:
        for record in records: stream.write(json.dumps(record, ensure_ascii=False) + '\n')
    save(out / 'semantic_annotator_v3_cv_report.json', report)
    print(json.dumps({'gate': report['gate'], 'protocol': aggregate['record_level_protocol'],
        'scores': {d: {k: v for k, v in aggregate['dimensions'][d].items() if k in ('accuracy', 'precision', 'recall', 'f1', 'label_coverage')} for d in DIMS}}, ensure_ascii=False), flush=True)


if __name__ == '__main__':
    main()
