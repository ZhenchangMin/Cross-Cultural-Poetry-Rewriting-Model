# -*- coding: utf-8 -*-
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Any

from .meter import check_qijue7
from .rhyme import check_qijue7_rhyme


@dataclass
class ScoreResult:
    ok: bool
    total: float
    meter_score: float
    rhyme_score: float
    details: Dict[str, Any]


def score_qijue7(text: str, w_meter: float = 0.7, w_rhyme: float = 0.3) -> ScoreResult:
    meter = check_qijue7(text)
    rhyme = check_qijue7_rhyme(text, mode = rhyme_mode)

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


def as_dict(res: ScoreResult) -> Dict[str, Any]:
    return {
        "ok": res.ok,
        "total": res.total,
        "meter_score": res.meter_score,
        "rhyme_score": res.rhyme_score,
        "details": res.details,
    }