# Style Annotation Guideline V1

This guideline operationalizes `research/configs/style_schema.json` for the first calibration and Gold-review workflow.

## 1. General principles

1. Judge from the poem text first. Author/title may be shown for provenance, but must not determine the label.
2. Labels describe the dominant effect of the whole poem, not every isolated line.
3. `emotion` allows 1–2 labels. Use two only when both are independently central; do not add a secondary label merely because one line supports it.
4. `imagery` allows 1–4 labels. Keep only imagery systems that are materially present, not incidental single characters.
5. `diction`, `expression`, `energy`, and `density` are single-label.
6. Evidence must quote short verbatim phrases from the poem. Evidence is justification, not a full interpretation.
7. When uncertain between adjacent labels, record the lower confidence and a short note. Do not invent a third category.
8. Machine prelabels are suggestions only. Final labels must be decided independently and may override them.

## 2. Emotion

### serene — 清宁 / 平和
Dominant affect is calm, tranquil, detached, contemplative, or quietly content. Typical cues: quiet landscapes, settled observation, untroubled meditation.

Do not use merely because the scene is beautiful; if the poem is clearly happy, use `joyful`.

### joyful — 欢愉 / 明朗
Dominant affect is delight, celebration, praise, confidence, sociability, or bright satisfaction. Includes courtly praise when the emotional tone is clearly affirmative and celebratory.

Do not use for merely energetic language without positive affect.

### melancholic — 感伤 / 惆怅
Dominant affect is sadness, longing, homesickness, regret, separation, aging, transience, or subdued grief.

Use this rather than `indignant` when sorrow is primarily personal or reflective rather than morally/protest-oriented.

### lonely — 孤寂 / 凄清
Dominant affect is solitude, isolation, abandonment, desolation, or emotionally empty surroundings.

Can co-occur with `melancholic` when both sadness and isolation independently dominate.

### heroic — 豪迈 / 昂扬
Dominant affect is expansive confidence, ambition, martial vigor, bold aspiration, or elevated spiritedness.

Do not infer heroic tone simply from frontier/military imagery if the poem is actually sorrowful.

### indignant — 悲愤 / 沉郁
Dominant affect combines grief with anger, moral frustration, political/social resentment, injustice, or heavy pent-up protest.

Use conservatively. Personal sadness alone is `melancholic`.

## 3. Imagery

### landscape — 山水自然
Mountains, rivers, lakes, seas, springs, cliffs, valleys, fields, islands, shores, natural terrain.

### celestial — 天象
Moon, stars, sun, sky, clouds, Milky Way, dawn/dusk light when functioning as celestial imagery.

### season_weather — 时令与气候
Spring/summer/autumn/winter, wind, rain, snow, frost, dew, cold/heat, seasonal markers.

### flora — 植物
Flowers, trees, bamboo, grass, lotus, willow, vines, named plants.

### fauna — 动物
Birds, fish, horses, apes, insects, dragons when functioning as creature imagery rather than purely political emblem.

### travel — 行旅
Roads, passes, boats, carriages, journeys, travelers/guests, returning home, departure, lodging, crossings.

### frontier — 边塞军旅
Frontier forts, borders, campaigns, armies, weapons, battlefields, garrisons, military watchtowers and explicitly martial border settings.

### human_culture — 人文文化
Buildings, temples, towers, palaces, cities, instruments, wine, lamps, books, ritual/religious objects, clothing, artifacts and other human-made cultural objects.

### Imagery adjudication
- A single incidental cue does not automatically justify a category.
- Prefer semantic role over substring lexicon matches.
- Maximum four categories: retain those most structurally important to the poem.

## 4. Diction

### plain — 质朴
Lexicon and syntax are comparatively direct, everyday, transparent, minimally ornamented, and easy to paraphrase.

### refined — 典雅
Classical, polished, literary, controlled diction with conventional poetic vocabulary or allusion, but without sustained luxuriant ornament.

