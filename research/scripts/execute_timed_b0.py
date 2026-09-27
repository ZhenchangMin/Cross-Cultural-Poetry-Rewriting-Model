"""Time an explicitly authorized frozen pilot without modifying its execution code."""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import runpy
import sys
import time

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('arm', choices=['A', 'B'])
    args = parser.parse_args()
    config = 'b0_pilot_gold_only.json' if args.arm == 'A' else 'b0_pilot_gold_partial_silver.json'
    out = ROOT / 'outputs/b0_pilot'; out.mkdir(parents=True, exist_ok=True)
    timing_path = out / f'{args.arm}_runtime.json'
    if timing_path.exists(): raise FileExistsError('Never overwrite recorded experiment timing')
    started = datetime.now(timezone.utc).isoformat(); clock = time.perf_counter(); success = False
    old_argv = sys.argv
    try:
        sys.argv = ['run_frozen_b0_pilot.py', 'configs/' + config, '--execute']
        runpy.run_path(str(ROOT / 'scripts/run_frozen_b0_pilot.py'), run_name='__main__')
        success = True
    finally:
        elapsed = time.perf_counter() - clock; sys.argv = old_argv
        record = {'arm': args.arm, 'started_utc': started, 'finished_utc': datetime.now(timezone.utc).isoformat(),
                  'wall_clock_seconds': elapsed, 'success': success, 'scope': 'complete runner including import/load/evaluation/checkpoint saving'}
        torch = sys.modules.get('torch')
        if torch is not None and torch.cuda.is_initialized():
            record.update(peak_allocated_bytes=torch.cuda.max_memory_allocated(), peak_reserved_bytes=torch.cuda.max_memory_reserved())
        timing_path.write_text(json.dumps(record, indent=2) + '\n', encoding='utf-8')


if __name__ == '__main__': main()
