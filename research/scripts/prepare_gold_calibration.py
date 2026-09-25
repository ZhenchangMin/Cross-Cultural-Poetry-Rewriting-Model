"""Build calibration Gold and next pending batch; never starts model training."""
import argparse
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.data.calibration_gold import reconcile_reviews, export_unresolved, audit_gold, sample_review_batch
from src.data.human_review import read_jsonl, write_jsonl, save_review_state
from src.data.dataset import PoetryTrainingDataset, record_to_example
from src.data.validate_dataset import load_schema, validate_jsonl


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--root', type=Path, default=ROOT)
    args = ap.parse_args()
    root = args.root.resolve()
    data = root/'data/processed/style_annotation'
    inputs = ['assistant_calibrated_v1_1.jsonl', 'calibration_sample_v1.jsonl',
              'review_candidates24_v2.jsonl', 'human_review_state_v1.json', 'human_review_state24_v2.json',
              'source_reference_all30_v2.jsonl', 'calibration_rule_v1_1.jsonl',
              'preannotated_v1_1.jsonl', 'quality_flags_v1.jsonl']
    hashes = {n:hashlib.sha256((data/n).read_bytes()).hexdigest() for n in inputs}
    hashes.update({str(p.relative_to(root)):hashlib.sha256(p.read_bytes()).hexdigest() for p in
                   [root/'configs/style_schema.json', root/'configs/imagery_lexicon_v1.json',
                    root/'src/data/preannotate_style.py', root/'src/data/calibration_gold.py']})
    read = lambda n: read_jsonl(data/n)
    obj = lambda n: json.loads((data/n).read_text(encoding='utf-8'))
    schema = load_schema(root/'configs/style_schema.json')
    original = read('assistant_calibrated_v1_1.jsonl')
    calibration = read('calibration_sample_v1.jsonl')
    assert [(r['id'],r['text'],r['form']) for r in original] == [(r['id'],r['text'],r['form']) for r in calibration]
    candidates = read('review_candidates24_v2.jsonl')
    rows, state = reconcile_reviews(original, candidates, obj('human_review_state_v1.json'),
                                     obj('human_review_state24_v2.json'), schema)
    state['provenance'] = {'method':'merge_by_id_without_modifying_source_reviews','input_sha256':hashes}
    pending = export_unresolved(rows, state, read('source_reference_all30_v2.jsonl'), read('calibration_rule_v1_1.jsonl'))
    batch, sampling = sample_review_batch(read('preannotated_v1_1.jsonl'), {r['id'] for r in rows},
                                         read('quality_flags_v1.jsonl'),
                                         json.loads((root/'configs/imagery_lexicon_v1.json').read_text(encoding='utf-8')))
    sampling['input_sha256'] = hashes
    # Prepare and validate everything in a temporary directory before publishing.
    with tempfile.TemporaryDirectory(prefix='gold-calibration-') as temp:
        staging = Path(temp)
        write_jsonl(rows, staging/'calibration_promotion_input_v1.jsonl')
        save_review_state(state, staging/'human_review_state30_reconciled_v1.json')
        subprocess.run([sys.executable, str(root/'scripts/human_review.py'), 'promote',
                        '--input',str(staging/'calibration_promotion_input_v1.jsonl'),
                        '--state',str(staging/'human_review_state30_reconciled_v1.json'),
                        '--schema',str(root/'configs/style_schema.json'), '--allow-partial',
                        '--output',str(staging/'gold_calibration_v1.jsonl'),
                        '--report',str(staging/'gold_calibration_report_v1.json')],check=True,cwd=root)
        gold = read_jsonl(staging/'gold_calibration_v1.jsonl')
        assert len(gold)==24 and len(pending)==6 and len(rows)==30
        # Promotion itself preserves the human-review entry; verify it rather than infer it.
        for row in gold:
            assert row['annotation']['human_review']['confirmation_provenance'] == state['records'][row['id']]
        previous = {r['id']:r for r in read('gold_calibration24_v1.jsonl')}
        assert set(previous)=={r['id'] for r in gold}
        assert all((r['text'],r['form'],r['style']) == (previous[r['id']]['text'],previous[r['id']]['form'],previous[r['id']]['style']) for r in gold)
        checks = validate_jsonl(staging/'gold_calibration_v1.jsonl', schema, stage='gold')
        assert checks.ok and checks.valid_records==24
        dataset = PoetryTrainingDataset(staging/'gold_calibration_v1.jsonl', schema_path=root/'configs/style_schema.json',validate=True)
        assert len(dataset)==24
        # Metamorphic check: changing metadata must leave prompts invariant.
        for row in gold:
            sentinel = deepcopy(row)
            sentinel['metadata'].update(title='TITLE_SENTINEL_891',author='AUTHOR_SENTINEL_891')
            assert record_to_example(sentinel).prompt_text == record_to_example(row).prompt_text
        write_jsonl(pending, staging/'adjudication_pending_v1.jsonl')
        write_jsonl(batch, staging/'review_batch_v2_100.jsonl')
        save_review_state(sampling, staging/'review_batch_v2_report.json')
        audit = audit_gold(gold, state, schema, candidates)
        audit['input_sha256'] = hashes
        audit['gold_sha256'] = hashlib.sha256((staging/'gold_calibration_v1.jsonl').read_bytes()).hexdigest()
        save_review_state(audit, staging/'gold_calibration_audit_v1.json')
        save_review_state({'gold_valid':24,'unresolved':6,'dataset_length':len(dataset),
                           'metadata_prompt_invariance':True,
                           'samples':[vars(dataset[i]) for i in [0,1]]}, staging/'gold_calibration_loader_check_v1.json')
        for p in staging.iterdir():
            dest = data/p.name
            if dest.exists() and dest.read_bytes()!=p.read_bytes():
                raise FileExistsError(f'Refusing to overwrite different artifact: {dest}')
        for p in staging.iterdir():
            (data/p.name).write_bytes(p.read_bytes())
    print(json.dumps({'confirmed':len(gold),'unresolved':len(pending),'audit':audit,'sampling':sampling},ensure_ascii=False,indent=2))


if __name__ == '__main__':
    main()
