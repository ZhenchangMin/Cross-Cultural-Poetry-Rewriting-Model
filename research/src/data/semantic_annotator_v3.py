"""Development CV, dimension-specific labels, then independent verbatim evidence."""
from collections import Counter
from itertools import combinations
import json
import math
import random

DIMS = ('emotion', 'diction', 'expression', 'energy')
SEED = 20260925
SEMANTIC_GATE = {'emotion': .70, 'diction': .60, 'expression': .60, 'energy': .60}
PROTOCOL_GATE = .90
GUIDANCE = {
    'emotion': '判断主要情感，可选1或2个标签。情感类别不等于语言气势。',
    'diction': '判断措辞：plain质朴自然；refined典雅凝练；ornate绮丽雕饰。只判断措辞，不判断情绪。',
    'expression': '判断抒情方式：direct直接说出感受；balanced景物叙述与情感表达交融；implicit以景物或言外之意含蓄寄情。只使用这三个标签。',
    'energy': '判断语言节奏与表达力度：gentle舒缓柔和；balanced平稳适中；vigorous强烈、顿挫或奔放。悲伤不必强烈，快乐不必奔放，写山川也不自动属于vigorous。不要用情感标签代替气势。',
}


def features(row):
    return {f'{d}:{v}' for d in DIMS for v in (row['style'][d] if d == 'emotion' else [row['style'][d]])}


def make_folds(rows, seed=SEED):
    """Seeded stratified search: exact sizes/form quotas, minimize label imbalance."""
    rows = sorted(rows, key=lambda r: r['id'])
    if len(rows) != 24 or len({r['id'] for r in rows}) != 24:
        raise ValueError('V3 requires exactly 24 distinct confirmed Gold')
    by_id = {r['id']: r for r in rows}
    totals = Counter(x for r in rows for x in features(r))
    forms = {f: [r['id'] for r in rows if r['form'] == f] for f in ('qijue7', 'qilv7')}
    if sorted(map(len, forms.values())) != [11, 13]:
        raise ValueError('Re-design quotas if actual form counts change')
    larger = max(forms, key=lambda f: len(forms[f]))
    rng = random.Random(seed)
    best = None
    for _ in range(4000):
        pools = {f: rng.sample(ids, len(ids)) for f, ids in forms.items()}
        folds = [[] for _ in range(4)]
        for f, pool in pools.items():
            quotas = [4, 3, 3, 3] if f == larger else [2, 3, 3, 3]
            start = 0
            for fold, size in zip(folds, quotas):
                fold.extend(pool[start:start + size]); start += size
        counts = [Counter(x for rid in fold for x in features(by_id[rid])) for fold in folds]
        # 每个校准子集都必须保有每个已有标签，不能把稀有类别全部放进evaluation。
        if any(c[label] == total for c in counts for label, total in totals.items()):
            continue
        score = sum((c[label] - total / 4) ** 2 / total for c in counts for label, total in totals.items())
        key = (score, tuple(tuple(sorted(f)) for f in folds))
        if best is None or key < best:
            best = key
    if best is None:
        raise ValueError('No feasible folds')
    return [{'fold': i, 'evaluation_ids': list(ids),
             'calibration_ids': sorted(set(by_id) - set(ids))} for i, ids in enumerate(best[1])]


def select_anchors(rows, dimension):
    """Coverage first; class medoids in source-character space are proxy anchors."""
    rows = sorted(rows, key=lambda r: r['id'])
    labels = lambda r: set(r['style'][dimension] if dimension == 'emotion' else [r['style'][dimension]])
    chars = lambda r: {c for c in r['text'] if '\u4e00' <= c <= '\u9fff'}
    def calculate_centrality(row):
        peers = [r for r in rows if r['id'] != row['id'] and labels(r) & labels(row)]
        a = chars(row)
        return sum(len(a & chars(r)) / max(1, len(a | chars(r))) for r in peers) / max(1, len(peers))
    centralities = {r['id']: calculate_centrality(r) for r in rows}
    centrality = lambda row: centralities[row['id']]
    if dimension == 'emotion':
        def score(group):
            return (len(set().union(*(labels(r) for r in group))),
                    sum(len(labels(r)) == 1 for r in group), sum(centrality(r) for r in group))
        chosen = max(combinations(rows, 4), key=score)
    else:
        chosen = []
        for label in sorted(set().union(*(labels(r) for r in rows))):
            candidates = [r for r in rows if label in labels(r)]
            chosen.append(max(candidates, key=centrality))
    return [{'id': r['id'], 'label': r['style'][dimension], 'centrality': centrality(r)} for r in chosen]


