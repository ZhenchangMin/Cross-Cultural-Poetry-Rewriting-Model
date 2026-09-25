# Semantic annotator V2 reliability

本轮只允许16条calibration开发、冻结后8条development validation评估。CLI没有批量Silver入口，不运行957条，不训练模型，不新增人工审核。

## 标签与协议分离

每个语义维度保存raw_prediction、normalized_prediction、label_valid、type_valid、type_repaired、confidence_valid、evidence_valid、full_protocol_valid、repair_used和normalization_provenance。

仅允许两种确定性标签类型修复：合法emotion字符串→单元素数组；合法single-label单元素数组→字符串。不猜新标签、不翻译标签、不去重或截断不合法多标签，不读取Gold修改预测。非法或缺失标签作为缺失计入全量分母，并另外报告合法标签覆盖率和只在合法标签上的准确率。

证据必须是原文中的非空连续子串，保留换行与繁简；不通过去换行来拼出原文没有的短语。证据或置信度不合格不清除合法标签。Semantic metrics读取normalized_prediction；Protocol metrics独立读取协议状态。

协议指标定义：

- json_parse_success：JSON可解析为对象；外层Markdown代码围栏可剥离，另记json_wrapper_removed。
- schema_success：根恰有四维，各维恰有value/confidence/evidence，且标签可合法normalize；原始标签类型另计。
- type_success：四维value原始类型均正确，确定性修复不会把原始type_valid改成true。
- evidence_verbatim_success：四维各含1–3条有效原文证据。
- full_protocol_success：结构、合法标签、原始类型、有限0–1数值置信度和证据全通过。

## 一次自动repair

首次完整协议失败时，最多调用一次repair。输入仅含原文、原响应、validator errors和required schema；不传Gold标签或few-shot答案。保存first_pass_raw/errors/result、repair_raw/errors、final_result及全部提示。

修复要求保留现有合法标签，只修格式、类型、证据；现有标签非法时才可重新解释。代码还会核对这一约束：修复响应若改动合法标签，该维度修复被拒绝，保留首轮结果、标记repair_semantic_change_rejected，并使最终完整协议失败。原始repair响应仍保留，不隐藏失败。

## 4-shot选择与校准

枚举16选4的所有组合，优先最大化维度—标签覆盖数，其次最大化最少覆盖的维度，再覆盖两种诗体；平局按排序ID固定选择。示例覆盖13种现有维度—标签组合。具体ID、标签和选择理由保存在config.json。示例confidence=0.8仅演示JSON数值格式，不是人工标注置信度；示例证据取既有助手证据中的原文子串，不称为独立人工证据Gold。

校准目标若是固定4-shot之一，会从其余15条重新按同一算法选4条，避免自身Gold答案出现在提示中。逐条保存实际few_shot_ids。校准报告是开发诊断，不作最终性能估计。

## 冻结与验证

calibrate完成后才能freeze；freeze绑定代码、schema、配置、校准报告和响应哈希。validate必须通过冻结核对才读取8条验证数据。v1只重分析已有原始响应，不重新请求模型；比较采用与v2相同的标签normalizer及指标分母，避免v1整包丢弃导致的0分掩盖语义信息。

这8条历史上参与过项目指南讨论，且已用于v1开发评估；明确称development validation，不称严格历史未见test set。

Silver gate保持原语义门槛：emotion micro F1≥0.70，三个单标签accuracy各≥0.60；规则imagery F1≥0.70、density accuracy≥0.95。额外要求最终完整协议成功率≥0.90（8条规模下意味着8/8）。无论pass或fail，本轮都不启动Silver。

## 运行

在research目录，依次运行：

```bash
python scripts/semantic_v2.py calibrate
python scripts/semantic_v2.py freeze
python scripts/semantic_v2.py validate
```

最终结果目录为data/processed/semantic_annotator_v2_r3/；前两次中止的校准尝试保留在semantic_annotator_v2/和semantic_annotator_v2_r2/。完成的报告拒绝覆盖；同配置中断可按提示和配置哈希恢复。要改代码或提示进行新的calibration开发，应显式建立新版本目录，不修改冻结实验。