This is the default middle category for much regulated Tang poetry.

### ornate — 绮丽
Noticeably embellished, luxuriant, sensuous, highly decorative, color-rich or densely allusive diction is central to the verbal surface.

Do not use simply because the poem contains several imagery words.

## 5. Expression

### direct — 直抒
Emotion/judgment is explicitly stated and carries the poem: e.g. words equivalent to grief, joy, hate, longing, sighing, resentment, praise.

### balanced — 情景交融
Scene description and explicit/implicit feeling have comparable weight; the poem moves between external scene and affect.

### implicit — 含蓄
Feeling is primarily conveyed through scene, juxtaposition, implication, symbol, or restrained suggestion rather than explicit emotional declaration.

If explicit affect words repeatedly appear, prefer `direct` or `balanced` over `implicit`.

## 6. Energy

### gentle — 舒缓
Quiet, soft, slow, flowing, meditative, restrained, or low-tension movement.

### balanced — 平稳
Moderate dynamic range; neither markedly soft nor forceful. Controlled narrative/descriptive motion.

### vigorous — 强烈 / 顿挫 / 奔放
Forceful verbs, rapid contrasts, exclamatory turns, martial movement, rhetorical pressure, strong emotional propulsion, or conspicuous tonal/semantic tension.

Energy is about rhetorical/dynamic force, not emotional valence.

## 7. Density

V1 keeps density as a reproducible weak quantitative feature rather than a purely subjective literary judgment.

Primary proxy:
- Count unique imagery-lexicon terms across the poem.
- Divide by number of poem lines.
- `sparse`: score < 0.75
- `medium`: 0.75 <= score < 1.5
- `dense`: score >= 1.5

Review rule (updated 2026-09-23, source-assisted V2):
- Freeze the imagery lexicon and `lexicon_heuristic_v1_1` code by SHA-256. Reproduce this proxy for every reviewed poem; do not override individual density values using literary impressions.
- Record ambiguous matches and omissions separately. A lexicon or algorithm change requires a new version and a complete recomputation before train/test use.
- This field measures dictionary-cue concentration, not semantic imagery richness, number of imagery categories, or literary quality.
- See [source-assisted V2 adjudication and review policy](source_adjudication_policy_v2.md) and `density_audit_v2.json` for term lists and limitations.

## 8. Confidence

Recommended interpretation:
- 0.90–1.00: clear dominant label, little plausible disagreement.
- 0.75–0.89: strong but not unique interpretation.
- 0.60–0.74: genuine ambiguity between neighboring labels.
- <0.60: calibration/problem case; prioritize for adjudication.

## 9. Calibration status

The first 30–50 records are a calibration set. AI or rule judgments are not automatically called Gold.

Recommended statuses:
- `assistant_calibrated_pending_human`: reviewed by the project assistant but not independently human-confirmed.
- `human_reviewed`: at least one human has confirmed/edited the final labels.
- `gold_adjudicated`: final agreed label set used as Gold supervision/evaluation.

This distinction must remain visible in metadata and reports.

## 10. Human review and Gold promotion

Assistant proposals are never promoted automatically. Initialize an explicit review state:

```bash
cd research
python scripts/human_review.py init --reviewer "<human reviewer>"
```

Every record starts with:

```text
decision = pending
```

even when the assistant suggestion is `accept` or `exclude`. The reviewer must explicitly set one of:

- `accept`: accept the proposed final style;
- `edit`: modify `final_style` and accept the edited labels;
- `exclude`: exclude the record from Gold for a documented quality reason;
- `pending`: not yet reviewed.

Inspect progress with:

```bash
python scripts/human_review.py status
```

Gold promotion is refused while any records remain pending:

```bash
python scripts/human_review.py promote
```

After all decisions are completed, promotion copies only the human-reviewed `final_style` into canonical `style`, records reviewer/provenance, and re-runs the canonical Gold validator. This promoted file is the first artifact eligible for supervised training.

