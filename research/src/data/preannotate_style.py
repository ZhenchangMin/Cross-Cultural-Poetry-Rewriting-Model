# -*- coding: utf-8 -*-
"""Hybrid V1 style pre-annotation for the 1000-poem Gold candidate set.

Design principles
-----------------
1. Never write weak labels directly into ``style``. Final training labels remain blank
   until human review.
2. Rule/lexicon cues annotate ``imagery`` and a partial ``density`` estimate.
3. An optional LLM stage annotates the judgment-heavy dimensions:
   ``emotion``, ``diction``, ``expression`` and ``energy``.
4. Every prelabel stores confidence, evidence and method for later review.
5. Paid LLM calls are opt-in. Running this module with no flags performs rules only.

Typical workflow (WSL, research/)
---------------------------------
    source .venv/bin/activate

    # Free/deterministic stage: all 1000 poems
    python -m src.data.preannotate_style

    # Optional small DeepSeek smoke test (explicitly incurs API usage)
    python -m src.data.preannotate_style --llm --llm-limit 5

    # Later, after inspecting the prompt/results, annotate all pending samples
    python -m src.data.preannotate_style --llm --llm-all --resume
"""
from __future__ import annotations

import argparse
import copy
import json
import math
import os
import re
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, MutableMapping, Optional, Sequence, Tuple
from urllib.parse import quote, urlsplit, urlunsplit

DEFAULT_INPUT = Path("data/processed/style_annotation/annotation_sample_v1.jsonl")
DEFAULT_OUTPUT = Path("data/processed/style_annotation/preannotated_v1.jsonl")
DEFAULT_REPORT = Path("data/processed/style_annotation/preannotation_report_v1.json")
DEFAULT_LEXICON = Path("configs/imagery_lexicon_v1.json")
DEFAULT_SCHEMA = Path("configs/style_schema.json")
ANNOTATION_VERSION = "v1"
RULE_METHOD = "lexicon_heuristic_v1"
LLM_METHOD = "deepseek_semantic_v1"
DEEPSEEK_URL = "https://api.deepseek.com/chat/completions"
LLM_DIMS = ("emotion", "diction", "expression", "energy")
RULE_DIMS = ("imagery", "density")


@dataclass(frozen=True)
class TermMatch:
    category: str
    term: str
    start: int
    end: int

    @property
    def length(self) -> int:
        return self.end - self.start


