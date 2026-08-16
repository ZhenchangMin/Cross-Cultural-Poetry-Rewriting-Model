# -*- coding: utf-8 -*-
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Any, Optional

from .meter import check_qijue7, check_qilv7
from .rhyme import check_qijue7_rhyme, check_qilv7_rhyme, positions_as_dict
from .parallel import check_qilv7_parallelism, as_dict as parallel_as_dict


@dataclass
class ScoreResult:
    ok: bool
    total: float
    meter_score: float
    rhyme_score: float
    details: Dict[str, Any]


def score_qijue7(text: str, w_meter: float = 0.7, w_rhyme: float = 0.3,
                 rhyme_mode: str = "strict") -> ScoreResult:
    meter = check_qijue7(text)
    rhyme = check_qijue7_rhyme(text, mode=rhyme_mode)

    total = w_meter * meter.score + w_rhyme * rhyme.score
    ok = (meter.ok and rhyme.ok)

    details = {
        "meter": {
            "ok": meter.ok,
            "score": meter.score,
            "details": meter.details,
            "lines_clean": meter.lines_clean,
        },
        "rhyme": {
            "ok": rhyme.ok,
            "score": rhyme.score,
            "details": rhyme.details,
            "line2_last": rhyme.last_2,
            "line2_finals": rhyme.finals_2,
            "line4_last": rhyme.last_4,
            "line4_finals": rhyme.finals_4,
        },
    }

    return ScoreResult(
        ok=ok,
        total=total,
        meter_score=meter.score,
        rhyme_score=rhyme.score,
        details=details,
    )


@dataclass
class QilvScoreResult:
    ok: bool
    total: float
    meter_score: float
    rhyme_score: float
    parallel_score: float
    details: Dict[str, Any]


def score_qilv7(text: str,
                w_meter: float = 0.5,
                w_rhyme: float = 0.3,
                w_parallel: float = 0.2,
                rhyme_mode: str = "strict",
                require_ping: bool = False) -> QilvScoreResult:
    """七律综合评分：格律（8句×7字）+ 押韵（2/4/6/8）+ 对仗（颔/颈联）。"""
    meter = check_qilv7(text)
    rhyme = check_qilv7_rhyme(text, mode=rhyme_mode, require_ping=require_ping)
    parallel = check_qilv7_parallelism(text)

    total = (w_meter * meter.score
             + w_rhyme * rhyme.score
             + w_parallel * parallel.score)
    ok = (meter.ok and rhyme.ok and parallel.ok)

    details = {
        "meter": {
            "ok": meter.ok,
            "score": meter.score,
            "details": meter.details,
            "lines_clean": meter.lines_clean,
        },
        "rhyme": positions_as_dict(rhyme),
        "parallel": parallel_as_dict(parallel),
    }

    return QilvScoreResult(
        ok=ok,
        total=total,
        meter_score=meter.score,
        rhyme_score=rhyme.score,
        parallel_score=parallel.score,
        details=details,
    )


def score_poem(text: str, form: str = "qilv7", **kwargs) -> Dict[str, Any]:
    """按诗体分发评分。form: 'qijue7' | 'qilv7'。"""
    if form == "qijue7":
        return as_dict(score_qijue7(text, **kwargs))
    if form == "qilv7":
        return qilv_as_dict(score_qilv7(text, **kwargs))
    raise ValueError(f"Unknown form: {form}")


def as_dict(res: ScoreResult) -> Dict[str, Any]:
    return {
        "ok": res.ok,
        "total": res.total,
        "meter_score": res.meter_score,
        "rhyme_score": res.rhyme_score,
        "details": res.details,
    }


def qilv_as_dict(res: QilvScoreResult) -> Dict[str, Any]:
    return {
        "ok": res.ok,
        "total": res.total,
        "meter_score": res.meter_score,
        "rhyme_score": res.rhyme_score,
        "parallel_score": res.parallel_score,
        "details": res.details,
    }
