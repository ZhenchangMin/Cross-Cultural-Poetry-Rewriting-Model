"""Reconcile existing reviews, describe Gold, and sample a pending review batch.

No model calls, training, or inferred human decisions occur here.
"""
from collections import Counter
from copy import deepcopy
import random

from .human_review import validate_review_entry
from .preannotate_style import rule_preannotate_record
from .validate_dataset import STYLE_DIMS


def index_unique(rows):
    result = {}
    for row in rows:
        rid = row['id']
        if rid in result:
            raise ValueError(f'duplicate id: {rid}')
        result[rid] = row
    return result


def reconcile_reviews(original, candidates, old_state, current_state, schema):
    """New 30-record snapshot; never mutate either historical review source."""
    originals, updates = index_unique(original), index_unique(candidates)
    if set(old_state['records']) != set(originals):
        raise ValueError('old state must cover exactly original calibration IDs')
    if set(current_state['records']) != set(updates) or not set(updates) <= set(originals):
        raise ValueError('candidate/state IDs mismatch')
    state = {'version': 'v1', 'status': 'human_review_in_progress', 'records': {}}
    rows = []
    for rid, original_row in originals.items():
        row = deepcopy(updates.get(rid, original_row))
        if (row['text'], row['form']) != (original_row['text'], original_row['form']):
            raise ValueError(f'silent text/form change: {rid}')
        old = old_state['records'][rid]
        entry = deepcopy(current_state['records'].get(rid, old))
        if old['decision'] != 'pending' and entry != old:
            raise ValueError(f'conflicting completed reviews: {rid}')
        validate_review_entry(row, entry, schema)
        # A pending prefilled style is a suggestion, not a final judgment.
        if entry['decision'] == 'pending':
            entry['unconfirmed_style_suggestion'] = entry.get('final_style')
            entry['final_style'] = None
        else:
            if not any(entry.get(k) for k in ['document_review', 'confirmation_source', 'resolution']):
                raise ValueError(f'missing confirmation provenance: {rid}')
        row.setdefault('metadata', {}).update(
            text_policy='source_preserved_v1',
            density_policy='frozen_lexicon_proxy_v1_1_on_original_text',
            annotation_scope='single_user_source_assisted_style_review_not_expert_or_full_prosody_certification')
        rows.append(row)
        state['records'][rid] = entry
    return rows, state


def export_unresolved(rows, state, references, rule_rows):
    refs, rules = index_unique(references), index_unique(rule_rows)
    pending = []
    for row in rows:
        rid = row['id']
        entry = state['records'][rid]
        if entry['decision'] != 'pending':
            continue
        ref = refs.get(rid, {})
        pending.append({
            'id': rid, 'title': row['metadata'].get('title'),
            'author': row['metadata'].get('author'), 'text': row['text'], 'form': row['form'],
            'status': 'unresolved', 'gold_eligible': False,
            'rule_prelabel': deepcopy(rules[rid]['annotation']['prelabel']),
            'assistant_proposal': deepcopy(ref.get('style_proposal')),
            'human_review': deepcopy(entry),
            'disputed_dimensions': deepcopy(entry.get('disputed_dimensions', entry.get('pending_dimensions', []))),
            'disputed_dimensions_basis': 'explicit_review_fields_only; empty means unspecified',
            'existing_resolution_flags': deepcopy(ref.get('needs_resolution', [])),
            'assistant_review_route': ref.get('review_route'),
            'assistant_adjudication': deepcopy(ref.get('assistant_adjudication')),
            'human_notes': entry.get('notes', ''),
            'sources': deepcopy(ref.get('sources', [])),
        })
    return pending