def load_json(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        obj = json.load(f)
    if not isinstance(obj, dict):
        raise ValueError(f"Expected JSON object: {path}")
    return obj


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
                raise ValueError(f"Expected object at {path}:{lineno}")
            records.append(obj)
    return records


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


def _all_term_matches(text: str, lexicon: Mapping[str, Sequence[str]]) -> List[TermMatch]:
    matches: List[TermMatch] = []
    for category, terms in lexicon.items():
        for term in terms:
            if not term:
                continue
            start = 0
            while True:
                idx = text.find(term, start)
                if idx < 0:
                    break
                matches.append(TermMatch(category, term, idx, idx + len(term)))
                start = idx + 1
    return matches


def find_imagery_matches(text: str, lexicon: Mapping[str, Sequence[str]]) -> Dict[str, List[str]]:
    """Return category -> matched terms, suppressing substring false positives.

    A shorter cue is discarded when its character span is strictly contained in a
    longer cue. Example: ``銀河`` should count as celestial but the ``河`` inside it
    should not independently create a landscape label. Equal-length identical-span
    matches are kept, because a cue such as ``關`` may legitimately support both
    travel and frontier weak labels.
    """
    raw = _all_term_matches(text, lexicon)
    kept: List[TermMatch] = []
    for match in raw:
        contained = any(
            other.length > match.length
            and other.start <= match.start
            and other.end >= match.end
            for other in raw
        )
        if not contained:
            kept.append(match)

    out: Dict[str, List[str]] = {category: [] for category in lexicon}
    for match in sorted(kept, key=lambda m: (m.start, -m.length, m.category, m.term)):
        if match.term not in out[match.category]:
            out[match.category].append(match.term)
    return out


def imagery_prelabel(text: str, lexicon_cfg: Mapping[str, Any]) -> Dict[str, Any]:
    categories = lexicon_cfg.get("categories")
    if not isinstance(categories, Mapping):
        raise ValueError("imagery lexicon missing categories")

    evidence = find_imagery_matches(text.replace("\n", ""), categories)  # type: ignore[arg-type]
    ranked = sorted(
        ((cat, terms) for cat, terms in evidence.items() if terms),
        key=lambda item: (-len(item[1]), list(categories).index(item[0])),
    )
    selected = [cat for cat, _ in ranked[:4]]
    selected_evidence = {cat: evidence[cat] for cat in selected}
    total_terms = sum(len(v) for v in selected_evidence.values())

    if not selected:
        confidence = 0.20
    else:
        # Evidence strength, not epistemic certainty: lexicon cues are intentionally weak.
        confidence = min(0.92, 0.42 + 0.07 * total_terms + 0.04 * len(selected))

    return {
        "value": selected,
        "confidence": round(confidence, 3),
        "evidence": selected_evidence,
        "method": RULE_METHOD,
        "status": "prelabeled",
    }


def _density_confidence(score: float, low: float, high: float) -> float:
    """Confidence rises with distance from the nearest decision boundary."""
    if score < low:
        distance = low - score
        scale = max(low, 0.5)
    elif score < high:
        distance = min(score - low, high - score)
        scale = max((high - low) / 2.0, 0.25)
    else:
        distance = score - high
        scale = max(high, 0.5)
    normalized = min(1.0, max(0.0, distance / scale))
    return 0.50 + 0.35 * normalized


def density_prelabel(text: str, imagery_result: Mapping[str, Any], lexicon_cfg: Mapping[str, Any]) -> Dict[str, Any]:
    density_cfg = lexicon_cfg.get("density", {})
    thresholds = density_cfg.get("thresholds", {}) if isinstance(density_cfg, Mapping) else {}
    low = float(thresholds.get("sparse_to_medium", 0.75))
    high = float(thresholds.get("medium_to_dense", 1.5))
    if not 0 <= low < high:
        raise ValueError("Invalid density thresholds")

    lines = [line for line in text.splitlines() if line.strip()]
    categories = lexicon_cfg.get("categories")
    if not isinstance(categories, Mapping):
        raise ValueError("imagery lexicon missing categories")
    # Density is a separate weak feature. Use all lexicon matches rather than only
    # the top-4 imagery labels exposed to the annotator, otherwise poems with many
    # different imagery systems would be artificially under-counted.
    all_evidence = find_imagery_matches(text.replace("\n", ""), categories)  # type: ignore[arg-type]
    terms: set[str] = set()
    for values in all_evidence.values():
        terms.update(str(x) for x in values)

    score = len(terms) / max(1, len(lines))
    if score < low:
        value = "sparse"
    elif score < high:
        value = "medium"
    else:
        value = "dense"

    return {
        "value": value,
        "confidence": round(_density_confidence(score, low, high), 3),
        "evidence": {
            "unique_imagery_terms": len(terms),
            "line_count": len(lines),
            "unique_imagery_terms_per_line": round(score, 3),
            "thresholds": {"sparse_to_medium": low, "medium_to_dense": high},
            "selected_imagery_labels": list(imagery_result.get("value", [])),
            "scope_note": "weak proxy: all lexicon imagery-cue concentration only",
        },
        "method": RULE_METHOD,
        "status": "prelabeled",
    }


def _pending_llm_dim() -> Dict[str, Any]:
    return {
        "value": None,
        "confidence": None,
        "evidence": [],
        "method": LLM_METHOD,
        "status": "pending_llm",
    }


def rule_preannotate_record(
    record: Mapping[str, Any],
    *,
    lexicon_cfg: Mapping[str, Any],
) -> Dict[str, Any]:
    """Attach weak annotation metadata while leaving the training ``style`` untouched."""
    item = copy.deepcopy(dict(record))
    text = item.get("text")
    if not isinstance(text, str) or not text.strip():
        raise ValueError(f"record {item.get('id')} has empty text")

    imagery = imagery_prelabel(text, lexicon_cfg)
    density = density_prelabel(text, imagery, lexicon_cfg)

    annotation = item.setdefault("annotation", {})
    annotation["version"] = ANNOTATION_VERSION
    annotation["prelabel"] = {
        "emotion": _pending_llm_dim(),
        "imagery": imagery,
        "diction": _pending_llm_dim(),
        "expression": _pending_llm_dim(),
        "energy": _pending_llm_dim(),
        "density": density,
    }
    annotation["review"] = {
        "status": "pending_human_review",
        "reviewer": None,
        "notes": None,
    }

    metadata = item.setdefault("metadata", {})
    if isinstance(metadata, MutableMapping):
        metadata["annotation_method"] = "hybrid_preannotation_v1"
        metadata["review_status"] = "preannotated_pending_review"
    return item


def _schema_values(schema: Mapping[str, Any], dim: str) -> Dict[str, str]:
    style = schema.get("style")
    if not isinstance(style, Mapping) or dim not in style:
        raise ValueError(f"schema missing style.{dim}")
    dim_cfg = style[dim]
    if not isinstance(dim_cfg, Mapping) or not isinstance(dim_cfg.get("values"), Mapping):
        raise ValueError(f"schema missing values for style.{dim}")
    return {str(k): str(v) for k, v in dim_cfg["values"].items()}


def build_llm_prompt(record: Mapping[str, Any], schema: Mapping[str, Any]) -> str:
    """Build an author-blind prompt for judgment-heavy dimensions.

    Metadata such as author/title is deliberately excluded to reduce shortcut bias.
    """
    text = str(record.get("text", ""))
    form = str(record.get("form", ""))

    definitions = []
    for dim in LLM_DIMS:
        values = _schema_values(schema, dim)
        definitions.append(
            f"{dim}: " + "; ".join(f"{key}={desc}" for key, desc in values.items())
        )

    return f"""你正在为中国古典诗歌风格研究做弱监督预标注。请只根据诗歌正文判断，不猜作者，不使用作者身份先验。

【诗体】{form}
【诗歌正文】
{text}

只标注以下四个维度：
{chr(10).join(definitions)}

要求：
1. emotion 必须选择 1~2 个合法标签；其余三个维度各选 1 个合法标签。
2. confidence 是 0~1 的小数，表示你对该判断的把握，不是文学质量评分。
3. evidence 只摘录诗中真正支持判断的短词或短语，每个维度最多 3 条；不要编造原文没有的词。
4. 如果两个标签都勉强成立，优先选择对全诗支配性更强的一个；emotion 才允许双标签。
5. 只输出一个 JSON 对象，不要 Markdown，不要解释性前后缀。

JSON 格式必须严格为：
{{
  "emotion": {{"value": ["label"], "confidence": 0.0, "evidence": ["原文短语"]}},
  "diction": {{"value": "label", "confidence": 0.0, "evidence": ["原文短语"]}},
  "expression": {{"value": "label", "confidence": 0.0, "evidence": ["原文短语"]}},
  "energy": {{"value": "label", "confidence": 0.0, "evidence": ["原文短语"]}}
}}
"""


def _extract_json_object(text: str) -> Dict[str, Any]:
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text, flags=re.IGNORECASE)
        text = re.sub(r"\s*```$", "", text)
    try:
        obj = json.loads(text)
    except json.JSONDecodeError:
        start = text.find("{")
        end = text.rfind("}")
        if start < 0 or end <= start:
            raise ValueError("LLM response does not contain a JSON object")
        obj = json.loads(text[start : end + 1])
    if not isinstance(obj, dict):
        raise ValueError("LLM response JSON must be an object")
    return obj


