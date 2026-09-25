from pathlib import Path
from collections import Counter
import hashlib
import json
import sys

root = Path(__file__).resolve().parents[2]
research = root / 'research'
out = research / 'data/processed/semantic_annotator_v3'
load = lambda p: json.loads(p.read_text(encoding='utf-8'))
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
if len(sys.argv) > 1 and sys.argv[1] == 'snapshot':
    paths = list((research / 'data/processed/style_annotation').glob('*'))
    paths += list((research / 'data/processed/silver_annotation_v1').glob('*'))
    paths += list((research / 'data/processed/semantic_annotator_v2_r3').glob('*'))
    snapshot = {p.relative_to(root).as_posix(): sha(p) for p in paths if p.is_file()}
    (out / 'protected_input_snapshot.json').write_text(json.dumps(snapshot, indent=2) + '\n', encoding='utf-8')
    print('Protected input snapshot:', len(snapshot)); sys.exit()

snapshot = load(out / 'protected_input_snapshot.json')
assert all(sha(root / p) == digest for p, digest in snapshot.items())
config = load(out / 'frozen_cv.json')
report = load(out / 'semantic_annotator_v3_cv_report.json')
records = [json.loads(line) for line in (out / 'out_of_fold_predictions.jsonl').read_text(encoding='utf-8').splitlines()]
gold = {r['id']: r for r in map(json.loads, (research / 'data/processed/style_annotation/gold_calibration_v1.jsonl').read_text(encoding='utf-8').splitlines())}
dims = ['emotion', 'diction', 'expression', 'energy']
agg = report['aggregate']; energy = agg['dimensions']['energy']
illegal = Counter(str(r['semantic']['energy']['raw_prediction']) for r in records if not r['semantic']['energy']['label_valid'])
emotion_energy = Counter(','.join(r['semantic']['emotion']['normalized_prediction'] or []) + ' -> ' + str(r['semantic']['energy']['normalized_prediction']) for r in records)
evidence_roots = Counter(); evidence_echoes = 0; evidence_json_valid = 0
for record in records:
    raw = record['evidence_raw'].strip()
    if raw.startswith('```') and raw.endswith('```') and '\n' in raw:
        raw = raw.split('\n', 1)[1].rsplit('```', 1)[0].strip()
    try:
        obj = json.loads(raw)
    except ValueError:
        obj = None
    if isinstance(obj, dict):
        evidence_json_valid += 1
        evidence_roots[','.join(sorted(obj))] += 1
        evidence_echoes += 'fixed_predictions' in obj
analysis = {'energy': {'gold_distribution': energy['gold_distribution'], 'prediction_distribution': energy['prediction_distribution'],
    'illegal_raw_values': dict(illegal), 'confusion': energy['confusion'], 'emotion_prediction_vs_energy_prediction': dict(emotion_energy),
    'causal_limit': 'Single configuration, 24 historically exposed Gold. Confusion supports descriptive diagnosis only; no ablation isolates definitions, examples, and model capacity.'},
    'evidence': {'json_parse_count': evidence_json_valid, 'input_wrapper_echo_count': evidence_echoes, 'root_key_patterns': dict(evidence_roots)},
    'protected_inputs_verified': len(snapshot), 'gold_modified': False, 'training_started': False, 'silver_batch_started': False}
