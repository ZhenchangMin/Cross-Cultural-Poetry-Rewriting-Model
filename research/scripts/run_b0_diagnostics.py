"""Bounded real-model engineering tests, never the long B0 pilot experiments."""
import argparse
from collections import Counter
from copy import deepcopy
import gc
import json
import os
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.training.pilot_protocol import sha, generation_metrics, sanity_pass, load_pilot_dataset
from src.data.dataset import record_to_example
from src.data.tokenization import encode_training_example, collate_tokenized_examples


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('phase', choices=['smoke', 'overfit'])
    args = parser.parse_args()
    root = ROOT / 'outputs/b0_training_pilot_20260926'
    load = lambda p: json.loads(p.read_text(encoding='utf-8'))
    preflight = load(root / 'preflight.json'); protocol = load(root / 'protocol.json')
    if not preflight['suitable']: raise ValueError('Preflight failed: no CPU fallback')
    for path, digest in protocol['protected_inputs'].items():
        if sha(ROOT / path) != digest: raise ValueError('Frozen data changed: ' + path)
    if args.phase == 'overfit' and not load(root / 'smoke_not_experiment_result/result.json')['success']:
        raise ValueError('Smoke must pass before overfit sanity')
    out = root / (args.phase + '_not_experiment_result')
    out.mkdir(exist_ok=False)
    def save(name, value):
        (out / name).write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    os.environ['HF_HUB_OFFLINE'] = '1'; os.environ['TOKENIZERS_PARALLELISM'] = 'false'
    import torch
    from transformers import AutoTokenizer, AutoModelForCausalLM
    from peft import PeftModel
    from src.training.config import load_baseline_config
    from src.training.model_factory import apply_lora, trainable_parameter_counts
    assert torch.cuda.is_available() and torch.cuda.is_bf16_supported()
    torch.manual_seed(protocol['seed']); torch.cuda.manual_seed_all(protocol['seed'])
    config = load(root / 'proposed_b0_B.json')
    config['data']['gold_path'] = protocol['smoke_gold_path']
    dataset = load_pilot_dataset(config, ROOT, training=True)
    examples = [record_to_example(x['record'], source=x['source']) for x in load(root / 'sanity_subset.json')]
    model_path = ROOT / 'models/_cache/Qwen2.5-1.5B-Instruct'
    tokenizer = AutoTokenizer.from_pretrained(model_path, local_files_only=True)
    tokenizer.pad_token = tokenizer.eos_token
    tokenizer.padding_side = 'right'
    length_audit = [len(encode_training_example(tokenizer, example, max_length=10000).input_ids) for example in load_pilot_dataset(load(root / 'proposed_b0_B.json'), ROOT, training=False)]
    save('token_length_audit.json', {'records': len(length_audit), 'max': max(length_audit), 'max_length': 512,
                                   'would_truncate': sum(n > 512 for n in length_audit)})
    if max(length_audit) > 512: raise ValueError('Do not silently truncate pilot targets')
    def batch(example):
        encoded = encode_training_example(tokenizer, example, max_length=512)
        assert not encoded.truncated
        return {k: torch.tensor(v, device='cuda') for k, v in collate_tokenized_examples([encoded], pad_token_id=tokenizer.pad_token_id).items()}
    def new_model(adapter=None):
        base = AutoModelForCausalLM.from_pretrained(model_path, local_files_only=True, torch_dtype=torch.bfloat16)
        if adapter:
            model = PeftModel.from_pretrained(base, adapter, is_trainable=False)
        else:
            base.config.use_cache = False
            base.gradient_checkpointing_enable(gradient_checkpointing_kwargs={'use_reentrant': False})
            model = apply_lora(base, load_baseline_config(root / 'proposed_b0_B.json'))
        return model.to('cuda')
    def teacher_metrics(model):
        model.eval(); total_loss = correct = tokens = 0
        with torch.inference_mode(), torch.autocast('cuda', dtype=torch.bfloat16):
            for ex in examples:
                b = batch(ex); result = model(**b)
                labels = b['labels'][:, 1:]; mask = labels != -100; n = int(mask.sum())
                total_loss += float(result.loss) * n
                correct += int(((result.logits[:, :-1].argmax(-1) == labels) & mask).sum())
                tokens += n
        return {'loss': total_loss / tokens, 'token_accuracy': correct / tokens, 'supervised_tokens': tokens}
    def generate(model, limit=None):
        model.eval(); samples = []
        for ex in examples[:limit]:
            ids = tokenizer.apply_chat_template([{'role': 'user', 'content': ex.prompt_text}], add_generation_prompt=True, return_tensors='pt').to('cuda')
            with torch.inference_mode(), torch.autocast('cuda', dtype=torch.bfloat16):
                generated = model.generate(input_ids=ids, attention_mask=torch.ones_like(ids), do_sample=False,
                    max_new_tokens=128, pad_token_id=tokenizer.pad_token_id, use_cache=True)
            output = tokenizer.decode(generated[0, ids.shape[1]:], skip_special_tokens=True)
            samples.append({'id': ex.id, 'source': ex.source, 'prompt': ex.prompt_text, 'target': ex.target_text,
                            'output': output, 'metrics': generation_metrics(output, ex.target_text, ex.form)})
        return samples
    try:
        model = new_model()
        trainable, total = trainable_parameter_counts(model)
        assert 0 < trainable < total and all('lora_' in name for name, p in model.named_parameters() if p.requires_grad)
        initial = teacher_metrics(model)
        initial_generations = generate(model)
        save('initial_generation.json', initial_generations)
        phase_smoke = args.phase == 'smoke'
        steps = protocol['smoke_optimizer_steps'] if phase_smoke else protocol['overfit_max_optimizer_steps']
        accumulation = protocol['smoke_gradient_accumulation'] if phase_smoke else protocol['overfit_gradient_accumulation']
        lr = config['training']['learning_rate'] if phase_smoke else protocol['overfit_learning_rate']
        optimizer = torch.optim.AdamW([p for p in model.parameters() if p.requires_grad], lr=lr, weight_decay=0.)
        rng = torch.Generator().manual_seed(protocol['seed'])
        weights = torch.tensor(dataset.sampling_weights, dtype=torch.double)
        torch.cuda.reset_peak_memory_stats()
        trained_sources = Counter(); trained_ids = []; history = []; checks = []
        training_seconds = 0.; processed_tokens = 0; final = initial; generations = initial_generations
        for step in range(1, steps + 1):
            model.train(); optimizer.zero_grad(set_to_none=True); losses = []
            # 小样本overfit固定无dropout；smoke沿用混合Dataset的0.1配置。
            if phase_smoke: indices = torch.multinomial(weights, accumulation, replacement=True, generator=rng).tolist()
            else: indices = [((step - 1) * accumulation + j) % len(examples) for j in range(accumulation)]
            torch.cuda.synchronize(); started = time.perf_counter()
            for index in indices:
                ex = dataset[index] if phase_smoke else examples[index]
                trained_ids.append(ex.id); trained_sources[ex.source] += 1
                if ex.id in protocol['reserved_eval_ids']: raise ValueError('Reserved evaluation leaked')
                b = batch(ex); processed_tokens += int(b['attention_mask'].sum())
                with torch.autocast('cuda', dtype=torch.bfloat16):
                    result = model(**b); loss = result.loss
                if not torch.isfinite(loss): raise ValueError('Nonfinite loss')
                losses.append(float(loss.detach())); (loss / accumulation).backward()
                del b, result, loss
            grad_norm = torch.nn.utils.clip_grad_norm_([p for p in model.parameters() if p.requires_grad], 1.)
            if not torch.isfinite(grad_norm) or float(grad_norm) <= 0: raise ValueError('Invalid/zero adapter gradient')
            optimizer.step(); torch.cuda.synchronize()
            elapsed = time.perf_counter() - started; training_seconds += elapsed
            item = {'optimizer_step': step, 'mean_training_loss': sum(losses) / len(losses), 'seconds': elapsed,
                    'gradient_norm_before_clip': float(grad_norm)}
            history.append(item)
            with (out / 'steps.jsonl').open('a', encoding='utf-8') as stream: stream.write(json.dumps(item) + '\n')
            print(f'{args.phase} optimizer {step}/{steps} loss={item["mean_training_loss"]:.4f} seconds={elapsed:.2f}', flush=True)
            if step == steps or (not phase_smoke and step % protocol['overfit_check_every_optimizer_steps'] == 0):
                final = teacher_metrics(model); generations = generate(model)
                check = {'optimizer_step': step, 'teacher_forced': final,
                         'generation_exact_matches': sum(x['metrics']['character_exact_match'] for x in generations)}
                checks.append(check); save('checks.json', checks)
                print('SANITY_CHECK', json.dumps(check), flush=True)
                if not phase_smoke and sanity_pass(initial, final, generations): break
        peak_allocated = torch.cuda.max_memory_allocated() / 2**20
        peak_reserved = torch.cuda.max_memory_reserved() / 2**20
        adapter_changed = any(bool(torch.count_nonzero(p).item()) for n, p in model.named_parameters() if 'lora_B' in n)
        assert adapter_changed
        checkpoint = out / 'adapter_smoke_not_experiment_result'
        model.save_pretrained(checkpoint); tokenizer.save_pretrained(checkpoint)
        save('checkpoint_metadata.json', {'purpose': 'smoke / not experiment result' if phase_smoke else 'tiny overfit sanity / not experiment result',
            'optimizer_steps': len(history), 'base_model_revision': preflight['model_revision'],
            'trainable_parameters': trainable, 'total_parameters': total, 'trainable_ratio': trainable / total,
            'checkpoint_files': {p.name: sha(p) for p in checkpoint.iterdir() if p.is_file()}})
        save('final_generation_before_reload.json', generations)
        del optimizer, model
        gc.collect(); torch.cuda.empty_cache()
        reloaded = new_model(checkpoint)
        reloaded_metrics = teacher_metrics(reloaded)
        reloaded_generations = generate(reloaded)
        loss_difference = abs(reloaded_metrics['loss'] - final['loss'])
        outputs_match = all(a['output'] == b['output'] for a, b in zip(generations, reloaded_generations))
        save('generation_after_reload.json', reloaded_generations)
        reload_ok = loss_difference <= .001 and outputs_match
        success = reload_ok and adapter_changed and all(x['metrics']['nonempty'] for x in reloaded_generations)
        if not phase_smoke: success = success and sanity_pass(initial, final, reloaded_generations)
        report = {'purpose': 'engineering diagnostic only; not B0 experiment result', 'success': success,
            'phase': args.phase, 'initial_teacher_forced': initial, 'final_teacher_forced': final,
            'first_training_batch_loss': history[0]['mean_training_loss'], 'last_training_batch_loss': history[-1]['mean_training_loss'],
            'optimizer_steps': len(history), 'gradient_accumulation': accumulation, 'learning_rate': lr,
            'trainable_parameters': trainable, 'total_parameters': total, 'trainable_ratio': trainable / total,
            'peak_allocated_mib': peak_allocated, 'peak_reserved_mib': peak_reserved,
            'training_seconds': training_seconds, 'tokens_per_training_second': processed_tokens / training_seconds,
            'mean_optimizer_step_seconds': training_seconds / len(history),
            'trained_source_counts': dict(trained_sources), 'unique_trained_ids': sorted(set(trained_ids)),
            'reserved_eval_leakage': False, 'checkpoint': str(checkpoint.relative_to(ROOT)),
            'checkpoint_reload_ok': reload_ok, 'reload_loss_abs_difference': loss_difference, 'reload_generation_identical': outputs_match,
            'generation_exact_matches': sum(x['metrics']['character_exact_match'] for x in reloaded_generations),
            'generation_examples': len(reloaded_generations), 'long_pilot_training_started': False}
        save('result.json', report)
        print('DIAGNOSTIC_RESULT', json.dumps(report), flush=True)
        if not success: raise RuntimeError('Diagnostic gate failed; do not launch long pilot')
    except Exception as exc:
        save('failure.json', {'type': type(exc).__name__, 'message': str(exc), 'long_pilot_training_started': False})
        raise


if __name__ == '__main__': main()
