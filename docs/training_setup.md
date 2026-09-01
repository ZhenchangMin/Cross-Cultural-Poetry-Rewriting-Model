# Research Training Environment Setup

This project keeps PyTorch installation separate from `research/requirements.txt` because the correct wheel depends on whether the machine is CPU-only or uses a specific CUDA stack.

## 1. Activate the research environment

```bash
cd /mnt/e/study/Cross-Cultural-Poetry-Rewriting-Model/research
source .venv/bin/activate
```

## 2. Install ordinary Python dependencies

```bash
pip install -r requirements.txt
```

## 3. Install PyTorch for the current machine

### Local CPU smoke tests

```bash
pip install --index-url https://download.pytorch.org/whl/cpu torch
```

This is enough for `scripts/tiny_overfit.py`, which exists to validate the training pipeline rather than benchmark speed.

### GPU training

Do **not** copy the CPU command above to a GPU server. Select the PyTorch build that matches the server's CUDA/driver environment from the official PyTorch installation instructions, then verify:

```bash
python - <<'PY'
import torch
print('torch:', torch.__version__)
print('cuda available:', torch.cuda.is_available())
if torch.cuda.is_available():
    print('device:', torch.cuda.get_device_name(0))
PY
```

## 4. Tiny-overfit checkpoint

Before using the pretrained 1.5B model, run:

```bash
python scripts/tiny_overfit.py
```

This uses a randomly initialized tiny Qwen2 model plus LoRA. Its purpose is to prove the following chain works end-to-end:

```text
TokenizedExample
  -> PyTorch batch
  -> Qwen2 forward
  -> causal-LM loss
  -> loss.backward()
  -> LoRA gradients
  -> optimizer.step()
```

The default pure-LoRA smoke test uses a frozen randomly initialized base model. Because its random frozen output head can keep cross-entropy numerically high even after the correct token becomes top-1, success is defined as:

- final teacher-forced supervised-token accuracy >= 0.95; and
- final loss / initial loss <= 0.90.

The acceptance criterion deliberately checks memorization and optimization rather than requiring an arbitrary near-zero loss that would encourage us to unfreeze components which the real pretrained LoRA baseline intends to keep frozen.

A successful tiny-overfit test is an engineering checkpoint only. It does not measure poetry quality and does not replace later training on human-reviewed Gold data.

## 5. B0 real-training framework

The real baseline is configured by:

```text
research/configs/baseline_qwen_lora.json
```

Default architecture:

```text
Human-reviewed Gold JSONL
  -> PoetryTrainingDataset (Gold gate)
  -> Qwen chat tokenization
  -> dynamic PyTorch batches
  -> Qwen/Qwen2.5-1.5B-Instruct
  -> LoRA adapters
  -> masked causal-LM loss
  -> gradient accumulation / clipping
  -> adapter checkpoints
```

Before Gold data exists, only run the configuration dry-run:

```bash
cd research
python scripts/train_baseline.py --dry-run
```

It should report `ready_for_gold_data` and does not load the 1.5B weights.

When a candidate Gold file arrives, verify the gate before training:

```bash
python scripts/train_baseline.py --dry-run --data path/to/gold.jsonl
```

The current `preannotated_v1.jsonl` is expected to fail this command because its final `style` fields have not been human-reviewed. Do not bypass this validation.

Only after the Gold file passes and a suitable GPU environment is verified should real training be started:

```bash
python scripts/train_baseline.py \
  --data path/to/gold.jsonl \
  --model-path /path/to/Qwen2.5-1.5B-Instruct \
  --device cuda
```

`--model-path` is optional; without it Transformers uses the model ID in the config. A local path is preferred on training servers for reproducibility and to avoid network failures during an experiment.

Checkpoints under `outputs/baseline_qwen_lora/` contain LoRA adapter weights, tokenizer files, and `training_state.json`; they do not duplicate the full base-model weights.

After training, controlled generation uses:

```bash
python scripts/generate_baseline.py \
  --adapter outputs/baseline_qwen_lora/checkpoint-XXXXXX \
  --control path/to/control.json \
  --model-path /path/to/Qwen2.5-1.5B-Instruct \
  --device cuda
```

The control JSON only needs the same `form` and `style` structure used by B0 prompts. Formal evaluation and constraint-based reranking remain later stages; this first baseline isolates whether explicit style controls can be learned at all.
