# Partial Silver V1：可信维度监督与混合Dataset

本轮仅自动生成form、imagery、density；emotion/diction/expression/energy全部明确为null。现有Gold保留六维人工监督。没有LLM请求，没有新增人工审核，没有下载或启动正式模型训练。完整六维Silver gate仍为fail；本轮按用户新授权单独放行已达到开发门槛的规则维度。

## 实际数据

- 输入：1000条既有候选。
- 保留：825条Partial Silver；七绝358、七律467。
- 过滤：175条；互斥主原因如下。

| 原因 | 数量 |
|---|---:|
| low_confidence:imagery | 111 |
| no_imagery_labels | 21 |
| existing_gold | 24 |
| high_risk_quality | 13 |
| unresolved_calibration | 6 |

高风险source-fragment总共14条，其中1条已经计入6条unresolved，因此互斥主原因另计13条高风险。21条无imagery的记录也属于低置信度，不能重复相加。完整重叠原因统计：`{'low_confidence:imagery': 132, 'no_imagery_labels': 21, 'existing_gold': 24, 'high_risk_quality': 14, 'source_fragment': 14, 'unresolved_calibration': 6}`。

因此，相对于原先剩余的957条候选，本轮再排除132条，保留825条。逐条ID、标题与全部原因见partial_silver_v1_rejected.jsonl，不生成待人工审核队列。

| imagery标签 | 数量（多标签可重叠） |
|---|---:|
| landscape | 540 |
| celestial | 351 |
| season_weather | 510 |
| flora | 438 |
| fauna | 216 |
| travel | 282 |
| frontier | 109 |
| human_culture | 526 |

| density标签 | 数量 |
|---|---:|
| sparse | 65 |
| medium | 485 |
| dense | 275 |

## 独立stage与schema

Gold schema文件没有修改；旧candidate/preannotated/gold路径维持原行为。新增partial-silver stage由partial_supervision.py独立校验，form-only是额外的结构监督接口。partial-silver必须具备：

- 合法诗体及对应行数、每行字数；这里的结构确认不代表平仄和押韵认证。
- 六个style字段全部存在；四个语义维度严格为JSON null，不接受省略、空字符串或“未知”等伪标签。
- imagery为1–4个不重复合法标签，density为合法单标签。
- available_controls固定为form、imagery、density；supervision精确声明structural/rule来源。
- metadata及annotation标记automatic_partial_silver，不保留human_review、reviewer或语义prelabel。
- 每维value/confidence/evidence/method/label_source；输入文件、原记录、词典、规则代码及V3 gate报告的SHA256。

真实记录的控制部分：

```json
{
  "id": "tang-ee5bd665-80a6-43ef-b098-dc72dd829139",
  "form": "qilv7",
  "style": {
    "emotion": null,
    "imagery": [
      "landscape",
      "human_culture",
      "fauna"
    ],
    "diction": null,
    "expression": null,
    "energy": null,
    "density": "medium"
  },
  "dataset_stage": "partial-silver",
  "available_controls": [
    "form",
    "imagery",
    "density"
  ],
  "supervision": {
    "form": "structural_v1",
    "imagery": "silver_rule_v1_1",
    "density": "silver_rule_v1_1"
  }
}
```

规则仍为lexicon_heuristic_v1_1。保留阈值imagery≥0.7、density≥0.5；confidence是规则证据强度，不是校准概率。source文本保留繁简原样，不在本轮做字符转换。规则内部去换行可能产生跨行匹配，因此构建器另行拒绝非原文连续子串的证据，本轮此项无额外排除。

规则的开发数据结果为imagery F1=0.800、density accuracy=1.000，24条Gold曾参与开发，不能声称独立测试证明泛化可靠。输出称Partial Silver，不称Gold。

## 真实prompt示例

Gold完整prompt默认逐字保持原样；下面使用实际记录，不包含题目、作者或target正文。

### gold: `tang-32fe3d88-fe52-4d0e-8431-2ff060e5c20b`

```text
你是一名中国古典诗歌生成模型。请严格依据给定诗体和风格控制，生成一首符合要求的古典诗。

【控制条件】
诗体：七言绝句
情感：清宁平和、欢愉明朗
意象：植物、山水自然、天象、人文文化
辞藻：典雅
表达：含蓄
气势：平稳
密度：密集

【输出要求】
只输出诗歌正文，不输出作者、标题、解释或额外说明。
```

### partial_silver: `tang-ee5bd665-80a6-43ef-b098-dc72dd829139`

```text
你是一名中国古典诗歌生成模型。请严格依据给定诗体和风格控制，生成一首符合要求的古典诗。

【控制条件】
诗体：七言律诗
意象：山水自然、人文文化、动物
密度：适中

【输出要求】
只输出诗歌正文，不输出作者、标题、解释或额外说明。
```

## Control dropout

PoetryTrainingDataset和MixedPoetryDataset均支持training、control_dropout、seed、set_epoch。默认probability=0（关闭）；准备清单示范training=True、probability=0.3、seed=20260926，但没有开始训练。

每个有监督的style维度独立按概率隐藏；随机数由SHA256(seed:epoch:record_id:dimension)产生，读取顺序和全局随机数不影响结果。form始终保留，target poem及原始标签不变。TrainingExample分别保存available_controls与active_controls。evaluation即training=False时强制有效dropout=0，即使配置概率为1也保留所有可用控制。训练循环每epoch调用set_epoch；这个机制减少来源捷径，但不保证彻底消除来源分布差异。

## 三种混合监督模式

| 模式 | 本次已准备条数 | 说明 |
|---|---:|---|
| gold-only | 24 | 六维人工监督 |
| gold+partial-silver | 849 | 24 Gold + 825 Partial Silver |
| gold+partial-silver+form-only | 849 | form-only接口已实现，本次没有加载18k语料 |

MixedPoetryDataset显式加载每个来源并按各自stage验证；Gold另外要求既有人工确认provenance。跨来源重复ID拒绝。TrainingExample保留source、supervision_type、sampling_weight、source文件及哈希、原annotation/metadata；这些元信息不进入模型prompt。清单逐条保存来源和监督类型，不是失去来源的简单拼接。

来源采样总权重默认均为1，可用source_weights配置。每条采样权重=该来源总权重/来源样本数，因此本次Gold每条为1/24、Silver每条为1/825；训练DataLoader用WeightedRandomSampler有放回采样，默认一epoch抽取总条数849次，预期各来源总抽样占比相同。evaluation不使用该加权采样。旧直接Gold Dataset仍使用原DataLoader路径。train_baseline可接收显式构建的MixedPoetryDataset，未来真正训练时保存data_manifest.json；当前未调用训练函数。

只检查数据的接口：

```bash
python scripts/inspect_mixed_data.py --gold data/processed/style_annotation/gold_calibration_v1.jsonl --partial-silver data/processed/partial_silver_v1/partial_silver_v1.jsonl --mode gold+partial-silver --control-dropout 0.3 --training-view
```

去掉--training-view即evaluation视图。第三模式可选--form-only路径，make_form_only负责生成独立结构监督记录；没有隐式读取整个corpus。

## 验证与文件

Partial Silver validator：825/825通过，无重复ID。42个既有style_annotation文件哈希保持一致；Gold schema未修改。

完整测试 `pytest tests/ -q`：139 passed, 1 warning in 254.90s (0:04:14)

实际数据：research/data/processed/partial_silver_v1/partial_silver_v1.jsonl；统计：partial_silver_v1_report.json；排除记录：partial_silver_v1_rejected.jsonl；三个manifest文件记录混合来源及权重；prompt_examples.json保存真实prompt与独立target。
