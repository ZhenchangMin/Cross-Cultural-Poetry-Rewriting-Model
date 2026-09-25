# Gold Calibration V1 数据冻结与下一轮审核

日期：2026-09-24。本轮只整理数据和运行测试，没有启动模型训练。此前试训属于历史工程验证，不是本轮正式训练成绩。

## 当前真实审核状态

旧 `human_review_state_v1.json` 是 30 条 pending 的初始化快照；有效的最新确认来源是 `human_review_state24_v2.json`，含 21 accept、3 edit。新建 `human_review_state30_reconciled_v1.json` 汇总全部 30 条：24 confirmed、6 pending、0 human exclude。两份原状态及人工填写文档均未覆盖。

24 条都保留 id、原文、form、完整六维 final style、reviewer、decision 和原审核 provenance。本次新命名 `gold_calibration_v1.jsonl` 与旧 `gold_calibration24_v1.jsonl` 的 id/text/form/style 完全一致；新增命名用于本轮 30 条部分提升工作流，非第二套人工标签。

## 校验与审计

Gold validator：24/24 valid，0 invalid，0 duplicate IDs。Dataset Loader：len=24；保存两条完整 prompt/target/form/style；通过修改 metadata 的不变性检查，作者和标题不进入 prompt。

样本含 13 首 qijue7、11 首 qilv7、24 位作者。以下是描述性计数，emotion/imagery 为多标签，不能按总和等于24来解释。

| 维度 | 标签与条数 |
|---|---|
| emotion | serene 7；joyful 6；melancholic 13；lonely 0；heroic 3；indignant 0 |
| imagery | landscape 18；celestial 7；season_weather 11；flora 15；fauna 7；travel 7；frontier 3；human_culture 16 |
| diction | plain 3；refined 17；ornate 4 |
| expression | direct 5；balanced 15；implicit 4 |
| energy | gentle 14；balanced 6；vigorous 4 |
| density | sparse 4；medium 8；dense 12 |

低频定义为次数 ≤2（含0）；当前仅 lonely=0、indignant=0。未因标签稀少而重采样、删样本或修改标签。

## 标注边界发现

- 实际人工修改：emotion 2条（删除非主导的 serene），diction 1条（ornate→refined）。这是单人审核记录，不能计算评委间一致性，也不能据此断言整个六维体系的争议排名。
- imagery 规则集合与最终标签有 17/24 条不同，是当前最明显的规则弱点。词典子串可能误读词义，例如瑟瑟波中的瑟；政治/神话符号也不能一律算实景动物。
- density 与固定代理全部一致是遵循定义的结果，不证明它能衡量文学密度。旧助手报告里的6次密度覆盖已由冻结词表政策取代。
- expression 的直抒/情景交融/含蓄需要看整诗，而非情绪词数量；energy 不能由军旅词或情绪正负代替。第11首的 energy 曾被提出疑问，最终保留 balanced；这不计为一次修改。
- 规则只给 imagery/density；其余四维不能因规则没有输出而被称为“正确”或“错误”。
- 繁简保持来源原文，不静默转字；字形及词典更改须单独版本化。

上述定义已小幅补入 `docs/style_annotation_guideline_v1.md`，未改枚举。现阶段可以按补充后的指南继续人工标注，无需先重写 schema。

## 六条未决

单独文件：`research/data/processed/style_annotation/adjudication_pending_v1.jsonl`。
保留原文、元数据、规则预标注、助手建议、当前人审、备注和已有来源；没有明确维度字段时 `disputed_dimensions=[]`，不据助手措辞推造人工冲突。

| 题目 | 已有助手建议及待查事项（不是最终决定） |
|---|---|
| 句 | 多场合辑句而非完整七律，维持排除建议。 |
| 春日與王右丞過新昌里訪呂逸人不遇 | 枉相过/任相过影响不遇语气，高卧眄/高枕盼亦不同；首版暂缓，保留两种记录，不静默换字。 |
| 登岳陽樓 | 自统/自绕异文仍待校勘；另查到北宋同名官员和误收入全唐诗的二手考证线索，尚未完成身份与作品对应核验。首版暂缓。 |
| 字字雙 | 词律明确列字字双二十八字词调并解释四句俱押韵；另有官坡馆联句近重复，首版七绝任务移出，保留供后续词体研究。 |
| 漁父引二首 一 | 全唐词收录、五代诗话记唱渔父引并引此词；林寺/村寺等异文未定。首版七绝任务移出，未删除原记录。 |
| 奉和聖製夏日遊石淙山 | 颍阴/水阴另见衆阴的电子转录；不同证据不能靠多数投票判正误，首版暂缓。 |

## 下一批100条

从原1000条候选中排除全部30条 calibration，剩970条。固定 seed=20260924；先选高风险记录，再优先选当前出现次数最少的作者，平局按基于排序ID的固定随机顺序决定。

结果：50 qijue7、50 qilv7、100位作者，每位1首；覆盖剩余13条高风险“句”记录。高风险用于质量审核，不自动判排除，更不自动升Gold。所有 canonical style 留空，只附 lexicon v1.1 imagery/density 提示，其余语义维度未自动填写。输入文件、词表、规则代码 SHA256 和样本ID清单保存在抽样报告。

这是风险增强的审核批次，不是无偏抽样，也不是独立测试集。现有异文清单仍非全库去重保证。

- JSONL：`review_batch_v2_100.jsonl`。
- 抽样报告：`review_batch_v2_report.json`。
- 便于逐首阅读填写的副本：`docs/review_batch_v2_100_review.md`；填写不会自动写入 Gold，后续必须重新导入与校验。

## 实现与验证入口

`research/scripts/prepare_gold_calibration.py` 调用已有 `human_review.py promote --allow-partial`，默认 promotion 仍拒绝未完成审核。新增模块负责状态汇总、未决导出、审计和抽样；promotion 仅补充保存完整审核 provenance，未降低校验门槛。

测试覆盖：部分提升、pending不进Gold、24条validator/loader、未决导出、状态冲突拒绝、抽样复现与作者覆盖、审计计数。完整 `pytest tests/ -q`：88 passed，1条 jieba/pkg_resources 弃用警告，103.34秒。日志见 `research/outputs/gold_calibration_full_tests_20260924.log`；提交号见 Git 历史和交付消息。

下一步：先审核13条高风险记录的完整性/体裁，再分批审核其余87条的风格；有疑问继续 pending。完成 pilot 扩充与一致性检查后，再讨论正式训练。
