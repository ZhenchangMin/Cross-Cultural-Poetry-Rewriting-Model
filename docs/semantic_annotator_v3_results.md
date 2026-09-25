# Semantic Annotator V3：两阶段 development 4-fold CV

本轮仅使用既有24条人工Gold；每折18条calibration、6条evaluation，每条恰好被evaluation一次。固定seed=20260925。四维分别分类，之后单独提取evidence；没有LLM repair。未运行957条Silver，未训练模型，未新增人工审核，未修改Gold。原始模型为Qwen2.5-1.5B-Instruct，不加载LoRA。

## 实验边界

全部Gold此前参与过项目指南或开发，本实验明确是development cross-validation，不能声称严格独立test。每折只从该折18条calibration选few-shot，evaluation从不进入自己的提示。提示、代码、划分、门槛在推理前冻结，没有根据fold结果调参。

划分从4000个固定seed候选中选择：每折恰好6条、诗体接近平衡，最小化按类别频率加权的标签分布偏差，并保留每个calibration子集中的所有已有语义类别。lonely、indignant在Gold中无正样本，无法估计这些类别的召回。

## Aggregate metrics（24条out-of-fold）

非法标签记为缺失，始终保留在24条总分母中；evidence、confidence或格式失败不会删除合法语义标签。emotion使用micro P/R/F1。

| 维度 | 主指标 | 合法标签覆盖率 | JSON成功率 | semantic schema成功率 | evidence成功率 |
|---|---:|---:|---:|---:|---:|
| emotion | f1=0.3396 | 100.0% | 100.0% | 100.0% | 0.0% |
| diction | accuracy=0.2917 | 100.0% | 100.0% | 100.0% | 0.0% |
| expression | accuracy=0.4167 | 100.0% | 100.0% | 100.0% | 0.0% |
| energy | accuracy=0.2917 | 100.0% | 100.0% | 100.0% | 0.0% |

emotion precision=0.3750，recall=0.3103，F1=0.3396。

| 每首四维全部通过的协议指标 | 比例 |
|---|---:|
| json_parse_success_rate | 100.0% |
| semantic_schema_success_rate | 100.0% |
| full_semantic_protocol_valid_rate | 100.0% |
| evidence_success_rate | 0.0% |
| full_two_stage_success_rate | 0.0% |

semantic schema允许合法的确定性单元素类型归一化；full semantic protocol仍要求模型原始类型正确。evidence success只检查原文逐字子串和输出结构，并不能证明证据的语义相关性。逐维evidence率以24条为分母，另有attempted分母指标保存在JSON。

evidence阶段JSON可解析24/24；其中20/24复述了输入的fixed_predictions外层结构，未按要求生成四个维度到原文短语数组的映射。根字段模式：`{'fixed_predictions,poem': 20, 'poem': 1, 'diction,emotion,energy,expression': 2, '境靜聞鐘聲易響,庭高見月影難沈,流水能清物外心,青山解隔塵中事': 1}`。这是独立证据阶段的协议失败，不能据此清除第一阶段的合法语义标签；本轮保留失败结果，不做LLM repair。

确定性normalization次数：{'emotion': 0, 'diction': 0, 'expression': 0, 'energy': 0}；LLM repair调用次数=0。

## 每fold结果

| Fold | 七绝/七律 | emotion P/R/F1 | diction acc | expression acc | energy acc | JSON全通过 | semantic schema全通过 | evidence全通过 |
|---|---|---|---:|---:|---:|---:|---:|---:|
| 1 | 4/2 | 0.333/0.286/0.308 | 0.333 | 0.000 | 0.333 | 100.0% | 100.0% | 0.0% |
| 2 | 3/3 | 0.667/0.571/0.615 | 0.333 | 0.667 | 0.500 | 100.0% | 100.0% | 0.0% |
| 3 | 3/3 | 0.167/0.125/0.143 | 0.167 | 0.667 | 0.167 | 100.0% | 100.0% | 0.0% |
| 4 | 3/3 | 0.333/0.286/0.308 | 0.333 | 0.333 | 0.167 | 100.0% | 100.0% | 0.0% |

