# -*- coding: utf-8 -*-
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import List, Dict, Any

# 常见中文/英文标点与空白
_PUNCT_RE = re.compile(r"[，。！？；：、,.!?;:\s\"'“”‘’（）()\[\]{}《》<>…—\-]+")


def _clean_line(line: str) -> str:
    """Remove punctuation and spaces, keep only remaining chars."""
    return re.sub(_PUNCT_RE, "", line.strip())


def clean_lines(text: str) -> List[str]:
    """Split text into non-empty lines, each stripped of punctuation."""
    return [_clean_line(ln) for ln in text.splitlines() if ln.strip()]


@dataclass
class MeterResult:
    ok: bool
    score: float
    lines_raw: List[str]
    lines_clean: List[str]
    details: str


def check_form(text: str, n_lines: int, n_chars: int) -> MeterResult:
    """
    通用齐言体检查：
    - 共 n_lines 句
    - 每句 n_chars 字（不计标点）
    部分分：句数不符为 0 分；字数不符按每句接近程度打分。
    """
    if not text or not text.strip():
        return MeterResult(False, 0.0, [], [], "Empty text")

    lines_raw = [ln.strip() for ln in text.splitlines() if ln.strip()]
    lines_clean = [_clean_line(ln) for ln in lines_raw]

    # 句数检查
    if len(lines_clean) != n_lines:
        return MeterResult(
            ok=False,
            score=0.0,
            lines_raw=lines_raw,
            lines_clean=lines_clean,
            details=f"Expected {n_lines} lines, got {len(lines_clean)}",
        )

    # 字数检查：每句 n_chars 字
    lens = [len(ln) for ln in lines_clean]
    wrong = [(i + 1, l) for i, l in enumerate(lens) if l != n_chars]
    if wrong:
        # 允许给部分分：按每句接近 n_chars 的程度打分
        # 每句得分 = max(0, 1 - |len-n_chars|/n_chars)
        per = [max(0.0, 1.0 - abs(l - n_chars) / float(n_chars)) for l in lens]
        score = sum(per) / float(n_lines)
        return MeterResult(
            ok=False,
            score=score,
            lines_raw=lines_raw,
            lines_clean=lines_clean,
            details=f"Line length mismatch: {wrong} (clean lengths={lens})",
        )

    return MeterResult(
        ok=True,
        score=1.0,
        lines_raw=lines_raw,
        lines_clean=lines_clean,
        details="OK",
    )


def check_qijue7(text: str) -> MeterResult:
    """七言绝句：4 句，每句 7 字。"""
    return check_form(text, n_lines=4, n_chars=7)


def check_qilv7(text: str) -> MeterResult:
    """七言律诗：8 句，每句 7 字。"""
    return check_form(text, n_lines=8, n_chars=7)


def as_dict(res: MeterResult) -> Dict[str, Any]:
    return {
        "ok": res.ok,
        "score": res.score,
        "lines_raw": res.lines_raw,
        "lines_clean": res.lines_clean,
        "details": res.details,
    }
