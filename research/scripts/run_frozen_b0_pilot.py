"""Explicit opt-in, fresh-base B0 pilot; defaults to audit only. Never resumes smoke adapters."""
import argparse
from collections import Counter
import json
import os
from pathlib import Path
import sys
import time
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.training.frozen_pilot import audit_config, read_json, write_json, sampling_plan
from src.training.pilot_protocol import load_pilot_dataset, sha


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('config', type=Path)
    parser.add_argument('--execute', action='store_true', help='Explicitly start the frozen 100-step pilot')
    args = parser.parse_args()
    config_path = args.config if args.config.is_absolute() else ROOT / args.config
    config, split, audit = audit_config(config_path, ROOT)
    print(json.dumps({'audit': audit, 'execute': args.execute}, ensure_ascii=False), flush=True)
    if not args.execute: return
    os.environ['HF_HUB_OFFLINE'] = '1'; os.environ['CUBLAS_WORKSPACE_CONFIG'] = ':4096:8'
    import torch
    from transformers import AutoTokenizer, AutoModelForCausalLM
    from peft import LoraConfig, get_peft_model, TaskType, PeftModel
    from src.training.pilot_evaluation import make_batch, evaluate
    from src.data.dataset import PoetryTrainingDataset
    if not torch.cuda.is_available() or not torch.cuda.is_bf16_supported(): raise RuntimeError('Requires BF16 CUDA; no CPU fallback')
    torch.use_deterministic_algorithms(True)
    torch.backends.cuda.matmul.allow_tf32 = False
    torch.backends.cudnn.benchmark = False
    t = config['training']; torch.manual_seed(t['seed']); torch.cuda.manual_seed_all(t['seed'])
    model_path = ROOT / config['model']['local_path']
    if sha(model_path / 'model.safetensors') != config['model']['weights_sha256']: raise ValueError('Base weights changed')
    dataset = load_pilot_dataset(config, ROOT, training=True)
    evaluation = PoetryTrainingDataset(ROOT / split['eval_path'], schema_path=ROOT / 'configs/style_schema.json', training=False)
    examples = list(evaluation)
    lexicon = read_json(ROOT / 'configs/imagery_lexicon_v1.json')
    tokenizer = AutoTokenizer.from_pretrained(model_path, local_files_only=True)
    tokenizer.pad_token = tokenizer.eos_token; tokenizer.padding_side = 'right'
    # Audit complete controls before any stochastic dropout can hide overlength input.
    from src.data.tokenization import encode_training_example
    for ex in list(load_pilot_dataset(config, ROOT, training=False)) + examples:
        if encode_training_example(tokenizer, ex, max_length=config['model']['max_length']).truncated:
            raise ValueError('Overlength example: ' + ex.id)
    out = ROOT / config['output_dir']; out.mkdir(parents=True, exist_ok=False)
    write_json(out / 'config.json', config); write_json(out / 'split.json', split)
    write_json(out / 'data_manifest.json', dataset.manifest()); write_json(out / 'isolation.json', audit)
    base = AutoModelForCausalLM.from_pretrained(model_path, local_files_only=True, torch_dtype=torch.bfloat16, attn_implementation='eager')
    base.config.use_cache = False
    base.gradient_checkpointing_enable(gradient_checkpointing_kwargs={'use_reentrant': False})
    lora = config['lora']
    model = get_peft_model(base, LoraConfig(task_type=TaskType.CAUSAL_LM, r=lora['r'], lora_alpha=lora['alpha'],
                          lora_dropout=lora['dropout'], target_modules=lora['target_modules'], bias='none')).to('cuda')
    if not all('lora_' in name for name, p in model.named_parameters() if p.requires_grad): raise ValueError('Base parameters unexpectedly trainable')
    optimizer = torch.optim.AdamW([p for p in model.parameters() if p.requires_grad], lr=t['learning_rate'], weight_decay=t['weight_decay'])
    plan = sampling_plan(dataset.sampling_weights, t['max_optimizer_steps'], t['batch_size'], t['gradient_accumulation_steps'], t['seed'])
    write_json(out / 'sampling_plan.json', [[dataset[i].id for i in step] for step in plan])
    counts = Counter(); exposures = Counter(); tokens = 0; torch.cuda.reset_peak_memory_stats()
    def evaluation_at(step):
        result = evaluate(model, tokenizer, examples, config, lexicon)
        write_json(out / f'evaluation_{step:04d}.json', result)
        return {k: result[k] for k in ('eval_loss', 'eval_token_accuracy')}
    with (out / 'history.jsonl').open('w', encoding='utf-8') as log:
        log.write(json.dumps({'step': 0, **evaluation_at(0)}) + '\n'); log.flush()
        for step, indices in enumerate(plan, 1):
            # Dropout clock is optimizer step, not source-dependent dataset epoch.
            dataset.set_epoch(step - 1); model.train(); optimizer.zero_grad(set_to_none=True)
            losses = []; step_counts = Counter(); torch.cuda.synchronize(); started = time.perf_counter()
            for start in range(0, len(indices), t['batch_size']):
                batch_examples = [dataset[i] for i in indices[start:start + t['batch_size']]]
                batch = make_batch(batch_examples, tokenizer, config['model']['max_length'], 'cuda')
                with torch.autocast('cuda', dtype=torch.bfloat16): loss = model(**batch).loss
                if not torch.isfinite(loss): raise RuntimeError('Nonfinite training loss')
                losses.append(float(loss.detach())); (loss / t['gradient_accumulation_steps']).backward()
                tokens += int(batch['attention_mask'].sum())
                for ex in batch_examples: counts[ex.source] += 1; step_counts[ex.source] += 1; exposures[ex.id] += 1
            torch.nn.utils.clip_grad_norm_(model.parameters(), t['max_grad_norm'], error_if_nonfinite=True)
            optimizer.step(); optimizer.zero_grad(set_to_none=True); torch.cuda.synchronize()
            row = {'step': step, 'train_loss': sum(losses) / len(losses), 'learning_rate': optimizer.param_groups[0]['lr'],
                   'step_sources': dict(step_counts), 'source_exposures': dict(counts), 'id_exposures': dict(exposures),
                   'source_fractions': {k: v / sum(counts.values()) for k, v in counts.items()},
                   'processed_tokens': tokens, 'train_step_seconds': time.perf_counter() - started,
                   'peak_allocated_bytes': torch.cuda.max_memory_allocated()}
            if step % t['eval_every_steps'] == 0 or step == t['max_optimizer_steps']: row.update(evaluation_at(step))
            if step % t['save_every_steps'] == 0 or step == t['max_optimizer_steps']:
                if not isinstance(model, PeftModel): raise TypeError('Only PEFT adapter checkpoints allowed')
                checkpoint = out / f'adapter_step_{step:04d}'; model.save_pretrained(checkpoint, safe_serialization=True)
                write_json(checkpoint / 'pilot_metadata.json', {'step': step, 'checkpoint_type': 'adapter_only',
                    'resume_supported': False, 'base_weights_sha256': config['model']['weights_sha256'], 'source_exposures': dict(counts)})
            log.write(json.dumps(row) + '\n'); log.flush(); print(json.dumps(row), flush=True)
    write_json(out / 'completion.json', {'optimizer_steps': len(plan), 'source_exposures': dict(counts), 'formal_pilot': True})


if __name__ == '__main__': main()