每折仅6条，单标签准确率每条影响16.7个百分点；汇总为24条pooled指标，不是简单平均fold F1。

## Confusion

### expression

行是真实Gold，列是预测；invalid也保留。

| Gold \ Prediction | direct | balanced | implicit | invalid |
|---|---:|---:|---:|---:|
| direct | 1 | 0 | 4 | 0 |
| balanced | 1 | 6 | 8 | 0 |
| implicit | 0 | 1 | 3 | 0 |
### energy

行是真实Gold，列是预测；invalid也保留。

| Gold \ Prediction | gentle | balanced | vigorous | invalid |
|---|---:|---:|---:|---:|
| gentle | 1 | 11 | 2 | 0 |
| balanced | 0 | 6 | 0 | 0 |
| vigorous | 0 | 4 | 0 | 0 |
### diction

行是真实Gold，列是预测；invalid也保留。

| Gold \ Prediction | plain | refined | ornate | invalid |
|---|---:|---:|---:|---:|
| plain | 3 | 0 | 0 | 0 |
| refined | 7 | 0 | 10 | 0 |
| ornate | 0 | 0 | 4 | 0 |

### emotion

遗漏/多报标签：`{'missed:joyful': 5, 'missed:melancholic': 12, 'extra:serene': 7, 'extra:indignant': 3, 'missed:heroic': 3, 'extra:lonely': 5}`。

主要替代标签对：`{'melancholic->serene': 6, 'melancholic->lonely': 4, 'melancholic->indignant': 2, 'heroic->indignant': 1, 'joyful->indignant': 1, 'joyful->serene': 1, 'heroic->lonely': 1}`。多标签替代对为描述性配对，不能视为独立样本数。

## Energy诊断

- Gold分布：`{'gentle': 14, 'balanced': 6, 'vigorous': 4}`；模型分布：`{'balanced': 21, 'vigorous': 2, 'gentle': 1}`。
- 非法原始标签：`{}`；合法标签覆盖率=100.0%。
- 主要可观察问题是类别偏置：24条中21条预测balanced；gentle→balanced共11条，vigorous→balanced共4条。标签全部合法，因此本轮energy低分主要是语义判断错误，而不是JSON或enum错误。始终猜Gold多数类gentle的描述性基线为14/24=58.3%，高于当前模型；这不是独立训练的基线。
- 每fold均提供gentle/balanced/vigorous三个类别的anchor；标签缺类不能解释错误，但文字相似度代表性不保证气势边界最清晰。
- 提示明确区分情感与节奏力度，且单独分类。是否仍与emotion混淆，只能结合联合预测表和具体诗判断；没有对照消融，不能把因果归结为某一种提示或模型能力。
- 定义延续现有schema并补充操作性解释，没有重标Gold；定义本身是否充分清晰仍未被独立检验。error_analysis.json保存分布、非法输出及emotion/energy联合预测。

其他明显偏置：diction没有预测任何refined（Gold有17条），expression把15条预测为implicit（Gold有4条）。这些结果不支持把协议可靠性提升视作语义分类改善。V2的8条结果与本轮24条CV评估集及few-shot不同，不作直接性能增减结论。

## Few-shot选择

单标签每类选1条，以同类诗汉字集合Jaccard相似度均值最大的样本作为代表；emotion选4条，优先覆盖类别、其次单标签清晰度、再同类代表性；平局按ID排序。此为确定性代理，不是新的人工清晰度确认。每折独立选择，仅把目标dimension标签放入该维提示，示例confidence=0.8只是格式示范。

### Fold 1

