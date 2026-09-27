"""Read-only result aggregation for the frozen B0 comparison; never loads a model."""
from collections import Counter
import hashlib
import json
import math
from pathlib import Path


def load(path): return json.loads(Path(path).read_text(encoding='utf-8'))

def read_arm(directory, runtime):
    directory = Path(directory)
    history = [json.loads(line) for line in (directory / 'history.jsonl').read_text(encoding='utf-8').splitlines()]
    if [x['step'] for x in history] != list(range(101)): raise ValueError('Require exactly steps 0..100')
    done = load(directory / 'completion.json')
    if done['optimizer_steps'] != 100 or not runtime['success']: raise ValueError('Incomplete experiment')
    evaluations = {step: load(directory / f'evaluation_{step:04d}.json') for step in range(0,101,10)}
    train = history[1:]; config = load(directory / 'config.json')
    for row in train:
        if not math.isfinite(row['train_loss']): raise ValueError('Nonfinite training loss')
        if row['learning_rate'] != config['training']['learning_rate']: raise ValueError('Learning rate changed')
        if sum(row['step_sources'].values()) != 8: raise ValueError('Effective batch changed')
    counts = Counter()
    for row in train:
        counts.update(row['step_sources'])
        if dict(counts) != row['source_exposures']: raise ValueError('Exposure accounting mismatch')
    if dict(counts) != done['source_exposures']: raise ValueError('Completion counts mismatch')
    manifest = load(directory / 'data_manifest.json'); sources = {x['id']:x['source'] for x in manifest['examples']}
    plan = load(directory / 'sampling_plan.json')
    if len(plan) != 100 or any(len(x) != 8 for x in plan): raise ValueError('Sampling plan budget mismatch')
    if Counter(sources[i] for step in plan for i in step) != counts: raise ValueError('Sampling differs from plan')
    if Counter(i for step in plan for i in step) != Counter(train[-1]['id_exposures']): raise ValueError('ID exposures differ from plan')
    for step, evaluation in evaluations.items():
        if evaluation['generation']['records'] != 6 or len(evaluation['generation']['samples']) != 6: raise ValueError('Missing evaluation poems')
        if evaluation['generation']['semantic_style_scores'] is not None: raise ValueError('Forbidden semantic scores')
        if not all(math.isfinite(evaluation[k]) for k in ('eval_loss','eval_token_accuracy')): raise ValueError('Nonfinite evaluation')
        if any(history[step][k] != evaluation[k] for k in ('eval_loss','eval_token_accuracy')): raise ValueError('Evaluation log mismatch')
    final = evaluations[100]; generation = final['generation']
    metrics = {k:final[k] for k in ('eval_loss','eval_token_accuracy')}
    metrics.update({k:generation[k] for k in ('form_compliance','imagery_micro_precision','imagery_micro_recall','imagery_micro_F1','density_accuracy')})
    metrics.update(peak_vram_gib=runtime['peak_allocated_bytes']/1024**3, wall_clock_seconds=runtime['wall_clock_seconds'],
                   training_seconds=sum(x['train_step_seconds'] for x in train), processed_tokens=train[-1]['processed_tokens'])
    return {'metrics':metrics, 'source_counts':dict(counts), 'source_ratios':{k:v/800 for k,v in counts.items()},
            'history':history, 'evaluations':evaluations, 'runtime':runtime}


def compare_generations(a, b, gold):
    a = a['generation']['samples']; b = b['generation']['samples']
    if [x['id'] for x in a] != [x['id'] for x in b] or len(a) != 6: raise ValueError('Evaluation IDs/order mismatch')
    result = []
    for x,y in zip(a,b):
        row = gold[x['id']]
        for sample in (x,y):
            if sample['target'] != row['text'] or sample['requested_style'] != row['style']: raise ValueError('Evaluation controls/reference changed')
        entry = {'id':x['id'], 'target_controls':{'form':row['form'], **row['style']}, 'reference_poem':row['text']}
        for name,sample in (('B0-A',x),('B0-B',y)):
            predicted=set(sample['imagery_rule_prediction']); target=set(row['style']['imagery'])
            entry[name]={'generation':sample['output'], 'form_compliance':sample['metrics']['form_compliance'],
                'imagery_prediction':sorted(predicted), 'imagery_matched':sorted(predicted & target),
                'imagery_missing':sorted(target-predicted), 'imagery_extra':sorted(predicted-target),
                'imagery_F1':2*len(predicted & target)/max(1,len(predicted)+len(target)),
                'density_prediction':sample['density_rule_prediction'], 'density_match':sample['density_rule_prediction']==row['style']['density']}
        result.append(entry)
    return result


def checkpoint_inventory(directory):
    from safetensors import safe_open
    inventory=[]
    for step in range(10,101,10):
        path=Path(directory)/f'adapter_step_{step:04d}'/'adapter_model.safetensors'
        with safe_open(path, framework='np') as tensors:
            keys=list(tensors.keys())
            if not keys or any('lora_' not in key for key in keys): raise ValueError('Not an adapter-only checkpoint')
            shapes={key:tensors.get_slice(key).get_shape() for key in keys}
        inventory.append({'step':step,'path':str(path),'bytes':path.stat().st_size,
                          'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'tensor_count':len(keys),
                          'parameter_count':sum(math.prod(shape) for shape in shapes.values()),'safetensors_structure_valid':True})
    return inventory
