# B0 Pilot：预先固定的评价方案

本轮只运行工程smoke及8条固定子集overfit，不报告正式B0-A/B实验效果，也不开展新人工审核。Qwen仅用于获准的训练及训练后生成检查，不用于重新标注数据。

## 两种数据范围必须分开

最终B0-A配置使用全部24条Gold，B0-B使用24条Gold＋825条Partial Silver。它们的Gold重构指标是in-sample描述，不能称held-out性能。dataset source manifest保留来源、监督类型、采样权重和输入哈希。

未来若做development CV，必须复用既有4-fold清单：每折仅18条Gold训练，6条Gold评估；B0-B仅将相同825条Partial Silver加入该折训练。已核对每折ID、去标点原文、已知异文、unresolved及高风险记录的隔离。不能用完整24条训练后再把其中6条声称为held-out。历史开发暴露仍然存在，不称独立test。

此次诊断选fold 1的18条Gold训练池，保留6条不参与smoke/overfit。overfit固定4条Gold＋4条Silver，优先七绝且prompt互不相同；它们都是训练样本，不是validation。

## 正式训练前固定的指标

| 范畴 | 指标 | 来源与限制 |
|---|---|---|
| form compliance | 4/8行、每行7汉字的通过率；另保留原始输出 | 标点规范化后检查；不声称平仄、押韵全部合规 |
| imagery controllability | 对请求imagery的micro precision/recall/F1及逐类覆盖 | 固定lexicon v1.1；只是规则代理，不是新的语义Gold |
| density controllability | 对请求density的accuracy、混淆矩阵 | 固定rule v1.1；畸形输出记失败并报告覆盖率 |
| Gold full-style | 既有Gold全文的teacher-forced NLL/token accuracy，按emotion/diction/expression/energy标签分组描述 | 人工标签来自已有Gold；这些是条件重构指标，不等于生成诗语义风格准确率 |
| 生成诗四个语义维度 | 暂不计分，字段保留为null/not_measured | 禁止使用semantic annotator v1/v2/v3作为评价真值；不新增人工审核 |
| generation quality | 非空率、结构合规、重复行比例、输出原文；训练文本重合度作为记忆诊断 | 无单一“诗歌质量总分”；BLEU/LCS等不得冒充文学质量 |

生成使用greedy、max_new_tokens=128；各模型用同一固定prompt列表，eval时control dropout禁用。指标定义不得在看到正式实验结果后调整门槛。

## Smoke与overfit协议

- Smoke：真实本地Qwen2.5-1.5B-Instruct，从原权重初始化新LoRA，仅10个optimizer steps。batch=1、accumulation=8、lr=2e-4、control dropout=0.1、source weights=0.3/0.7。
- 检查加载、LoRA参数隔离、forward/backward、有限且非零梯度、optimizer更新、显存峰值、adapter保存、从本地base重新加载adapter以及greedy生成。
- loss前后比较使用同一固定8条probe、eval模式、关闭control dropout；另记录首末训练批次loss，二者不可混淆。
- Overfit从原base重新初始化LoRA，不续用smoke adapter。固定8条、control dropout关闭、lr=5e-4、accumulation=4，最多160个optimizer steps；每20步检查。
- 预先规定停止条件：固定子集NLL≤初始的40%，teacher-forced token accuracy≥90%，至少4/8条生成在去标点汉字层面精确复现target。满足即停止；到上限仍失败则报告失败，不借此启动正式训练。
- Checkpoint为adapter-only，保存为smoke/not experiment result。重载后相同probe loss差≤0.001且greedy文本相同，才通过重载检查。

## 正式配置草案的冻结参数

bf16、batch=1、gradient accumulation=8、effective batch=8、max_length=512、gradient checkpointing；LoRA r=16、alpha=32、dropout=0.05，覆盖q/k/v/o及gate/up/down投影；lr=2e-4、seed=20260926、control dropout=0.1。

B0-A先定3 epochs，B0-B先定1 epoch；来源抽样权重A为Gold=1，B为Gold=0.3、Partial Silver=0.7。这里epoch是MixedDataset对应数量的有放回抽样，不保证每首恰好遍历一次。每10个optimizer steps保存checkpoint，并在结束时保存。正式配置仅在smoke及overfit通过后写到configs；本轮不执行这些epochs。
