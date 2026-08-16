# -*- coding: utf-8 -*-
"""把 docs/ 下的 docx 语料材料结构化为 JSONL，输出到 research/data/raw/。

- 韩国诗合集.docx → korean_samples.jsonl（乡歌/时调/现代诗，原文+中译）
- 俄语诗歌材料.docx → russian_samples.jsonl（普希金三首，原文+中译）

用法（WSL, research/ 目录下）：
    .venv/bin/python -m src.data.docx_to_jsonl --docs ../docs --out data/raw
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Dict, List, Optional

from docx import Document

CYR_RE = re.compile(r"[А-Яа-яЁё]")
HANGUL_RE = re.compile(r"[가-힣]")
CIRCLED_NUM_RE = re.compile(r"^[①②③④⑤⑥⑦⑧⑨⑩⑪⑫⑬⑭⑮]")
RU_TITLE_RE = re.compile(r"^(给娜塔利亚|我记得那美妙的一瞬|致大海)[\s①②③④⑤⑥⑦⑧⑨⑩⑪⑫⑬⑭⑮]*$")
AUTHOR_RE = re.compile(r"[（(]([^（）()]{1,12})\s*作[）)]")
HYANGGA_TITLE_RE = re.compile(r"^(.*?)([가-힣][가-힣\s]*)?（(四句体|八句体|十句体)）$")
SLASH_SEP_RE = re.compile(r"\s*/\s*")

KOREAN_PROSE_PREFIXES = ("形式：", "四句体：", "十句体：", "吏读：", "平时调：", "两种变体：")
KOREAN_SECTIONS = {"乡歌：", "时调：", "辞说时调："}


def _is_ru(text: str) -> bool:
    n = len(CYR_RE.findall(text))
    return n >= 3 or (n > 0 and n / max(1, len(text.replace(" ", ""))) > 0.3)


def _nonempty_paras(doc_path: Path) -> List[str]:
    doc = Document(str(doc_path))
    return [p.text.strip() for p in doc.paragraphs if p.text.strip()]


# ── 韩国诗合集 ─────────────────────────────────────────────────────────

def parse_korean(doc_path: Path) -> List[Dict]:
    paras = _nonempty_paras(doc_path)
    entries: List[Dict] = []
    section = None
    # 当前正在收集的字段：("hyangchal"|"ko"|"zh"|"ko_sijo"|"zh_sijo"|"zh_modern", entry, buffer)
    state: Optional[str] = None
    cur: Optional[Dict] = None

    def flush():
        nonlocal cur, state
        if cur is not None:
            for key in ("text_ko", "text_zh", "hyangchal"):
                v = cur.get(key)
                if isinstance(v, list):
                    cur[key] = "\n".join(v).strip()
            if cur.get("text_ko") or cur.get("text_zh") or cur.get("hyangchal"):
                entries.append(cur)
        cur, state = None, None

    def set_field(field: str, entry: Dict):
        nonlocal state, cur
        flush_if_new(entry)
        state = field
        entry[field] = []

    def flush_if_new(entry: Dict):
        nonlocal cur
        if cur is not None and cur is not entry:
            flush()
        cur = entry

    i = 0
    while i < len(paras):
        line = paras[i]

        if line in KOREAN_SECTIONS:
            flush()
            section = line[:-1]
            i += 1
            continue

        if any(line.startswith(p) for p in KOREAN_PROSE_PREFIXES):
            i += 1
            continue

        # 乡歌条目标题：xxx韩文（四句体）
        m = HYANGGA_TITLE_RE.match(line)
        if m and section == "乡歌":
            flush()
            cur = {
                "section": section,
                "form": m.group(3),
                "title_zh": m.group(1).strip() or None,
                "title_ko": (m.group(2) or "").strip() or None,
                "lang": "ko",
                "source": "docs/韩国诗合集.docx",
            }
            i += 1
            continue

        # 乡歌三栏
        if cur is not None and section == "乡歌":
            if line.startswith("“吏读”版本：") or line.startswith("\u201c吏读\u201d版本："):
                set_field("hyangchal", cur)
                rest = line.split("：", 1)[1] if "：" in line else ""
                if rest:
                    cur["hyangchal"].append(rest)
                i += 1
                continue
            if line.startswith("现代韩文版："):
                set_field("text_ko", cur)
                rest = line.split("：", 1)[1] if "：" in line else ""
                if rest:
                    cur["text_ko"].append(rest)
                i += 1
                continue
            if line.startswith("中文翻译："):
                set_field("text_zh", cur)
                rest = line.split("：", 1)[1] if "：" in line else ""
                if rest:
                    cur["text_zh"].append(rest)
                i += 1
                continue
            # 三栏的续行
            if state in ("hyangchal", "text_ko", "text_zh") and cur.get(state) is not None \
                    and not line.startswith("原文") and not line.startswith("译文"):
                cur[state].append(line)
                i += 1
                continue

        # 时调/现代诗：原文： → 译文：
        if line.startswith("原文："):
            # 现代诗标题：紧邻原文：之前的独立行（排除字段标记、章节头、
            # 说明文字，以及上一首译文的末句——标题不会以句读标点结尾）
            prev = paras[i - 1] if i > 0 else ""
            prev_ok = (prev
                       and not prev.startswith(("译文", "原文"))
                       and not any(prev.startswith(p) for p in KOREAN_PROSE_PREFIXES)
                       and not prev.endswith(("：", "。", "！", "？", "；", "，", "…")))
            title_candidate = prev if prev_ok else None
            # 辞说时调区之后没有新的章节头，带标题的独立诗按现代诗归类
            if title_candidate and section == "辞说时调":
                section = "现代诗"
            flush()
            cur = {
                "section": section,
                "lang": "ko",
                "title": title_candidate,
                "source": "docs/韩国诗合集.docx",
            }
            set_field("text_ko", cur)
            rest = line.split("：", 1)[1] if "：" in line else ""
            if rest:
                cur["text_ko"].append(rest)
            i += 1
            continue

        if line.startswith("译文："):
            if cur is None:
                cur = {"section": section, "lang": "ko", "title": None,
                       "source": "docs/韩国诗合集.docx"}
            set_field("text_zh", cur)
            rest = line.split("：", 1)[1] if "：" in line else ""
            if rest:
                cur["text_zh"].append(rest)
            i += 1
            continue

        # 原文/译文的续行
        if state in ("text_ko", "text_zh") and cur is not None and cur.get(state) is not None:
            cur[state].append(line)
            i += 1
            continue

        i += 1

    flush()

    # 后处理：作者、单行 " / " 分隔、独立成行的（作者 作）
    for e in entries:
        ko = e.get("text_ko")
        if isinstance(ko, str) and " / " in ko and "\n" not in ko:
            e["text_ko"] = "\n".join(SLASH_SEP_RE.split(ko))
        if isinstance(ko, str):
            m2 = AUTHOR_RE.search(ko)
            if m2:
                e["author"] = m2.group(1).strip()
                e["text_ko"] = AUTHOR_RE.sub("", e["text_ko"]).strip()

    # 编号
    for idx, e in enumerate(entries, 1):
        sec_en = {"乡歌": "hyangga", "时调": "sijo", "辞说时调": "sijo-variant",
                  "现代诗": "modern"}.get(e["section"], "misc")
        e["id"] = f"ko-{sec_en}-{idx:03d}"
        e.pop("section", None)
        e2 = {"id": e["id"], "section": sec_en}
        e2.update({k: v for k, v in e.items() if k != "id"})
        entries[idx - 1] = e2
    return entries


# ── 俄语诗歌材料 ──────────────────────────────────────────────────────

def parse_russian(doc_path: Path) -> List[Dict]:
    paras = _nonempty_paras(doc_path)
    entries: List[Dict] = []
    cur: Optional[Dict] = None
    mode: Optional[str] = None  # "zh" | "ru" | "notes"

    for line in paras:
        if RU_TITLE_RE.match(line):
            if cur:
                entries.append(cur)
            title = CIRCLED_NUM_RE.sub("", line).strip()
            cur = {"author": "普希金", "title_zh": title, "lang": "ru",
                   "source": "docs/俄语诗歌材料.docx"}
            mode = "zh"
            continue
        if cur is None:
            continue

        if line in ("俄语原文：", "中译文："):
            mode = "ru" if line == "俄语原文：" else "zh"
            cur.setdefault("text_ru" if mode == "ru" else "text_zh", [])
            continue

        if mode == "zh":
            if CIRCLED_NUM_RE.match(line):
                mode = "notes"
                cur.setdefault("notes", []).append(line)
            elif re.match(r"^\d{4}$", line):
                cur["year"] = line
            elif line.endswith("译") or re.match(r"^[\u4e00-\u9fff\s·]+译$", line):
                cur["translator"] = line[:-1].strip() if line.endswith("译") else line
            elif _is_ru(line):
                # 有的诗没有"俄语原文："标记，直接以俄文行开始
                mode = "ru"
                cur.setdefault("text_ru", []).append(line)
            else:
                cur.setdefault("text_zh", []).append(line)
        elif mode == "ru":
            if _is_ru(line):
                cur.setdefault("text_ru", []).append(line)
            else:
                mode = "notes"
                cur.setdefault("notes", []).append(line)
        else:  # notes
            if _is_ru(line):
                mode = "ru"
                cur.setdefault("text_ru", []).append(line)
            else:
                cur.setdefault("notes", []).append(line)

    if cur:
        entries.append(cur)

    for idx, e in enumerate(entries, 1):
        for key in ("text_ru", "text_zh", "notes"):
            if isinstance(e.get(key), list):
                e[key] = "\n".join(e[key]).strip()
        e["id"] = f"ru-pushkin-{idx:03d}"

    return entries


def write_jsonl(entries: List[Dict], out_path: Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        for e in entries:
            f.write(json.dumps(e, ensure_ascii=False) + "\n")
    print(f"{out_path}: {len(entries)} 条")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--docs", type=Path, default=Path("../docs"))
    ap.add_argument("--out", type=Path, default=Path("data/raw"))
    args = ap.parse_args()

    ko_doc = args.docs / "韩国诗合集.docx"
    ru_doc = args.docs / "俄语诗歌材料.docx"

    if ko_doc.exists():
        ko = parse_korean(ko_doc)
        write_jsonl(ko, args.out / "korean_samples.jsonl")
        for e in ko:
            has_ko = bool(e.get("text_ko") or e.get("hyangchal"))
            if not has_ko or not e.get("text_zh"):
                print(f"  [warn] {e['id']}: ko={'Y' if has_ko else 'N'} zh={'Y' if e.get('text_zh') else 'N'} title={e.get('title_zh') or e.get('title')}", file=sys.stderr)
    else:
        print(f"missing: {ko_doc}", file=sys.stderr)

    if ru_doc.exists():
        ru = parse_russian(ru_doc)
        write_jsonl(ru, args.out / "russian_samples.jsonl")
        for e in ru:
            if not e.get("text_ru") or not e.get("text_zh"):
                print(f"  [warn] {e['id']} {e.get('title_zh')}: ru={'Y' if e.get('text_ru') else 'N'} zh={'Y' if e.get('text_zh') else 'N'}", file=sys.stderr)
    else:
        print(f"missing: {ru_doc}", file=sys.stderr)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
