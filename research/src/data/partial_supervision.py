"""Separate schema for rule-only partial supervision; unknown is explicitly null."""
import math
from collections.abc import Mapping

STYLE_DIMS = ('emotion', 'imagery', 'diction', 'expression', 'energy', 'density')
UNKNOWN_DIMS = ('emotion', 'diction', 'expression', 'energy')
PARTIAL_CONTROLS = ('form', 'imagery', 'density')
RULE_VERSION = 'lexicon_heuristic_v1_1'
ANNOTATION_VERSION = 'partial_silver_v1'


def partial_issues(record, schema, stage='partial-silver'):
    """Return field/message pairs without relaxing the legacy Gold validator."""
    issues = []
    def bad(field, message): issues.append((field, message))
    partial = stage == 'partial-silver'
    controls = PARTIAL_CONTROLS if partial else ('form',)
    unknown = UNKNOWN_DIMS if partial else STYLE_DIMS
    style = record.get('style')
    if not isinstance(style, Mapping) or set(style) != set(STYLE_DIMS):
        bad('style', 'must contain exactly six dimensions, unknown fields explicitly null')
    else:
        for d in unknown:
            if style[d] is not None: bad('style.' + d, 'must be explicitly null; no pseudo semantic labels')
        if partial:
            imagery = style['imagery']
            if not isinstance(imagery, list) or not 1 <= len(imagery) <= 4 or any(not isinstance(v, str) or v not in schema['style']['imagery']['values'] for v in imagery):
                bad('style.imagery', 'requires 1..4 legal labels')
            elif len(set(imagery)) != len(imagery): bad('style.imagery', 'duplicate labels')
            if not isinstance(style['density'], str) or style['density'] not in schema['style']['density']['values']:
                bad('style.density', 'requires a legal density label')
    if record.get('dataset_stage') != stage: bad('dataset_stage', 'must match explicit stage')
    if record.get('available_controls') != list(controls): bad('available_controls', 'must list only supervised controls in canonical order')
    expected = {'form': 'structural_v1'}
    if partial: expected.update(imagery='silver_rule_v1_1', density='silver_rule_v1_1')
    if record.get('supervision') != expected: bad('supervision', 'wrong supervision sources')
    metadata = record.get('metadata', {})
    source = 'automatic_partial_silver' if partial else 'structural_form_only'
    if not isinstance(metadata, Mapping) or metadata.get('label_source') != source or metadata.get('review_status') != source + '_accepted':
        bad('metadata', 'automatic/structural provenance must not claim Gold')
    if isinstance(metadata, Mapping) and metadata.get('reviewer'): bad('metadata.reviewer', 'automatic data must not claim a human reviewer')
    annotation = record.get('annotation', {})
    if not isinstance(annotation, Mapping):
        bad('annotation', 'required object'); return issues
    if any(k in annotation for k in ('human_review', 'assistant_calibration', 'prelabel', 'review')):
        bad('annotation', 'must not carry human-review or semantic preannotation claims')
    if annotation.get('label_source') != source: bad('annotation.label_source', 'source mismatch')
    if annotation.get('version') != (ANNOTATION_VERSION if partial else 'form_only_v1'):
        bad('annotation.version', 'unsupported annotation version')
    provenance = annotation.get('provenance', {})
    required = ['source_file', 'source_sha256', 'source_record_id', 'source_record_sha256', 'text_policy']
    if partial: required += ['rule_version', 'rule_code_sha256', 'lexicon_sha256', 'gate_report_sha256']
    if not isinstance(provenance, Mapping):
        bad('annotation.provenance', 'required object'); provenance = {}
    for key in required:
        v = provenance.get(key)
        if not isinstance(v, str) or not v.strip(): bad('annotation.provenance.' + key, 'required nonempty string')
        elif key.endswith('sha256') and (len(v) != 64 or any(c not in '0123456789abcdef' for c in v)):
            bad('annotation.provenance.' + key, 'must be a SHA256 hex digest')
    if provenance.get('source_record_id') != record.get('id'): bad('annotation.provenance.source_record_id', 'ID mismatch')
    if partial and provenance.get('rule_version') != RULE_VERSION: bad('annotation.provenance.rule_version', 'rule version mismatch')
    per_dim = annotation.get('per_dimension', {})
    if not isinstance(per_dim, Mapping) or set(per_dim) != set(controls):
        bad('annotation.per_dimension', 'must describe exactly available controls'); return issues
    for d in controls:
        block = per_dim[d]
        if not isinstance(block, Mapping): bad('annotation.per_dimension.' + d, 'required object'); continue
        actual = record.get('form') if d == 'form' else (style.get(d) if isinstance(style, Mapping) else None)
        if block.get('value') != actual: bad('annotation.per_dimension.' + d, 'value mismatch')
        conf = block.get('confidence')
        if isinstance(conf, bool) or not isinstance(conf, (float, int)) or not math.isfinite(conf) or not 0 <= conf <= 1:
            bad('annotation.per_dimension.' + d + '.confidence', 'requires finite [0,1] confidence')
        if block.get('method') != ('structural_v1' if d == 'form' else RULE_VERSION): bad('annotation.per_dimension.' + d + '.method', 'wrong method')
        if block.get('label_source') != ('structural' if d == 'form' else 'rule'): bad('annotation.per_dimension.' + d + '.label_source', 'wrong source')
        if not isinstance(block.get('evidence'), Mapping) or not block['evidence']: bad('annotation.per_dimension.' + d + '.evidence', 'required evidence object')
    return issues
