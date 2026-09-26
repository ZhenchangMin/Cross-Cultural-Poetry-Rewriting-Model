"""Explicit source-aware mixed supervision, with balanced source sampling masses."""
from collections import Counter
from copy import deepcopy
import hashlib
import math
from pathlib import Path
from typing import Sequence

from .dataset import PoetryTrainingDataset, TrainingExample, record_to_example, dropout_controls
from .validate_dataset import DEFAULT_SCHEMA, STYLE_DIMS, validate_record
from .partial_silver import record_hash, structural_block

MODES = ('gold-only', 'gold+partial-silver', 'gold+partial-silver+form-only')


def make_form_only(row, schema, source_file, source_sha256):
    """Interface only: caller explicitly supplies a structurally valid source record."""
    if validate_record(row, schema, stage='candidate'): raise ValueError('Invalid structural record')
    result = {'id': row['id'], 'text': row['text'], 'form': row['form'], 'style': {d: None for d in STYLE_DIMS},
        'culture': {'adaptation': None}, 'dataset_stage': 'form-only', 'available_controls': ['form'],
        'supervision': {'form': 'structural_v1'},
        'metadata': {'label_source': 'structural_form_only', 'review_status': 'structural_form_only_accepted'},
        'annotation': {'version': 'form_only_v1', 'label_source': 'structural_form_only',
            'per_dimension': {'form': structural_block(row)}, 'provenance': {'source_file': str(source_file),
                'source_sha256': source_sha256, 'source_record_id': row['id'], 'source_record_sha256': record_hash(row),
                'text_policy': 'source_preserved_v1'}}}
    issues = validate_record(result, schema, stage='form-only')
    if issues: raise ValueError(str(issues))
    return result


class MixedPoetryDataset(Sequence[TrainingExample]):
    def __init__(self, gold_path, *, mode='gold-only', partial_silver_path=None, form_only_path=None,
                 schema_path=DEFAULT_SCHEMA, source_weights=None, training=False, control_dropout=0., seed=0):
        if mode not in MODES: raise ValueError('Unknown training data mode')
        if not math.isfinite(control_dropout) or not 0 <= control_dropout <= 1: raise ValueError('Invalid control dropout')
        if mode == 'gold-only' and (partial_silver_path is not None or form_only_path is not None): raise ValueError('Unexpected source for gold-only')
        if mode == 'gold+partial-silver' and form_only_path is not None: raise ValueError('form-only requires third mode')
        if mode != 'gold-only' and partial_silver_path is None: raise ValueError('Partial Silver path is required')
        paths = [('gold', gold_path)]
        if mode != 'gold-only': paths.append(('partial-silver', partial_silver_path))
        # 第三种模式允许暂时不提供form-only文件，不隐式扫描18k语料。
        if form_only_path is not None: paths.append(('form-only', form_only_path))
        weights = {'gold': 1., 'partial-silver': 1., 'form-only': 1.}
        if source_weights:
            if not set(source_weights) <= set(weights): raise ValueError('Unknown sampling source')
            weights.update(source_weights)
        if any(isinstance(w, bool) or not isinstance(w, (float, int)) or not math.isfinite(w) or w <= 0 for w in weights.values()):
            raise ValueError('Sampling source weights must be positive finite numbers')
        self.mode = mode; self.training = training; self.control_dropout = control_dropout; self.seed = seed; self.epoch = 0
        self._items = []; self.sources = []; seen = set()
        for source, path in paths:
            dataset = PoetryTrainingDataset(path, schema_path=schema_path, stage=source)
            if not len(dataset): raise ValueError('Empty source: ' + source)
            digest = hashlib.sha256(Path(path).read_bytes()).hexdigest()
            self.sources.append({'source': source, 'path': str(path), 'sha256': digest, 'records': len(dataset),
                                 'source_sampling_mass': weights[source], 'per_record_sampling_weight': weights[source] / len(dataset)})
            for row in dataset._records:
                if row['id'] in seen: raise ValueError('Cross-source duplicate ID: ' + row['id'])
                if source == 'gold':
                    review = row.get('annotation', {}).get('human_review', {})
                    if row.get('metadata', {}).get('review_status') != 'gold_adjudicated' or review.get('decision') not in ('accept', 'edit') or not review.get('reviewer') or not review.get('confirmation_provenance'):
                        raise ValueError('Mixed Gold source requires existing human confirmation provenance')
                seen.add(row['id'])
                self._items.append((row, source, weights[source] / len(dataset),
                    {'source_file': str(path), 'source_sha256': digest, 'source_sampling_mass': weights[source],
                     'annotation': deepcopy(row.get('annotation', {})), 'metadata': deepcopy(row.get('metadata', {}))}))

    def __len__(self): return len(self._items)

    def __getitem__(self, index):
        row, source, weight, provenance = self._items[index]
        controls = dropout_controls(row, self.control_dropout, self.seed, self.epoch, self.training)
        return record_to_example(row, controls=controls, source=source, sampling_weight=weight, provenance=provenance)

    @property
    def sampling_weights(self): return [x[2] for x in self._items]

    def set_epoch(self, epoch): self.epoch = epoch

    def manifest(self):
        return {'mode': self.mode, 'records': len(self), 'sources': deepcopy(self.sources),
                'training': self.training, 'control_dropout': self.control_dropout,
                'effective_dropout': self.control_dropout if self.training else 0., 'seed': self.seed,
                'sampling_policy': 'training only: per-record weight = source mass / source record count; replacement sampling',
                'form_only_interface_unpopulated': self.mode.endswith('+form-only') and not any(s['source'] == 'form-only' for s in self.sources),
                'examples': [{'id': self[i].id, 'source': self[i].source, 'supervision_type': self[i].supervision_type,
                              'available_controls': self[i].available_controls, 'sampling_weight': self[i].sampling_weight} for i in range(len(self))]}
