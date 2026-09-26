"""Fixed evaluation: completion-only teacher forcing and rule-based generation proxies."""
from contextlib import nullcontext
from src.training.pilot_protocol import generation_metrics
from src.data.preannotate_style import imagery_prelabel, density_prelabel
from src.data.tokenization import encode_training_example, collate_tokenized_examples


def make_batch(examples, tokenizer, max_length, device):
    import torch
    encoded = [encode_training_example(tokenizer, ex, max_length=max_length) for ex in examples]
    if any(x.truncated for x in encoded): raise ValueError('Pilot never silently truncates controls/targets')
    return {k: torch.tensor(v, device=device) for k, v in collate_tokenized_examples(encoded, pad_token_id=tokenizer.pad_token_id).items()}


def teacher_counts(logits, labels):
    shifted = labels[:, 1:]; mask = shifted != -100
    return int(((logits[:, :-1].argmax(-1) == shifted) & mask).sum()), int(mask.sum())


def score_generations(samples, examples, lexicon):
    tp = fp = fn = density_correct = forms = 0; details = []
    if len(samples) != len(examples) or not examples: raise ValueError('All evaluation records required')
    for output, ex in zip(samples, examples):
        metrics = generation_metrics(output, ex.target_text, ex.form); valid = metrics['form_compliance']
        image = imagery_prelabel(output, lexicon) if valid else {'value': []}
        density = density_prelabel(output, image, lexicon)['value'] if valid else None
        predicted = set(image['value']); expected = set(ex.style['imagery'])
        tp += len(predicted & expected); fp += len(predicted - expected); fn += len(expected - predicted)
        forms += valid; density_correct += density == ex.style['density']
        details.append({'id': ex.id, 'prompt': ex.prompt_text, 'target': ex.target_text, 'output': output,
                        'requested_style': dict(ex.style), 'metrics': metrics,
                        'imagery_rule_prediction': image['value'], 'density_rule_prediction': density})
    return {'records': len(examples), 'form_compliance': forms / len(examples),
            'imagery_micro_precision': tp / max(1, tp + fp), 'imagery_micro_recall': tp / max(1, tp + fn),
            'imagery_micro_F1': 2 * tp / max(1, 2 * tp + fp + fn), 'density_accuracy': density_correct / len(examples),
            'rule_metrics_are_proxies': True, 'semantic_style_scores': None, 'samples': details}


def evaluate(model, tokenizer, examples, config, lexicon, device='cuda'):
    import torch
    was_training = model.training
    cpu_rng = torch.get_rng_state(); cuda_rng = torch.cuda.get_rng_state_all() if torch.cuda.is_available() else None
    total_loss = correct = tokens = 0; samples = []
    def autocast(): return torch.autocast('cuda', dtype=torch.bfloat16) if str(device).startswith('cuda') else nullcontext()
    try:
        model.eval()
        with torch.inference_mode(), autocast():
            for ex in examples:
                batch = make_batch([ex], tokenizer, config['model']['max_length'], device)
                result = model(**batch); hit, n = teacher_counts(result.logits, batch['labels'])
                if not n: raise ValueError('No evaluation target tokens')
                total_loss += float(result.loss) * n; correct += hit; tokens += n
                ids = tokenizer.apply_chat_template([{'role': 'user', 'content': ex.prompt_text}], tokenize=True, add_generation_prompt=True)
                ids = torch.tensor([ids], device=device)
                output = model.generate(input_ids=ids, attention_mask=torch.ones_like(ids),
                    max_new_tokens=config['generation']['max_new_tokens'], do_sample=False, num_beams=1,
                    pad_token_id=tokenizer.pad_token_id, eos_token_id=tokenizer.eos_token_id, use_cache=True)
                samples.append(tokenizer.decode(output[0, ids.shape[1]:], skip_special_tokens=True))
        return {'eval_loss': total_loss / tokens, 'eval_token_accuracy': correct / tokens,
                'supervised_tokens': tokens, 'generation': score_generations(samples, examples, lexicon)}
    finally:
        model.train(was_training); torch.set_rng_state(cpu_rng)
        if cuda_rng is not None: torch.cuda.set_rng_state_all(cuda_rng)
