"""Freeze final pilot configs only after bounded real-model diagnostics pass."""
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.training.config import load_baseline_config
from src.training.pilot_protocol import sha


def main():
    out = ROOT / 'outputs/b0_training_pilot_20260926'
    load = lambda p: json.loads(p.read_text(encoding='utf-8'))
    smoke = load(out / 'smoke_not_experiment_result/result.json')
    sanity = load(out / 'overfit_not_experiment_result/result.json')
    if not smoke['success'] or not sanity['success']: raise ValueError('Diagnostics have not passed')
    protocol = load(out / 'protocol.json'); preflight = load(out / 'preflight.json')
    for path, digest in protocol['protected_inputs'].items():
        if sha(ROOT / path) != digest: raise ValueError('Protected input changed')
    for letter, filename in [('A', 'b0_gold_only.json'), ('B', 'b0_gold_partial_silver.json')]:
        target = ROOT / 'configs' / filename
        if target.exists(): raise FileExistsError(target)
        raw = load(out / ('proposed_b0_' + letter + '.json'))
        raw['diagnostic_gate'] = {'smoke_passed': True, 'tiny_overfit_passed': True,
            'source_reports': 'outputs/b0_training_pilot_20260926', 'long_training_started': False}
        target.write_text(json.dumps(raw, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
        load_baseline_config(target)
    summary = {'preflight_suitable': preflight['suitable'], 'smoke_success': smoke['success'], 'overfit_success': sanity['success'],
        'configs': {name: sha(ROOT / 'configs' / name) for name in ('b0_gold_only.json', 'b0_gold_partial_silver.json')},
        'long_pilot_training_started': False}
    (out / 'completion.json').write_text(json.dumps(summary, indent=2) + '\n', encoding='utf-8')
    print('Final configs frozen; long pilot has NOT been started')


if __name__ == '__main__': main()
