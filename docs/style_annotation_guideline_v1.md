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

Review rule:
- Keep the deterministic proxy unless obvious lexicon noise or missed multi-character terms materially changes the interpretation.
- If overridden, record the reason explicitly.

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
