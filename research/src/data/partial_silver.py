"""Build trusted-dimension Silver without importing or invoking an LLM annotator."""
from collections import Counter
from copy import deepcopy
import hashlib
import json
import re

from .partial_supervision import ANNOTATION_VERSION, PARTIAL_CONTROLS, RULE_VERSION, STYLE_DIMS
from .preannotate_style import imagery_prelabel, density_prelabel, find_imagery_matches
from .validate_dataset import validate_record


def record_hash(row):
    return hashlib.sha256(json.dumps(row, ensure_ascii=False, sort_keys=True).encode()).hexdigest()


def source_fragment(row):
    title = str(row.get('metadata', {}).get('title', '')).strip()
    return bool(re.fullmatch(r'(?:句|斷句|断句|殘句|残句|佚句)(?:\s*[一二三四五六七八九十0-9]+)?', title))


def structural_block(row):
    lines = row['text'].splitlines()
    return {'value': row['form'], 'label_source': 'structural', 'method': 'structural_v1', 'confidence': 1.0,
            'evidence': {'line_count': len(lines), 'line_lengths': [len(x) for x in lines],
                         'scope': 'line/character counts only; not tonal or rhyme certification'}}


def make_partial(row, lexicon, provenance, schema, thresholds=None):
    thresholds = thresholds or {'imagery': .7, 'density': .5}
    # 仅调用两个规则函数；没有语义四维生成，也没有待人工审核状态。
    imagery = imagery_prelabel(row['text'], lexicon)
    density = density_prelabel(row['text'], imagery, lexicon)
    reasons = []
    if not imagery['value']: reasons.append('no_imagery_labels')
    for d, block in [('imagery', imagery), ('density', density)]:
        if block['confidence'] < thresholds[d]: reasons.append('low_confidence:' + d)
    # v1.1内部去换行匹配；不改规则，只排除产生跨行伪短语的记录。
    all_terms = find_imagery_matches(row['text'].replace('\n', ''), lexicon['categories'])
    if any(term not in row['text'] for terms in all_terms.values() for term in terms):
        reasons.append('non_verbatim_rule_evidence')
    if reasons: return None, reasons
    style = {d: None for d in STYLE_DIMS}
    style.update(imagery=imagery['value'], density=density['value'])
    blocks = {'form': structural_block(row)}
    for d, block in [('imagery', imagery), ('density', density)]:
        blocks[d] = {**deepcopy(block), 'label_source': 'rule'}
    metadata = {k: deepcopy(row.get('metadata', {}).get(k)) for k in ('title', 'author', 'dynasty', 'source') if k in row.get('metadata', {})}
    metadata.update(label_source='automatic_partial_silver', review_status='automatic_partial_silver_accepted')
    result = {'id': row['id'], 'text': row['text'], 'form': row['form'], 'style': style,
        'culture': {'adaptation': None}, 'dataset_stage': 'partial-silver', 'available_controls': list(PARTIAL_CONTROLS),
        'supervision': {'form': 'structural_v1', 'imagery': 'silver_rule_v1_1', 'density': 'silver_rule_v1_1'},
        'metadata': metadata, 'annotation': {'version': ANNOTATION_VERSION, 'label_source': 'automatic_partial_silver',
            'per_dimension': blocks, 'provenance': {**provenance, 'source_record_id': row['id'], 'source_record_sha256': record_hash(row)}}}
    issues = validate_record(result, schema, stage='partial-silver')
    if issues: return None, ['invalid_partial_schema:' + x.field for x in issues]
    return result, []


def build_partial(pool, gold, pending, flags, variants, lexicon, schema, provenance):
    if len({r['id'] for r in pool}) != len(pool): raise ValueError('Duplicate candidate IDs')
    gold_ids = {r['id'] for r in gold}; pending_ids = {r['id'] for r in pending}
    excluded = gold_ids | pending_ids
    changed = True
    while changed:
        before = len(excluded)
        for group in variants:
            if excluded.intersection(group['members']): excluded.update(group['members'])
        changed = len(excluded) != before
    protected_texts = {re.sub(r'\W', '', r['text']) for r in gold + pending}
    accepted = []; rejected = []
    for row in pool:
        rid = row['id']; reasons = []
        if rid in gold_ids: reasons.append('existing_gold')
        if rid in pending_ids: reasons.append('unresolved_calibration')
        if rid in excluded - gold_ids - pending_ids: reasons.append('protected_variant')
        if rid not in excluded and re.sub(r'\W', '', row['text']) in protected_texts: reasons.append('protected_duplicate_text')
        high = [f['code'] for f in flags.get(rid, {}).get('flags', []) if f['severity'] == 'high']
        if high: reasons.append('high_risk_quality')
        if source_fragment(row): reasons.append('source_fragment')
        if validate_record(row, schema, stage='candidate'): reasons.append('invalid_candidate_structure')
        result = None
        if not reasons: result, reasons = make_partial(row, lexicon, provenance, schema)
        if reasons: rejected.append({'id': rid, 'title': row.get('metadata', {}).get('title'), 'reasons': reasons, 'high_risk_codes': high})
        else: accepted.append(result)
    return accepted, rejected