def semantic_prompt(poem, dimension, examples, schema):
    definitions = json.dumps(schema['style'][dimension]['values'], ensure_ascii=False)
    shots = '\n\n'.join('诗：\n' + r['text'] + '\n答案：' + json.dumps(
        {'value': r['style'][dimension], 'confidence': .8}, ensure_ascii=False) for r in examples)
    return ('只判断一个维度：' + dimension + '。' + GUIDANCE[dimension] + '\n标签定义：' + definitions +
            '\n只输出两个键的JSON：value和confidence。confidence是0到1数值。不要输出证据或解释。' +
            ('value必须为1到2个合法英文标签的数组。' if dimension == 'emotion' else 'value必须为一个合法英文标签字符串。') +
            '\n示例confidence仅演示格式，不是人工概率。\n' + shots + '\n\n待标注诗：\n' + poem + '\n答案：')


def parse_object(raw):
    text = raw.strip(); wrapper = False
    if text.startswith('```') and text.endswith('```') and '\n' in text:
        text = text.split('\n', 1)[1].rsplit('```', 1)[0].strip(); wrapper = True
    try:
        obj = json.loads(text)
        return (obj if isinstance(obj, dict) else None), wrapper
    except (ValueError, TypeError):
        return None, wrapper


def normalize(raw, dimension, schema):
    obj, wrapper = parse_object(raw)
    value = obj.get('value') if obj is not None else None
    confidence = obj.get('confidence') if obj is not None else None
    allowed = schema['style'][dimension]['values']
    normalized = value; repairs = []
    type_valid = isinstance(value, list) if dimension == 'emotion' else isinstance(value, str)
    if dimension == 'emotion' and isinstance(value, str) and value in allowed:
        normalized = [value]; repairs.append('emotion_string_to_singleton_list')
    if dimension != 'emotion' and isinstance(value, list) and len(value) == 1 and isinstance(value[0], str) and value[0] in allowed:
        normalized = value[0]; repairs.append('single_label_singleton_list_to_string')
    if dimension == 'emotion':
        valid = (isinstance(normalized, list) and 1 <= len(normalized) <= 2 and
                 all(isinstance(v, str) and v in allowed for v in normalized) and len(set(normalized)) == len(normalized))
    else:
        valid = isinstance(normalized, str) and normalized in allowed
    cv = isinstance(confidence, (float, int)) and not isinstance(confidence, bool) and math.isfinite(confidence) and 0 <= confidence <= 1
    shape = obj is not None and set(obj) == {'value', 'confidence'}
    return {'raw_prediction': value, 'normalized_prediction': normalized if valid else None,
            'label_valid': bool(valid), 'type_valid': type_valid, 'confidence': confidence if cv else None,
            'confidence_valid': cv, 'json_parse_success': obj is not None, 'json_wrapper_removed': wrapper,
            'semantic_schema_success': bool(shape and valid and cv),
            'full_semantic_protocol_valid': bool(shape and valid and cv and type_valid),
            'type_repaired': bool(repairs), 'repair_provenance': repairs, 'llm_repair_used': False}


def evidence_prompt(poem, predictions):
    # 输入仅有原文和固定的模型预测；不接受Gold或examples。
    labels = {d: predictions[d]['normalized_prediction'] for d in DIMS if predictions[d]['label_valid']}
    return ('标签已经确定，禁止修改标签，禁止重新分类或解释整首诗。为每个给定维度找1到3个支持标签的短语。'
            '短语必须逐字复制原文，保留繁简，不能跨换行拼接。找不到就给空数组。'
            '只输出JSON：键为给定维度，值为短语数组。不要输出value、confidence、标签或说明。\n' +
            json.dumps({'poem': poem, 'fixed_predictions': labels}, ensure_ascii=False))


def validate_evidence(raw, poem, predictions):
    obj, _ = parse_object(raw)
    expected = {d for d in DIMS if predictions[d]['label_valid']}
    shape = obj is not None and set(obj) == expected
    result = {}
    for d in DIMS:
        value = obj.get(d) if obj is not None else None
        valid = (d in expected and isinstance(value, list) and 1 <= len(value) <= 3 and
                 all(isinstance(s, str) and bool(s.strip()) and s in poem for s in value))
        result[d] = {'evidence': value, 'evidence_valid': bool(valid), 'evidence_attempted': d in expected}
    return {'json_parse_success': obj is not None, 'schema_success': shape, 'dimensions': result,
            'all_dimensions_success': bool(shape and all(v['evidence_valid'] for v in result.values()))}