- emotion：竹 `tang-4e7818af-b432-424d-b011-21180f6e9053` → ['serene']；陪遊上苑遇雪 `tang-a39ebbbd-8626-4de4-a582-23146a31e189` → ['joyful']；自蘇州至望亭驛有作 `tang-ba01a06a-d48f-4b98-bdc7-ffb5dd200438` → ['melancholic']；詩 `tang-fe589d8b-6a1f-4a8f-9a91-89c870603419` → ['heroic']
- diction：詠柳二首 一 `tang-95477829-6273-4f85-a0b8-d5bf3c07e507` → ornate；上歸州刺史代通狀二首 一 `tang-c591cbbd-4b6d-4284-a265-d29ffb1db9b4` → plain；題越州袁秀才林亭 `tang-805df95b-c30d-4773-ac47-68f6574f6d81` → refined
- expression：自蘇州至望亭驛有作 `tang-ba01a06a-d48f-4b98-bdc7-ffb5dd200438` → balanced；柱上詩 `tang-f240f42f-4bf0-4463-8026-4bb19f4db3af` → direct；詠柳二首 一 `tang-95477829-6273-4f85-a0b8-d5bf3c07e507` → implicit
- energy：秋日經潼關感寓 `tang-599f85c6-76cb-4af5-bc51-67b9c36b2ab4` → balanced；題越州袁秀才林亭 `tang-805df95b-c30d-4773-ac47-68f6574f6d81` → gentle；詩 `tang-fe589d8b-6a1f-4a8f-9a91-89c870603419` → vigorous

### Fold 2

- emotion：登越王樓見喬公詩偶題 `tang-4c612a51-0ac3-4166-bad1-90d6e4cb6def` → ['serene']；早發龍沮館舟中寄東海徐司倉鄭司戶 `tang-7cb201dc-c6ee-45c2-a3e8-55f422fe789b` → ['melancholic']；奉和聖製元日大雪登樓 `tang-a0e56e1e-22a7-4afa-8f2b-9da47aff3e0e` → ['joyful']；詩 `tang-fe589d8b-6a1f-4a8f-9a91-89c870603419` → ['heroic']
- diction：詠柳二首 一 `tang-95477829-6273-4f85-a0b8-d5bf3c07e507` → ornate；上歸州刺史代通狀二首 一 `tang-c591cbbd-4b6d-4284-a265-d29ffb1db9b4` → plain；題越州袁秀才林亭 `tang-805df95b-c30d-4773-ac47-68f6574f6d81` → refined
- expression：題越州袁秀才林亭 `tang-805df95b-c30d-4773-ac47-68f6574f6d81` → balanced；春日南山行 `tang-c8f4ef3d-dfd7-4d77-8d4c-df0e8575eeef` → direct；詠柳二首 一 `tang-95477829-6273-4f85-a0b8-d5bf3c07e507` → implicit
- energy：登越王樓見喬公詩偶題 `tang-4c612a51-0ac3-4166-bad1-90d6e4cb6def` → balanced；題越州袁秀才林亭 `tang-805df95b-c30d-4773-ac47-68f6574f6d81` → gentle；贈淮西賈兵馬使 `tang-7887d2d9-3655-45b1-a556-349d95304058` → vigorous

### Fold 3

- emotion：春夜宿雲際寺 `tang-740c1743-61f4-4694-908b-6737af54523d` → ['serene']；陪遊上苑遇雪 `tang-a39ebbbd-8626-4de4-a582-23146a31e189` → ['joyful']；自蘇州至望亭驛有作 `tang-ba01a06a-d48f-4b98-bdc7-ffb5dd200438` → ['melancholic']；詩 `tang-fe589d8b-6a1f-4a8f-9a91-89c870603419` → ['heroic']
- diction：詠柳二首 一 `tang-95477829-6273-4f85-a0b8-d5bf3c07e507` → ornate；春日南山行 `tang-c8f4ef3d-dfd7-4d77-8d4c-df0e8575eeef` → plain；早發龍沮館舟中寄東海徐司倉鄭司戶 `tang-7cb201dc-c6ee-45c2-a3e8-55f422fe789b` → refined
- expression：早發龍沮館舟中寄東海徐司倉鄭司戶 `tang-7cb201dc-c6ee-45c2-a3e8-55f422fe789b` → balanced；春日南山行 `tang-c8f4ef3d-dfd7-4d77-8d4c-df0e8575eeef` → direct；詠柳二首 一 `tang-95477829-6273-4f85-a0b8-d5bf3c07e507` → implicit
- energy：春日南山行 `tang-c8f4ef3d-dfd7-4d77-8d4c-df0e8575eeef` → balanced；早發龍沮館舟中寄東海徐司倉鄭司戶 `tang-7cb201dc-c6ee-45c2-a3e8-55f422fe789b` → gentle；洞陽峯 `tang-88020cd6-c877-4632-a3d0-174216653e83` → vigorous

