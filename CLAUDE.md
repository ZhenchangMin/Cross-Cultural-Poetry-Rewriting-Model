# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Rules
Start with calling me "Min" before any other content. Always follow the instructions in this file.

When encountering uncertain code design problems, always ask Min for clarification before proceeding. Do not make assumptions about requirements or constraints.


## Environment

All Python work must run in **WSL** (the `.venv` is Linux-style, created in WSL):

```bash
cd /mnt/e/study/Cross-Cultural-Poetry-Rewriting-Model/research
source .venv/bin/activate
```

All commands below assume you are inside `research/` with the venv activated.


## Architecture

### Trinity Model (三位一体)

The core innovation is injecting two learned prefix tokens into Qwen's input space instead of translating source text:

```
Source poem (Russian/Korean/Chinese)
    ↓ XLM-R tokenizer
SemanticEncoder (frozen XLM-R-base)  →  [CLS] vector [B, 768]
    ↓
ProjectionMLP (768 → 1536, trainable)  →  semantic prefix [B, 1536]

CultureEmbedding (lookup table, trainable)  →  culture prefix [B, 1536]

Stack → prefix_embeds [B, 2, 1536]
    ↓ concat with Qwen token embeddings
Qwen2.5-1.5B + LoRA  →  七律 output
```

**Why this works for zero-shot cross-lingual transfer:** XLM-R is multilingual — Russian/Korean semantic vectors land near their Chinese equivalents in the same embedding space. Training only on Chinese self-reconstruction is sufficient for the model to handle Russian/Korean inputs at inference.

**Trainable parameters only:**
- `ProjectionMLP` (~1.5M params)
- `CultureEmbedding` (tiny)
- Qwen LoRA adapters (~7–20M params, `r=16`)

**Frozen:** XLM-R (~280M) and Qwen base weights (~1.5B).

### Key Files

| File | Role |
|------|------|
| `src/models/rewriter.py` | `TrinityRewriter` — assembles all components, defines `forward()` and `save/load_trainable()` |
| `src/models/semantic_encoder.py` | Wraps frozen XLM-R, outputs `[CLS]` vector |
| `src/models/projection.py` | `ProjectionMLP`: 768→1536 |
| `src/models/culture_embedding.py` | `CultureEmbedding` + `CULTURE_REGISTRY` (add new poem styles here) |
| `src/train_trinity.py` | Training loop with gradient accumulation, cosine LR schedule, val loss checkpointing |
| `src/generate_trinity.py` | Inference: single text, batch JSONL, or interactive mode |
| `src/constraints/scorer_qilu.py` | Scores generated poems on meter + rhyme; used to pick best candidate |
| `configs/train_trinity_config.yaml` | All hyperparameters — edit here, not in code |

### Training Task: Self-Reconstruction

Each training sample: input is a qilu poem tokenized by XLM-R → model must regenerate the same poem. Labels use `-100` for system/user prompt positions (not counted in loss), only the assistant response (the poem) is supervised.

### Data Flow

```
data/raw/qilu_corpus.jsonl          (collected by collect_corpus.py)
    ↓ build_dataset_trinity.py
data/processed/trinity/
    train.jsonl / val.jsonl / test.jsonl
    ↓ train_trinity.py
outputs/trinity/
    final/       projection.pt + culture_embedding.pt + lora_adapter/
    best/        best validation checkpoint
    checkpoint-N/
```

### Adding a New Culture/Poem Style

1. Add entry to `CULTURE_REGISTRY` in `src/models/culture_embedding.py`
2. Update `num_cultures` in `configs/train_trinity_config.yaml`
3. Add training samples with the new `"culture"` field in JSONL data

### Baseline vs Trinity

`train.py` / `generate.py` are the **baseline** (requires DeepSeek translation API). Keep them for comparison — do not modify. All new work goes into the `*_trinity.py` files.