def evaluate(rows, records, schema):
    lookup = {r['id']: r for r in records}
    if len(lookup) != len(records) or set(lookup) != {r['id'] for r in rows}:
        raise ValueError('Evaluation IDs must match exactly')
    n = len(rows); dimensions = {}; failures = []
    for d in DIMS:
        correct = tp = fp = fn = valid = 0
        confusion = Counter(); pairs = Counter(); gold_counts = Counter(); predicted_counts = Counter()
        protocol = Counter()
        for row in rows:
            record = lookup[row['id']]; p = record['semantic'][d]
            gold = row['style'][d]; pred = p['normalized_prediction']; valid += p['label_valid']
            for field in ('json_parse_success', 'semantic_schema_success', 'full_semantic_protocol_valid', 'type_valid', 'type_repaired'):
                protocol[field] += p[field]
            protocol['evidence_success'] += record['evidence']['dimensions'][d]['evidence_valid']
            protocol['evidence_attempted'] += record['evidence']['dimensions'][d]['evidence_attempted']
            if d == 'emotion':
                a, b = set(gold), set(pred or [])
                tp += len(a & b); fp += len(b - a); fn += len(a - b); ok = a == b
                gold_counts.update(a); predicted_counts.update(b)
                for label in a - b: confusion['missed:' + label] += 1
                for label in b - a: confusion['extra:' + label] += 1
                for x in a - b:
                    for y in b - a: pairs[x + '->' + y] += 1
            else:
                ok = gold == pred; gold_counts[gold] += 1; predicted_counts[pred or '<invalid>'] += 1
                confusion[gold + '->' + (pred or '<invalid>')] += 1
            correct += ok
            if not ok: failures.append({'id': row['id'], 'dimension': d, 'gold': gold, 'prediction': pred,
                                        'raw_prediction': p['raw_prediction'], 'label_valid': p['label_valid']})
        m = {'n': n, 'accuracy': correct / n, 'label_coverage': valid / n,
             'accuracy_on_legal_predictions': correct / valid if valid else None,
             'confusion': dict(confusion), 'confusion_label_pairs': dict(pairs.most_common()),
             'gold_distribution': dict(gold_counts), 'prediction_distribution': dict(predicted_counts),
             'protocol': {k + '_rate': protocol[k] / n for k in ('json_parse_success', 'semantic_schema_success', 'full_semantic_protocol_valid', 'type_valid', 'evidence_success')},
             'normalization_count': protocol['type_repaired'],
             'evidence_success_on_attempted': protocol['evidence_success'] / protocol['evidence_attempted'] if protocol['evidence_attempted'] else None}
        if d == 'emotion':
            m.update(precision=tp / (tp + fp) if tp + fp else 0, recall=tp / (tp + fn) if tp + fn else 0,
                     f1=2 * tp / (2 * tp + fp + fn) if 2 * tp + fp + fn else 0,
                     counts={'tp': tp, 'fp': fp, 'fn': fn}, averaging='micro')
        dimensions[d] = m
    protocol = {field + '_rate': sum(all(r['semantic'][d][field] for d in DIMS) for r in records) / n
                for field in ('json_parse_success', 'semantic_schema_success', 'full_semantic_protocol_valid')}
    protocol['evidence_success_rate'] = sum(r['evidence']['all_dimensions_success'] for r in records) / n
    protocol['full_two_stage_success_rate'] = sum(r['evidence']['all_dimensions_success'] and all(r['semantic'][d]['full_semantic_protocol_valid'] for d in DIMS) for r in records) / n
    return {'n': n, 'dimensions': dimensions, 'record_level_protocol': protocol, 'errors': failures,
            'note': 'All evaluation records remain in semantic denominators, independent of evidence; invalid labels are missing predictions.'}


def gate(report, rules):
    ready = {}; quality = {}; reasons = []
    for d in DIMS:
        m = report['dimensions'][d]; key = 'f1' if d == 'emotion' else 'accuracy'
        quality[d] = m[key] >= SEMANTIC_GATE[d]
        ready[d] = quality[d] and m['protocol']['full_semantic_protocol_valid_rate'] >= PROTOCOL_GATE and m['protocol']['evidence_success_rate'] >= PROTOCOL_GATE
        if not ready[d]: reasons.append(f'{d}: metric={m[key]:.4f} (required {SEMANTIC_GATE[d]}), semantic protocol={m["protocol"]["full_semantic_protocol_valid_rate"]:.4f}, evidence={m["protocol"]["evidence_success_rate"]:.4f} (each required .90)')
    for d, key, threshold in [('imagery', 'f1', .70), ('density', 'accuracy', .95)]:
        quality[d] = ready[d] = rules[d][key] >= threshold
        if not ready[d]: reasons.append(f'{d}: {key}={rules[d][key]:.4f} < {threshold}')
    joint = report['record_level_protocol']['full_two_stage_success_rate']
    if joint < PROTOCOL_GATE: reasons.append(f'full two-stage success={joint:.4f} < .90')
    return {'silver_gate': 'pass' if all(ready.values()) and joint >= PROTOCOL_GATE else 'fail',
            'dimension_ready': ready, 'semantic_quality_threshold_met': quality, 'reasons': reasons,
            'readiness_scope': 'development-only screening, not independent test proof; future per-record confidence filters still apply',
            'silver_batch_started': False}
