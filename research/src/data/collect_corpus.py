# -*- coding: utf-8 -*-
"""Collect Tang regulated-verse *structural candidates* for style annotation.

This module deliberately separates three stages:

1. Upstream corpus acquisition (data/external, not committed)
2. Deterministic structural filtering (this file)
3. Style annotation / training split (later stages)

The first-pass form detector is intentionally conservative:
- qijue7 candidate: exactly 4 verse lines, each exactly 7 Han characters
- qilv7 candidate: exactly 8 verse lines, each exactly 7 Han characters

This does NOT prove that a poem satisfies historical regulated-verse prosody.
Ping/ze patterns, Pingshui rhyme, exceptions, and poetic parallelism require
separate validation. Therefore the output is named an annotation-candidate
corpus rather than a final training corpus.

Default upstream source:
    https://github.com/chinese-poetry/chinese-poetry
    directory: 全唐诗/

Run in WSL from research/:
    source .venv/bin/activate
    python -m src.data.collect_corpus

Useful smoke test:
    python -m src.data.collect_corpus --max-files 1 --max-poems 20 \
        --output data/raw/tang_candidates_smoke.jsonl
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, Iterator, List, Optional, Sequence, Tuple

SOURCE_REPO = "https://github.com/chinese-poetry/chinese-poetry.git"
SOURCE_WEB = "https://github.com/chinese-poetry/chinese-poetry"
SOURCE_LICENSE = "MIT"
SOURCE_COLLECTION = "全唐诗"
SOURCE_API = (
    "https://api.github.com/repos/chinese-poetry/chinese-poetry/contents/"
    "%E5%85%A8%E5%94%90%E8%AF%97?ref=master"
)
HTTP_USER_AGENT = "Cross-Cultural-Poetry-Rewriting-Model/1.0"

DEFAULT_SOURCE_DIR = Path("data/external/chinese-poetry")
DEFAULT_OUTPUT = Path("data/raw/tang_style_annotation_candidates.jsonl")

# Verse punctuation used by the upstream corpus. A paragraph usually contains
# one couplet, e.g. "秦川雄帝宅，函谷壯皇居。".
_SENTENCE_SPLIT_RE = re.compile(r"[，。！？；：,.!?;:\n\r]+")
_WHITESPACE_RE = re.compile(r"\s+")


@dataclass(frozen=True)
class Candidate:
    source_id: str
    title: str
    author: str
    source_file: str
    form: str
    lines: Tuple[str, ...]

    @property
    def text(self) -> str:
        return "\n".join(self.lines)


def _is_cjk(ch: str) -> bool:
    """Return True for common and extension CJK unified ideographs."""
    cp = ord(ch)
    return (
        0x3400 <= cp <= 0x4DBF  # Extension A
        or 0x4E00 <= cp <= 0x9FFF  # Unified Ideographs
        or 0xF900 <= cp <= 0xFAFF  # Compatibility Ideographs
        or 0x20000 <= cp <= 0x2FA1F  # Extensions B-F + compatibility supplement
        or 0x30000 <= cp <= 0x3134F  # Extension G
    )


def _normalize_piece(text: str) -> str:
    """Remove whitespace only; do not simplify or rewrite historical text."""
    return _WHITESPACE_RE.sub("", text.strip())


def split_verse_lines(paragraphs: Sequence[str]) -> List[str]:
    """Split upstream paragraph strings into individual verse lines.

    The upstream `paragraphs` field commonly stores a whole couplet per item,
    so counting paragraphs is not the same as counting verse lines.
    """
    lines: List[str] = []
    for paragraph in paragraphs:
        if not isinstance(paragraph, str):
            continue
        for piece in _SENTENCE_SPLIT_RE.split(paragraph):
            clean = _normalize_piece(piece)
            if clean:
                lines.append(clean)
    return lines


def is_exact_han_line(line: str, chars: int = 7) -> bool:
    """Check exact character count and reject annotations/non-Han symbols."""
    return len(line) == chars and all(_is_cjk(ch) for ch in line)


def detect_form(lines: Sequence[str]) -> Optional[str]:
    """Detect V1 form by structure only.

    Returns:
        'qijue7', 'qilv7', or None.
    """
    if not all(is_exact_han_line(line, 7) for line in lines):
        return None
    if len(lines) == 4:
        return "qijue7"
    if len(lines) == 8:
        return "qilv7"
    return None


def _blank_style() -> Dict[str, Any]:
    """Return the V1 style annotation template (unlabeled at collection time)."""
    return {
        "emotion": [],
        "imagery": [],
        "diction": "",
        "expression": "",
        "energy": "",
        "density": "",
    }


def _stable_project_id(source_id: str, text: str) -> str:
    """Build a stable project-local ID while preserving upstream provenance."""
    if source_id:
        return f"tang-{source_id}"
    digest = hashlib.sha1(text.encode("utf-8")).hexdigest()[:16]
    return f"tang-sha1-{digest}"


def candidate_to_record(candidate: Candidate) -> Dict[str, Any]:
    """Convert one structural candidate to the project V1 annotation format."""
    text = candidate.text
    return {
        "id": _stable_project_id(candidate.source_id, text),
        "text": text,
        "form": candidate.form,
        "style": _blank_style(),
        "culture": {"adaptation": None},
        "metadata": {
            "title": candidate.title,
            "author": candidate.author,
            "dynasty": "唐",
            "source": "chinese-poetry/chinese-poetry:全唐诗",
            "collection": SOURCE_COLLECTION,
            "source_id": candidate.source_id,
            "source_file": candidate.source_file,
            "source_url": SOURCE_WEB,
            "source_license": SOURCE_LICENSE,
            "script": "traditional",
            "form_detection": "automatic_structure_only",
            "annotation_method": "style_unlabeled",
            "review_status": "unreviewed",
        },
    }


def iter_source_files(source_dir: Path) -> List[Path]:
    """Return locally cached full-Tang JSON shards in deterministic order."""
    tang_dir = source_dir / SOURCE_COLLECTION
    if not tang_dir.is_dir():
        raise FileNotFoundError(
            f"Missing upstream directory: {tang_dir}. "
            "Run without --no-download, or provide --source-dir."
        )

    files = list(tang_dir.glob("poet.tang.*.json"))

    def shard_key(path: Path) -> Tuple[int, str]:
        m = re.search(r"poet\.tang\.(\d+)\.json$", path.name)
        return (int(m.group(1)) if m else sys.maxsize, path.name)

    files.sort(key=shard_key)
    if not files:
        raise FileNotFoundError(f"No poet.tang.*.json files found under {tang_dir}")
    return files


def iter_candidates(
    source_files: Iterable[Path],
    allowed_forms: Sequence[str] = ("qijue7", "qilv7"),
) -> Iterator[Candidate]:
    """Yield deduplicated structural candidates from upstream JSON shards."""
    allowed = set(allowed_forms)
    seen_texts: set[str] = set()

    for path in source_files:
        with path.open("r", encoding="utf-8") as f:
            items = json.load(f)
        if not isinstance(items, list):
            continue

        for item in items:
            if not isinstance(item, dict):
                continue
            paragraphs = item.get("paragraphs")
            if not isinstance(paragraphs, list) or not paragraphs:
                continue

            lines = split_verse_lines(paragraphs)
            form = detect_form(lines)
            if form is None or form not in allowed:
                continue

            text = "\n".join(lines)
            if text in seen_texts:
                continue
            seen_texts.add(text)

            yield Candidate(
                source_id=str(item.get("id") or ""),
                title=str(item.get("title") or "").strip(),
                author=str(item.get("author") or "").strip(),
                source_file=path.name,
                form=form,
                lines=tuple(lines),
            )


def _ascii_url(url: str) -> str:
    """Percent-encode non-ASCII URL path/query components for urllib/http.client."""
    parts = urllib.parse.urlsplit(url)
    path = urllib.parse.quote(urllib.parse.unquote(parts.path), safe="/%:@")
    query = urllib.parse.quote(urllib.parse.unquote(parts.query), safe="=&%:+,;@/?")
    return urllib.parse.urlunsplit((parts.scheme, parts.netloc, path, query, parts.fragment))


def _http_get_bytes(url: str, retries: int = 3, timeout: int = 30) -> bytes:
    """Download bytes with a small retry loop and an explicit User-Agent."""
    url = _ascii_url(url)
    last_error: Optional[BaseException] = None
    for attempt in range(1, retries + 1):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": HTTP_USER_AGENT})
            with urllib.request.urlopen(req, timeout=timeout) as response:
                return response.read()
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            last_error = exc
            if attempt < retries:
                time.sleep(float(attempt))
    raise RuntimeError(f"Failed to download {url}: {last_error}") from last_error


def _remote_shards() -> List[Dict[str, str]]:
    """List canonical Tang JSON shards using one GitHub Contents API request."""
    payload = json.loads(_http_get_bytes(SOURCE_API).decode("utf-8"))
    if not isinstance(payload, list):
        raise RuntimeError("Unexpected GitHub API response: expected a directory list")

    shards: List[Dict[str, str]] = []
    for item in payload:
        if not isinstance(item, dict):
            continue
        name = str(item.get("name") or "")
        if not re.fullmatch(r"poet\.tang\.\d+\.json", name):
            continue
        download_url = str(item.get("download_url") or "")
        if download_url:
            shards.append({"name": name, "download_url": download_url})

    def shard_key(item: Dict[str, str]) -> Tuple[int, str]:
        m = re.search(r"poet\.tang\.(\d+)\.json$", item["name"])
        return (int(m.group(1)) if m else sys.maxsize, item["name"])

    shards.sort(key=shard_key)
    if not shards:
        raise RuntimeError("GitHub API returned no poet.tang.*.json shards")
    return shards


def ensure_source(
    source_dir: Path,
    allow_download: bool = True,
    max_files: Optional[int] = None,
) -> List[Path]:
    """Ensure required upstream shards exist and return local file paths.

    We intentionally download only the `poet.tang.*.json` shards instead of
    cloning the whole upstream repository. This keeps the external cache small
    and avoids Git transport differences across Windows/WSL environments.
    """
    tang_dir = source_dir / SOURCE_COLLECTION

    if not allow_download:
        files = iter_source_files(source_dir)
        return files[:max_files] if max_files is not None else files

    tang_dir.mkdir(parents=True, exist_ok=True)
    shards = _remote_shards()
    if max_files is not None:
        shards = shards[:max_files]

    local_files = [tang_dir / shard["name"] for shard in shards]
    missing = [
        (shard, tang_dir / shard["name"])
        for shard in shards
        if not (tang_dir / shard["name"]).exists()
        or (tang_dir / shard["name"]).stat().st_size == 0
    ]

    def download_one(shard: Dict[str, str], target: Path) -> str:
        data = _http_get_bytes(shard["download_url"])
        # Parse before committing the cache file, so an HTML/error response is
        # never mistaken for a valid corpus shard on the next run.
        parsed = json.loads(data.decode("utf-8"))
        if not isinstance(parsed, list):
            raise RuntimeError(f"Unexpected JSON structure in {shard['name']}")
        tmp = target.with_suffix(target.suffix + ".tmp")
        tmp.write_bytes(data)
        tmp.replace(target)
        return shard["name"]

    if missing:
        workers = min(6, len(missing))
        print(f"[download] missing={len(missing)}, workers={workers}")
        with ThreadPoolExecutor(max_workers=workers) as pool:
            futures = {
                pool.submit(download_one, shard, target): shard["name"]
                for shard, target in missing
            }
            completed = 0
            for future in as_completed(futures):
                name = future.result()
                completed += 1
                print(f"[download {completed}/{len(missing)}] {name}")

    return local_files


def collect(
    source_dir: Path,
    output: Path,
    allowed_forms: Sequence[str],
    max_files: Optional[int] = None,
    max_poems: Optional[int] = None,
    allow_download: bool = True,
) -> Dict[str, Any]:
    """Collect candidates and return reproducibility statistics."""
    files = ensure_source(
        source_dir,
        allow_download=allow_download,
        max_files=max_files,
    )

    output.parent.mkdir(parents=True, exist_ok=True)
    counts: Counter[str] = Counter()
    n_written = 0

    with output.open("w", encoding="utf-8", newline="\n") as f:
        for candidate in iter_candidates(files, allowed_forms=allowed_forms):
            record = candidate_to_record(candidate)
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
            counts[candidate.form] += 1
            n_written += 1
            if max_poems is not None and n_written >= max_poems:
                break

    stats = {
        "source_repo": SOURCE_REPO,
        "source_collection": SOURCE_COLLECTION,
        "source_files_scanned": len(files),
        "output": str(output),
        "written": n_written,
        "by_form": dict(sorted(counts.items())),
        "form_detection": "structure_only",
    }
    return stats


def _parse_forms(raw: str) -> List[str]:
    forms = [part.strip() for part in raw.split(",") if part.strip()]
    allowed = {"qijue7", "qilv7"}
    unknown = [form for form in forms if form not in allowed]
    if unknown:
        raise argparse.ArgumentTypeError(f"Unknown forms: {unknown}; allowed={sorted(allowed)}")
    if not forms:
        raise argparse.ArgumentTypeError("At least one form is required")
    return forms


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Collect Tang qijue7/qilv7 structural candidates for V1 style annotation."
    )
    ap.add_argument("--source-dir", type=Path, default=DEFAULT_SOURCE_DIR)
    ap.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    ap.add_argument(
        "--forms",
        type=_parse_forms,
        default=["qijue7", "qilv7"],
        help="Comma-separated: qijue7,qilv7",
    )
    ap.add_argument("--max-files", type=int, default=None, help="Debug/smoke-test limit")
    ap.add_argument("--max-poems", type=int, default=None, help="Debug/smoke-test limit")
    ap.add_argument(
        "--no-download",
        action="store_true",
        help="Use only locally cached upstream shards; fail if none exist",
    )
    args = ap.parse_args()

    stats = collect(
        source_dir=args.source_dir,
        output=args.output,
        allowed_forms=args.forms,
        max_files=args.max_files,
        max_poems=args.max_poems,
        allow_download=not args.no_download,
    )
    print(json.dumps(stats, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