def audit_gold(gold, state, schema, candidates):
    distribution = {dim: {label: 0 for label in schema['style'][dim]['values']} for dim in STYLE_DIMS}
    edits = {dim: 0 for dim in STYLE_DIMS}
    rule_differences = {dim: 0 for dim in ['imagery', 'density']}
    proposed = index_unique(candidates)
    for row in gold:
        for dim in STYLE_DIMS:
            val = row['style'][dim]
            for label in val if isinstance(val, list) else [val]:
                distribution[dim][label] += 1
            block = proposed[row['id']]['annotation']['assistant_calibration']['style_proposal'][dim]
            before = block['value']
            differs = set(val) != set(before) if isinstance(val, list) else val != before
            edits[dim] += int(differs)
        for dim in rule_differences:
            before = row['annotation']['prelabel'][dim]['value']
            after = row['style'][dim]
            rule_differences[dim] += int(set(before) != set(after) if isinstance(after, list) else before != after)
    decisions = Counter(x['decision'] for x in state['records'].values())
    return {
        'scope': 'descriptive_only; single reviewer; not inter-rater reliability',
        'total': len(gold), 'forms': dict(Counter(r['form'] for r in gold)),
        'unique_authors': len({r['metadata']['author'] for r in gold}),
        'style_distribution': distribution,
        'multi_label_counts': ['emotion', 'imagery'],
        'review_decisions_all30': {k: decisions[k] for k in ['accept','edit','exclude','pending']},
        'review_decisions_gold': dict(Counter(r['annotation']['human_review']['decision'] for r in gold)),
        'low_frequency_threshold': 'count <= 2, including zero; descriptive, no resampling',
        'low_frequency_labels': {d: {k:v for k,v in counts.items() if v <= 2} for d,counts in distribution.items()},
        'human_changes_vs_source_assisted_proposal': edits,
        'rule_disagreements_with_gold': rule_differences,
        'interpretation': 'changes and weak-rule differences are not a measured dispute rate',
    }


def sample_review_batch(pool, calibration_ids, flags, lexicon, *, seed=20260924, per_form=50):
    index_unique(pool)
    eligible = sorted((deepcopy(r) for r in pool if r['id'] not in calibration_ids), key=lambda r:r['id'])
    if any(any(r['style'].values()) for r in eligible):
        raise ValueError('review pool must have blank canonical style')
    flagmap = index_unique(flags)
    rng = random.Random(seed)
    rng.shuffle(eligible)
    priority = {r['id']: n for n,r in enumerate(eligible)}
    risk = lambda r: any(f.get('severity') == 'high' for f in flagmap.get(r['id'], {}).get('flags', []))
    selected, counts, authors = [], Counter(), Counter()
    remaining = list(eligible)
    for form in ['qijue7','qilv7']:
        if sum(r['form'] == form for r in remaining) < per_form:
            raise ValueError(f'insufficient pool for {form}')
    # Include known high-risk records first, then minimize repeated authors globally.
    for risk_only in [True, False]:
        while True:
            choices = [r for r in remaining if counts[r['form']] < per_form and (risk(r) or not risk_only)]
            if not choices:
                break
            row = min(choices, key=lambda r:(authors[r['metadata'].get('author','')], priority[r['id']]))
            remaining.remove(row)
            counts[row['form']] += 1
            authors[row['metadata'].get('author','')] += 1
            selected.append(row)
    result = []
    for order, row in enumerate(selected, 1):
        row = rule_preannotate_record(row, lexicon_cfg=lexicon)
        row['annotation']['quality_review'] = {
            'decision':'pending', 'reviewer':'', 'notes':'',
            'flags':deepcopy(flagmap.get(row['id'], {}).get('flags', []))}
        row['metadata']['review_batch'] = {
            'version':'v2_100', 'seed':seed, 'order':order,
            'purpose':'quality_and_style_review_only',
            'selection_reason':'high_risk_priority' if risk(row) else 'author_diversity_fill'}
        row['metadata']['text_policy'] = 'source_preserved_v1'
        result.append(row)
    selected_risk = [r['id'] for r in result if risk(r)]
    report = {
        'seed':seed, 'method':'high_risk_first_then_min_author_count_seeded_tiebreak_v1',
        'input_order_independent':True, 'pool_total':len(pool), 'calibration_excluded':len(calibration_ids),
        'eligible':len(eligible), 'selected':len(result), 'forms':dict(counts),
        'unique_authors':len(authors), 'max_records_per_author':max(authors.values(), default=0),
        'author_counts':dict(sorted(authors.items())),
        'high_risk_eligible':sum(risk(r) for r in eligible),
        'high_risk_selected':len(selected_risk), 'high_risk_selected_ids':selected_risk,
        'selected_ids':[r['id'] for r in result],
        'canonical_style_filled':0, 'human_confirmed':0,
        'deduplication_scope':'excludes 30 calibration IDs only; not a corpus-wide variant split guarantee',
        'policy':'risk enrichment is for quality review, not representative sampling or automatic Gold',
    }
    return result, report