def validate_llm_result(result: Mapping[str, Any], schema: Mapping[str, Any], poem_text: str) -> Dict[str, Any]:
    normalized: Dict[str, Any] = {}
    for dim in LLM_DIMS:
        if dim not in result or not isinstance(result[dim], Mapping):
            raise ValueError(f"LLM result missing object: {dim}")
        block = result[dim]
        allowed = set(_schema_values(schema, dim))
        value = block.get("value")

        if dim == "emotion":
            if not isinstance(value, list) or not 1 <= len(value) <= 2:
                raise ValueError("emotion.value must contain 1-2 labels")
            labels = [str(v) for v in value]
            if len(labels) != len(set(labels)) or any(v not in allowed for v in labels):
                raise ValueError(f"invalid emotion labels: {labels}")
            normalized_value: Any = labels
        else:
            if not isinstance(value, str) or value not in allowed:
                raise ValueError(f"invalid {dim} label: {value!r}")
            normalized_value = value

        confidence = block.get("confidence")
        if not isinstance(confidence, (int, float)) or isinstance(confidence, bool):
            raise ValueError(f"{dim}.confidence must be numeric")
        confidence = float(confidence)
        if not 0.0 <= confidence <= 1.0:
            raise ValueError(f"{dim}.confidence outside [0,1]")

        evidence_raw = block.get("evidence", [])
        if not isinstance(evidence_raw, list) or len(evidence_raw) > 3:
            raise ValueError(f"{dim}.evidence must be a list of at most 3 strings")
        evidence: List[str] = []
        for phrase in evidence_raw:
            if not isinstance(phrase, str) or not phrase.strip():
                raise ValueError(f"invalid evidence in {dim}")
            phrase = phrase.strip()
            if phrase not in poem_text.replace("\n", ""):
                raise ValueError(f"evidence not found verbatim in poem for {dim}: {phrase!r}")
            evidence.append(phrase)

        normalized[dim] = {
            "value": normalized_value,
            "confidence": round(confidence, 3),
            "evidence": evidence,
            "method": LLM_METHOD,
            "status": "prelabeled",
        }
    return normalized


