# Semantic Annotator V3 frozen protocol

V3仅处理现有24条人工Gold的development 4-fold CV，每折18条calibration、6条evaluation。任何Gold变动都会中止当前配置。命令行没有训练、批量Silver或人工审核入口；原始Gold、preannotation及v1/v2实验不覆盖。

## 两阶段

第一阶段分别调用emotion、diction、expression、energy分类。每次仅返回`{"value": ..., "confidence": ...}`，不用evidence。各维独立few-shot，只传该维标签，不传目标Gold、题目、作者或审核意见。

合法emotion字符串可归一化为单元素数组；合法single-label单元素数组可归一化为字符串，记录type_valid=false、type_repaired=true与repair_provenance。非法enum不猜测、不翻译、不截断。LLM repair完全禁用，llm_repair_used恒为false。

第二阶段只接收原诗及已经确定的合法模型标签，不接收Gold或few-shot，也不允许重新分类。输出每维1–3条原文短语。严格按原始文本检查连续子串，保留繁简和换行。无合法标签的维度不要求生成证据；统计全量成功率时仍计为失败。evidence解析、结构或逐字校验失败均不修改语义预测。

原始请求逐次保存，缓存绑定完整prompt、冻结配置哈希和输出token限制；恢复运行不会重复已完成请求。每首最多4次semantic调用和1次evidence调用。

## CV与few-shot

seed=20260925。从4000个确定性候选划分中，选择按标签频率加权后分布偏差最小的划分；每折6条、七绝/七律配额为4/2、3/3、3/3、3/3。每个calibration必须保有全部已有语义类别。每条恰好被evaluation一次。

单标签各维每类选1条同类文字Jaccard中心样本。emotion选4条，依次最大化类别覆盖、单标签样本数和同类文字代表性。所有平局按ID排序解决。文字代表性只是可复现代理，不声称新的人类清晰度判断。实际ID、标签及中心度在frozen_cv.json。calibration中的标签用于示例选择是允许的；目标evaluation绝不进入自己的示例。

模型为本地原始Qwen2.5-1.5B-Instruct，greedy解码；semantic最多96个新token，evidence最多320个。无LoRA、无训练。提示及schema在推理前冻结，此轮不依据fold指标调参。

## 指标与gate

emotion使用pooled micro precision/recall/F1，其余accuracy。所有24条始终进入分母；非法标签记缺失，evidence错误不影响语义计分。分别报告逐维与四维同时通过的JSON、semantic schema和evidence成功率。

semantic schema成功要求固定字段、合法可归一化标签及0–1有限数值confidence；full semantic protocol额外要求原始标签类型正确。evidence成功只代表结构与原文子串符合协议，不证明语义相关性。

保留原质量门槛：emotion F1≥0.70，diction/expression/energy accuracy≥0.60，imagery F1≥0.70，density accuracy≥0.95；整体两阶段完整协议成功率≥0.90。逐语义维dimension_ready还要求该维原始semantic protocol与evidence成功率各≥0.90。未来逐条confidence门槛仍为semantic 0.8、imagery 0.7、density 0.5；模型自报confidence不等于已校准概率。

固定lexicon/rule v1.1仅在这24条上补充评估imagery/density，不在每折训练。规则历史上使用过Gold校准，结果不可表述为独立泛化验证。所有Gold都有历史开发暴露；dimension_ready仅是development筛查，不自动授权Silver构建。

## 复现

在research目录、具有原模型缓存的项目Python环境中运行：

```bash
python scripts/semantic_v3.py prepare
python scripts/semantic_v3.py run
pytest tests/ -q
```

完成实验后拒绝覆盖冻结配置或最终报告。结果目录为data/processed/semantic_annotator_v3。当前配置依赖冻结的本地文件字节哈希，跨平台改变换行会导致核对失败；不得为绕过核对而覆写已有实验。
