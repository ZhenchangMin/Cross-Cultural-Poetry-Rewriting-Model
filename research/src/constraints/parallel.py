# -*- coding: utf-8 -*-
"""对仗（parallelism）检查：七律颔联（3-4句）与颈联（5-6句）。

启发式评分：
1. 同位异字（对仗忌同字）：同位置字不同的比例；
2. 词性对齐（可选，需安装 jieba）：两句分词后词数一致时，
   逐词比较词性首字母（n/v/a/...）的一致比例。
两项平均得总分；jieba 缺失时仅用第 1 项。
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Any, List, Optional, Tuple

from .meter import _clean_line

try:
    import jieba.posseg as pseg  # type: ignore
except ImportError:  # jieba 可选
    pseg = None


@dataclass
class PairResult:
    ok: bool
    score: float
    diff_score: float                  # 同位异字比例
    pos_score: Optional[float]         # 词性对齐比例；None = 不可用
    details: str


def check_pair(line_a: str, line_b: str, threshold: float = 0.6) -> PairResult:
    a = _clean_line(line_a)
    b = _clean_line(line_b)

    if not a or not b:
        return PairResult(False, 0.0, 0.0, None, "Empty line in pair")
    if len(a) != len(b):
        return PairResult(False, 0.0, 0.0, None,
                          f"Length mismatch: {len(a)} vs {len(b)}")

    # 1) 同位异字
    diff = sum(1 for ca, cb in zip(a, b) if ca != cb)
    diff_score = diff / float(len(a))

    # 2) 词性对齐（jieba 可选）
    pos_score: Optional[float] = None
    if pseg is not None:
        wa = list(pseg.cut(a))
        wb = list(pseg.cut(b))
        if len(wa) == len(wb) and len(wa) > 0:
            match = sum(1 for ta, tb in zip(wa, wb)
                        if ta.flag[:1] == tb.flag[:1])
            pos_score = match / float(len(wa))

    score = diff_score if pos_score is None else (diff_score + pos_score) / 2.0
    ok = score >= threshold

    if pos_score is None:
        details = f"diff={diff_score:.2f} (jieba 不可用，仅同位异字)"
    else:
        details = f"diff={diff_score:.2f}, pos={pos_score:.2f}"

    return PairResult(ok=ok, score=score, diff_score=diff_score,
                      pos_score=pos_score, details=details)


@dataclass
class ParallelResult:
    ok: bool
    score: float
    pairs: Dict[str, Any]   # {"颔联": PairResult, "颈联": PairResult}


def check_qilv7_parallelism(text: str, threshold: float = 0.6) -> ParallelResult:
    """检查七律颔联（第3-4句）与颈联（第5-6句）是否对仗。"""
    lines_clean = [_clean_line(ln) for ln in text.splitlines() if ln.strip()]
    if len(lines_clean) < 6:
        return ParallelResult(
            ok=False,
            score=0.0,
            pairs={},
        )

    hanlian = check_pair(lines_clean[2], lines_clean[3], threshold)
    jinglian = check_pair(lines_clean[4], lines_clean[5], threshold)

    score = (hanlian.score + jinglian.score) / 2.0
    return ParallelResult(
        ok=(hanlian.ok and jinglian.ok),
        score=score,
        pairs={
            "颔联": {"ok": hanlian.ok, "score": hanlian.score,
                    "diff_score": hanlian.diff_score, "pos_score": hanlian.pos_score,
                    "details": hanlian.details},
            "颈联": {"ok": jinglian.ok, "score": jinglian.score,
                    "diff_score": jinglian.diff_score, "pos_score": jinglian.pos_score,
                    "details": jinglian.details},
        },
    )


def as_dict(res: ParallelResult) -> Dict[str, Any]:
    return {
        "ok": res.ok,
        "score": res.score,
        "pairs": res.pairs,
    }
