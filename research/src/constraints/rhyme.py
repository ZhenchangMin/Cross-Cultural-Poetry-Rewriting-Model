# -*- coding: utf-8 -*-
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import List, Dict, Any, Optional, Tuple

from pypinyin import pinyin, Style

# 去标点用（要和 meter 一致）
_PUNCT_RE = re.compile(r"[，。！？；：、,.!?;:\s\"'“”‘’（）()\[\]{}《》<>…—\-]+")


def _clean_line(line: str) -> str:
    return re.sub(_PUNCT_RE, "", line.strip())


def _last_char(clean_line: str) -> Optional[str]:
    clean_line = clean_line.strip()
    if not clean_line:
        return None
    return clean_line[-1]


def _finals_of_char(ch: str) -> Optional[str]:
    """
    取单字拼音韵母（简化）。
    多音字默认取 pypinyin 的第一个读音。
    """
    if not ch:
        return None
    py = pinyin(ch, style=Style.FINALS, strict=False)
    if not py or not py[0] or not py[0][0]:
        return None
    return py[0][0]


@dataclass
class RhymeResult:
    ok: bool
    score: float
    finals_2: Optional[str]
    finals_4: Optional[str]
    last_2: Optional[str]
    last_4: Optional[str]
    details: str


def check_qijue7_rhyme(text: str) -> RhymeResult:
    """
    七言绝句（简化押韵）：
    - 第 2 句、 第 4 句句末字韵母一致视为押韵
    """
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

    line2 = lines_clean[1]
    line4 = lines_clean[3]
    last2 = _last_char(line2)
    last4 = _last_char(line4)

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

    ok = (f2 == f4)
    return RhymeResult(
        ok=ok,
        score=1.0 if ok else 0.0,
        finals_2=f2,
        finals_4=f4,
        last_2=last2,
        last_4=last4,
        details="OK" if ok else f"Rhyme mismatch: line2({last2}:{f2}) vs line4({last4}:{f4})",
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