## 11. Source-assisted V2 review inputs (2026-09-23)

The active source-assisted candidate pack is `data/processed/style_annotation/review_candidates24_v2.jsonl`, paired only with `human_review_state24_v2.json`. The original 30-record state is retained for history. Do not mix these states or run the default promotion command against the wrong input. At initialization, all 24 decisions were pending. The completed state now contains 21 accepts and 3 edits; preserve that history. Suggested values alone are not human judgments.

Inspect V2 explicitly:

```bash
python scripts/human_review.py status --state data/processed/style_annotation/human_review_state24_v2.json
```

After actual human decisions, use explicit V2 input, state and new output/report paths. Keep the default refusal of incomplete review. The source-adjudication policy documents three held and three proposed out-of-scope/fragment records. Near-duplicate groups are a manifest for future splitting, not an implemented leakage guarantee.


## 12. Calibration Gold V1 freeze and next review round (2026-09-24)

The original 30-record state is an initialization snapshot, not the latest review.
`human_review_state30_reconciled_v1.json` combines the completed 24-record state with
six unresolved records. Original state files and human-written review notes are not
rewritten. Three assistant exclusion proposals remain **pending**, not human exclusions.

The explicit partial promotion is:

```bash
python scripts/human_review.py promote --input data/processed/style_annotation/calibration_promotion_input_v1.jsonl --state data/processed/style_annotation/human_review_state30_reconciled_v1.json --allow-partial --output data/processed/style_annotation/gold_calibration_v1.jsonl --report data/processed/style_annotation/gold_calibration_report_v1.json
```

Use `prepare_gold_calibration.py` to reproduce the full export and audit. It refuses
changed existing outputs. The 24-record artifact is calibration Gold, not a sufficiently
large training dataset or an independent evaluation set. Do not start formal B0 training
until the pilot review and consistency checks are complete.

Clarifications supported by the completed review:

- **Emotion:** do not add `serene` simply because a poem describes a quiet scene or
  religious withdrawal. The reviews of 贈頭陀僧 and 丁元和詩 removed this secondary
  label while retaining the dominant feeling. These are two observed edits, not a
  general inter-reviewer disagreement rate.
- **Diction:** allusions alone do not establish `ornate`; sustained decorative verbal
  texture is required. 登越王樓見喬公詩偶題 was confirmed as `refined`.
- **Expression and energy:** explicit feeling in one line does not automatically make
  the whole poem `direct`, and military vocabulary does not automatically make it
  `vigorous`. Examine the overall development and ending. The questioned energy of
  秋日經潼關感寓 was confirmed as `balanced`, not changed. Record uncertainty without
  inventing new label values.
- **Imagery:** inspect the semantic role of each cue. 瑟瑟波 does not denote a musical
  instrument merely because 瑟 matches; mythic/emblematic 龍 or 青鳥 need not denote
  animals in the scene. Select at most four central systems, not the four most frequent
  character matches. In this Gold24, 17 rule imagery sets differ from the final set.
- **Density:** zero disagreement with the frozen proxy is expected by policy and is
  not independent validation of literary density. The six density overrides in the old
  assistant report are historical proposals superseded by the frozen-proxy rule.
- **Script forms:** keep original characters in the reviewed text. Simplification may
  change tokenization and lexicon matches; any normalization experiment needs separate
  versioned text and lexicon treatment. Never silently convert canonical source text.

For the next 100 records, perform quality review before style review. A title of 句 is
an elevated-risk cue, not an automatic exclusion. Confirm coherent whole-poem status,
genre and unresolved textual variants before accepting style. If the reviewer cannot
resolve these, leave the record pending. Blank canonical styles and rule cues must
remain separate until an explicit human decision. This risk-enriched batch is not an
unbiased sample of the corpus; a later independent test split must consider authors
and variant families.
