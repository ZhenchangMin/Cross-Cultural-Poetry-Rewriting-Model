# Semantic annotator V2 reliability 运行报告

范围：只使用现有16条calibration开发，冻结后评估原8条development validation。未运行957条，未训练Qwen，未增加人工审核。模型仍是本地原始Qwen2.5-1.5B-Instruct，不加载LoRA。

## v1为什么是0

v1的validate_llm_result一次检查完整四维。emotion类型错误或某一维证据错误会使整包语义结果丢弃，所以四维端到端有效覆盖率均为0。这个0不能证明四个语义分类都错误。下文对v1保存的原始响应重新做相同的确定性normalize，未重新调用v1模型、未修改标签。

V2按维度保留合法标签，证据、类型和置信度独立校验。仅做合法emotion字符串转单元素数组、合法单标签单元素数组转字符串；不猜标签、不依Gold改预测。非法标签计为缺失并进入总分母，同时报告合法预测覆盖率。

## calibration开发与4-shot

开发阶段第一次试验的首条结果复述schema，因此中止并保留原始响应。第二版调整为直接的输入/输出示例；随后在代码检查中修正repair语义变更被拒绝后的汇总协议指标，最终在r3目录完整运行。以上变化只依据calibration或实现检查，validation未用于这些修改。

示例选择枚举16选4，最大化“维度—标签”覆盖，平局规则固定。选中组合覆盖现有13种组合：4种emotion以及其余三维各3种；Gold缺少lonely/indignant，无法覆盖。具体选择：

| 诗歌 | 情感 | 辞藻 | 表达 | 气势 |
|---|---|---|---|---|
| 成都 | serene, joyful | refined | implicit | balanced |
| 登越王樓見喬公詩偶題 | serene | refined | balanced | balanced |
| 洞陽峯 | serene, heroic | ornate | balanced | vigorous |
| 柱上詩 | melancholic | plain | direct | gentle |

这是全局最优覆盖组合加固定ID平局选择，不为每条都声称具有不可替代性。校准目标若是选中示例之一，会从其余15条重新选4条，目标自己的标签不会作为示例进入提示。示例confidence=0.8为格式演示值，不是人工概率标注。

## 16条calibration开发诊断

确定性类型normalize：0条响应，逐维次数 `{'emotion': 0, 'diction': 0, 'expression': 0, 'energy': 0}`。

自动repair调用 14 次，其中最终完整协议通过 0 次；拒绝改动原合法标签的响应 0 条。每条最多1次repair。

| 协议指标 | 首轮 | repair后最终 |
|---|---:|---:|
| json_parse_success_rate | 100.0% | 100.0% |
| schema_success_rate | 12.5% | 18.8% |
| type_success_rate | 100.0% | 93.8% |
| evidence_verbatim_success_rate | 62.5% | 50.0% |
| full_protocol_success_rate | 12.5% | 12.5% |

| 语义维度 | 首轮 | 最终 | 最终合法标签覆盖率 |
|---|---:|---:|---:|
| emotion (f1) | 0.6857 | 0.6857 | 100.0% |
| diction (accuracy) | 0.5000 | 0.5000 | 100.0% |
| expression (accuracy) | 0.1875 | 0.1875 | 37.5% |
| energy (accuracy) | 0.0625 | 0.1250 | 68.8% |

最终emotion micro precision=0.7500，recall=0.6316，F1=0.6857。

协议失败样例（最多3条；完整列表见JSON）：

- `tang-4c612a51-0ac3-4166-bad1-90d6e4cb6def`：expression.label_valid=false
- `tang-4e7818af-b432-424d-b011-21180f6e9053`：diction.evidence_valid=false；expression.label_valid=false
- `tang-599f85c6-76cb-4af5-bc51-67b9c36b2ab4`：diction.evidence_valid=false；expression.label_valid=false

以上是开发诊断，不是独立性能估计。完成诊断后，frozen_v2.json绑定代码、配置、校准响应和报告哈希，随后才运行8条验证。

## 8条development validation

确定性类型normalize：0条响应，逐维次数 `{'emotion': 0, 'diction': 0, 'expression': 0, 'energy': 0}`。

