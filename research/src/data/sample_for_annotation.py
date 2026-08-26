# -*- coding: utf-8 -*-
"""从唐诗结构候选集中抽取人工风格标注样本。

目标不是模拟原始语料的作者频率，而是为“人工复核金标集”获得尽可能广的
作者与诗体覆盖，避免白居易等高频作者主导 Gold Dataset。

默认：
- 七言绝句 qijue7: 500 首
- 七言律诗 qilv7: 500 首
- 同一作者在同一诗体中最多抽 1 首
- 固定随机种子 20260823，保证可复现

注意：输出仍是“待标注候选集”。只有 style 六维标签完成人工复核后，
才可以称为真正的 Gold Dataset。

用法（WSL, research/）：
    source .venv/bin/activate
    python -m src.data.sample_for_annotation

自定义：
    python -m src.data.sample_for_annotation \
        --qijue 400 --qilv 400 --seed 20260823
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import random
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Sequence

DEFAULT_INPUT = Path("data/raw/tang_style_annotation_candidates.jsonl")
DEFAULT_OUTPUT = Path("data/processed/style_annotation/annotation_sample_v1.jsonl")
DEFAULT_REPORT = Path("data/processed/style_annotation/sampling_report_v1.json")
DEFAULT_TARGETS = {"qijue7": 500, "qilv7": 500}
DEFAULT_SEED = 20260823
SAMPLE_VERSION = "v1"
SAMPLING_METHOD = "uniform_author_then_uniform_poem_within_form"


def load_jsonl(path: Path) -> List[Dict[str, Any]]:
    records: List[Dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as f:
        for lineno, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"Invalid JSON at {path}:{lineno}: {exc}") from exc
            if not isinstance(obj, dict):
                raise ValueError(f"Expected JSON object at {path}:{lineno}")
            records.append(obj)
    return records


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _author_of(record: Mapping[str, Any]) -> str:
    metadata = record.get("metadata")
    if not isinstance(metadata, Mapping):
        return "UNKNOWN"
    author = metadata.get("author")
    if not isinstance(author, str) or not author.strip():
        return "UNKNOWN"
    return author.strip()


def _validate_record(record: Mapping[str, Any], index: int) -> None:
    for field in ("id", "text", "form", "style", "culture", "metadata"):
        if field not in record:
            raise ValueError(f"Record #{index} missing required field: {field}")
    if record["form"] not in DEFAULT_TARGETS:
        raise ValueError(f"Record #{index} has unsupported form: {record['form']!r}")


def sample_form_author_balanced(
    records: Sequence[Dict[str, Any]],
    *,
    form: str,
    target: int,
    seed: int,
    max_per_author: int = 1,
) -> List[Dict[str, Any]]:
    """在单一诗体内做作者均衡抽样。

    第 1 轮每位作者最多抽 1 首；若 max_per_author > 1 且 target 大于作者数，
    再开启后续轮次。每轮作者顺序和作者内部诗歌顺序都由固定 seed 决定。
    """
    if target < 0:
        raise ValueError("target must be >= 0")
    if max_per_author < 1:
        raise ValueError("max_per_author must be >= 1")
    if target == 0:
        return []

    by_author: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for record in records:
        if record.get("form") == form:
            by_author[_author_of(record)].append(record)

    if not by_author:
        raise ValueError(f"No records available for form={form}")

    capacity = sum(min(len(items), max_per_author) for items in by_author.values())
    if target > capacity:
        raise ValueError(
            f"Cannot sample {target} records for {form}: capacity={capacity} "
            f"under max_per_author={max_per_author}"
        )

    rng = random.Random(seed)
    authors = sorted(by_author)
    rng.shuffle(authors)

    # 每位作者内部也先固定打乱，后续轮次按位置取，避免永远偏向源文件前部。
    shuffled_by_author: Dict[str, List[Dict[str, Any]]] = {}
    for author in authors:
        items = list(by_author[author])
        rng.shuffle(items)
        shuffled_by_author[author] = items

    selected: List[Dict[str, Any]] = []
    for round_idx in range(max_per_author):
        round_authors = list(authors)
        rng.shuffle(round_authors)
        for author in round_authors:
            items = shuffled_by_author[author]
            if round_idx >= len(items):
                continue
            selected.append(items[round_idx])
            if len(selected) == target:
                return selected

    raise RuntimeError("Sampling ended before reaching target despite sufficient capacity")


def sample_balanced(
    records: Sequence[Dict[str, Any]],
    *,
    targets: Mapping[str, int],
    seed: int = DEFAULT_SEED,
    max_per_author_per_form: int = 1,
) -> List[Dict[str, Any]]:
    """按诗体配额抽样，再将结果以固定 seed 打乱。"""
    for i, record in enumerate(records, 1):
        _validate_record(record, i)

    selected: List[Dict[str, Any]] = []
    # 给不同诗体使用不同但稳定的整数 seed，避免相同随机流造成不必要耦合。
    form_seed_offsets = {"qijue7": 101, "qilv7": 211}
    for form in ("qijue7", "qilv7"):
        target = int(targets.get(form, 0))
        selected.extend(
            sample_form_author_balanced(
                records,
                form=form,
                target=target,
                seed=seed + form_seed_offsets[form],
                max_per_author=max_per_author_per_form,
            )
        )

    # 不按诗体分块呈现，避免人工标注时连续看到同一诗体产生顺序效应。
    rng = random.Random(seed + 997)
    rng.shuffle(selected)

    ids = [str(r["id"]) for r in selected]
    if len(ids) != len(set(ids)):
        raise ValueError("Duplicate record ids found in selected sample")
    return selected


def prepare_annotation_records(
    selected: Iterable[Dict[str, Any]],
    *,
    seed: int,
    targets: Mapping[str, int],
    max_per_author_per_form: int,
) -> List[Dict[str, Any]]:
    """复制样本并写入抽样追踪元数据，不修改原始候选集。"""
    out: List[Dict[str, Any]] = []
    for record in selected:
        item = copy.deepcopy(record)
        metadata = item.setdefault("metadata", {})
        metadata["review_status"] = "pending_annotation"
        metadata["annotation_method"] = "unlabeled"
        metadata["sampling"] = {
            "sample_version": SAMPLE_VERSION,
            "method": SAMPLING_METHOD,
            "seed": seed,
            "form_target": int(targets[item["form"]]),
            "max_per_author_per_form": max_per_author_per_form,
        }
        out.append(item)
    return out


def build_report(
    *,
    source_path: Path,
    source_sha256: str,
    all_records: Sequence[Dict[str, Any]],
    selected: Sequence[Dict[str, Any]],
    seed: int,
    targets: Mapping[str, int],
    max_per_author_per_form: int,
) -> Dict[str, Any]:
    source_forms = Counter(str(r["form"]) for r in all_records)
    selected_forms = Counter(str(r["form"]) for r in selected)
    selected_authors = Counter(_author_of(r) for r in selected)

    author_forms: Dict[str, set[str]] = defaultdict(set)
    for record in selected:
        author_forms[_author_of(record)].add(str(record["form"]))

    return {
        "sample_version": SAMPLE_VERSION,
        "sampling_method": SAMPLING_METHOD,
        "seed": seed,
        "source": {
            "path": str(source_path),
            "sha256": source_sha256,
            "records": len(all_records),
            "by_form": dict(source_forms),
            "unique_authors": len({_author_of(r) for r in all_records}),
        },
        "target": dict(targets),
        "selected": {
            "records": len(selected),
            "by_form": dict(selected_forms),
            "unique_authors": len(selected_authors),
            "authors_in_both_forms": sum(1 for forms in author_forms.values() if len(forms) > 1),
            "max_records_from_one_author": max(selected_authors.values(), default=0),
        },
        "constraints": {
            "max_per_author_per_form": max_per_author_per_form,
            "style_labels_are_still_unlabeled": True,
            "gold_status": "candidate_only_until_human_review",
        },
    }


def write_jsonl(records: Iterable[Mapping[str, Any]], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for record in records:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")


def write_json(obj: Mapping[str, Any], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)
        f.write("\n")


def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser(description="Sample author-balanced Tang poems for manual style annotation")
    ap.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    ap.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    ap.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    ap.add_argument("--qijue", type=int, default=DEFAULT_TARGETS["qijue7"])
    ap.add_argument("--qilv", type=int, default=DEFAULT_TARGETS["qilv7"])
    ap.add_argument("--seed", type=int, default=DEFAULT_SEED)
    ap.add_argument("--max-per-author-per-form", type=int, default=1)
    return ap.parse_args()


def main() -> int:
    args = parse_args()
    targets = {"qijue7": args.qijue, "qilv7": args.qilv}

    if not args.input.exists():
        raise FileNotFoundError(
            f"Missing candidate corpus: {args.input}. Run `python -m src.data.collect_corpus` first."
        )

    records = load_jsonl(args.input)
    source_hash = sha256_file(args.input)
    selected = sample_balanced(
        records,
        targets=targets,
        seed=args.seed,
        max_per_author_per_form=args.max_per_author_per_form,
    )
    annotation_records = prepare_annotation_records(
        selected,
        seed=args.seed,
        targets=targets,
        max_per_author_per_form=args.max_per_author_per_form,
    )
    report = build_report(
        source_path=args.input,
        source_sha256=source_hash,
        all_records=records,
        selected=annotation_records,
        seed=args.seed,
        targets=targets,
        max_per_author_per_form=args.max_per_author_per_form,
    )

    write_jsonl(annotation_records, args.output)
    write_json(report, args.report)

    print(json.dumps({"output": str(args.output), "report": str(args.report), **report["selected"]}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
