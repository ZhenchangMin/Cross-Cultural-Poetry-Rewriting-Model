"""Rules-only release of trusted dimensions. No model imports, training or review."""
import hashlib
import json
from collections import Counter
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.data.human_review import read_jsonl, write_jsonl
from src.data.validate_dataset import load_schema, validate_jsonl
from src.data.silver_annotation import discover_gold
from src.data.partial_silver import build_partial
from src.data.partial_supervision import RULE_VERSION
from src.data.mixed_dataset import MixedPoetryDataset, MODES
from src.data.dataset import PoetryTrainingDataset


def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()
def load(path): return json.loads(path.read_text(encoding='utf-8'))
def save(path, value): path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def main():
    data = ROOT / 'data/processed/style_annotation'
    out = ROOT / 'data/processed/partial_silver_v1'
    if out.exists(): raise FileExistsError('Do not overwrite a completed or partial release')
    schema = load_schema(ROOT / 'configs/style_schema.json')
    gate_path = ROOT / 'data/processed/semantic_annotator_v3/semantic_annotator_v3_cv_report.json'
    gate = load(gate_path)
    if not all(gate['gate']['dimension_ready'][d] for d in ('imagery', 'density')):
        raise ValueError('Rule dimensions have not passed the existing gate')
    gold, _ = discover_gold(sorted(data.glob('gold_calibration*_v1.jsonl')), schema)
    pending = read_jsonl(data / 'adjudication_pending_v1.jsonl')
    source = data / 'preannotated_v1_1.jsonl'
    pool = read_jsonl(source)
    lex_path = ROOT / 'configs/imagery_lexicon_v1.json'
    flags = {r['id']: r for r in read_jsonl(data / 'quality_flags_v1.jsonl')}
    variants = load(data / 'variant_groups_v2.json')['groups']
    protected = {p.relative_to(ROOT).as_posix(): sha(p) for p in data.iterdir() if p.is_file()}
    provenance = {'source_file': source.relative_to(ROOT).as_posix(), 'source_sha256': sha(source),
        'rule_version': RULE_VERSION, 'rule_code_sha256': sha(ROOT / 'src/data/preannotate_style.py'),
        'lexicon_sha256': sha(lex_path), 'gate_report_sha256': sha(gate_path), 'text_policy': 'source_preserved_v1'}
    accepted, rejected = build_partial(pool, gold, pending, flags, variants, load(lex_path), schema, provenance)
    out.mkdir(parents=True)
    path = out / 'partial_silver_v1.jsonl'
    write_jsonl(accepted, path)
    write_jsonl(rejected, out / 'partial_silver_v1_rejected.jsonl')
    validation = validate_jsonl(path, schema, stage='partial-silver')
    if not validation.ok: raise ValueError(str(validation))
    reasons = Counter(reason for r in rejected for reason in r['reasons'])
    primary = Counter(r['reasons'][0] for r in rejected)
    report = {'version': 'partial_silver_v1', 'input_count': len(pool), 'retained': len(accepted), 'filtered': len(rejected),
        'gold_excluded_total': len(gold), 'unresolved_preserved': len(pending),
        'filter_reasons_overlapping': dict(reasons), 'primary_filter_reasons_disjoint': dict(primary),
        'filter_detail_file': 'partial_silver_v1_rejected.jsonl',
        'forms': dict(Counter(r['form'] for r in accepted)),
        'imagery_distribution': {label: sum(label in r['style']['imagery'] for r in accepted) for label in schema['style']['imagery']['values']},
        'density_distribution': {label: sum(r['style']['density'] == label for r in accepted) for label in schema['style']['density']['values']},
        'confidence_thresholds': {'imagery': .7, 'density': .5}, 'rule_version': RULE_VERSION, 'provenance': provenance,
        'validation': validation.to_dict(), 'output_sha256': sha(path),
        'trusted_dimensions': ['form', 'imagery', 'density'], 'unknown_semantic_dimensions': ['emotion', 'diction', 'expression', 'energy'],
        'unknown_representation': 'explicit JSON null, never a style label',
        'full_silver_gate': 'fail', 'partial_release_authorization': 'user-approved trusted dimensions only',
        'gate_scope': 'development evidence: imagery F1=.8 and density accuracy=1; not independent test proof',
        'new_human_review_tasks': 0, 'llm_calls': 0, 'training_started': False,
        'protected_input_hashes': protected,
        'build_code_hashes': {p: sha(ROOT / p) for p in ['scripts/build_partial_silver.py', 'src/data/partial_silver.py', 'src/data/partial_supervision.py', 'src/data/validate_dataset.py']}}
    if not all(sha(ROOT / p) == h for p, h in protected.items()): raise ValueError('Protected source changed')
    save(out / 'partial_silver_v1_report.json', report)
    # 数据准备清单不运行tokenizer或模型；第三模式只声明form-only接口。
    gold_path = data / 'gold_calibration_v1.jsonl'
    for mode in MODES:
        dataset = MixedPoetryDataset(gold_path, mode=mode, partial_silver_path=path if mode != 'gold-only' else None,
            schema_path=ROOT / 'configs/style_schema.json', training=True, control_dropout=.3, seed=20260926)
        save(out / ('manifest_' + mode.replace('+', '_') + '.json'), dataset.manifest())
    g = PoetryTrainingDataset(gold_path, schema_path=ROOT / 'configs/style_schema.json')[0]
    s = PoetryTrainingDataset(path, schema_path=ROOT / 'configs/style_schema.json', stage='partial-silver')[0]
    save(out / 'prompt_examples.json', {'gold': {'id': g.id, 'prompt': g.prompt_text, 'target': g.target_text},
                                     'partial_silver': {'id': s.id, 'prompt': s.prompt_text, 'target': s.target_text}})
    print(json.dumps({k: report[k] for k in ('input_count', 'retained', 'filtered', 'primary_filter_reasons_disjoint', 'forms', 'imagery_distribution', 'density_distribution')}, ensure_ascii=False, indent=2))


if __name__ == '__main__': main()