def _ascii_url(url: str) -> str:
    parts = urlsplit(url)
    return urlunsplit((parts.scheme, parts.netloc, quote(parts.path), parts.query, parts.fragment))


def call_deepseek(
    *,
    api_key: str,
    prompt: str,
    model: str = "deepseek-chat",
    timeout: int = 90,
) -> str:
    payload = {
        "model": model,
        "messages": [
            {
                "role": "system",
                "content": "你是严格的古典诗歌数据标注器。必须遵守给定标签枚举，并只返回 JSON。",
            },
            {"role": "user", "content": prompt},
        ],
        "temperature": 0,
        "max_tokens": 700,
    }
    req = urllib.request.Request(
        _ascii_url(DEEPSEEK_URL),
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        method="POST",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "User-Agent": "poetry-research-style-annotation/1.0",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as response:
            body = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"DeepSeek HTTP {exc.code}: {detail[:500]}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"DeepSeek network error: {exc}") from exc

    try:
        return str(body["choices"][0]["message"]["content"])
    except (KeyError, IndexError, TypeError) as exc:
        raise RuntimeError(f"Unexpected DeepSeek response shape: {body}") from exc


def apply_llm_prelabel(record: Dict[str, Any], *, schema: Mapping[str, Any], api_key: str, model: str) -> None:
    prompt = build_llm_prompt(record, schema)
    raw = call_deepseek(api_key=api_key, prompt=prompt, model=model)
    parsed = _extract_json_object(raw)
    validated = validate_llm_result(parsed, schema, str(record["text"]))
    prelabel = record["annotation"]["prelabel"]
    for dim, block in validated.items():
        prelabel[dim] = block


def _has_llm_labels(record: Mapping[str, Any]) -> bool:
    try:
        prelabel = record["annotation"]["prelabel"]
        return all(prelabel[dim].get("status") == "prelabeled" for dim in LLM_DIMS)
    except (KeyError, TypeError, AttributeError):
        return False


def build_report(records: Sequence[Mapping[str, Any]], *, llm_attempted: int, llm_success: int, llm_failed: int) -> Dict[str, Any]:
    imagery_empty = 0
    imagery_counts: Dict[str, int] = {}
    density_counts = {"sparse": 0, "medium": 0, "dense": 0}
    llm_complete = 0

    for record in records:
        prelabel = record.get("annotation", {}).get("prelabel", {})  # type: ignore[union-attr]
        imagery = prelabel.get("imagery", {}).get("value", []) if isinstance(prelabel, Mapping) else []
        if not imagery:
            imagery_empty += 1
        else:
            for label in imagery:
                imagery_counts[str(label)] = imagery_counts.get(str(label), 0) + 1
        density = prelabel.get("density", {}).get("value") if isinstance(prelabel, Mapping) else None
        if density in density_counts:
            density_counts[str(density)] += 1
        if _has_llm_labels(record):
            llm_complete += 1

    return {
        "annotation_version": ANNOTATION_VERSION,
        "records": len(records),
        "rules": {
            "method": RULE_METHOD,
            "imagery_empty": imagery_empty,
            "imagery_label_counts": imagery_counts,
            "density_label_counts": density_counts,
        },
        "llm": {
            "method": LLM_METHOD,
            "complete_records": llm_complete,
            "attempted_this_run": llm_attempted,
            "success_this_run": llm_success,
            "failed_this_run": llm_failed,
        },
        "gold_status": "candidate_only_until_human_review",
        "style_fields_modified": False,
    }


def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser(description="Hybrid weak style pre-annotation for Tang Gold candidates")
    ap.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    ap.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    ap.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    ap.add_argument("--lexicon", type=Path, default=DEFAULT_LEXICON)
    ap.add_argument("--schema", type=Path, default=DEFAULT_SCHEMA)
    ap.add_argument("--llm", action="store_true", help="Opt in to paid/external DeepSeek semantic annotation")
    ap.add_argument("--llm-limit", type=int, default=10, help="Max pending LLM records this run; ignored with --llm-all")
    ap.add_argument("--llm-all", action="store_true", help="Annotate all pending records; requires --llm")
    ap.add_argument("--resume", action="store_true", help="Reuse existing output so completed LLM labels are preserved")
    ap.add_argument("--api-key-env", default="DEEPSEEK_API_KEY")
    ap.add_argument("--model", default="deepseek-chat")
    return ap.parse_args()


def main() -> int:
    args = parse_args()
    if args.llm_limit < 0:
        raise ValueError("--llm-limit must be >= 0")
    if args.llm_all and not args.llm:
        raise ValueError("--llm-all requires --llm")

    lexicon_cfg = load_json(args.lexicon)
    schema = load_json(args.schema)

    if args.resume and args.output.exists():
        records = load_jsonl(args.output)
        # Refresh only the rule dimensions so lexicon improvements are reproducible,
        # while preserving any completed LLM judgments.
        refreshed: List[Dict[str, Any]] = []
        for existing in records:
            old_prelabel = copy.deepcopy(existing.get("annotation", {}).get("prelabel", {}))
            item = rule_preannotate_record(existing, lexicon_cfg=lexicon_cfg)
            for dim in LLM_DIMS:
                if isinstance(old_prelabel, Mapping) and old_prelabel.get(dim, {}).get("status") == "prelabeled":
                    item["annotation"]["prelabel"][dim] = old_prelabel[dim]
            refreshed.append(item)
        records = refreshed
    else:
        source = load_jsonl(args.input)
        records = [rule_preannotate_record(record, lexicon_cfg=lexicon_cfg) for record in source]

    llm_attempted = llm_success = llm_failed = 0
    if args.llm:
        api_key = os.getenv(args.api_key_env, "").strip()
        if not api_key:
            raise RuntimeError(f"{args.api_key_env} is not set; rules-only output is safe and free")
        pending = [record for record in records if not _has_llm_labels(record)]
        if not args.llm_all:
            pending = pending[: args.llm_limit]

        for idx, record in enumerate(pending, 1):
            llm_attempted += 1
            try:
                apply_llm_prelabel(record, schema=schema, api_key=api_key, model=args.model)
                llm_success += 1
                print(f"[llm {idx}/{len(pending)}] ok {record.get('id')}")
            except Exception as exc:  # retain record for human/next-run review
                llm_failed += 1
                record.setdefault("annotation", {}).setdefault("errors", []).append(
                    {"stage": "llm", "message": str(exc)[:1000]}
                )
                print(f"[llm {idx}/{len(pending)}] failed {record.get('id')}: {exc}")

    report = build_report(
        records,
        llm_attempted=llm_attempted,
        llm_success=llm_success,
        llm_failed=llm_failed,
    )
    write_jsonl(records, args.output)
    write_json(report, args.report)
    print(json.dumps({"output": str(args.output), "report": str(args.report), **report}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