(out / 'error_analysis.json').write_text(json.dumps(analysis, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
text = '''# Semantic Annotator V3：两阶段 development 4-fold CV

本轮仅使用既有24条人工Gold；每折18条calibration、6条evaluation，每条恰好被evaluation一次。固定seed=20260925。四维分别分类，之后单独提取evidence；没有LLM repair。未运行957条Silver，未训练模型，未新增人工审核，未修改Gold。原始模型为Qwen2.5-1.5B-Instruct，不加载LoRA。

## 实验边界

全部Gold此前参与过项目指南或开发，本实验明确是development cross-validation，不能声称严格独立test。每折只从该折18条calibration选few-shot，evaluation从不进入自己的提示。提示、代码、划分、门槛在推理前冻结，没有根据fold结果调参。

划分从4000个固定seed候选中选择：每折恰好6条、诗体接近平衡，最小化按类别频率加权的标签分布偏差，并保留每个calibration子集中的所有已有语义类别。lonely、indignant在Gold中无正样本，无法估计这些类别的召回。

## Aggregate metrics（24条out-of-fold）

非法标签记为缺失，始终保留在24条总分母中；evidence、confidence或格式失败不会删除合法语义标签。emotion使用micro P/R/F1。

| 维度 | 主指标 | 合法标签覆盖率 | JSON成功率 | semantic schema成功率 | evidence成功率 |
|---|---:|---:|---:|---:|---:|
'''
for d in dims:
    m = agg['dimensions'][d]; p = m['protocol']; key = 'f1' if d == 'emotion' else 'accuracy'
    text += f'| {d} | {key}={m[key]:.4f} | {m["label_coverage"]:.1%} | {p["json_parse_success_rate"]:.1%} | {p["semantic_schema_success_rate"]:.1%} | {p["evidence_success_rate"]:.1%} |\n'
e = agg['dimensions']['emotion']
text += f'\nemotion precision={e["precision"]:.4f}，recall={e["recall"]:.4f}，F1={e["f1"]:.4f}。\n\n'
text += '| 每首四维全部通过的协议指标 | 比例 |\n|---|---:|\n'
for k, v in agg['record_level_protocol'].items(): text += f'| {k} | {v:.1%} |\n'
text += '\nsemantic schema允许合法的确定性单元素类型归一化；full semantic protocol仍要求模型原始类型正确。evidence success只检查原文逐字子串和输出结构，并不能证明证据的语义相关性。逐维evidence率以24条为分母，另有attempted分母指标保存在JSON。\n\n'
text += f'evidence阶段JSON可解析{evidence_json_valid}/24；其中{evidence_echoes}/24复述了输入的fixed_predictions外层结构，未按要求生成四个维度到原文短语数组的映射。根字段模式：`{dict(evidence_roots)}`。这是独立证据阶段的协议失败，不能据此清除第一阶段的合法语义标签；本轮保留失败结果，不做LLM repair。\n\n'
text += '确定性normalization次数：' + str({d: agg['dimensions'][d]['normalization_count'] for d in dims}) + '；LLM repair调用次数=0。\n\n'
text += '## 每fold结果\n\n| Fold | 七绝/七律 | emotion P/R/F1 | diction acc | expression acc | energy acc | JSON全通过 | semantic schema全通过 | evidence全通过 |\n|---|---|---|---:|---:|---:|---:|---:|---:|\n'
for f, split in zip(report['folds'], config['folds']):
    m = f['dimensions']; p = f['record_level_protocol']; e = m['emotion']; forms = split['evaluation_forms']
    text += f'| {f["fold"] + 1} | {forms["qijue7"]}/{forms["qilv7"]} | {e["precision"]:.3f}/{e["recall"]:.3f}/{e["f1"]:.3f} | {m["diction"]["accuracy"]:.3f} | {m["expression"]["accuracy"]:.3f} | {m["energy"]["accuracy"]:.3f} | {p["json_parse_success_rate"]:.1%} | {p["semantic_schema_success_rate"]:.1%} | {p["evidence_success_rate"]:.1%} |\n'
text += '\n每折仅6条，单标签准确率每条影响16.7个百分点；汇总为24条pooled指标，不是简单平均fold F1。\n\n## Confusion\n\n'
for d in ['expression', 'energy', 'diction']:
    labels = list(load(research / 'configs/style_schema.json')['style'][d]['values'])
    text += f'### {d}\n\n行是真实Gold，列是预测；invalid也保留。\n\n| Gold \\ Prediction | ' + ' | '.join(labels + ['invalid']) + ' |\n|---|' + '---:|' * (len(labels) + 1) + '\n'
    confusion = agg['dimensions'][d]['confusion']
    for a in labels:
        text += '| ' + a + ' | ' + ' | '.join(str(confusion.get(a + '->' + b, 0)) for b in labels + ['<invalid>']) + ' |\n'
text += '\n### emotion\n\n遗漏/多报标签：`' + str(agg['dimensions']['emotion']['confusion']) + '`。\n\n主要替代标签对：`' + str(agg['dimensions']['emotion']['confusion_label_pairs']) + '`。多标签替代对为描述性配对，不能视为独立样本数。\n\n'
text += '## Energy诊断\n\n'
text += f'- Gold分布：`{energy["gold_distribution"]}`；模型分布：`{energy["prediction_distribution"]}`。\n'
text += f'- 非法原始标签：`{dict(illegal)}`；合法标签覆盖率={energy["label_coverage"]:.1%}。\n'
text += f'- 主要可观察问题是类别偏置：24条中{energy["prediction_distribution"].get("balanced", 0)}条预测balanced；gentle→balanced共{energy["confusion"].get("gentle->balanced", 0)}条，vigorous→balanced共{energy["confusion"].get("vigorous->balanced", 0)}条。标签全部合法，因此本轮energy低分主要是语义判断错误，而不是JSON或enum错误。始终猜Gold多数类gentle的描述性基线为14/24=58.3%，高于当前模型；这不是独立训练的基线。\n'
text += '- 每fold均提供gentle/balanced/vigorous三个类别的anchor；标签缺类不能解释错误，但文字相似度代表性不保证气势边界最清晰。\n'
text += '- 提示明确区分情感与节奏力度，且单独分类。是否仍与emotion混淆，只能结合联合预测表和具体诗判断；没有对照消融，不能把因果归结为某一种提示或模型能力。\n'
text += '- 定义延续现有schema并补充操作性解释，没有重标Gold；定义本身是否充分清晰仍未被独立检验。error_analysis.json保存分布、非法输出及emotion/energy联合预测。\n\n'
text += '其他明显偏置：diction没有预测任何refined（Gold有17条），expression把15条预测为implicit（Gold有4条）。这些结果不支持把协议可靠性提升视作语义分类改善。V2的8条结果与本轮24条CV评估集及few-shot不同，不作直接性能增减结论。\n\n'
text += '## Few-shot选择\n\n单标签每类选1条，以同类诗汉字集合Jaccard相似度均值最大的样本作为代表；emotion选4条，优先覆盖类别、其次单标签清晰度、再同类代表性；平局按ID排序。此为确定性代理，不是新的人工清晰度确认。每折独立选择，仅把目标dimension标签放入该维提示，示例confidence=0.8只是格式示范。\n\n'
for fold in config['folds']:
    text += f'### Fold {fold["fold"] + 1}\n\n'
    for d in dims:
        text += '- ' + d + '：' + '；'.join(gold[a['id']]['metadata']['title'] + ' `' + a['id'] + '` → ' + str(a['label']) for a in fold['anchors'][d]) + '\n'
    text += '\n'
text += '## Dimension readiness与Silver gate\n\n'
text += '原门槛不降低：emotion F1≥0.70，diction/expression/energy accuracy≥0.60，imagery F1≥0.70，density accuracy≥0.95；完整两阶段协议≥0.90。逐语义维ready还要求本维原始semantic protocol与evidence成功率各≥0.90。ready仅表示开发集上的候选来源，不等于已获独立泛化验证或可立即放行整批数据。未来逐条confidence门槛保持semantic≥0.8、imagery≥0.7、density≥0.5。\n\n'
text += '| Dimension | 质量指标达标 | dimension_ready |\n|---|---|---|\n'
for d, value in report['gate']['dimension_ready'].items(): text += f'| {d} | {report["gate"]["semantic_quality_threshold_met"][d]} | {value} |\n'
text += f'\n固定rule v1.1在24条上的imagery F1={report["rules"]["imagery"]["f1"]:.4f}，density accuracy={report["rules"]["density"]["accuracy"]:.4f}；规则此前受Gold校准，不能视为新独立验证。\n\n**silver_gate={report["gate"]["silver_gate"]}**\n\n'
text += '\n'.join('- ' + reason for reason in report['gate']['reasons']) + '\n\n'
text += f'## 完整性与测试\n\n{len(snapshot)}个原有Gold、preannotation、review、v1/v2结果及候选文件哈希一致。原始请求和响应在requests.jsonl，out-of-fold结果及独立evidence校验在out_of_fold_predictions.jsonl，完整报告在semantic_annotator_v3_cv_report.json。\n\n'
text += '测试日志：research/outputs/semantic_v3_tests.log。\n\n' + (research / 'outputs/semantic_v3_tests.log').read_text(encoding='utf-8').splitlines()[-1] + '\n'
(root / 'docs/semantic_annotator_v3_results.md').write_text(text, encoding='utf-8')
print('V3 report and error analysis written; protected inputs unchanged')
