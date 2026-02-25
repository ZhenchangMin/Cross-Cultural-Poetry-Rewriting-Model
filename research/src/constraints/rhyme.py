# -*- coding: utf-8 -*-
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Dict, Any, Optional

from pypinyin import pinyin, Style

_PUNCT_RE = re.compile(r"[，。！？；：、,.!?;:\s\"'“”‘’（）()\[\]{}《》<>…—\-]+")


def _clean_line(line: str) -> str:
    return re.sub(_PUNCT_RE, "", line.strip())


def _last_char(clean_line: str) -> Optional[str]:
    clean_line = clean_line.strip()
    if not clean_line:
        return None
    return clean_line[-1]


def _finals_of_char(ch: str) -> Optional[str]:
    if not ch:
        return None
    py = pinyin(ch, style=Style.FINALS, strict=False)
    if not py or not py[0] or not py[0][0]:
        return None
    return py[0][0]


def _normalize_finals(finals: str, mode: str = "strict") -> str:
    """
    mode:
      - strict: no normalization
      - loose: light normalization to approximate rhyme groups
    """
    finals = finals.strip().lower()
    if mode == "strict":
        return finals

    # loose normalization (heuristic):
    # - merge uang -> ang (霜/光/乡 often rhyme-ish in modern ear)
    # - merge iang -> ang (强/香/凉 may rhyme-ish with ang group)
    # - merge eng/ing/ong? 先不乱合并，避免过宽
    mapping = {
        "uang": "ang",
        "iang": "ang",
        # 你也可以逐步扩展：
        # "iong": "ong",
    }
    return mapping.get(finals, finals)


@dataclass
class RhymeResult:
    ok: bool
    score: float
    finals_2: Optional[str]
    finals_4: Optional[str]
    last_2: Optional[str]
    last_4: Optional[str]
    details: str


def check_qijue7_rhyme(text: str, mode: str = "strict") -> RhymeResult:
    lines_raw = [ln.strip() for ln in text.splitlines() if ln.strip()]
    lines_clean = [_clean_line(ln) for ln in lines_raw]

    if len(lines_clean) < 4:
        return RhymeResult(
            ok=False,
            score=0.0,
            finals_2=None,
            finals_4=None,
            last_2=None,
            last_4=None,
            details=f"Need >=4 lines for rhyme check, got {len(lines_clean)}",
        )

    last2 = _last_char(lines_clean[1])
    last4 = _last_char(lines_clean[3])

    if not last2 or not last4:
        return RhymeResult(
            ok=False,
            score=0.0,
            finals_2=None,
            finals_4=None,
            last_2=last2,
            last_4=last4,
            details="Empty last char in line 2 or 4",
        )

    f2 = _finals_of_char(last2)
    f4 = _finals_of_char(last4)

    if not f2 or not f4:
        return RhymeResult(
            ok=False,
            score=0.0,
            finals_2=f2,
            finals_4=f4,
            last_2=last2,
            last_4=last4,
            details="Failed to get finals for last chars",
        )

    nf2 = _normalize_finals(f2, mode=mode)
    nf4 = _normalize_finals(f4, mode=mode)

    ok = (nf2 == nf4)

    return RhymeResult(
        ok=ok,
        score=1.0 if ok else 0.0,
        finals_2=f"{f2}->{nf2}" if mode != "strict" else f2,
        finals_4=f"{f4}->{nf4}" if mode != "strict" else f4,
        last_2=last2,
        last_4=last4,
        details="OK" if ok else f"Rhyme mismatch: line2({last2}:{nf2}) vs line4({last4}:{nf4})",
    )


def as_dict(res: RhymeResult) -> Dict[str, Any]:
    return {
        "ok": res.ok,
        "score": res.score,
        "last_2": res.last_2,
        "finals_2": res.finals_2,
        "last_4": res.last_4,
        "finals_4": res.finals_4,
        "details": res.details,
    }