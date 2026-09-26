# B0 Pilot frozen protocol — 2026-09-26

Status: **prepared only; formal Pilot has not started**. No real-model smoke was repeated. Annotation systems and Gold/Silver labels are unchanged.

## Data and interpretation

The canonical 24 human Gold records are partitioned with seed `20260926` into 18 training and 6 evaluation records. Both arms use exactly the same evaluation file. Source records, annotations, and human provenance are copied without edits.

| Partition | qijue7 | qilv7 | Total |
|---|---:|---:|---:|
| Training | 10 | 8 | 18 |
| Evaluation | 3 | 3 | 6 |

The selector exhaustively compares all 3+3 evaluation subsets, minimizing inverse-frequency style-label imbalance while retaining every observed label in training. Seeded record order breaks equal-score ties. It does not inspect model results. Exact IDs and all label counts are in `research/configs/b0_pilot_split.json`; immutable copies are in `research/data/processed/b0_pilot_20260926/`.

Evaluation covers diction plain/refined/ornate = 1/4/1, expression direct/balanced/implicit = 2/3/1, energy gentle/balanced/vigorous = 3/2/1, density sparse/medium/dense = 1/2/3. Every observed imagery and emotion category appears in both partitions. Classes absent from the original Gold remain absent.

This is a **development holdout**, not a historically unseen test: all 24 Gold have participated in earlier annotation development, and earlier engineering diagnostics used some Gold. Formal A/B must each initialize fresh LoRA from the original pretrained base; no smoke/overfit adapters are reused. Six evaluation records provide a very uncertain performance estimate; one poem changes accuracy by 16.7 percentage points. The final step-100 adapter is the predetermined comparison checkpoint, with no best-checkpoint selection on these six records.

## Matched budget

| Setting | B0-A | B0-B |
|---|---|---|
| Training source | 18 Gold | 18 Gold + 825 Partial Silver |
| Source probability | Gold 1.0 | Gold 0.3 / Silver 0.7 |
| Optimizer steps | 100 | 100 |
| Microbatch / accumulation / effective batch | 1 / 8 / 8 | 1 / 8 / 8 |
| Learning rate / scheduler / weight decay | 0.0002 / constant / 0 | same |
| Max gradient norm | 1 | 1 |
| Precision / max length | BF16 / 512 | same |
| LoRA rank / alpha / dropout | 16 / 32 / 0.05 | same |
| Control dropout | 0.1 | 0.1 |
| Seed | 20260926 | 20260926 |
| Evaluation / adapter-save cadence | every 10 updates | same |
| Decoding | greedy, one beam, max 128 new tokens | same |

LoRA targets q/k/v/o projections and gate/up/down projections. Attention implementation is eager; deterministic Torch operations are required (unsupported nondeterministic operations fail). Model weights are reused locally and checked by SHA256. No remote model download occurs.

The existing smoke measured about 3.20 seconds/update with about 3.6 GiB allocated memory on RTX 4060 Laptop 8GB. Therefore 100 updates is a conservative first budget, approximately 5.3 minutes of training operations per arm, plus loading, evaluation, and checkpoint overhead. This is an estimate, not a new measurement; deterministic eager attention and different input lengths can change runtime.

Each arm makes exactly 800 replacement draws, without epoch-boundary tail updates. A draws Gold 800 times. The frozen Python RNG sampling algorithm and seed produce B draws of **232 Gold / 568 Silver (29% / 71%)**. These are planned counts, not completed training exposures. Per-record weight is source mass divided by source size. Updates/effective batch/hyperparameters match, but exact token FLOPs and wall time need not match because poems and prompts have different lengths. Log processed token counts and step time to make this visible.

Control dropout uses `(seed, optimizer_step-1, record ID, dimension)` so it follows the same update clock in both arms. Form is always retained. Evaluation is constructed separately with training=false; all seven controls remain available and no evaluation item is ever sampled.

## Fixed evaluation

At step 0 and steps 10,20,...,100, evaluate all six records:

- Completion-token-weighted causal loss and shifted-token accuracy; prompt/padding labels are excluded. Completion includes the chat-template assistant terminator.
- Deterministic greedy generation from each complete Gold control prompt.
- Form compliance checks four/eight seven-character lines, not tonal prosody or rhyme.
- Imagery micro precision/recall/F1 and density accuracy use unchanged lexicon/rule v1.1 against requested Gold controls. These are rule-based controllability proxies, not independent poetry-quality truth. Invalid-form outputs receive empty imagery and null density and remain in all-six accounting.
- No emotion/diction/expression/energy automatic scores. Save prompts, requested controls, targets and raw generations for later analysis; no new human-review tasks are created.

Evaluation restores training mode and CPU/CUDA RNG state. Per-update JSONL logs contain loss, learning rate, step and cumulative source exposures, ID exposures, source fractions, processed tokens, update time and peak allocated VRAM. Adapter-only checkpoints are saved every ten updates; base weights are never re-saved. They are inference checkpoints, not resumable optimizer-state checkpoints. Existing output directories cannot be overwritten.

## Fail-closed isolation

Before tokenizer or model loading, audit both arms: frozen config/code/data hashes; exact 18/6 partition and copied record contents; stage validation; human/Silver provenance; disjoint train/eval IDs and normalized Chinese text; transitive known variant groups; exclusion of unresolved and high-severity quality-flag records (including source fragments). Silver is included in the train/eval audit. Both actual configurations passed: 843 eligible training records, six evaluation records, zero ID/text/variant/prohibited overlaps.

`research/configs/b0_pilot_freeze.json` binds configs, split, data and runtime code hashes. The freeze builder refuses silent regeneration. Changing the protocol requires an explicit new protocol version and review, not bypassing hash checks.

## Entrypoint

From `research/`, the following performs audit only and imports no Torch/model runtime:

```sh
python scripts/run_frozen_b0_pilot.py configs/b0_pilot_gold_only.json
python scripts/run_frozen_b0_pilot.py configs/b0_pilot_gold_partial_silver.json
```

The runner has an explicit `--execute` opt-in for a later authorized turn. It was **not used** in this preparation. Older epoch-based configs and diagnostic runners are historical artifacts and are not the matched Pilot protocol.

Full suite results are saved in `research/outputs/b0_pilot_protocol_20260926/tests.log`.

Validation completed: `pytest tests/ -q` — **162 passed**, one existing jieba/pkg_resources deprecation warning, 121.05 seconds. Both audit-only entrypoint runs passed. No pretrained model was loaded during this task.
