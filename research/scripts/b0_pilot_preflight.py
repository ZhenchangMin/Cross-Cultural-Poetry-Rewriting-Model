"""Read-only model/GPU checks; refuse CPU training and never download weights."""
import hashlib
import importlib.metadata
import json
from pathlib import Path
import shutil
import subprocess

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'outputs/b0_training_pilot_20260926'


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    path = OUT / 'preflight.json'
    if path.exists(): raise FileExistsError('Preserve existing preflight')
    model = ROOT / 'models/_cache/Qwen2.5-1.5B-Instruct'
    provenance = json.loads((model / 'download_provenance.json').read_text(encoding='utf-8-sig'))
    expected = next(x['lfs']['sha256'] for x in provenance['siblings'] if x['rfilename'] == 'model.safetensors')
    weights = model / 'model.safetensors'
    with weights.open('rb') as stream:
        digest = hashlib.file_digest(stream, 'sha256').hexdigest()
    import torch
    available = torch.cuda.is_available()
    gpu = torch.cuda.get_device_properties(0) if available else None
    free, total = torch.cuda.mem_get_info() if available else (0, 0)
    report = {'versions': {x: importlib.metadata.version(x) for x in ('torch', 'transformers', 'peft', 'accelerate')},
        'torch_cuda_available': available, 'torch_cuda_version': torch.version.cuda,
        'gpu_name': gpu.name if gpu else None, 'gpu_total_bytes': total, 'gpu_free_bytes': free,
        'bf16_supported': available and torch.cuda.is_bf16_supported(),
        'nvidia_smi': subprocess.check_output(['nvidia-smi'], text=True),
        'project_disk_free_bytes': shutil.disk_usage(ROOT).free,
        'runtime_disk_free_bytes': shutil.disk_usage('/').free,
        'local_model_path': str(model), 'weights_bytes': weights.stat().st_size,
        'weights_sha256': digest, 'expected_weights_sha256': expected, 'weights_verified': digest == expected,
        'model_revision': provenance['revision'], 'download_required': False,
        'recommended': {'precision': 'bf16', 'batch_size': 1, 'gradient_accumulation_steps': 8,
                        'max_length': 512, 'gradient_checkpointing': True, 'quantization': None},
        'checkpoint_disk_budget_bytes': 2 * 1024**3}
    report['suitable'] = bool(available and report['bf16_supported'] and total >= 7 * 1024**3 and free >= 5 * 1024**3 and digest == expected and report['project_disk_free_bytes'] > 10 * 1024**3)
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({k: v for k, v in report.items() if k != 'nvidia_smi'}, ensure_ascii=False, indent=2), flush=True)
    if not report['suitable']: raise SystemExit('GPU/model/disk preflight failed; no training permitted')


if __name__ == '__main__': main()