自动repair调用 4 次，其中最终完整协议通过 0 次；拒绝改动原合法标签的响应 0 条。每条最多1次repair。

| 协议指标 | 首轮 | repair后最终 |
|---|---:|---:|
| json_parse_success_rate | 100.0% | 100.0% |
| schema_success_rate | 50.0% | 50.0% |
| type_success_rate | 100.0% | 100.0% |
| evidence_verbatim_success_rate | 100.0% | 100.0% |
| full_protocol_success_rate | 50.0% | 50.0% |

| 语义维度 | 首轮 | 最终 | 最终合法标签覆盖率 |
|---|---:|---:|---:|
| emotion (f1) | 0.5556 | 0.5556 | 100.0% |
| diction (accuracy) | 0.7500 | 0.7500 | 100.0% |
| expression (accuracy) | 0.5000 | 0.5000 | 50.0% |
| energy (accuracy) | 0.1250 | 0.1250 | 75.0% |

最终emotion micro precision=0.6250，recall=0.5000，F1=0.5556。

协议失败样例（最多3条；完整列表见JSON）：

- `tang-3dc2c19f-a20a-4405-b4e7-5a1b2f75cf03`：expression.label_valid=false
- `tang-a0e56e1e-22a7-4afa-8f2b-9da47aff3e0e`：expression.label_valid=false；energy.label_valid=false
- `tang-c591cbbd-4b6d-4284-a265-d29ffb1db9b4`：expression.label_valid=false

## v1与v2同口径比较

| 指标 | v1原始响应经相同normalize | v2首轮 | v2最终 |
|---|---:|---:|---:|
| emotion f1 | 0.2222 | 0.5556 | 0.5556 |
| diction accuracy | 0.6250 | 0.7500 | 0.7500 |
| expression accuracy | 0.8750 | 0.5000 | 0.5000 |
| energy accuracy | 0.0000 | 0.1250 | 0.1250 |
| json_parse_success_rate | 100.0% | 100.0% | 100.0% |
| schema_success_rate | 100.0% | 50.0% | 50.0% |
| type_success_rate | 0.0% | 100.0% | 100.0% |
| evidence_verbatim_success_rate | 37.5% | 100.0% | 100.0% |
| full_protocol_success_rate | 0.0% | 50.0% | 50.0% |

v1类型normalize次数：`{'emotion': 8, 'diction': 0, 'expression': 0, 'energy': 0}`。这只是无语义改变的离线重分析，原v1结果保留不覆盖。

语义指标独立于证据/置信度校验，因此应同时看合法预测覆盖率。协议的type success仍指原始类型正确，不把确定性修复倒记为原始正确；严格full protocol要求四维全部合格。schema success指所需字段形状加合法可normalize标签。

这8条历史上参与指南讨论，也已参与v1评估，明确是development validation，不声称是严格历史未见test set。8条规模下单标签准确率每条影响12.5个百分点。

## Silver gate：fail

门槛未下调：emotion F1≥0.70；diction/expression/energy各≥0.60；imagery F1≥0.70、density accuracy≥0.95；新增最终完整协议成功率≥0.90（8条即需8/8）。

- emotion.f1=0.5556 < 0.7
- expression.accuracy=0.5000 < 0.6
- energy.accuracy=0.1250 < 0.6
- final protocol success=0.5000 < 0.9

无论gate结果如何，本轮没有调用批量Silver流程。957条候选和原Gold、审核文件保持不变。完整测试 `pytest tests/ -q`：111 passed，1 warning（既有jieba/pkg_resources弃用警告），131.86秒。原始输入共18项哈希核对通过；另一个Gold副本与已有Git提交内容一致（仅归一化换行进行比较）。完整pytest结果见research/outputs/semantic_v2_r3_tests.log，提交号见本次Git提交与交付消息。

结果目录：research/data/processed/semantic_annotator_v2_r3/。校准报告为semantic_annotator_v2_calibration_report.json，验证比较为semantic_annotator_v2_validation_report.json；逐条JSONL保留原响应、错误、修复输入输出、最终结果和实际示例ID。