### Fold 4

- emotion：竹 `tang-4e7818af-b432-424d-b011-21180f6e9053` → ['serene']；贈淮西賈兵馬使 `tang-7887d2d9-3655-45b1-a556-349d95304058` → ['heroic', 'joyful']；陪遊上苑遇雪 `tang-a39ebbbd-8626-4de4-a582-23146a31e189` → ['joyful']；上歸州刺史代通狀二首 一 `tang-c591cbbd-4b6d-4284-a265-d29ffb1db9b4` → ['melancholic']
- diction：洞陽峯 `tang-88020cd6-c877-4632-a3d0-174216653e83` → ornate；春日南山行 `tang-c8f4ef3d-dfd7-4d77-8d4c-df0e8575eeef` → plain；題越州袁秀才林亭 `tang-805df95b-c30d-4773-ac47-68f6574f6d81` → refined
- expression：自蘇州至望亭驛有作 `tang-ba01a06a-d48f-4b98-bdc7-ffb5dd200438` → balanced；春日南山行 `tang-c8f4ef3d-dfd7-4d77-8d4c-df0e8575eeef` → direct；竹 `tang-4e7818af-b432-424d-b011-21180f6e9053` → implicit
- energy：自蘇州至望亭驛有作 `tang-ba01a06a-d48f-4b98-bdc7-ffb5dd200438` → balanced；題越州袁秀才林亭 `tang-805df95b-c30d-4773-ac47-68f6574f6d81` → gentle；奉和聖製元日大雪登樓 `tang-a0e56e1e-22a7-4afa-8f2b-9da47aff3e0e` → vigorous

## Dimension readiness与Silver gate

原门槛不降低：emotion F1≥0.70，diction/expression/energy accuracy≥0.60，imagery F1≥0.70，density accuracy≥0.95；完整两阶段协议≥0.90。逐语义维ready还要求本维原始semantic protocol与evidence成功率各≥0.90。ready仅表示开发集上的候选来源，不等于已获独立泛化验证或可立即放行整批数据。未来逐条confidence门槛保持semantic≥0.8、imagery≥0.7、density≥0.5。

| Dimension | 质量指标达标 | dimension_ready |
|---|---|---|
| emotion | False | False |
| diction | False | False |
| expression | False | False |
| energy | False | False |
| imagery | True | True |
| density | True | True |

固定rule v1.1在24条上的imagery F1=0.8000，density accuracy=1.0000；规则此前受Gold校准，不能视为新独立验证。

**silver_gate=fail**

- emotion: metric=0.3396 (required 0.7), semantic protocol=1.0000, evidence=0.0000 (each required .90)
- diction: metric=0.2917 (required 0.6), semantic protocol=1.0000, evidence=0.0000 (each required .90)
- expression: metric=0.4167 (required 0.6), semantic protocol=1.0000, evidence=0.0000 (each required .90)
- energy: metric=0.2917 (required 0.6), semantic protocol=1.0000, evidence=0.0000 (each required .90)
- full two-stage success=0.0000 < .90

## 完整性与测试

60个原有Gold、preannotation、review、v1/v2结果及候选文件哈希一致。原始请求和响应在requests.jsonl，out-of-fold结果及独立evidence校验在out_of_fold_predictions.jsonl，完整报告在semantic_annotator_v3_cv_report.json。

测试日志：research/outputs/semantic_v3_tests.log。

125 passed, 1 warning in 135.65s (0:02:15)
